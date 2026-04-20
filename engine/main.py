import io
import logging
import struct
import tempfile
import zipfile
import zlib
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import Response
from translator import translate, UnsupportedConsolePair
from report import generate_report, ReportGenerationError

logger = logging.getLogger(__name__)

app = FastAPI(title="Show File Translator Engine", version="1.0.0")

SUPPORTED_CONSOLES = [
    "yamaha_cl", "yamaha_cl_binary", "yamaha_ql",
    "yamaha_tf", "yamaha_dm7", "yamaha_rivage",
    "digico_sd",
]

OUTPUT_FILENAMES = {
    "digico_sd": "translated.show",
    "yamaha_cl": "translated.cle",
    "yamaha_cl_binary": "translated.clf",
    "yamaha_ql": "translated.clf",
    "yamaha_tf": "translated.tff",
    "yamaha_rivage": "translated.RIVAGEPM",
    "yamaha_dm7": "translated.dm7f",
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
        if not result.parse_gate_passed:
            raise HTTPException(
                status_code=422,
                detail="Translation produced an unreadable output file. The file cannot be safely downloaded."
            )
        source_filename = file.filename or "unknown"
        report_pdf = generate_report(
            result=result,
            source_console=source_console,
            target_console=target_console,
            source_filename=source_filename,
            user_email=user_email or "",
        )
    except HTTPException:
        raise
    except UnsupportedConsolePair as e:
        raise HTTPException(status_code=400, detail=str(e))
    except (ValueError, struct.error, zlib.error) as e:
        raise HTTPException(status_code=422, detail=f"Could not parse show file: {e}")
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
    output_filename = OUTPUT_FILENAMES.get(target_console, "translated.bin")
    bundle = io.BytesIO()
    with zipfile.ZipFile(bundle, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(output_filename, result.output_bytes)
        zf.writestr("translation_report.pdf", report_pdf)

    headers = {
        "Content-Disposition": "attachment; filename=translation_bundle.zip",
        "X-Channel-Count": str(result.channel_count),
        "X-Translated": _safe_header(",".join(result.translated_parameters)),
        "X-Dropped": _safe_header(",".join(result.dropped_parameters)),
        "X-Parse-Gate-Passed": str(result.parse_gate_passed).lower(),
    }
    if result.fidelity_score is not None:
        headers["X-Fidelity-Names"] = str(round(result.fidelity_score.names, 1))
        headers["X-Fidelity-HPF"] = str(round(result.fidelity_score.hpf, 1))
        headers["X-Fidelity-EQ"] = str(round(result.fidelity_score.eq, 1))
        headers["X-Fidelity-Gate"] = str(round(result.fidelity_score.gate, 1))
        headers["X-Fidelity-Compressor"] = str(round(result.fidelity_score.compressor, 1))
        headers["X-Fidelity-MixBuses"] = str(round(result.fidelity_score.mix_buses, 1))
        headers["X-Fidelity-VCAs"] = str(round(result.fidelity_score.vcas, 1))
        headers["X-Fidelity-Overall"] = str(round(result.fidelity_score.overall, 1))

    return Response(
        content=bundle.getvalue(),
        media_type="application/zip",
        headers=headers,
    )
