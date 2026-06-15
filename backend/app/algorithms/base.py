from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel

from app.models.patient import Patient


class PlanningState(BaseModel):
    current_time: float
    waiting_patients: list[Patient]
    resource_availability: dict[str, int]
    random_seed: int = 0


class PlanningAlgorithm(ABC):
    name: str

    @abstractmethod
    def plan(self, state: PlanningState) -> list[Patient]:
        raise NotImplementedError

    def planning_time_penalty_minutes(self) -> float:
        return 0.0
