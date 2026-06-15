from app.simulation.event_queue import EventQueue
from app.simulation.events import Event, EventType


def test_event_queue_orders_same_timestamp_deterministically() -> None:
    queue = EventQueue()
    queue.push(Event(time=10, priority=1, event_type=EventType.DOCTOR_ROUND_START))
    queue.push(Event(time=10, priority=1, event_type=EventType.DETERIORATION_UPDATE))
    queue.push(Event(time=10, priority=0, event_type=EventType.PATIENT_ARRIVAL))

    first = queue.pop()
    second = queue.pop()
    third = queue.pop()

    assert first.event_type == EventType.PATIENT_ARRIVAL
    assert second.event_type == EventType.DOCTOR_ROUND_START
    assert third.event_type == EventType.DETERIORATION_UPDATE
