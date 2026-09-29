from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .desk import ServiceDesk
from .models import Incident, Service

TRANSFER_RESOLUTION_LIMIT_HOURS = 0.25
CRITICAL_VIOLATION_THRESHOLD = 10.0


def _hours(start: datetime, end: datetime) -> float:
    return (end - start).total_seconds() / 3600


def calculate_response_time(incident: Incident, now: datetime | None = None) -> float:
    end = incident.assigned_time or now or datetime.now()
    return _hours(incident.created_time, end)


def calculate_resolution_time(incident: Incident, now: datetime | None = None) -> float:
    end = incident.resolved_time or now or datetime.now()
    return _hours(incident.created_time, end)


@dataclass
class SlaCheck:
    incident_id: str
    service_id: str
    response_hours: float
    resolution_hours: float
    response_target: float
    resolution_target: float

    @property
    def response_met(self) -> bool:
        return self.response_hours <= self.response_target

    @property
    def resolution_met(self) -> bool:
        return self.resolution_hours <= self.resolution_target

    @property
    def met(self) -> bool:
        return self.response_met and self.resolution_met

    def reason(self) -> str:
        parts = []
        if not self.response_met:
            parts.append(f"response {self.response_hours * 60:.0f} min > {self.response_target * 60:.0f} min")
        if not self.resolution_met:
            parts.append(f"resolution {self.resolution_hours * 60:.0f} min > {self.resolution_target * 60:.0f} min")
        return "; ".join(parts) or "OK"


def check_sla_compliance(incident: Incident, service: Service,
                         now: datetime | None = None) -> SlaCheck:
    return SlaCheck(
        incident_id=incident.incident_id,
        service_id=service.service_id,
        response_hours=calculate_response_time(incident, now),
        resolution_hours=calculate_resolution_time(incident, now),
        response_target=service.sla_response_time_hours,
        resolution_target=service.sla_resolution_time_hours,
    )


def apply_money_transfer_policy(desk: ServiceDesk,
                                limit_hours: float = TRANSFER_RESOLUTION_LIMIT_HOURS) -> list[str]:
    changes = []
    for service in desk.services.values():
        if service.money_transfer and service.sla_resolution_time_hours > limit_hours:
            changes.append(f"{service.service_name}: resolution target "
                           f"{service.sla_resolution_time_hours * 60:.0f} min -> {limit_hours * 60:.0f} min")
            service.sla_resolution_time_hours = limit_hours
    return changes


@dataclass
class SlaReport:
    checks: list[SlaCheck]
    by_service: dict[str, tuple[int, int]]

    @property
    def total(self) -> int:
        return len(self.checks)

    @property
    def met(self) -> int:
        return sum(c.met for c in self.checks)

    @property
    def compliance_percent(self) -> float:
        return 100.0 * self.met / self.total if self.total else 100.0

    @property
    def violation_percent(self) -> float:
        return 100.0 - self.compliance_percent

    @property
    def violations(self) -> list[SlaCheck]:
        return [c for c in self.checks if not c.met]

    def service_percent(self, service_id: str) -> float:
        met, total = self.by_service.get(service_id, (0, 0))
        return 100.0 * met / total if total else 100.0


def build_sla_report(desk: ServiceDesk, now: datetime | None = None) -> SlaReport:
    checks = [check_sla_compliance(i, desk.get_service(i.service_id), now) for i in desk.incidents]
    by_service = {}
    for sid in desk.services:
        own = [c for c in checks if c.service_id == sid]
        by_service[sid] = (sum(c.met for c in own), len(own))
    return SlaReport(checks, by_service)


def critical_warning(report: SlaReport,
                     threshold: float = CRITICAL_VIOLATION_THRESHOLD) -> str | None:
    if report.violation_percent > threshold:
        return (f"CRITICAL WARNING: {report.violation_percent:.1f}% of incidents violated the SLA "
                f"(allowed: {threshold:.0f}%). Escalate to the IT director.")
    return None
