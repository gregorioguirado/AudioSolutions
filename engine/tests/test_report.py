import pytest
from report import generate_report
from translator import TranslationResult

def _make_result() -> TranslationResult:
    return TranslationResult(
        output_bytes=b"fake",
        channel_count=24,
        translated_parameters=["channel_names", "hpf", "eq_bands"],
        approximated_parameters=["eq_band_types"],
        dropped_parameters=["yamaha_premium_rack"],
    )

def test_generate_report_returns_bytes():
    result = _make_result()
    pdf_bytes = generate_report(
        result=result,
        source_console="yamaha_cl",
        target_console="digico_sd",
    )
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0

def test_generate_report_is_pdf():
    result = _make_result()
    pdf_bytes = generate_report(
        result=result,
        source_console="yamaha_cl",
        target_console="digico_sd",
    )
    # PDF files start with %PDF
    assert pdf_bytes[:4] == b"%PDF"
