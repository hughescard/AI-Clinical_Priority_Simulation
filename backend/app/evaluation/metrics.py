from __future__ import annotations

from statistics import mean

from app.models.patient import Patient, PatientStatus


def compute_metrics(patients: list[Patient], duration_minutes: int, timeline: list[dict]) -> dict:
    treated = [patient for patient in patients if patient.status == PatientStatus.TREATED]
    untreated = [patient for patient in patients if patient.status != PatientStatus.TREATED]
    waiting_times = [
        patient.assigned_start_time - patient.arrival_time
        for patient in treated
        if patient.assigned_start_time is not None
    ]
    length_of_stay = [
        patient.service_end_time - patient.arrival_time
        for patient in treated
        if patient.service_end_time is not None
    ]
    high_risk_treated = [patient for patient in treated if patient.risk_level >= 4]
    high_risk_count = len([patient for patient in patients if patient.risk_level >= 4])
    critical_late_patients = sum(
        1
        for patient in patients
        if patient.risk_level >= 4 and _effective_wait_time(patient, duration_minutes) > patient.max_wait_time
    )
    total_clinical_impact = round(sum(_clinical_impact_score(patient, duration_minutes) for patient in patients), 2)
    average_resource_utilization = round(_average_resource_utilization(timeline), 4)
    round_end_events = [event for event in timeline if event.get("event_type") == "DOCTOR_ROUND_END"]
    initial_assessment_events = [event for event in timeline if event.get("event_type") == "INITIAL_ASSESSMENT"]
    service_start_events = [event for event in timeline if event.get("event_type") == "SERVICE_START"]
    arrival_events_by_patient = {
        event["patient_id"]: float(event.get("time", 0.0))
        for event in timeline
        if event.get("event_type") == "PATIENT_ARRIVAL" and event.get("patient_id")
    }
    assessment_delays = [
        float(event.get("time", 0.0)) - arrival_events_by_patient[event["patient_id"]]
        for event in initial_assessment_events
        if event.get("patient_id") in arrival_events_by_patient
    ]
    deterioration_events = [event for event in timeline if event.get("event_type") == "DETERIORATION_UPDATE"]
    deteriorated_waiting_patients = {
        patient_id
        for event in deterioration_events
        for patient_id in event.get("priority_changes", [])
    }
    total_doctor_round_time = round(sum(float(event.get("round_duration", 0.0)) for event in round_end_events), 4)
    number_of_doctor_rounds = len(round_end_events)
    average_doctor_round_duration = round(
        total_doctor_round_time / number_of_doctor_rounds,
        4,
    ) if number_of_doctor_rounds else 0.0
    total_planning_overhead_time = round(
        sum(float(event.get("planning_overhead", 0.0)) for event in round_end_events),
        4,
    )
    services_started_from_arrival = sum(
        1 for event in service_start_events if event.get("trigger") == "arrival_initial_assessment"
    )
    services_started_from_service_end = sum(
        1 for event in service_start_events if event.get("trigger") == "service_end_resource_available"
    )
    services_started_from_deterioration = sum(
        1 for event in service_start_events if event.get("trigger") == "deterioration_reassessment"
    )
    services_started_from_doctor_round = sum(
        1 for event in service_start_events if event.get("trigger") == "doctor_round_replan"
    )
    critical_patients = [patient for patient in patients if patient.risk_level >= 5]
    return {
        "total_patients": len(patients),
        "treated_patients": len(treated),
        "untreated_patients": len(untreated),
        "number_of_initial_assessments": len(initial_assessment_events),
        "services_started_from_arrival": services_started_from_arrival,
        "services_started_from_service_end": services_started_from_service_end,
        "services_started_from_deterioration": services_started_from_deterioration,
        "services_started_from_doctor_round": services_started_from_doctor_round,
        "average_time_to_initial_assessment": round(mean(assessment_delays), 2) if assessment_delays else 0.0,
        "average_time_to_service_start": round(mean(waiting_times), 2) if waiting_times else 0.0,
        "patients_deteriorated_while_waiting": len(deteriorated_waiting_patients),
        "critical_patients_waited": sum(1 for patient in critical_patients if _effective_wait_time(patient, duration_minutes) > 0),
        "critical_patients_started_immediately": sum(
            1 for patient in critical_patients if patient.assigned_start_time == patient.arrival_time
        ),
        "average_waiting_time": round(mean(waiting_times), 2) if waiting_times else 0.0,
        "max_waiting_time": max(waiting_times) if waiting_times else 0,
        "average_length_of_stay": round(mean(length_of_stay), 2) if length_of_stay else 0.0,
        "throughput_per_hour": round(len(treated) / max(duration_minutes / 60, 1), 2),
        "high_risk_treatment_rate": round(len(high_risk_treated) / high_risk_count, 4) if high_risk_count else 0.0,
        "critical_late_patients": critical_late_patients,
        "total_clinical_impact": total_clinical_impact,
        "average_resource_utilization": average_resource_utilization,
        "total_doctor_round_time": total_doctor_round_time,
        "number_of_doctor_rounds": number_of_doctor_rounds,
        "average_doctor_round_duration": average_doctor_round_duration,
        "total_planning_overhead_time": total_planning_overhead_time,
    }


def _effective_wait_time(patient: Patient, duration_minutes: int) -> int:
    if patient.assigned_start_time is not None:
        return patient.assigned_start_time - patient.arrival_time
    return max(0, duration_minutes - patient.arrival_time)


def _clinical_impact_score(patient: Patient, duration_minutes: int) -> float:
    wait_time = _effective_wait_time(patient, duration_minutes)
    overdue = max(0, wait_time - patient.max_wait_time)
    untreated_penalty = 25.0 if patient.status != PatientStatus.TREATED else 0.0
    return (
        patient.current_risk * wait_time
        + patient.deterioration_rate * wait_time * 20.0
        + overdue * (5.0 + patient.current_risk)
        + untreated_penalty
    )


def _average_resource_utilization(timeline: list[dict]) -> float:
    utilization_values: list[float] = []
    for event in timeline:
        resources = event.get("resources") or {}
        total_capacity = sum(resource["capacity"] for resource in resources.values())
        total_in_use = sum(resource["in_use"] for resource in resources.values())
        if total_capacity > 0:
            utilization_values.append(total_in_use / total_capacity)
    return mean(utilization_values) if utilization_values else 0.0
