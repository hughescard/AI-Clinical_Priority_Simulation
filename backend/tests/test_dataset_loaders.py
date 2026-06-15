from pathlib import Path

import pytest

from app.data.mietic_loader import MIETICLoader
from app.data.mimic_iv_ed_loader import MIMICIVEDLoader

ROOT = Path(__file__).resolve().parents[2]


def test_mimic_sample_csv_loads_correctly() -> None:
    records = MIMICIVEDLoader().load(ROOT / "data" / "sample" / "mimic_iv_ed_sample.csv")
    assert len(records) == 4
    assert records[0].external_id == "1001"
    assert records[0].chief_complaint == "Chest pain"
    assert records[0].structured_acuity == 2


def test_mietic_sample_csv_loads_correctly() -> None:
    records = MIETICLoader().load(ROOT / "data" / "sample" / "mietic_sample.csv")
    assert len(records) == 3
    assert records[0].external_id == "M-001"
    assert "severe bleeding" in records[0].clinical_description.lower()


def test_missing_chief_complaint_fails_clearly(tmp_path: Path) -> None:
    csv_path = tmp_path / "broken_mimic.csv"
    csv_path.write_text("stay_id,temperature\n1001,37.0\n", encoding="utf-8")
    with pytest.raises(ValueError, match="chief complaint"):
        MIMICIVEDLoader().load(csv_path)
