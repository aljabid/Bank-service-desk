# IWS 1 – Managing IT services and support processes

Independent work 1, **Option 5: Financial organization (bank)**.

A small Service Desk model in Python: a register of the bank's IT services,
a register of incidents, SLA compliance analysis, incident statistics and
simulation of process improvements.

## Option 5 requirements

- Services: Money Transfer System (SBP), Internet Banking, Card Processing System,
  AS Bank (core banking), Call Center (+ Data Center Network as an infrastructure service).
- Resolution time for money transfer services is limited to **15 minutes**.
- Incident history of **15 incidents**, SLA compliance percentage.
- If more than **10 %** of incidents violate the SLA, a **critical warning** is issued.

## Requirements

- Python 3.10+
- No third-party packages (standard library only)

## Usage

```bash
python main.py                                   # full demonstration in the console
python ui.py                                     # desktop window (Tkinter)
python -m unittest discover -s tests -t . -v     # run the tests
```

The desktop window has five tabs: **Services** (register, edit SLA targets),
**Incidents** (register with SLA status, add a new incident), **SLA report**
(compliance by service with a chart, violations, critical warning banner),
**Statistics** and **Improvements** (run custom or preset scenarios).

`main()` prints:

1. the register of IT services;
2. the register of incidents with response/resolution time and SLA status;
3. the SLA compliance report (total and per service), the list of violations and the critical warning;
4. incident statistics: incidents per service, average resolution time by priority and by service,
   top 3 problematic services, first contact resolution (FCR);
5. improvement scenarios and their effect on SLA compliance.

## Project structure

```
main.py                     entry point, main() demonstration
ui.py                       desktop UI (Tkinter)
service_desk/
    models.py               Service and Incident (life cycle New -> Assigned -> Resolved -> Closed)
    desk.py                 ServiceDesk: service register and incident register
    data.py                 option 5 data: 6 bank services, 15 incidents (September 2026)
    sla.py                  calculate_response_time, calculate_resolution_time,
                            check_sla_compliance, money transfer policy, SLA report, critical warning
    statistics.py           generate_incident_statistics
    simulation.py           Scenario, simulate_improvement
    report.py               text tables for the console
tests/
    test_service_desk.py    unit tests
```

## How SLA is checked

- **Response time** = assignment time − creation time.
- **Resolution time** = resolution time − creation time.
- An incident meets the SLA if both times are within the targets of its service.
- **SLA compliance, %** = incidents within SLA / all incidents × 100.

## Improvement model

- **Operators:** response (waiting) time is proportional to the load per operator:
  `new_response = old_response × old_operators / new_operators`.
- **Resolution reduction:** the work time (resolution − response) is reduced by the given share
  (knowledge base, runbooks, automatic failover).
- **Target changes:** new SLA targets for selected services.

## Results (current data)

| Metric | Value |
|---|---|
| SLA compliance | 11 / 15 = **73.3 %** |
| Violations | 4 (26.7 %) → critical warning |
| Money transfer services within 15 min | 4 / 6 (66.7 %) |
| FCR | 13.3 % |

| Scenario | SLA after |
|---|---|
| A. +1 operator (2 → 3) | 80.0 % |
| B. +1 operator and runbooks / auto-failover for payment services | **93.3 %** (no critical warning) |
| C. Stricter targets for Internet Banking and AS Bank | 53.3 % |
