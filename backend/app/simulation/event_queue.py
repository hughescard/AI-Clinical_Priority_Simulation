from __future__ import annotations

import heapq
from itertools import count

from app.simulation.events import Event


class EventQueue:
    def __init__(self) -> None:
        self._queue: list[tuple[int, int, int, Event]] = []
        self._counter = count()

    def push(self, event: Event) -> None:
        heapq.heappush(self._queue, (event.time, event.priority, next(self._counter), event))

    def pop(self) -> Event:
        return heapq.heappop(self._queue)[-1]

    def __len__(self) -> int:
        return len(self._queue)

    def is_empty(self) -> bool:
        return not self._queue

