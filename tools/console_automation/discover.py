"""
discover.py — Print every UIA-accessible control in a running desktop app.

Usage:
    python tools/console_automation/discover.py --app "CL Editor"
    python tools/console_automation/discover.py --app "DM7 Editor"
    python tools/console_automation/discover.py --pid 12345

The output tells you what pywinauto can see and interact with.
Share the output so we can write targeted automation scripts.
"""
import argparse
import sys

try:
    from pywinauto.application import Application
    from pywinauto import Desktop
except ImportError:
    print("ERROR: pywinauto not installed. Run: pip install pywinauto")
    sys.exit(1)


def discover_by_title(title_fragment: str):
    desktop = Desktop(backend="uia")
    windows = desktop.windows()
    matches = [w for w in windows if title_fragment.lower() in w.window_text().lower()]

    if not matches:
        print(f"No windows found containing '{title_fragment}'")
        print("\nAll open windows:")
        for w in windows:
            t = w.window_text()
            if t.strip():
                print(f"  [{w.process_id()}] {t!r}")
        return

    for win in matches:
        print(f"\n{'='*60}")
        print(f"Window: {win.window_text()!r}  PID={win.process_id()}")
        print('='*60)
        try:
            app = Application(backend="uia").connect(handle=win.handle)
            top = app.window(handle=win.handle)
            top.print_control_identifiers(depth=6)
        except Exception as e:
            print(f"  UIA failed ({e}), trying win32 backend...")
            try:
                app = Application(backend="win32").connect(handle=win.handle)
                top = app.window(handle=win.handle)
                top.print_control_identifiers(depth=6)
            except Exception as e2:
                print(f"  win32 also failed: {e2}")


def discover_by_pid(pid: int):
    try:
        app = Application(backend="uia").connect(process=pid)
        for win in app.windows():
            print(f"\n{'='*60}")
            print(f"Window: {win.window_text()!r}")
            print('='*60)
            win.print_control_identifiers(depth=6)
    except Exception as e:
        print(f"Failed to connect to PID {pid}: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Discover UIA controls in a running app")
    parser.add_argument("--app", help="Window title fragment to match (e.g. 'CL Editor')")
    parser.add_argument("--pid", type=int, help="Process ID to connect to")
    args = parser.parse_args()

    if args.pid:
        discover_by_pid(args.pid)
    elif args.app:
        discover_by_title(args.app)
    else:
        parser.print_help()
