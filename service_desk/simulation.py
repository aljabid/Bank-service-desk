from __future__ import annotations

import copy
from dataclasses import dataclass, field
from datetime import timedelta

from .desk import ServiceDesk
from .sla import SlaReport, build_sla_report, calculate_resolution_time, calculate_response_time


@dataclass
class Scenario:
    name: str
    operators: int | None = None
    resolution_reduction: float = 0.0
    reduction_services: list[str] | None = None
    target_changes: dict[str, tuple[float, float]] = field(default_factory=dict)


@dataclass
class ScenarioResult:
    scenario: Scenario
    before: SlaReport
    after: SlaReport
    desk_after: ServiceDesk

    @property
    def change_points(self) -> float:
        return self.after.compliance_percent - self.before.compliance_percent


def simulate_improvement(desk: ServiceDesk, scenario: Scenario) -> ScenarioResult:
    before = build_sla_report(desk)
    sim = copy.deepcopy(desk)

    if scenario.operators:
        load_factor = desk.operators / scenario.operators
        sim.operators = scenario.operators
    else:
        load_factor = 1.0

    for incident in sim.incidents:
        response = calculate_response_time(incident)
        work = calculate_resolution_time(incident) - response
        new_response = response * load_factor
        applies = scenario.reduction_services is None or incident.service_id in scenario.reduction_services
        new_work = work * (1 - scenario.resolution_reduction) if applies else work

        incident.assigned_time = incident.created_time + timedelta(hours=new_response)
        if incident.resolved_time is not None:
            closing_delay = (incident.closed_time - incident.resolved_time) if incident.closed_time else None
            incident.resolved_time = incident.assigned_time + timedelta(hours=new_work)
            if closing_delay is not None:
                incident.closed_time = incident.resolved_time + closing_delay

    for sid, (response_h, resolution_h) in scenario.target_changes.items():
        service = sim.get_service(sid)
        service.sla_response_time_hours = response_h
        service.sla_resolution_time_hours = resolution_h

    return ScenarioResult(scenario, before, build_sla_report(sim), sim)
