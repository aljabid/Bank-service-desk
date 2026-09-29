from __future__ import annotations

from datetime import datetime

from .models import Incident, Service


class ServiceDesk:
    def __init__(self, name: str, operators: int = 1) -> None:
        self.name = name
        self.operators = operators
        self.services: dict[str, Service] = {}
        self.incidents: list[Incident] = []

    def add_service(self, service: Service) -> None:
        if service.service_id in self.services:
            raise ValueError(f"Duplicate service_id: {service.service_id}")
        self.services[service.service_id] = service

    def get_service(self, service_id: str) -> Service:
        try:
            return self.services[service_id]
        except KeyError:
            raise KeyError(f"Service {service_id} is not in the register") from None

    def open_incident(self, service_id: str, description: str, priority: str,
                      created_time: datetime) -> Incident:
        self.get_service(service_id)
        incident = Incident(
            incident_id=f"INC-{len(self.incidents) + 1:03d}",
            service_id=service_id,
            description=description,
            priority=priority,
            created_time=created_time,
        )
        self.incidents.append(incident)
        return incident

    def get_incident(self, incident_id: str) -> Incident:
        for incident in self.incidents:
            if incident.incident_id == incident_id:
                return incident
        raise KeyError(f"Incident {incident_id} not found")

    def incidents_for(self, service_id: str) -> list[Incident]:
        return [i for i in self.incidents if i.service_id == service_id]
