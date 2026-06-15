from __future__ import annotations

from app.algorithms.base import PlanningAlgorithm, PlanningState
from app.config import settings
from app.evaluation.metrics import compute_metrics
from app.models.patient import Patient, PatientStatus
from app.models.resources import ResourcePool
from app.models.simulation import PatientTrace, SimulationConfig, SimulationResult, SimulationState, WaitingReasonEvent
from app.simulation.event_queue import EventQueue
from app.simulation.events import Event, EventType
from app.simulation.scenario_generator import ScenarioGenerator


class ClinicalTriageSimulator:
    DISPATCH_TRIGGER_ARRIVAL = "arrival_initial_assessment"
    DISPATCH_TRIGGER_SERVICE_END = "service_end_resource_available"
    DISPATCH_TRIGGER_DETERIORATION = "deterioration_reassessment"
    DISPATCH_TRIGGER_DOCTOR_ROUND = "doctor_round_replan"

    def __init__(self, config: SimulationConfig, algorithm: PlanningAlgorithm) -> None:
        self.config = config
        self.algorithm = algorithm
        self.generator = ScenarioGenerator(
            seed=config.seed,
            data_source=config.data_source,
            base_resource_capacities=config.resource_capacities,
            advanced_config=config.advanced_config,
        )
        self.resource_pool = ResourcePool(capacities=config.resource_capacities)
        self.event_queue = EventQueue()
        self.state = SimulationState()
        self.patients_by_id: dict[str, Patient] = {}
        self._active_doctor_rounds: dict[float, dict] = {}

    def run(self) -> SimulationResult:
        patients, capacities = self.generator.generate(self.config.scenario, self.config.duration_minutes)
        self.resource_pool = ResourcePool(capacities=capacities)
        self.patients_by_id = {patient.patient_id: patient for patient in patients}
        self._schedule_initial_events(patients)
        while not self.event_queue.is_empty():
            event = self.event_queue.pop()
            if event.time > self.config.duration_minutes:
                continue
            self.state.current_time = event.time
            self._handle_event(event)
        self._finalize_unfinished_patients()
        return SimulationResult(
            algorithm=self.algorithm.name,
            scenario=self.config.scenario,
            seed=self.config.seed,
            duration_minutes=self.config.duration_minutes,
            data_source=str(self.generator.scenario_metadata.get("data_source", self.config.data_source)),
            dataset_records_used=self._coerce_optional_int(self.generator.scenario_metadata.get("dataset_records_used")),
            dataset_name=self._coerce_optional_str(self.generator.scenario_metadata.get("dataset_name")),
            metrics=compute_metrics(
                list(self.patients_by_id.values()),
                self.config.duration_minutes,
                self.state.timeline,
            ),
            resource_summary=self._build_resource_summary(),
            active_resource_catalog={
                resource_id: entry.model_dump(mode="json")
                for resource_id, entry in self.generator.active_resource_catalog.items()
            },
            advanced_config=(
                self.config.advanced_config.model_dump(mode="json")
                if self.config.advanced_config is not None
                else None
            ),
            patient_status_summary=self._build_patient_status_summary(),
            event_counts=self._build_event_counts(),
            llm_provider_requested=self.generator.extractor_metadata.get("llm_provider_requested"),
            llm_provider_used=self.generator.extractor_metadata.get("llm_provider_used"),
            llm_fallback_order=list(self.generator.extractor_metadata.get("llm_fallback_order", [])),
            llm_fallback_count=int(self.generator.extractor_metadata.get("llm_fallback_count", 0)),
            llm_cache_hits=int(self.generator.extractor_metadata.get("llm_cache_hits", 0)),
            llm_cache_misses=int(self.generator.extractor_metadata.get("llm_cache_misses", 0)),
            llm_provider_attempts=dict(self.generator.extractor_metadata.get("llm_provider_attempts", {})),
            llm_provider_retries=dict(self.generator.extractor_metadata.get("llm_provider_retries", {})),
            patient_traces=self._build_patient_traces(),
            timeline=self.state.timeline,
        )

    def _schedule_initial_events(self, patients: list[Patient]) -> None:
        for patient in patients:
            self.event_queue.push(
                Event(
                    time=patient.arrival_time,
                    priority=0,
                    event_type=EventType.PATIENT_ARRIVAL,
                    patient_id=patient.patient_id,
                )
            )
        for minute in range(
            self.config.doctor_round_interval_minutes,
            self.config.duration_minutes + 1,
            self.config.doctor_round_interval_minutes,
        ):
            self.event_queue.push(Event(time=minute, priority=1, event_type=EventType.DOCTOR_ROUND_START))
        for minute in range(
            self.config.deterioration_interval_minutes,
            self.config.duration_minutes + 1,
            self.config.deterioration_interval_minutes,
        ):
            self.event_queue.push(Event(time=minute, priority=3, event_type=EventType.DETERIORATION_UPDATE))

    def _handle_event(self, event: Event) -> None:
        if event.event_type == EventType.PATIENT_ARRIVAL:
            self._on_patient_arrival(event)
        elif event.event_type == EventType.DOCTOR_ROUND_START:
            self._on_doctor_round_start()
        elif event.event_type == EventType.DOCTOR_ROUND_END:
            self._on_doctor_round_end(event)
        elif event.event_type == EventType.DETERIORATION_UPDATE:
            self._on_deterioration_update()
        elif event.event_type == EventType.SERVICE_END:
            self._on_service_end(event)

    def _on_patient_arrival(self, event: Event) -> None:
        patient = self.patients_by_id[event.patient_id]
        patient.update_waiting_time(self.state.current_time)
        self.state.waiting_patients.append(patient)
        self._record_event(
            EventType.PATIENT_ARRIVAL,
            patient=patient,
            extra={"arrival_time": round(patient.arrival_time, 4)},
        )
        self._record_event(
            EventType.INITIAL_ASSESSMENT,
            patient=patient,
            note="Patient completed initial triage assessment",
            extra={
                "clinical_category": patient.clinical_category,
                "required_resources": list(patient.required_resources),
                "textual_risk_score": patient.textual_risk_score,
            },
        )
        self._try_dispatch_waiting_patients(trigger=self.DISPATCH_TRIGGER_ARRIVAL)
        self._annotate_latest_initial_assessment(patient)

    def _on_doctor_round_start(self) -> None:
        if not self.state.waiting_patients and not self.state.active_patients:
            self._record_event(
                EventType.DOCTOR_ROUND_IDLE_CHECK,
                note="Doctor round skipped because no waiting patients or active services required review",
                extra={
                    "waiting_patient_count": 0,
                    "active_patient_count": 0,
                    "algorithm": self.algorithm.name,
                },
            )
            return

        waiting_count = len(self.state.waiting_patients)
        active_count = len(self.state.active_patients)
        round_duration, planning_overhead = self._calculate_doctor_round_duration(waiting_count)
        round_end_time = self.state.current_time + round_duration
        self._active_doctor_rounds[round_end_time] = {
            "round_duration": round_duration,
            "planning_overhead": planning_overhead,
            "waiting_count": waiting_count,
            "active_count": active_count,
        }
        self._record_event(
            EventType.DOCTOR_ROUND_START,
            note="Doctor round started",
            extra={
                "waiting_patient_count": waiting_count,
                "active_patient_count": active_count,
                "round_duration": round(round_duration, 4),
                "planning_overhead": round(planning_overhead, 4),
                "algorithm": self.algorithm.name,
            },
        )
        self.event_queue.push(
            Event(
                time=round_end_time,
                priority=2,
                event_type=EventType.DOCTOR_ROUND_END,
                payload={
                    "round_duration": round_duration,
                    "planning_overhead": planning_overhead,
                    "waiting_patient_count": waiting_count,
                    "active_patient_count": active_count,
                    "algorithm": self.algorithm.name,
                },
            )
        )

    def _on_doctor_round_end(self, event: Event) -> None:
        round_duration = float(event.payload.get("round_duration", 0.0))
        planning_overhead = float(event.payload.get("planning_overhead", 0.0))
        waiting_count = len(self.state.waiting_patients)
        active_count = len(self.state.active_patients)
        self._record_event(
            EventType.DOCTOR_ROUND_END,
            note="Doctor round ended",
            extra={
                "trigger": self.DISPATCH_TRIGGER_DOCTOR_ROUND,
                "round_duration": round(round_duration, 4),
                "planning_overhead": round(planning_overhead, 4),
                "waiting_patient_count": waiting_count,
                "active_patient_count": active_count,
                "active_service_count": active_count,
                "algorithm": event.payload.get("algorithm", self.algorithm.name),
            },
        )
        self._try_dispatch_waiting_patients(trigger=self.DISPATCH_TRIGGER_DOCTOR_ROUND)

    def _on_deterioration_update(self) -> None:
        affected_waiting_patients = len(self.state.waiting_patients)
        priority_changes: list[str] = []
        for patient in self.state.waiting_patients:
            patient.update_waiting_time(self.state.current_time)
            previous_risk = patient.current_risk
            previous_exceeded_wait = patient.exceeded_wait
            patient.apply_deterioration(self.config.deterioration_interval_minutes)
            if patient.current_risk > previous_risk or (not previous_exceeded_wait and patient.exceeded_wait):
                priority_changes.append(patient.patient_id)
        self._record_event(
            EventType.DETERIORATION_UPDATE,
            note="Waiting patients deterioration updated",
            extra={
                "affected_waiting_patients": affected_waiting_patients,
                "priority_changes": priority_changes,
            },
        )
        if self.state.waiting_patients and self._has_any_available_capacity():
            self._try_dispatch_waiting_patients(trigger=self.DISPATCH_TRIGGER_DETERIORATION)

    def _on_service_end(self, event: Event) -> None:
        patient = self.patients_by_id[event.patient_id]
        self.resource_pool.release(patient.required_resources)
        patient.status = PatientStatus.TREATED
        patient.service_end_time = self.state.current_time
        self.state.active_patients = [
            active for active in self.state.active_patients if active.patient_id != patient.patient_id
        ]
        self.state.completed_patients.append(patient)
        self._record_event(
            EventType.SERVICE_END,
            patient=patient,
            extra={"resources_released": list(patient.required_resources)},
        )
        self._try_dispatch_waiting_patients(trigger=self.DISPATCH_TRIGGER_SERVICE_END)

    def _start_service(self, patient: Patient, *, trigger: str) -> bool:
        if patient.status != PatientStatus.WAITING:
            return False
        if not self.resource_pool.allocate(patient.required_resources):
            return False
        patient.status = PatientStatus.IN_SERVICE
        patient.assigned_start_time = self.state.current_time
        patient.service_end_time = self.state.current_time + patient.estimated_service_time
        self.state.waiting_patients = [
            waiting for waiting in self.state.waiting_patients if waiting.patient_id != patient.patient_id
        ]
        self.state.active_patients.append(patient)
        self._record_event(
            EventType.SERVICE_START,
            patient=patient,
            extra={
                "trigger": trigger,
                "algorithm": self.algorithm.name,
                "resources_allocated": list(patient.required_resources),
            },
        )
        self.event_queue.push(
            Event(
                time=patient.service_end_time,
                priority=0,
                event_type=EventType.SERVICE_END,
                patient_id=patient.patient_id,
            )
        )
        return True

    def _try_dispatch_waiting_patients(self, *, trigger: str) -> int:
        if not self.state.waiting_patients:
            return 0

        started_total = 0
        while self.state.waiting_patients:
            for patient in self.state.waiting_patients:
                patient.update_waiting_time(self.state.current_time)
            plan = self.algorithm.plan(self._build_planning_state())
            if not plan:
                break

            started_this_pass = 0
            for patient in plan:
                if patient.status != PatientStatus.WAITING:
                    continue
                if self._start_service(patient, trigger=trigger):
                    started_this_pass += 1
                    started_total += 1

            if started_this_pass == 0:
                feasible_patient_count = self._count_feasible_waiting_patients()
                self._record_event(
                    EventType.DISPATCH_ATTEMPT,
                    note="No feasible waiting patient could be started with current available resources.",
                    extra={
                        "trigger": trigger,
                        "algorithm": self.algorithm.name,
                        "waiting_patient_count": len(self.state.waiting_patients),
                        "active_patient_count": len(self.state.active_patients),
                        "active_service_count": len(self.state.active_patients),
                        "available_resources": self._current_available_resources(),
                        "feasible_patient_count": feasible_patient_count,
                        "started_patient_count": 0,
                        "blocking_resources": self._compute_blocking_resources() if feasible_patient_count == 0 else [],
                        "message": "No feasible waiting patient could be started with current available resources.",
                    },
                )
                break

        return started_total

    def _build_planning_state(self) -> PlanningState:
        return PlanningState(
            current_time=self.state.current_time,
            waiting_patients=list(self.state.waiting_patients),
            resource_availability={name: self.resource_pool.available(name) for name in self.resource_pool.capacities},
            random_seed=self.config.seed,
        )

    def _has_any_available_capacity(self) -> bool:
        return any(self.resource_pool.available(name) > 0 for name in self.resource_pool.capacities)

    def _current_available_resources(self) -> dict[str, int]:
        return {name: self.resource_pool.available(name) for name in self.resource_pool.capacities}

    def _count_feasible_waiting_patients(self) -> int:
        return sum(
            1
            for patient in self.state.waiting_patients
            if patient.status == PatientStatus.WAITING and self.resource_pool.can_allocate(patient.required_resources)
        )

    def _compute_blocking_resources(self) -> list[str]:
        missing: set[str] = set()
        for patient in self.state.waiting_patients:
            if patient.status != PatientStatus.WAITING:
                continue
            required_counts: dict[str, int] = {}
            for resource in patient.required_resources:
                required_counts[resource] = required_counts.get(resource, 0) + 1
            for resource_name, amount in required_counts.items():
                if self.resource_pool.available(resource_name) < amount:
                    missing.add(resource_name)
        return sorted(missing)

    def _annotate_latest_initial_assessment(self, patient: Patient) -> None:
        for entry in reversed(self.state.timeline):
            if entry.get("event_type") != EventType.INITIAL_ASSESSMENT.value:
                continue
            if entry.get("patient_id") != patient.patient_id:
                continue
            entry["selected_for_immediate_service"] = patient.assigned_start_time == self.state.current_time
            entry["critical_waiting"] = patient.risk_level >= 5 and patient.status == PatientStatus.WAITING
            break

    def _calculate_doctor_round_duration(self, waiting_patient_count: int) -> tuple[float, float]:
        planning_overhead = self.algorithm.planning_time_penalty_minutes()
        round_duration = (
            settings.doctor_round_base_duration_minutes
            + settings.doctor_round_time_per_waiting_patient_minutes * waiting_patient_count
            + planning_overhead
        )
        return round(round_duration, 4), round(planning_overhead, 4)

    def _build_resource_summary(self) -> dict[str, dict[str, float | int | str]]:
        resource_names = self.resource_pool.capacities.keys()
        summary: dict[str, dict[str, float | int | str]] = {}
        for resource_name in resource_names:
            snapshots = [
                event.get("resources", {}).get(resource_name)
                for event in self.state.timeline
                if resource_name in event.get("resources", {})
            ]
            capacity = self.resource_pool.capacities.get(resource_name, 0)
            in_use_values = [int(snapshot["in_use"]) for snapshot in snapshots if snapshot]
            avg_utilization = (
                sum((value / capacity) for value in in_use_values) / len(in_use_values)
                if capacity > 0 and in_use_values
                else 0.0
            )
            peak_in_use = max(in_use_values) if in_use_values else 0
            final_in_use = self.resource_pool.in_use.get(resource_name, 0)
            final_available = self.resource_pool.available(resource_name)
            status = "available"
            if capacity > 0 and final_available == 0:
                status = "fully_allocated"
            elif capacity > 0 and final_available <= max(1, capacity // 3):
                status = "constrained"
            summary[resource_name] = {
                "capacity": capacity,
                "final_in_use": final_in_use,
                "final_available": final_available,
                "peak_in_use": peak_in_use,
                "average_utilization": round(avg_utilization, 4),
                "status": status,
            }
        return summary

    def _build_patient_status_summary(self) -> dict[str, int]:
        counts = {status.value: 0 for status in PatientStatus}
        for patient in self.patients_by_id.values():
            counts[patient.status.value] += 1
        return counts

    def _build_event_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for event in self.state.timeline:
            event_type = event["event_type"]
            counts[event_type] = counts.get(event_type, 0) + 1
        return counts

    def _build_patient_traces(self) -> list[PatientTrace]:
        llm_provider_used = self.generator.extractor_metadata.get("llm_provider_used")
        traces: dict[str, dict] = {}
        for patient in self.patients_by_id.values():
            traces[patient.patient_id] = {
                "patient_id": patient.patient_id,
                "arrival_time": round(patient.arrival_time, 4),
                "initial_assessment_time": None,
                "time_to_initial_assessment": None,
                "service_start_time": patient.assigned_start_time,
                "service_end_time": patient.service_end_time,
                "waiting_time": None,
                "service_time": None,
                "final_status": patient.status.value,
                "clinical_category": patient.clinical_category,
                "risk_level": patient.risk_level,
                "current_risk": round(patient.current_risk, 3),
                "textual_risk_score": patient.textual_risk_score,
                "deterioration_rate": patient.deterioration_rate,
                "max_wait_time": patient.max_wait_time,
                "estimated_service_time": patient.estimated_service_time,
                "required_resources": list(patient.required_resources),
                "allocated_resources": [],
                "resources_released": [],
                "service_start_trigger": None,
                "algorithm": self.algorithm.name,
                "deterioration_events_count": 0,
                "deterioration_times": [],
                "deteriorated_while_waiting": False,
                "critical_waiting": False,
                "immediate_service": False,
                "llm_provider_used": llm_provider_used,
                "llm_explanation": patient.enrichment_explanation,
                "waiting_reason_events": [],
                "timeline_event_ids": [],
            }

        for index, event in enumerate(self.state.timeline):
            patient_id = event.get("patient_id")
            event_type = event.get("event_type")
            if patient_id and patient_id in traces:
                trace = traces[patient_id]
                trace["timeline_event_ids"].append(index)
                if event_type == EventType.PATIENT_ARRIVAL.value:
                    trace["arrival_time"] = round(float(event.get("time", trace["arrival_time"])), 4)
                elif event_type == EventType.INITIAL_ASSESSMENT.value:
                    trace["initial_assessment_time"] = round(float(event.get("time", 0.0)), 4)
                    trace["clinical_category"] = event.get("clinical_category", trace["clinical_category"])
                    if event.get("textual_risk_score") is not None:
                        trace["textual_risk_score"] = int(event["textual_risk_score"])
                    if event.get("required_resources"):
                        trace["required_resources"] = list(event["required_resources"])
                    trace["critical_waiting"] = bool(event.get("critical_waiting", trace["critical_waiting"]))
                    trace["immediate_service"] = bool(
                        event.get("selected_for_immediate_service", trace["immediate_service"])
                    )
                elif event_type == EventType.SERVICE_START.value:
                    trace["service_start_time"] = round(float(event.get("time", 0.0)), 4)
                    trace["service_start_trigger"] = event.get("trigger")
                    trace["allocated_resources"] = list(event.get("resources_allocated", []))
                elif event_type == EventType.SERVICE_END.value:
                    trace["service_end_time"] = round(float(event.get("time", 0.0)), 4)
                    trace["resources_released"] = list(event.get("resources_released", []))

            if event_type == EventType.DETERIORATION_UPDATE.value:
                for affected_id in event.get("priority_changes", []):
                    if affected_id not in traces:
                        continue
                    trace = traces[affected_id]
                    trace["timeline_event_ids"].append(index)
                    trace["deterioration_events_count"] += 1
                    trace["deterioration_times"].append(round(float(event.get("time", 0.0)), 4))
                    trace["deteriorated_while_waiting"] = True

        for patient in self.patients_by_id.values():
            trace = traces[patient.patient_id]
            arrival_time = float(trace["arrival_time"])
            service_start_time = trace["service_start_time"]
            service_end_time = trace["service_end_time"]
            initial_assessment_time = trace["initial_assessment_time"]
            if initial_assessment_time is not None:
                trace["time_to_initial_assessment"] = round(float(initial_assessment_time) - arrival_time, 4)
            if service_start_time is not None:
                trace["waiting_time"] = round(float(service_start_time) - arrival_time, 4)
            else:
                trace["waiting_time"] = round(float(self.config.duration_minutes) - arrival_time, 4)
            if service_start_time is not None and service_end_time is not None:
                trace["service_time"] = round(float(service_end_time) - float(service_start_time), 4)
            trace["immediate_service"] = bool(
                trace["immediate_service"]
                or (
                    trace["service_start_time"] is not None
                    and abs(float(trace["service_start_time"]) - arrival_time) <= 1e-9
                )
            )

            wait_end_time = float(service_start_time) if service_start_time is not None else float(self.config.duration_minutes)
            for index, event in enumerate(self.state.timeline):
                if event.get("event_type") != EventType.DISPATCH_ATTEMPT.value:
                    continue
                event_time = float(event.get("time", 0.0))
                if not (arrival_time <= event_time <= wait_end_time):
                    continue
                if not event.get("blocking_resources") and not event.get("message"):
                    continue
                trace["timeline_event_ids"].append(index)
                trace["waiting_reason_events"].append(
                    WaitingReasonEvent(
                        time=round(event_time, 4),
                        trigger=event.get("trigger"),
                        blocking_resources=list(event.get("blocking_resources", [])),
                        available_resources=dict(event.get("available_resources", {})),
                        message=event.get("message"),
                    ).model_dump(mode="json")
                )

            trace["timeline_event_ids"] = sorted(set(trace["timeline_event_ids"]))

        return [
            PatientTrace(**traces[patient_id])
            for patient_id in sorted(
                traces,
                key=lambda pid: (float(traces[pid]["arrival_time"]), pid),
            )
        ]

    def _finalize_unfinished_patients(self) -> None:
        for patient in self.patients_by_id.values():
            if patient.status == PatientStatus.WAITING:
                patient.status = PatientStatus.LEFT_UNTREATED
            elif (
                patient.status == PatientStatus.IN_SERVICE
                and patient.service_end_time is not None
                and patient.service_end_time > self.config.duration_minutes
            ):
                self.resource_pool.release(patient.required_resources)
                patient.status = PatientStatus.TREATED

    def _record_event(
        self,
        event_type: EventType,
        patient: Patient | None = None,
        note: str | None = None,
        extra: dict | None = None,
    ) -> None:
        entry = {
            "time": round(self.state.current_time, 4),
            "event_type": event_type.value,
            "patient_id": patient.patient_id if patient else None,
            "status": patient.status.value if patient else None,
            "resources": self.resource_pool.snapshot(),
        }
        if patient:
            entry["risk_level"] = patient.risk_level
            entry["current_risk"] = round(patient.current_risk, 3)
        if note:
            entry["note"] = note
        if extra:
            entry.update(extra)
        self.state.timeline.append(entry)

    def _coerce_optional_int(self, value: object) -> int | None:
        return int(value) if value is not None else None

    def _coerce_optional_str(self, value: object) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None
