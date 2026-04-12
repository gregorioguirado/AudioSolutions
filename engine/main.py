import io
import logging
import tempfile
import zipfile
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import Response
from translator import translate, UnsupportedConsolePair
from report import generate_report, ReportGenerationError

logger = logging.getLogger(__name__)

app = FastAPI(title="Show File Translator Engine", version="1.0.0")

SUPPORTED_CONSOLES = ["yamaha_cl", "digico_sd"]

OUTPUT_FILENAMES = {
    "digico_sd": "translated.show",
    "yamaha_cl": "translated.cle",
}

MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB


def _safe_header(value: str) -> str:
    """Strip characters that would break HTTP header integrity."""
    return value.replace("\r", "").replace("\n", "")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/consoles")
def list_consoles():
    return {"supported_consoles": SUPPORTED_CONSOLES}


@app.post("/translate")
async def translate_file(
    file: UploadFile = File(...),
    source_console: str = Form(...),
    target_console: str = Form(...),
    user_email: Optional[str] = Form(None),
):
    if source_console not in SUPPORTED_CONSOLES:
        raise HTTPException(status_code=400,
                            detail=f"Unsupported source console: {source_console}")
    if target_console not in SUPPORTED_CONSOLES:
        raise HTTPException(status_code=400,
                            detail=f"Unsupported target console: {target_console}")

    if file.size and file.size > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Upload exceeds 50 MB limit")

    # Save uploaded file to a temp path
    suffix = Path(file.filename).suffix if file.filename else ""
    tmp_path = None
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp_path = Path(tmp.name)
        bytes_written = 0
        while chunk := await file.read(65536):
            bytes_written += len(chunk)
            if bytes_written > MAX_UPLOAD_BYTES:
                tmp_path.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail="Upload exceeds 50 MB limit")
            tmp.write(chunk)

    try:
        result = translate(
            source_file=tmp_path,
            source_console=source_console,
            target_console=target_console,
        )
        source_filename = file.filename or "unknown"
        report_pdf = generate_report(
            result=result,
            source_console=source_console,
            target_console=target_console,
            source_filename=source_filename,
            user_email=user_email or "",
        )
    except UnsupportedConsolePair as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ReportGenerationError as e:
        logger.exception("Report generation failure")
        raise HTTPException(status_code=500, detail="Report generation failed.")
    except Exception as e:
        logger.exception("Unexpected translation failure")
        raise HTTPException(status_code=500, detail="An unexpected error occurred during translation.")
    finally:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)

    # Return output file + report as a ZIP bundle
    bundle = io.BytesIO()
    with zipfile.ZipFile(bundle, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(OUTPUT_FILENAMES[target_console], result.output_bytes)
        zf.writestr("translation_report.pdf", report_pdf)

    return Response(
        content=bundle.getvalue(),
        media_type="application/zip",
        headers={
            "Content-Disposition": "attachment; filename=translation_bundle.zip",
            "X-Channel-Count": str(result.channel_count),
            "X-Translated": _safe_header(",".join(result.translated_parameters)),
            "X-Dropped": _safe_header(",".join(result.dropped_parameters)),
        },
    )
