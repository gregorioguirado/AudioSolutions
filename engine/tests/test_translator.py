import pytest
from pathlib import Path
from translator import translate, TranslationResult, UnsupportedConsolePair

def test_yamaha_to_digico(yamaha_cl5_fixture):
    result = translate(
        source_file=yamaha_cl5_fixture,
        source_console="yamaha_cl",
        target_console="digico_sd",
    )
    assert isinstance(result, TranslationResult)
    assert result.output_bytes is not None
    assert len(result.output_bytes) > 0

def test_digico_to_yamaha(digico_sd12_fixture):
    result = translate(
        source_file=digico_sd12_fixture,
        source_console="digico_sd",
        target_console="yamaha_cl",
    )
    assert isinstance(result, TranslationResult)
    assert result.output_bytes is not None

def test_translation_result_has_channel_count(yamaha_cl5_fixture):
    result = translate(
        source_file=yamaha_cl5_fixture,
        source_console="yamaha_cl",
        target_console="digico_sd",
    )
    assert result.channel_count == 2

def test_translation_result_has_translated_parameters(yamaha_cl5_fixture):
    result = translate(
        source_file=yamaha_cl5_fixture,
        source_console="yamaha_cl",
        target_console="digico_sd",
    )
    assert len(result.translated_parameters) > 0
    assert "channel_names" in result.translated_parameters

def test_unsupported_pair_raises(yamaha_cl5_fixture):
    with pytest.raises(UnsupportedConsolePair):
        translate(
            source_file=yamaha_cl5_fixture,
            source_console="yamaha_cl",
            target_console="ssl_live",
        )

def test_same_console_raises(yamaha_cl5_fixture):
    with pytest.raises(UnsupportedConsolePair):
        translate(
            source_file=yamaha_cl5_fixture,
            source_console="yamaha_cl",
            target_console="yamaha_cl",
        )

def test_tf_to_yamaha_cl_binary():
    samples_dir = Path(__file__).parent.parent.parent / "samples"
    result = translate(
        source_file=samples_dir / "DOM CASMURRO 2.tff",
        source_console="yamaha_tf",
        target_console="yamaha_cl_binary",
    )
    assert isinstance(result, TranslationResult)
    assert result.output_bytes is not None
    assert len(result.output_bytes) > 0
    assert result.channel_count > 0
    assert result.parse_gate_passed is True

def test_tf_to_digico():
    samples_dir = Path(__file__).parent.parent.parent / "samples"
    result = translate(
        source_file=samples_dir / "DOM CASMURRO 2.tff",
        source_console="yamaha_tf",
        target_console="digico_sd",
    )
    assert isinstance(result, TranslationResult)
    assert result.output_bytes is not None
    assert len(result.output_bytes) > 0
    assert result.channel_count > 0
    assert result.parse_gate_passed is True

def test_dm7_to_yamaha_cl_binary():
    samples_dir = Path(__file__).parent.parent.parent / "samples"
    result = translate(
        source_file=samples_dir / "dm7_named.dm7f",
        source_console="yamaha_dm7",
        target_console="yamaha_cl_binary",
    )
    assert isinstance(result, TranslationResult)
    assert result.output_bytes is not None
    assert len(result.output_bytes) > 0
    assert result.channel_count > 0
    assert result.parse_gate_passed is True

def test_dm7_to_digico():
    samples_dir = Path(__file__).parent.parent.parent / "samples"
    result = translate(
        source_file=samples_dir / "dm7_named.dm7f",
        source_console="yamaha_dm7",
        target_console="digico_sd",
    )
    assert isinstance(result, TranslationResult)
    assert result.output_bytes is not None
    assert len(result.output_bytes) > 0
    assert result.channel_count > 0
    assert result.parse_gate_passed is True

def test_rivage_to_yamaha_cl_binary():
    samples_dir = Path(__file__).parent.parent.parent / "samples"
    result = translate(
        source_file=samples_dir / "RIVAGE EMI 21.3.RIVAGEPM",
        source_console="yamaha_rivage",
        target_console="yamaha_cl_binary",
    )
    assert isinstance(result, TranslationResult)
    assert result.output_bytes is not None
    assert len(result.output_bytes) > 0
    assert result.channel_count > 0
    assert result.parse_gate_passed is True

def test_rivage_to_digico():
    samples_dir = Path(__file__).parent.parent.parent / "samples"
    result = translate(
        source_file=samples_dir / "RIVAGE EMI 21.3.RIVAGEPM",
        source_console="yamaha_rivage",
        target_console="digico_sd",
    )
    assert isinstance(result, TranslationResult)
    assert result.output_bytes is not None
    assert len(result.output_bytes) > 0
    assert result.channel_count > 0
    assert result.parse_gate_passed is True
