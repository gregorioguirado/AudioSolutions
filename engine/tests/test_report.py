import pytest
from report import generate_report
from translator import TranslationResult
from models.universal import Channel, ChannelColor, EQBand, EQBandType, Gate, Compressor


def _make_channel(id: int, name: str, hpf_enabled=False, hpf_freq=80.0) -> Channel:
    return Channel(
        id=id,
        name=name,
        color=ChannelColor.WHITE,
        input_patch=id,
        hpf_frequency=hpf_freq,
        hpf_enabled=hpf_enabled,
    )


def _make_result(channels=None) -> TranslationResult:
    chs = channels or []
    return TranslationResult(
        output_bytes=b"fake",
        channel_count=len(chs) or 24,
        translated_parameters=["channel_names", "hpf", "eq_bands"],
        approximated_parameters=["eq_band_types"],
        dropped_parameters=["yamaha_premium_rack"],
        channels=chs,
    )


def test_generate_report_returns_bytes():
    result = _make_result()
    pdf = generate_report(result, "yamaha_cl", "digico_sd")
    assert isinstance(pdf, bytes)
    assert len(pdf) > 0


def test_generate_report_is_pdf():
    result = _make_result()
    pdf = generate_report(result, "yamaha_cl", "digico_sd")
    assert pdf[:4] == b"%PDF"


def test_generate_report_accepts_metadata():
    result = _make_result()
    pdf = generate_report(
        result,
        "yamaha_cl",
        "digico_sd",
        source_filename="Example 1 CL5.CLF",
        user_email="engineer@example.com",
    )
    assert pdf[:4] == b"%PDF"


def test_generate_report_with_active_channels():
    chs = [
        _make_channel(1, "KICK", hpf_enabled=True, hpf_freq=80.0),
        _make_channel(2, "SNARE TOP", hpf_enabled=True, hpf_freq=120.0),
        _make_channel(3, "CH 3"),   # default name → treated as default
    ]
    chs[0].eq_bands = [EQBand(frequency=200, gain=3.0, q=1.0, band_type=EQBandType.PEAK)]
    result = _make_result(channels=chs)
    pdf = generate_report(
        result,
        "yamaha_cl",
        "digico_sd",
        source_filename="My Show.CLF",
        user_email="foh@venue.com",
    )
    assert pdf[:4] == b"%PDF"


def test_generate_report_with_empty_sections():
    result = TranslationResult(
        output_bytes=b"fake",
        channel_count=2,
        translated_parameters=["channel_names"],
        approximated_parameters=[],
        dropped_parameters=[],
        channels=[],
    )
    pdf = generate_report(result, "yamaha_cl", "digico_sd")
    assert pdf[:4] == b"%PDF"


def test_generate_report_with_unknown_console():
    result = _make_result()
    pdf = generate_report(result, "ssl_live", "allen_heath_dlive")
    assert pdf[:4] == b"%PDF"


def test_generate_report_all_default_channels():
    """All channels are default — should show 0 active channels and a footnote."""
    chs = [_make_channel(i, f"CH {i}") for i in range(1, 11)]
    result = _make_result(channels=chs)
    pdf = generate_report(result, "yamaha_cl", "digico_sd")
    assert pdf[:4] == b"%PDF"
