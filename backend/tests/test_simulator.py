from app.algorithms.astar import AStarPlanningAlgorithm
from app.algorithms.cpsat import CPSATPlanningAlgorithm
from app.algorithms.fifo import FIFOPlanningAlgorithm
from app.algorithms.greedy import DynamicGreedyPlanningAlgorithm
from app.algorithms.simulated_annealing import SimulatedAnnealingPlanningAlgorithm
from app.config import settings
from app.models.patient import Patient
from app.models.patient import PatientStatus
from app.models.simulation import SimulationConfig
from app.simulation.simulator import ClinicalTriageSimulator
from app.simulation.scenario_generator import ScenarioGenerator


def build_config(seed: int) -> SimulationConfig:
    return SimulationConfig(
        algorithm="fifo",
        scenario="normal",
        seed=seed,
        duration_minutes=240,
        doctor_round_interval_minutes=settings.doctor_round_interval_minutes,
        deterioration_interval_minutes=settings.deterioration_interval_minutes,
        resource_capacities=settings.default_resource_capacity.copy(),
    )


def test_simulator_is_deterministic_for_same_seed() -> None:
    algorithm = FIFOPlanningAlgorithm()
    first = ClinicalTriageSimulator(build_config(42), algorithm).run()
    second = ClinicalTriageSimulator(build_config(42), algorithm).run()
    assert first.metrics == second.metrics
    assert first.timeline == second.timeline


def test_scenario_generation_is_seeded() -> None:
    first_patients, first_resources = ScenarioGenerator(seed=42).generate("normal", 240)
    second_patients, second_resources = ScenarioGenerator(seed=42).generate("normal", 240)
    assert first_patients == second_patients
    assert first_resources == second_resources
    assert all(patient.textual_risk_score is not None for patient in first_patients)
    assert all(patient.clinical_category is not None for patient in first_patients)


def test_dataset_backed_scenario_generation_is_deterministic() -> None:
    first_patients, first_resources = ScenarioGenerator(seed=42, data_source="mimic_iv_ed_sample").generate("normal", 240)
    second_patients, second_resources = ScenarioGenerator(seed=42, data_source="mimic_iv_ed_sample").generate("normal", 240)
    assert first_patients == second_patients
    assert first_resources == second_resources


def test_service_end_releases_resources() -> None:
    algorithm = FIFOPlanningAlgorithm()
    simulator = ClinicalTriageSimulator(
        SimulationConfig(
            algorithm="fifo",
            scenario="normal",
            seed=7,
            duration_minutes=30,
            doctor_round_interval_minutes=1,
            deterioration_interval_minutes=15,
            resource_capacities={"doctor": 1, "nurse": 1},
        ),
        algorithm,
    )
    patient = Patient(
        patient_id="P001",
        age=30,
        arrival_time=1,
        chief_complaint="Fever",
        clinical_description="Short treatment case",
        risk_level=2,
        current_risk=2.0,
        deterioration_rate=0.0,
        max_wait_time=60,
        estimated_service_time=5,
        required_resources=["doctor", "nurse"],
    )
    simulator.generator.generate = lambda scenario, duration: ([patient], {"doctor": 1, "nurse": 1})

    result = simulator.run()

    service_end_events = [event for event in result.timeline if event["event_type"] == "SERVICE_END"]
    assert len(service_end_events) == 1
    event = service_end_events[0]
    assert event["status"] == PatientStatus.TREATED.value
    assert event["resources"]["doctor"]["in_use"] == 0
    assert event["resources"]["nurse"]["in_use"] == 0
    assert simulator.resource_pool.in_use == {}


def test_cutoff_finalization_releases_in_service_resources() -> None:
    algorithm = FIFOPlanningAlgorithm()
    simulator = ClinicalTriageSimulator(
        SimulationConfig(
            algorithm="fifo",
            scenario="normal",
            seed=11,
            duration_minutes=5,
            doctor_round_interval_minutes=1,
            deterioration_interval_minutes=15,
            resource_capacities={"doctor": 1},
        ),
        algorithm,
    )
    patient = Patient(
        patient_id="P002",
        age=44,
        arrival_time=1,
        chief_complaint="Fever",
        clinical_description="Treatment extends beyond simulation cutoff",
        risk_level=2,
        current_risk=2.0,
        deterioration_rate=0.0,
        max_wait_time=60,
        estimated_service_time=10,
        required_resources=["doctor"],
    )
    simulator.generator.generate = lambda scenario, duration: ([patient], {"doctor": 1})

    simulator.run()

    assert simulator.patients_by_id["P002"].status == PatientStatus.TREATED
    assert simulator.resource_pool.in_use == {}


def test_doctor_round_end_occurs_after_start() -> None:
    simulator = ClinicalTriageSimulator(build_config(42), FIFOPlanningAlgorithm())
    result = simulator.run()
    starts = [event for event in result.timeline if event["event_type"] == "DOCTOR_ROUND_START"]
    ends = [event for event in result.timeline if event["event_type"] == "DOCTOR_ROUND_END"]
    assert starts
    assert ends
    assert ends[0]["time"] > starts[0]["time"]


def test_doctor_round_duration_increases_with_waiting_patient_count() -> None:
    simulator = ClinicalTriageSimulator(build_config(42), FIFOPlanningAlgorithm())
    short_duration, _ = simulator._calculate_doctor_round_duration(1)
    long_duration, _ = simulator._calculate_doctor_round_duration(6)
    assert long_duration > short_duration


def test_astar_has_higher_planning_overhead_than_greedy_and_fifo() -> None:
    fifo_simulator = ClinicalTriageSimulator(build_config(42), FIFOPlanningAlgorithm())
    greedy_simulator = ClinicalTriageSimulator(build_config(42), DynamicGreedyPlanningAlgorithm())
    astar_simulator = ClinicalTriageSimulator(build_config(42), AStarPlanningAlgorithm())
    _, fifo_penalty = fifo_simulator._calculate_doctor_round_duration(3)
    _, greedy_penalty = greedy_simulator._calculate_doctor_round_duration(3)
    _, astar_penalty = astar_simulator._calculate_doctor_round_duration(3)
    assert fifo_penalty < greedy_penalty < astar_penalty


def test_cpsat_has_higher_planning_overhead_than_astar() -> None:
    astar_simulator = ClinicalTriageSimulator(build_config(42), AStarPlanningAlgorithm())
    cpsat_simulator = ClinicalTriageSimulator(build_config(42), CPSATPlanningAlgorithm())
    _, astar_penalty = astar_simulator._calculate_doctor_round_duration(3)
    _, cpsat_penalty = cpsat_simulator._calculate_doctor_round_duration(3)
    assert cpsat_penalty > astar_penalty


def test_simulated_annealing_has_higher_planning_overhead_than_astar() -> None:
    astar_simulator = ClinicalTriageSimulator(build_config(42), AStarPlanningAlgorithm())
    annealing_simulator = ClinicalTriageSimulator(build_config(42), SimulatedAnnealingPlanningAlgorithm())
    _, astar_penalty = astar_simulator._calculate_doctor_round_duration(3)
    _, annealing_penalty = annealing_simulator._calculate_doctor_round_duration(3)
    assert annealing_penalty > astar_penalty


def test_total_doctor_round_time_is_positive_when_rounds_occur() -> None:
    simulator = ClinicalTriageSimulator(build_config(42), FIFOPlanningAlgorithm())
    result = simulator.run()
    assert result.metrics["total_doctor_round_time"] > 0
    assert result.metrics["number_of_doctor_rounds"] > 0
    assert result.metrics["average_doctor_round_duration"] > 0
    assert result.metrics["total_planning_overhead_time"] > 0


def test_empty_rounds_do_not_increase_round_metrics() -> None:
    simulator = ClinicalTriageSimulator(build_config(42), FIFOPlanningAlgorithm())
    simulator.generator.generate = lambda scenario, duration: ([], settings.default_resource_capacity.copy())

    result = simulator.run()

    assert result.metrics["number_of_doctor_rounds"] == 0
    assert result.metrics["total_doctor_round_time"] == 0.0
    assert result.metrics["total_planning_overhead_time"] == 0.0
    assert "DOCTOR_ROUND_START" not in result.event_counts
    assert result.event_counts.get("DOCTOR_ROUND_IDLE_CHECK", 0) > 0


def test_simulations_with_patients_still_produce_doctor_rounds() -> None:
    simulator = ClinicalTriageSimulator(build_config(42), FIFOPlanningAlgorithm())

    result = simulator.run()

    assert result.metrics["number_of_doctor_rounds"] > 0
    assert result.event_counts.get("DOCTOR_ROUND_START", 0) > 0


def test_simulation_result_includes_data_source_metadata() -> None:
    simulator = ClinicalTriageSimulator(build_config(42), FIFOPlanningAlgorithm())

    result = simulator.run()

    assert result.data_source == "synthetic"
    assert result.dataset_name == "Synthetic Scenario Generator"


def test_patient_arrival_creates_initial_assessment_event() -> None:
    simulator = ClinicalTriageSimulator(build_config(42), FIFOPlanningAlgorithm())
    patient = Patient(
        patient_id="P100",
        age=30,
        arrival_time=1,
        chief_complaint="Fever",
        clinical_description="Moderate fever",
        risk_level=2,
        current_risk=2.0,
        deterioration_rate=0.0,
        max_wait_time=60,
        estimated_service_time=5,
        required_resources=["doctor"],
        clinical_category="infectious",
        textual_risk_score=2,
    )
    simulator.generator.generate = lambda scenario, duration: ([patient], {"doctor": 1})

    result = simulator.run()

    assessment_events = [event for event in result.timeline if event["event_type"] == "INITIAL_ASSESSMENT"]
    assert len(assessment_events) == 1
    assert assessment_events[0]["patient_id"] == "P100"
    assert assessment_events[0]["clinical_category"] == "infectious"


def test_patient_can_start_before_next_doctor_round_if_resources_available() -> None:
    simulator = ClinicalTriageSimulator(
        SimulationConfig(
            algorithm="fifo",
            scenario="normal",
            seed=1,
            duration_minutes=60,
            doctor_round_interval_minutes=15,
            deterioration_interval_minutes=15,
            resource_capacities={"doctor": 1},
        ),
        FIFOPlanningAlgorithm(),
    )
    patient = Patient(
        patient_id="P101",
        age=30,
        arrival_time=1,
        chief_complaint="Fever",
        clinical_description="Short case",
        risk_level=2,
        current_risk=2.0,
        deterioration_rate=0.0,
        max_wait_time=60,
        estimated_service_time=5,
        required_resources=["doctor"],
    )
    simulator.generator.generate = lambda scenario, duration: ([patient], {"doctor": 1})

    result = simulator.run()

    service_start = next(event for event in result.timeline if event["event_type"] == "SERVICE_START")
    assert service_start["time"] == 1
    assert service_start["trigger"] == ClinicalTriageSimulator.DISPATCH_TRIGGER_ARRIVAL
    assert service_start["time"] < 15

    patient_trace = next(trace for trace in result.patient_traces if trace.patient_id == "P101")
    assert patient_trace.arrival_time == 1
    assert patient_trace.initial_assessment_time == 1
    assert patient_trace.service_start_time == 1
    assert patient_trace.service_end_time == 6
    assert patient_trace.waiting_time == 0
    assert patient_trace.service_start_trigger == ClinicalTriageSimulator.DISPATCH_TRIGGER_ARRIVAL
    assert patient_trace.required_resources == ["doctor"]
    assert patient_trace.allocated_resources == ["doctor"]
    assert patient_trace.resources_released == ["doctor"]


def test_service_end_triggers_dispatch_of_waiting_patient() -> None:
    simulator = ClinicalTriageSimulator(
        SimulationConfig(
            algorithm="fifo",
            scenario="normal",
            seed=2,
            duration_minutes=30,
            doctor_round_interval_minutes=20,
            deterioration_interval_minutes=15,
            resource_capacities={"doctor": 1},
        ),
        FIFOPlanningAlgorithm(),
    )
    first = Patient(
        patient_id="P102",
        age=50,
        arrival_time=1,
        chief_complaint="Case 1",
        clinical_description="First case",
        risk_level=2,
        current_risk=2.0,
        deterioration_rate=0.0,
        max_wait_time=60,
        estimated_service_time=5,
        required_resources=["doctor"],
    )
    second = Patient(
        patient_id="P103",
        age=51,
        arrival_time=2,
        chief_complaint="Case 2",
        clinical_description="Second case",
        risk_level=2,
        current_risk=2.0,
        deterioration_rate=0.0,
        max_wait_time=60,
        estimated_service_time=5,
        required_resources=["doctor"],
    )
    simulator.generator.generate = lambda scenario, duration: ([first, second], {"doctor": 1})

    result = simulator.run()

    service_start_events = [event for event in result.timeline if event["event_type"] == "SERVICE_START"]
    assert len(service_start_events) == 2
    assert service_start_events[0]["patient_id"] == "P102"
    assert service_start_events[0]["trigger"] == ClinicalTriageSimulator.DISPATCH_TRIGGER_ARRIVAL
    assert service_start_events[1]["patient_id"] == "P103"
    assert service_start_events[1]["trigger"] == ClinicalTriageSimulator.DISPATCH_TRIGGER_SERVICE_END


def test_doctor_round_still_performs_global_replanning() -> None:
    simulator = ClinicalTriageSimulator(
        SimulationConfig(
            algorithm="fifo",
            scenario="normal",
            seed=3,
            duration_minutes=20,
            doctor_round_interval_minutes=5,
            deterioration_interval_minutes=15,
            resource_capacities={"doctor": 0},
        ),
        FIFOPlanningAlgorithm(),
    )
    patient = Patient(
        patient_id="P104",
        age=47,
        arrival_time=1,
        chief_complaint="Blocked case",
        clinical_description="No doctor available yet",
        risk_level=3,
        current_risk=3.0,
        deterioration_rate=0.0,
        max_wait_time=30,
        estimated_service_time=5,
        required_resources=["doctor"],
    )
    simulator.generator.generate = lambda scenario, duration: ([patient], {"doctor": 0})

    result = simulator.run()

    round_end = next(event for event in result.timeline if event["event_type"] == "DOCTOR_ROUND_END")
    assert round_end["trigger"] == ClinicalTriageSimulator.DISPATCH_TRIGGER_DOCTOR_ROUND
    assert round_end["active_service_count"] == round_end["active_patient_count"]


def test_deterioration_can_affect_future_dispatch_priority() -> None:
    simulator = ClinicalTriageSimulator(
        SimulationConfig(
            algorithm="greedy",
            scenario="normal",
            seed=4,
            duration_minutes=30,
            doctor_round_interval_minutes=50,
            deterioration_interval_minutes=2,
            resource_capacities={"doctor": 1},
        ),
        DynamicGreedyPlanningAlgorithm(),
    )
    active = Patient(
        patient_id="P105",
        age=40,
        arrival_time=0,
        chief_complaint="Busy doctor",
        clinical_description="Occupies doctor briefly",
        risk_level=2,
        current_risk=2.0,
        deterioration_rate=0.0,
        max_wait_time=30,
        estimated_service_time=6,
        required_resources=["doctor"],
    )
    low = Patient(
        patient_id="P106",
        age=35,
        arrival_time=1,
        chief_complaint="Low risk",
        clinical_description="Stable patient",
        risk_level=1,
        current_risk=1.0,
        deterioration_rate=0.01,
        max_wait_time=60,
        estimated_service_time=5,
        required_resources=["doctor"],
    )
    deteriorating = Patient(
        patient_id="P107",
        age=36,
        arrival_time=2,
        chief_complaint="Worsening case",
        clinical_description="Potential deterioration",
        risk_level=2,
        current_risk=2.0,
        deterioration_rate=1.0,
        max_wait_time=60,
        estimated_service_time=5,
        required_resources=["doctor"],
    )
    simulator.generator.generate = lambda scenario, duration: ([active, low, deteriorating], {"doctor": 1})

    result = simulator.run()

    service_start_events = [event for event in result.timeline if event["event_type"] == "SERVICE_START"]
    assert service_start_events[1]["patient_id"] == "P107"
    assert result.metrics["patients_deteriorated_while_waiting"] >= 1
    deteriorating_trace = next(trace for trace in result.patient_traces if trace.patient_id == "P107")
    assert deteriorating_trace.deteriorated_while_waiting is True
    assert deteriorating_trace.deterioration_events_count >= 1
    assert deteriorating_trace.deterioration_times


def test_untreated_patient_trace_still_includes_waiting_time() -> None:
    simulator = ClinicalTriageSimulator(
        SimulationConfig(
            algorithm="fifo",
            scenario="normal",
            seed=12,
            duration_minutes=20,
            doctor_round_interval_minutes=10,
            deterioration_interval_minutes=10,
            resource_capacities={"doctor": 0},
        ),
        FIFOPlanningAlgorithm(),
    )
    patient = Patient(
        patient_id="P400",
        age=44,
        arrival_time=5,
        chief_complaint="Blocked",
        clinical_description="No available doctor",
        risk_level=3,
        current_risk=3.0,
        deterioration_rate=0.0,
        max_wait_time=30,
        estimated_service_time=5,
        required_resources=["doctor"],
    )
    simulator.generator.generate = lambda scenario, duration: ([patient], {"doctor": 0})

    result = simulator.run()

    patient_trace = next(trace for trace in result.patient_traces if trace.patient_id == "P400")
    assert patient_trace.final_status == "LEFT_UNTREATED"
    assert patient_trace.service_start_time is None
    assert patient_trace.waiting_time == 15
    assert patient_trace.waiting_reason_events


def test_critical_patient_is_considered_immediately_on_arrival() -> None:
    simulator = ClinicalTriageSimulator(
        SimulationConfig(
            algorithm="fifo",
            scenario="normal",
            seed=5,
            duration_minutes=20,
            doctor_round_interval_minutes=15,
            deterioration_interval_minutes=15,
            resource_capacities={"doctor": 0, "resuscitation_room": 0},
        ),
        FIFOPlanningAlgorithm(),
    )
    patient = Patient(
        patient_id="P108",
        age=70,
        arrival_time=1,
        chief_complaint="Collapse",
        clinical_description="Critical collapse",
        risk_level=5,
        current_risk=5.0,
        deterioration_rate=0.2,
        max_wait_time=0,
        estimated_service_time=10,
        required_resources=["doctor", "resuscitation_room"],
    )
    simulator.generator.generate = lambda scenario, duration: ([patient], {"doctor": 0, "resuscitation_room": 0})

    result = simulator.run()

    assessment_event = next(event for event in result.timeline if event["event_type"] == "INITIAL_ASSESSMENT")
    assert assessment_event["critical_waiting"] is True
    assert assessment_event["selected_for_immediate_service"] is False


def test_no_infinite_loop_when_no_waiting_patient_is_feasible() -> None:
    simulator = ClinicalTriageSimulator(
        SimulationConfig(
            algorithm="fifo",
            scenario="normal",
            seed=6,
            duration_minutes=10,
            doctor_round_interval_minutes=5,
            deterioration_interval_minutes=5,
            resource_capacities={"doctor": 0},
        ),
        FIFOPlanningAlgorithm(),
    )
    patient = Patient(
        patient_id="P109",
        age=22,
        arrival_time=1,
        chief_complaint="Unfeasible",
        clinical_description="No available doctor",
        risk_level=2,
        current_risk=2.0,
        deterioration_rate=0.0,
        max_wait_time=30,
        estimated_service_time=5,
        required_resources=["doctor"],
    )
    simulator.generator.generate = lambda scenario, duration: ([patient], {"doctor": 0})

    result = simulator.run()

    assert result.metrics["treated_patients"] == 0
    assert result.event_counts.get("SERVICE_START", 0) == 0
    assert result.event_counts.get("DISPATCH_ATTEMPT", 0) > 0
    assert len(result.timeline) < 20


def test_doctor_round_end_uses_current_waiting_count_when_patient_arrives_during_round() -> None:
    simulator = ClinicalTriageSimulator(
        SimulationConfig(
            algorithm="fifo",
            scenario="normal",
            seed=8,
            duration_minutes=10,
            doctor_round_interval_minutes=2,
            deterioration_interval_minutes=15,
            resource_capacities={"doctor": 0},
        ),
        FIFOPlanningAlgorithm(),
    )
    first = Patient(
        patient_id="P200",
        age=40,
        arrival_time=1.0,
        chief_complaint="Blocked 1",
        clinical_description="No doctor available",
        risk_level=2,
        current_risk=2.0,
        deterioration_rate=0.0,
        max_wait_time=30,
        estimated_service_time=5,
        required_resources=["doctor"],
    )
    second = Patient(
        patient_id="P201",
        age=41,
        arrival_time=2.2,
        chief_complaint="Blocked 2",
        clinical_description="Arrives during round",
        risk_level=2,
        current_risk=2.0,
        deterioration_rate=0.0,
        max_wait_time=30,
        estimated_service_time=5,
        required_resources=["doctor"],
    )
    simulator.generator.generate = lambda scenario, duration: ([first, second], {"doctor": 0})

    result = simulator.run()

    round_end = next(event for event in result.timeline if event["event_type"] == "DOCTOR_ROUND_END")
    assert round_end["time"] == 2.7
    assert round_end["waiting_patient_count"] == 2


def test_doctor_round_end_uses_current_active_service_count_when_service_changes_during_round() -> None:
    simulator = ClinicalTriageSimulator(
        SimulationConfig(
            algorithm="fifo",
            scenario="normal",
            seed=9,
            duration_minutes=10,
            doctor_round_interval_minutes=2,
            deterioration_interval_minutes=15,
            resource_capacities={"doctor": 1, "nurse": 0},
        ),
        FIFOPlanningAlgorithm(),
    )
    active_patient = Patient(
        patient_id="P202",
        age=50,
        arrival_time=1.0,
        chief_complaint="Short service",
        clinical_description="Ends during round",
        risk_level=2,
        current_risk=2.0,
        deterioration_rate=0.0,
        max_wait_time=30,
        estimated_service_time=3,
        required_resources=["doctor"],
    )
    waiting_patients = [
        Patient(
            patient_id=f"P20{i}",
            age=30 + i,
            arrival_time=1.1,
            chief_complaint="Blocked waiting",
            clinical_description="Needs unavailable nurse",
            risk_level=2,
            current_risk=2.0,
            deterioration_rate=0.0,
            max_wait_time=30,
            estimated_service_time=5,
            required_resources=["doctor", "nurse"],
        )
        for i in range(3, 18)
    ]
    simulator.generator.generate = lambda scenario, duration: ([active_patient, *waiting_patients], {"doctor": 1, "nurse": 0})

    result = simulator.run()

    round_end = next(event for event in result.timeline if event["event_type"] == "DOCTOR_ROUND_END")
    assert round_end["time"] == 4.1
    assert round_end["active_service_count"] == 0
    assert round_end["active_patient_count"] == 0


def test_dispatch_attempt_records_trigger_and_blocking_resources() -> None:
    simulator = ClinicalTriageSimulator(
        SimulationConfig(
            algorithm="fifo",
            scenario="normal",
            seed=10,
            duration_minutes=10,
            doctor_round_interval_minutes=15,
            deterioration_interval_minutes=15,
            resource_capacities={"doctor": 0, "vital_sign_monitor": 0},
        ),
        FIFOPlanningAlgorithm(),
    )
    patient = Patient(
        patient_id="P300",
        age=65,
        arrival_time=1,
        chief_complaint="Blocked resource case",
        clinical_description="Needs multiple unavailable resources",
        risk_level=4,
        current_risk=4.0,
        deterioration_rate=0.0,
        max_wait_time=30,
        estimated_service_time=5,
        required_resources=["doctor", "vital_sign_monitor"],
    )
    simulator.generator.generate = lambda scenario, duration: ([patient], {"doctor": 0, "vital_sign_monitor": 0})

    result = simulator.run()

    dispatch_attempt = next(event for event in result.timeline if event["event_type"] == "DISPATCH_ATTEMPT")
    assert dispatch_attempt["trigger"] == ClinicalTriageSimulator.DISPATCH_TRIGGER_ARRIVAL
    assert dispatch_attempt["feasible_patient_count"] == 0
    assert dispatch_attempt["started_patient_count"] == 0
    assert dispatch_attempt["blocking_resources"] == ["doctor", "vital_sign_monitor"]
    assert dispatch_attempt["message"] == "No feasible waiting patient could be started with current available resources."


def test_dispatch_attempt_blocks_enabled_zero_capacity_resource() -> None:
    simulator = ClinicalTriageSimulator(
        SimulationConfig(
            algorithm="fifo",
            scenario="normal",
            seed=10,
            duration_minutes=10,
            doctor_round_interval_minutes=15,
            deterioration_interval_minutes=15,
            resource_capacities={"doctor": 1, "ct_scanner": 0},
            active_resource_catalog={
                "doctor": {"id": "doctor", "capacity": 1, "enabled": True},
                "ct_scanner": {"id": "ct_scanner", "capacity": 0, "enabled": True},
            },
        ),
        FIFOPlanningAlgorithm(),
    )
    patient = Patient(
        patient_id="P301",
        age=67,
        arrival_time=1,
        chief_complaint="Head trauma",
        clinical_description="Head trauma with confusion requiring CT imaging",
        risk_level=4,
        current_risk=4.0,
        deterioration_rate=0.0,
        max_wait_time=30,
        estimated_service_time=5,
        required_resources=["doctor", "ct_scanner"],
    )
    simulator.generator.generate = lambda scenario, duration: ([patient], {"doctor": 1, "ct_scanner": 0})

    result = simulator.run()

    dispatch_attempt = next(event for event in result.timeline if event["event_type"] == "DISPATCH_ATTEMPT")
    assert dispatch_attempt["blocking_resources"] == ["ct_scanner"]
    assert dispatch_attempt["available_resources"]["ct_scanner"] == 0
