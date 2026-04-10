import io
import tempfile
import zipfile
from pathlib import Path
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import Response
from translator import translate, UnsupportedConsolePair
from report import generate_report, ReportGenerationError

app = FastAPI(title="Show File Translator Engine", version="1.0.0")

SUPPORTED_CONSOLES = ["yamaha_cl", "digico_sd"]

OUTPUT_FILENAMES = {
    "digico_sd": "translated.show",
    "yamaha_cl": "translated.cle",
}


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
):
    if source_console not in SUPPORTED_CONSOLES:
        raise HTTPException(status_code=400,
                            detail=f"Unsupported source console: {source_console}")
    if target_console not in SUPPORTED_CONSOLES:
        raise HTTPException(status_code=400,
                            detail=f"Unsupported target console: {target_console}")

    # Save uploaded file to a temp path
    suffix = Path(file.filename).suffix if file.filename else ""
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = Path(tmp.name)

    try:
        result = translate(
            source_file=tmp_path,
            source_console=source_console,
            target_console=target_console,
        )
        report_pdf = generate_report(
            result=result,
            source_console=source_console,
            target_console=target_console,
        )
    except UnsupportedConsolePair as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ReportGenerationError as e:
        raise HTTPException(status_code=500, detail=f"Report generation failed: {e}")
    except Exception as e:
        raise HTTPException(status_code=500,
                            detail=f"Translation failed: {str(e)}")
    finally:
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
            "X-Translated": ",".join(result.translated_parameters),
            "X-Dropped": ",".join(result.dropped_parameters),
        },
    )
