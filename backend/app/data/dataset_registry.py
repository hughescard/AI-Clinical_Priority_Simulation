from __future__ import annotations

import os
from pathlib import Path

from app.data.base import DatasetLoader
from app.data.mietic_loader import MIETICLoader
from app.data.mimic_iv_ed_loader import MIMICIVEDLoader
from app.data.schemas import DatasetPatientRecord


_ROOT = Path(__file__).resolve().parents[3]
_SAMPLE_DIR = _ROOT / "data" / "sample"


def list_data_sources() -> tuple[str, ...]:
    return ("synthetic", "mimic_iv_ed_sample", "mietic_sample", "mimic_iv_ed", "mietic")


def get_data_source_label(data_source: str) -> str:
    labels = {
        "synthetic": "Synthetic Scenario Generator",
        "mimic_iv_ed_sample": "MIMIC-IV-ED Sample",
        "mietic_sample": "MIETIC Sample",
        "mimic_iv_ed": "MIMIC-IV-ED Local CSV",
        "mietic": "MIETIC Local CSV",
    }
    if data_source not in labels:
        raise ValueError(f"Unsupported data source: {data_source}")
    return labels[data_source]


def get_dataset_records(data_source: str) -> list[DatasetPatientRecord]:
    loader, path = _resolve_loader_and_path(data_source)
    return loader.load(path)


def _resolve_loader_and_path(data_source: str) -> tuple[DatasetLoader, Path]:
    if data_source == "mimic_iv_ed_sample":
        return MIMICIVEDLoader(), _SAMPLE_DIR / "mimic_iv_ed_sample.csv"
    if data_source == "mietic_sample":
        return MIETICLoader(), _SAMPLE_DIR / "mietic_sample.csv"
    if data_source == "mimic_iv_ed":
        path = os.getenv("MIMIC_IV_ED_TRIAGE_CSV")
        if not path:
            raise ValueError("MIMIC_IV_ED_TRIAGE_CSV is not configured for data_source='mimic_iv_ed'.")
        return MIMICIVEDLoader(), Path(path)
    if data_source == "mietic":
        path = os.getenv("MIETIC_CSV")
        if not path:
            raise ValueError("MIETIC_CSV is not configured for data_source='mietic'.")
        return MIETICLoader(), Path(path)
    raise ValueError(f"Unsupported data source: {data_source}")
