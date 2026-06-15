from __future__ import annotations

import csv
from pathlib import Path

from app.data.base import DatasetLoader
from app.data.schemas import DatasetPatientRecord


def read_csv_rows(path: str | Path) -> list[dict[str, str]]:
    csv_path = Path(path)
    if not csv_path.exists():
        raise FileNotFoundError(f"Dataset file not found: {csv_path}")
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [dict(row) for row in reader]


def first_present_value(row: dict[str, str], candidates: list[str]) -> str | None:
    lowered = {key.lower(): value for key, value in row.items()}
    for candidate in candidates:
        value = lowered.get(candidate.lower())
        if value is not None and str(value).strip() != "":
            return str(value).strip()
    return None


def parse_float(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def parse_int(value: str | None) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except ValueError:
        return None


class ConfigurableCSVLoader(DatasetLoader):
    def __init__(self, source_name: str, mapping: dict[str, list[str]]) -> None:
        self.source_name = source_name
        self.mapping = mapping

    def load(self, path: str | Path) -> list[DatasetPatientRecord]:
        rows = read_csv_rows(path)
        records: list[DatasetPatientRecord] = []
        for index, row in enumerate(rows):
            chief_complaint = first_present_value(row, self.mapping["chief_complaint"])
            clinical_text = first_present_value(row, self.mapping["clinical_description"])
            if not chief_complaint and not clinical_text:
                raise ValueError("Configurable CSV loader requires chief complaint or clinical description.")
            records.append(
                DatasetPatientRecord(
                    external_id=first_present_value(row, self.mapping["external_id"]) or f"{self.source_name}-{index + 1}",
                    age=parse_int(first_present_value(row, self.mapping.get("age", []))),
                    arrival_time=parse_int(first_present_value(row, self.mapping.get("arrival_time", []))),
                    chief_complaint=chief_complaint or clinical_text or "",
                    clinical_description=clinical_text or chief_complaint or "",
                    structured_acuity=parse_int(first_present_value(row, self.mapping.get("structured_acuity", []))),
                    temperature=parse_float(first_present_value(row, self.mapping.get("temperature", []))),
                    heart_rate=parse_float(first_present_value(row, self.mapping.get("heart_rate", []))),
                    respiratory_rate=parse_float(first_present_value(row, self.mapping.get("respiratory_rate", []))),
                    oxygen_saturation=parse_float(first_present_value(row, self.mapping.get("oxygen_saturation", []))),
                    systolic_bp=parse_float(first_present_value(row, self.mapping.get("systolic_bp", []))),
                    diastolic_bp=parse_float(first_present_value(row, self.mapping.get("diastolic_bp", []))),
                    pain=first_present_value(row, self.mapping.get("pain", [])),
                    source_dataset=self.source_name,
                )
            )
        return records
