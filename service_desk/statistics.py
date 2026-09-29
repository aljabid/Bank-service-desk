from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from statistics import mean

from .desk import ServiceDesk
from .models import PRIORITIES
from .sla import build_sla_report, calculate_resolution_time


@dataclass
class IncidentStatistics:
    count_by_service: dict[str, int]
    avg_resolution_by_priority: dict[str, float]
    avg_resolution_by_service: dict[str, float]
    top_problem_services: list[tuple[str, int, int]]
    first_contact_resolution_percent: float


def generate_incident_statistics(desk: ServiceDesk) -> IncidentStatistics:
    incidents = desk.incidents
    report = build_sla_report(desk)
    violations = Counter(c.service_id for c in report.violations)
    counts = Counter(i.service_id for i in incidents)

    count_by_service = {sid: counts.get(sid, 0) for sid in desk.services}

    by_priority = {}
    for prio in PRIORITIES:
        times = [calculate_resolution_time(i) for i in incidents if i.priority == prio]
        if times:
            by_priority[prio] = mean(times)

    by_service = {}
    for sid in desk.services:
        times = [calculate_resolution_time(i) for i in desk.incidents_for(sid)]
        if times:
            by_service[sid] = mean(times)

    ranked = sorted(desk.services, key=lambda s: (count_by_service[s], violations.get(s, 0)), reverse=True)
    top3 = [(sid, count_by_service[sid], violations.get(sid, 0)) for sid in ranked[:3]]

    fcr = 100.0 * sum(i.was_resolved_at_first_contact for i in incidents) / len(incidents) if incidents else 0.0

    return IncidentStatistics(count_by_service, by_priority, by_service, top3, fcr)
