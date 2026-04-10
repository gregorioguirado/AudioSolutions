import zipfile
import io
import pytest
from lxml import etree
from parsers.digico_sd import parse_digico_sd
from writers.yamaha_cl import write_yamaha_cl

def _get_xml_root(result_bytes: bytes) -> etree._Element:
    buf = io.BytesIO(result_bytes)
    with zipfile.ZipFile(buf) as zf:
        xml_name = next(n for n in zf.namelist() if n.endswith(".xml"))
        return etree.fromstring(zf.read(xml_name))

def test_write_returns_bytes(digico_sd12_fixture):
    show = parse_digico_sd(digico_sd12_fixture)
    result = write_yamaha_cl(show)
    assert isinstance(result, bytes)

def test_write_is_valid_zip(digico_sd12_fixture):
    show = parse_digico_sd(digico_sd12_fixture)
    result = write_yamaha_cl(show)
    buf = io.BytesIO(result)
    assert zipfile.is_zipfile(buf)

def test_write_zip_contains_xml(digico_sd12_fixture):
    show = parse_digico_sd(digico_sd12_fixture)
    result = write_yamaha_cl(show)
    buf = io.BytesIO(result)
    with zipfile.ZipFile(buf) as zf:
        xml_files = [n for n in zf.namelist() if n.endswith(".xml")]
    assert len(xml_files) == 1

def test_write_channel_name(digico_sd12_fixture):
    show = parse_digico_sd(digico_sd12_fixture)
    result = write_yamaha_cl(show)
    root = _get_xml_root(result)
    first = root.find(".//Channel[@channelNo='1']")
    assert first.findtext("Name") == "KICK"

def test_write_channel_color(digico_sd12_fixture):
    show = parse_digico_sd(digico_sd12_fixture)
    result = write_yamaha_cl(show)
    root = _get_xml_root(result)
    first = root.find(".//Channel[@channelNo='1']")
    assert first.findtext("Color") == "RED"

def test_write_hpf(digico_sd12_fixture):
    show = parse_digico_sd(digico_sd12_fixture)
    result = write_yamaha_cl(show)
    root = _get_xml_root(result)
    first = root.find(".//Channel[@channelNo='1']")
    hpf = first.find("HPF")
    assert hpf.findtext("On") == "true"
    assert float(hpf.findtext("Freq")) == 80.0

def test_write_eq_bands(digico_sd12_fixture):
    show = parse_digico_sd(digico_sd12_fixture)
    result = write_yamaha_cl(show)
    root = _get_xml_root(result)
    first = root.find(".//Channel[@channelNo='1']")
    bands = first.findall(".//Band")
    assert len(bands) == 2
    assert float(bands[0].findtext("Freq")) == 100.0
