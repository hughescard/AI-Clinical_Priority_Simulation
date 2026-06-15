from __future__ import annotations

from pathlib import Path

from app.data.base import DatasetLoader
from app.data.csv_loader import first_present_value, parse_float, parse_int, read_csv_rows
from app.data.schemas import DatasetPatientRecord


class MIMICIVEDLoader(DatasetLoader):
    source_name = "mimic_iv_ed"

    def load(self, path: str | Path) -> list[DatasetPatientRecord]:
        rows = read_csv_rows(path)
        records: list[DatasetPatientRecord] = []
        for index, row in enumerate(rows):
            chief_complaint = first_present_value(row, ["chiefcomplaint", "chief_complaint"])
            if not chief_complaint:
                raise ValueError("MIMIC-IV-ED dataset requires a chief complaint column.")
            external_id = (
                first_present_value(row, ["stay_id"])
                or first_present_value(row, ["subject_id"])
                or f"mimic-{index + 1}"
            )
            clinical_parts = [chief_complaint]
            for label, value in (
                ("temperature", first_present_value(row, ["temperature"])),
                ("heart rate", first_present_value(row, ["heartrate", "heart_rate"])),
                ("respiratory rate", first_present_value(row, ["resprate", "respiratory_rate"])),
                ("oxygen saturation", first_present_value(row, ["o2sat", "oxygen_saturation"])),
                ("systolic bp", first_present_value(row, ["sbp", "systolic_bp"])),
                ("diastolic bp", first_present_value(row, ["dbp", "diastolic_bp"])),
                ("pain", first_present_value(row, ["pain"])),
            ):
                if value:
                    clinical_parts.append(f"{label}: {value}")
            records.append(
                DatasetPatientRecord(
                    external_id=external_id,
                    age=parse_int(first_present_value(row, ["anchor_age", "age"])),
                    arrival_time=parse_int(first_present_value(row, ["intime", "arrival_time", "arrival_minute"])),
                    chief_complaint=chief_complaint,
                    clinical_description="; ".join(clinical_parts),
                    structured_acuity=parse_int(first_present_value(row, ["acuity", "triage_level", "esi"])),
                    temperature=parse_float(first_present_value(row, ["temperature"])),
                    heart_rate=parse_float(first_present_value(row, ["heartrate", "heart_rate"])),
                    respiratory_rate=parse_float(first_present_value(row, ["resprate", "respiratory_rate"])),
                    oxygen_saturation=parse_float(first_present_value(row, ["o2sat", "oxygen_saturation"])),
                    systolic_bp=parse_float(first_present_value(row, ["sbp", "systolic_bp"])),
                    diastolic_bp=parse_float(first_present_value(row, ["dbp", "diastolic_bp"])),
                    pain=first_present_value(row, ["pain"]),
                    source_dataset=self.source_name,
                )
            )
        return records

