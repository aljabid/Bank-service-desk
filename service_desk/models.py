from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

PRIORITIES = ("Low", "Medium", "High", "Critical")
CATEGORIES = ("business service", "technical service", "infrastructure service")
SERVICE_STATUSES = ("active", "under development", "supported", "decommissioned")
INCIDENT_STATUSES = ("New", "Assigned", "Resolved", "Closed")


@dataclass
class Service:
    service_id: str
    service_name: str
    service_category: str
    sla_response_time_hours: float
    sla_resolution_time_hours: float
    owner: str
    status: str = "active"
    priority_levels: tuple[str, ...] = PRIORITIES
    money_transfer: bool = False

    def __post_init__(self) -> None:
        if self.service_category not in CATEGORIES:
            raise ValueError(f"Unknown category: {self.service_category}")
        if self.status not in SERVICE_STATUSES:
            raise ValueError(f"Unknown service status: {self.status}")
        if self.sla_response_time_hours <= 0 or self.sla_resolution_time_hours <= 0:
            raise ValueError("SLA target times must be positive")


@dataclass
class Incident:
    incident_id: str
    service_id: str
    description: str
    priority: str
    created_time: datetime
    assigned_time: datetime | None = None
    resolved_time: datetime | None = None
    closed_time: datetime | None = None
    assigned_to: str | None = None
    status: str = "New"
    was_resolved_at_first_contact: bool = False
    history: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.priority not in PRIORITIES:
            raise ValueError(f"Unknown priority: {self.priority}")
        self.history.append(f"{self.created_time:%Y-%m-%d %H:%M} created ({self.priority})")

    def assign(self, engineer: str, when: datetime) -> None:
        if when < self.created_time:
            raise ValueError("Incident cannot be assigned before it was created")
        self.assigned_to = engineer
        self.assigned_time = when
        self.status = "Assigned"
        self.history.append(f"{when:%Y-%m-%d %H:%M} assigned to {engineer}")

    def resolve(self, when: datetime, first_contact: bool = False) -> None:
        if self.assigned_time is None:
            raise ValueError("Incident must be assigned before it is resolved")
        if when < self.assigned_time:
            raise ValueError("Incident cannot be resolved before it was assigned")
        self.resolved_time = when
        self.was_resolved_at_first_contact = first_contact
        self.status = "Resolved"
        self.history.append(f"{when:%Y-%m-%d %H:%M} resolved")

    def close(self, when: datetime) -> None:
        if self.resolved_time is None:
            raise ValueError("Only resolved incidents can be closed")
        self.closed_time = when
        self.status = "Closed"
        self.history.append(f"{when:%Y-%m-%d %H:%M} closed")
