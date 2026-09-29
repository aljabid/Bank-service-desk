from __future__ import annotations

from datetime import datetime, timedelta

from .desk import ServiceDesk
from .models import Service

SERVICES = [
    ("SVC-01", "Money Transfer System (SBP)", "business service", 0.1, 1.0,
     "Head of Payment Systems", True),
    ("SVC-02", "Internet Banking", "business service", 0.25, 2.0,
     "Head of Digital Channels", False),
    ("SVC-03", "Card Processing System", "technical service", 0.1, 1.0,
     "Head of Card Processing", True),
    ("SVC-04", "AS Bank (core banking)", "technical service", 0.25, 4.0,
     "Head of Core Banking", False),
    ("SVC-05", "Call Center", "business service", 0.5, 4.0,
     "Head of Customer Support", False),
    ("SVC-06", "Data Center Network", "infrastructure service", 0.25, 2.0,
     "Head of Network Operations", False),
]

L1_OPERATORS = ["A. Petrov (L1)", "M. Sidorova (L1)"]
L2_ENGINEERS = {
    "SVC-01": "D. Kim (L2 Payments)",
    "SVC-02": "E. Volkova (L2 Web)",
    "SVC-03": "D. Kim (L2 Payments)",
    "SVC-04": "I. Smirnov (L2 Core)",
    "SVC-05": "M. Sidorova (L1)",
    "SVC-06": "S. Orlov (L2 Network)",
}

INCIDENTS = [
    ("SVC-01", "SBP transfers stuck in 'processing' status", "Critical",
     "2026-09-01 10:12", 4, 13, False),
    ("SVC-03", "Card authorizations declined for Mir cards", "Critical",
     "2026-09-02 14:30", 5, 42, False),
    ("SVC-02", "Internet banking login page returns error 502", "High",
     "2026-09-03 09:05", 10, 95, False),
    ("SVC-04", "End-of-day batch in core banking failed", "High",
     "2026-09-04 23:40", 20, 210, False),
    ("SVC-05", "IVR menu does not play the greeting", "Medium",
     "2026-09-05 11:00", 25, 150, False),
    ("SVC-01", "Incoming SBP transfers credited twice", "Critical",
     "2026-09-07 16:20", 3, 12, False),
    ("SVC-06", "Packet loss between main and backup data center", "High",
     "2026-09-08 08:45", 12, 100, False),
    ("SVC-02", "SMS confirmation codes are delayed", "Medium",
     "2026-09-09 13:10", 14, 115, False),
    ("SVC-03", "Partner POS terminals cannot connect to processing", "High",
     "2026-09-11 18:05", 6, 14, False),
    ("SVC-05", "Operator cannot open client card in CRM", "Low",
     "2026-09-12 10:30", 20, 35, True),
    ("SVC-04", "Slow account statement generation", "Medium",
     "2026-09-15 12:00", 10, 180, False),
    ("SVC-01", "QR payments via SBP time out", "Critical",
     "2026-09-17 19:50", 5, 27, False),
    ("SVC-02", "Client password reset request", "Low",
     "2026-09-18 09:20", 8, 12, True),
    ("SVC-03", "Card-to-card transfer limit error", "High",
     "2026-09-21 11:40", 4, 11, False),
    ("SVC-06", "Core switch power supply failure", "Critical",
     "2026-09-24 03:15", 30, 95, False),
]


def build_bank_service_desk(operators: int = 2) -> ServiceDesk:
    desk = ServiceDesk("Bank Service Desk", operators=operators)
    for sid, name, category, resp, res, owner, transfer in SERVICES:
        desk.add_service(Service(sid, name, category, resp, res, owner,
                                 money_transfer=transfer))

    for n, (sid, text, prio, created, resp_min, res_min, fcr) in enumerate(INCIDENTS):
        created_time = datetime.strptime(created, "%Y-%m-%d %H:%M")
        incident = desk.open_incident(sid, text, prio, created_time)
        engineer = L1_OPERATORS[n % 2] if fcr else L2_ENGINEERS[sid]
        incident.assign(engineer, created_time + timedelta(minutes=resp_min))
        resolved = created_time + timedelta(minutes=res_min)
        incident.resolve(resolved, first_contact=fcr)
        incident.close(resolved + timedelta(minutes=30))
    return desk
