from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from app.data.schemas import DatasetPatientRecord


class DatasetLoader(ABC):
    source_name: str

    @abstractmethod
    def load(self, path: str | Path) -> list[DatasetPatientRecord]:
        raise NotImplementedError

