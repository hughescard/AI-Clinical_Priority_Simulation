from __future__ import annotations

from pathlib import Path

from app.data.base import DatasetLoader
from app.data.csv_loader import first_present_value, parse_float, parse_int, read_csv_rows
from app.data.schemas import DatasetPatientRecord


class MIETICLoader(DatasetLoader):
    source_name = "mietic"

    def load(self, path: str | Path) -> list[DatasetPatientRecord]:
        rows = read_csv_rows(path)
        records: list[DatasetPatientRecord] = []
        for index, row in enumerate(rows):
            chief_complaint = first_present_value(row, ["chief_complaint", "chiefcomplaint", "complaint"])
            extra_text = first_present_value(row, ["clinical_text", "history", "medical_history"])
            if not chief_complaint and not extra_text:
                raise ValueError("MIETIC dataset requires chief complaint or clinical text.")
            complaint_text = chief_complaint or extra_text or ""
            external_id = first_present_value(row, ["case_id", "id"]) or f"mietic-{index + 1}"
            clinical_parts = [part for part in [complaint_text, extra_text] if part]
            for label, value in (
                ("temperature", first_present_value(row, ["temperature"])),
                ("heart rate", first_present_value(row, ["heart_rate", "heartrate"])),
                ("respiratory rate", first_present_value(row, ["respiratory_rate", "resprate"])),
                ("oxygen saturation", first_present_value(row, ["oxygen_saturation", "o2sat"])),
                ("systolic bp", first_present_value(row, ["systolic_bp", "sbp"])),
                ("diastolic bp", first_present_value(row, ["diastolic_bp", "dbp"])),
                ("pain", first_present_value(row, ["pain"])),
            ):
                if value:
                    clinical_parts.append(f"{label}: {value}")
            records.append(
                DatasetPatientRecord(
                    external_id=external_id,
                    age=parse_int(first_present_value(row, ["age"])),
                    arrival_time=parse_int(first_present_value(row, ["arrival_time", "arrival_minute"])),
                    chief_complaint=complaint_text,
                    clinical_description="; ".join(dict.fromkeys(clinical_parts)),
                    structured_acuity=parse_int(first_present_value(row, ["esi", "triage_level", "acuity"])),
                    temperature=parse_float(first_present_value(row, ["temperature"])),
                    heart_rate=parse_float(first_present_value(row, ["heart_rate", "heartrate"])),
                    respiratory_rate=parse_float(first_present_value(row, ["respiratory_rate", "resprate"])),
                    oxygen_saturation=parse_float(first_present_value(row, ["oxygen_saturation", "o2sat"])),
                    systolic_bp=parse_float(first_present_value(row, ["systolic_bp", "sbp"])),
                    diastolic_bp=parse_float(first_present_value(row, ["diastolic_bp", "dbp"])),
                    pain=first_present_value(row, ["pain"]),
                    source_dataset=self.source_name,
                )
            )
        return records

