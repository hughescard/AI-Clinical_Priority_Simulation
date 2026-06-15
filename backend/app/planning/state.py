from __future__ import annotations

from dataclasses import dataclass

from app.models.patient import Patient


@dataclass(frozen=True)
class SearchPlanningState:
    current_time: float
    ordered_patient_ids: tuple[str, ...]
    remaining_patient_ids: tuple[str, ...]
    accumulated_cost: float
    available_resources: tuple[tuple[str, int], ...]
    projected_time: float

    @classmethod
    def initial(
        cls,
        *,
        current_time: float,
        candidate_patients: list[Patient],
        available_resources: dict[str, int],
    ) -> "SearchPlanningState":
        return cls(
            current_time=current_time,
            ordered_patient_ids=(),
            remaining_patient_ids=tuple(patient.patient_id for patient in candidate_patients),
            accumulated_cost=0.0,
            available_resources=tuple(sorted(available_resources.items())),
            projected_time=current_time,
        )

    @property
    def available_resources_map(self) -> dict[str, int]:
        return dict(self.available_resources)

    def can_assign(self, patient: Patient) -> bool:
        remaining = self.available_resources_map
        requirements: dict[str, int] = {}
        for resource in patient.required_resources:
            requirements[resource] = requirements.get(resource, 0) + 1
        return all(remaining.get(resource, 0) >= needed for resource, needed in requirements.items())

    def select(self, patient: Patient, incremental_cost: float) -> "SearchPlanningState":
        remaining_resources = self.available_resources_map
        for resource in patient.required_resources:
            remaining_resources[resource] = remaining_resources.get(resource, 0) - 1
        return SearchPlanningState(
            current_time=self.current_time,
            ordered_patient_ids=self.ordered_patient_ids + (patient.patient_id,),
            remaining_patient_ids=tuple(
                patient_id for patient_id in self.remaining_patient_ids if patient_id != patient.patient_id
            ),
            accumulated_cost=self.accumulated_cost + incremental_cost,
            available_resources=tuple(sorted(remaining_resources.items())),
            projected_time=self.projected_time + patient.estimated_service_time,
        )

    @property
    def signature(self) -> tuple[tuple[str, ...], tuple[str, ...], tuple[tuple[str, int], ...], int]:
        return (
            self.ordered_patient_ids,
            self.remaining_patient_ids,
            self.available_resources,
            self.projected_time,
        )
