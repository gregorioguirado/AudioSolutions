"""Shared pywinauto helpers for editor validation.

Each per-editor driver in this directory subclasses :class:`EditorDriver`
and overrides the ``wait_for_load`` hook if that editor doesn't signal
success in the default way (updating the window title to include the
file name).

Design: favour loud, specific failures over silent auto-recovery. If
the editor isn't installed, we SKIP (not FAIL). If it's installed but
rejects the file, we FAIL with the error dialog's exact text + a
screenshot of the whole desktop.
"""
from __future__ import annotations

import logging
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

try:
    import pywinauto
    from pywinauto.application import Application
    from pywinauto import keyboard
    from PIL import ImageGrab
except ImportError as e:
    raise SystemExit(
        f"pywinauto / Pillow not installed. Run: pip install pywinauto pillow\n"
        f"Original error: {e}"
    )


logger = logging.getLogger("editor_validation")


@dataclass
class EditorConfig:
    name: str                               # e.g. 'yamaha_dm7'
    exe: Optional[str]                      # absolute path to .exe, or None = SKIP
    window_title_prefix: str
    open_shortcut: str = "ctrl+o"
    success_title_contains_filename: bool = True
    launch_timeout_s: int = 30
    open_timeout_s: int = 15


@dataclass
class ValidationResult:
    editor: str
    file_path: str
    status: str                             # 'pass' | 'fail' | 'skipped' | 'error'
    message: str = ""
    screenshot_path: Optional[str] = None
    elapsed_s: float = 0.0


class EditorDriver:
    """Drives one console editor's GUI to open a file and check acceptance."""

    def __init__(self, config: EditorConfig, output_dir: Path):
        self.config = config
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def is_installed(self) -> bool:
        """Heuristic: the configured executable exists on disk."""
        if not self.config.exe:
            return False
        return Path(self.config.exe).exists()

    def validate(self, file_path: Path) -> ValidationResult:
        """Open *file_path* in this editor and report whether it accepted the file."""
        t0 = time.time()
        file_path = Path(file_path).resolve()

        if not self.is_installed():
            return ValidationResult(
                editor=self.config.name,
                file_path=str(file_path),
                status="skipped",
                message=f"editor executable not found at {self.config.exe}",
                elapsed_s=0.0,
            )

        if not file_path.exists():
            return ValidationResult(
                editor=self.config.name,
                file_path=str(file_path),
                status="error",
                message=f"file to validate does not exist: {file_path}",
                elapsed_s=0.0,
            )

        app: Optional[Application] = None
        try:
            logger.info("Launching %s: %s", self.config.name, self.config.exe)
            app = Application(backend="uia").start(
                cmd_line=self.config.exe, timeout=self.config.launch_timeout_s
            )

            # Wait for main window to appear
            main_window = app.top_window()
            main_window.wait("visible", timeout=self.config.launch_timeout_s)
            logger.info("Main window visible: %r", main_window.window_text())

            # Trigger File > Open
            keyboard.send_keys("^o")  # Ctrl+O
            time.sleep(1)

            # Wait for file-open dialog, type path, Enter
            # Use the clipboard would be more reliable for paths with spaces,
            # but direct typing with quotes usually works for Windows Open dialog.
            keyboard.send_keys(str(file_path), with_spaces=True, pause=0.02)
            time.sleep(0.5)
            keyboard.send_keys("{ENTER}")

            # Now wait up to open_timeout_s for either success or a modal dialog.
            result = self._wait_for_load_or_error(app, file_path)
            result.elapsed_s = time.time() - t0
            return result

        except Exception as e:  # noqa: BLE001
            screenshot = self._screenshot(f"exception_{self.config.name}")
            return ValidationResult(
                editor=self.config.name,
                file_path=str(file_path),
                status="error",
                message=f"{type(e).__name__}: {e}",
                screenshot_path=screenshot,
                elapsed_s=time.time() - t0,
            )
        finally:
            if app is not None:
                try:
                    app.kill(soft=False)
                except Exception:  # noqa: BLE001
                    pass

    def _wait_for_load_or_error(self, app: Application, file_path: Path) -> ValidationResult:
        """Poll for either window-title success or an error dialog."""
        deadline = time.time() + self.config.open_timeout_s
        filename = file_path.name
        last_title = ""
        error_dialog_text = None

        while time.time() < deadline:
            # Check for error dialog: any new top-level window with "Error" or the
            # editor's main window *preceded by* a child modal.
            try:
                for win in app.windows():
                    title = win.window_text()
                    if title == last_title:
                        continue
                    last_title = title
                    logger.debug("window seen: %r", title)
                    if self._looks_like_error_dialog(title):
                        # Pull the static text from the dialog as the message
                        try:
                            texts = win.descendants(control_type="Text")
                            error_dialog_text = " | ".join(
                                t.window_text() for t in texts if t.window_text()
                            )
                        except Exception:  # noqa: BLE001
                            error_dialog_text = title
                        screenshot = self._screenshot(f"fail_{self.config.name}")
                        return ValidationResult(
                            editor=self.config.name,
                            file_path=str(file_path),
                            status="fail",
                            message=f"editor dialog: {error_dialog_text}",
                            screenshot_path=screenshot,
                        )
                # Main window title changed to include filename?
                if self.config.success_title_contains_filename:
                    try:
                        main = app.top_window().window_text()
                        if filename.lower() in main.lower() or Path(filename).stem.lower() in main.lower():
                            return ValidationResult(
                                editor=self.config.name,
                                file_path=str(file_path),
                                status="pass",
                                message=f"main window title now: {main!r}",
                            )
                    except Exception:  # noqa: BLE001
                        pass
            except Exception as e:  # noqa: BLE001
                logger.debug("window enumeration error (recoverable): %s", e)
            time.sleep(0.25)

        # Timeout: no error shown, but no success detected either. Screenshot
        # whatever's on screen so a human can tell us which bucket this is.
        screenshot = self._screenshot(f"timeout_{self.config.name}")
        return ValidationResult(
            editor=self.config.name,
            file_path=str(file_path),
            status="fail",
            message=f"timed out after {self.config.open_timeout_s}s without success or error dialog",
            screenshot_path=screenshot,
        )

    def _looks_like_error_dialog(self, title: str) -> bool:
        tl = title.lower()
        return any(k in tl for k in (
            "error", "couldn't access", "cannot access", "warning", "different kinds of data",
            "failed", "invalid", "corrupt", "unsupported",
        ))

    def _screenshot(self, tag: str) -> str:
        path = self.output_dir / f"{tag}_{int(time.time())}.png"
        try:
            img = ImageGrab.grab(all_screens=True)
            img.save(path)
            return str(path)
        except Exception as e:  # noqa: BLE001
            logger.warning("screenshot failed: %s", e)
            return ""


def load_config(path: Path) -> dict[str, EditorConfig]:
    """Parse config.yaml into typed editor configs."""
    try:
        import yaml
    except ImportError:
        raise SystemExit("pyyaml required: pip install pyyaml")
    data = yaml.safe_load(path.read_text())
    out = {}
    for name, cfg in (data.get("editors") or {}).items():
        out[name] = EditorConfig(name=name, **cfg)
    return out


def default_output_dir() -> Path:
    return Path(".tmp/editor_validation").resolve()
