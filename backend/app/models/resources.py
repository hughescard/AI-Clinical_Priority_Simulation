from __future__ import annotations

from pydantic import BaseModel, Field


class ResourcePool(BaseModel):
    capacities: dict[str, int] = Field(default_factory=dict)
    in_use: dict[str, int] = Field(default_factory=dict)

    def available(self, resource_name: str) -> int:
        return self.capacities.get(resource_name, 0) - self.in_use.get(resource_name, 0)

    def can_allocate(self, required_resources: list[str]) -> bool:
        counts: dict[str, int] = {}
        for resource in required_resources:
            counts[resource] = counts.get(resource, 0) + 1
        return all(self.available(name) >= amount for name, amount in counts.items())

    def allocate(self, required_resources: list[str]) -> bool:
        if not self.can_allocate(required_resources):
            return False
        for resource in required_resources:
            self.in_use[resource] = self.in_use.get(resource, 0) + 1
        return True

    def release(self, required_resources: list[str]) -> None:
        for resource in required_resources:
            current = self.in_use.get(resource, 0)
            if current <= 1:
                self.in_use.pop(resource, None)
            else:
                self.in_use[resource] = current - 1

    def snapshot(self) -> dict[str, dict[str, int]]:
        return {
            name: {
                "capacity": capacity,
                "in_use": self.in_use.get(name, 0),
                "available": self.available(name),
            }
            for name, capacity in self.capacities.items()
        }

