import pytest
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"

@pytest.fixture
def yamaha_cl5_fixture() -> Path:
    return FIXTURES_DIR / "yamaha_cl5_sample.cle"

@pytest.fixture
def digico_sd12_fixture() -> Path:
    return FIXTURES_DIR / "digico_sd12_sample.show"
