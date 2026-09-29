from service_desk.data import build_bank_service_desk
from service_desk.desk import ServiceDesk
from service_desk.report import hours, minutes, table, title
from service_desk.simulation import Scenario, simulate_improvement
from service_desk.sla import (CRITICAL_VIOLATION_THRESHOLD, apply_money_transfer_policy,
                              build_sla_report, critical_warning)
from service_desk.statistics import generate_incident_statistics


def show_service_register(desk: ServiceDesk) -> None:
    print(title("1. REGISTER OF IT SERVICES"))
    rows = [[s.service_id, s.service_name, s.service_category, minutes(s.sla_response_time_hours),
             minutes(s.sla_resolution_time_hours), "/".join(p[0] for p in s.priority_levels),
             s.owner, s.status, "yes" if s.money_transfer else "no"]
            for s in desk.services.values()]
    print(table(["ID", "Service", "Category", "Response", "Resolution", "Prio",
                 "Owner", "Status", "Transfer"], rows, "lllrrllll"))


def show_incident_register(desk: ServiceDesk) -> None:
    print(title("2. REGISTER OF INCIDENTS"))
    report = build_sla_report(desk)
    rows = []
    for inc, check in zip(desk.incidents, report.checks):
        rows.append([inc.incident_id, inc.service_id, inc.priority, f"{inc.created_time:%d.%m %H:%M}",
                     inc.assigned_to, minutes(check.response_hours), minutes(check.resolution_hours),
                     inc.status, "yes" if inc.was_resolved_at_first_contact else "no",
                     "OK" if check.met else "VIOLATED"])
    print(table(["ID", "Service", "Priority", "Created", "Assigned to", "Response",
                 "Resolution", "Status", "FCR", "SLA"], rows, "lllllrrlll"))
    print("\nIncident descriptions:")
    for inc in desk.incidents:
        print(f"  {inc.incident_id}  {inc.description}")


def show_sla_report(desk: ServiceDesk) -> None:
    print(title("3. SLA COMPLIANCE REPORT"))
    report = build_sla_report(desk)
    rows = []
    for sid, service in desk.services.items():
        met, total = report.by_service[sid]
        rows.append([sid, service.service_name, total, met, total - met, f"{report.service_percent(sid):.1f}%"])
    rows.append(["", "TOTAL", report.total, report.met, report.total - report.met,
                 f"{report.compliance_percent:.1f}%"])
    print(table(["ID", "Service", "Incidents", "SLA met", "Violated", "Compliance"], rows, "llrrrr"))

    print("\nIncidents that violated the SLA:")
    for check in report.violations:
        inc = desk.get_incident(check.incident_id)
        print(f"  {check.incident_id} [{inc.priority}] {desk.get_service(check.service_id).service_name}: "
              f"{check.reason()}")

    transfer_ids = [sid for sid, s in desk.services.items() if s.money_transfer]
    t_checks = [c for c in report.checks if c.service_id in transfer_ids]
    t_met = sum(c.met for c in t_checks)
    print(f"\nMoney transfer services (15-minute rule): {t_met}/{len(t_checks)} incidents within SLA "
          f"({100 * t_met / len(t_checks):.1f}%)")

    warning = critical_warning(report)
    print(f"\nViolation share: {report.violation_percent:.1f}% (threshold {CRITICAL_VIOLATION_THRESHOLD:.0f}%)")
    print(f"!!! {warning}" if warning else "SLA violations are within the allowed limit.")


def show_statistics(desk: ServiceDesk) -> None:
    print(title("4. INCIDENT STATISTICS"))
    stats = generate_incident_statistics(desk)
    rows = [[sid, desk.services[sid].service_name, n, hours(stats.avg_resolution_by_service.get(sid, 0))]
            for sid, n in stats.count_by_service.items()]
    print(table(["ID", "Service", "Incidents", "Avg resolution"], rows, "llrr"))

    print("\nAverage resolution time by priority:")
    print(table(["Priority", "Avg resolution"],
                [[p, hours(v)] for p, v in stats.avg_resolution_by_priority.items()], "lr"))

    print("\nTop 3 most problematic services (by number of incidents, then SLA violations):")
    for place, (sid, n, v) in enumerate(stats.top_problem_services, 1):
        print(f"  {place}. {desk.services[sid].service_name}: {n} incidents, {v} SLA violation(s)")

    print(f"\nFirst contact resolution (FCR): {stats.first_contact_resolution_percent:.1f}%")


SCENARIOS = [
    Scenario("A. +1 Service Desk operator (2 -> 3)", operators=3),
    Scenario("B. +1 operator and runbooks/auto-failover for payment services",
             operators=3, resolution_reduction=0.7, reduction_services=["SVC-01", "SVC-03"]),
    Scenario("C. Stricter targets: Internet Banking and AS Bank resolution in 1 h",
             target_changes={"SVC-02": (0.25, 1.0), "SVC-04": (0.25, 1.0)}),
]


def show_improvements(desk: ServiceDesk) -> None:
    print(title("5. IMPROVEMENT SCENARIOS"))
    rows = []
    for scenario in SCENARIOS:
        result = simulate_improvement(desk, scenario)
        rows.append([scenario.name, f"{result.before.compliance_percent:.1f}%",
                     f"{result.after.compliance_percent:.1f}%", f"{result.change_points:+.1f}",
                     len(result.after.violations),
                     "YES" if critical_warning(result.after) else "no"])
    print(table(["Scenario", "SLA before", "SLA after", "Change", "Violations", "Critical warning"],
                rows, "lrrrrl"))
    best = max(SCENARIOS, key=lambda s: simulate_improvement(desk, s).after.compliance_percent)
    print(f"\nBest scenario: {best.name}")


def main() -> None:
    desk = build_bank_service_desk(operators=2)
    print(f"{desk.name}: {len(desk.services)} services, {len(desk.incidents)} incidents, "
          f"{desk.operators} operators")

    print("\nOption 5 policy - resolution time for money transfer services <= 15 minutes:")
    for change in apply_money_transfer_policy(desk):
        print(f"  {change}")

    show_service_register(desk)
    show_incident_register(desk)
    show_sla_report(desk)
    show_statistics(desk)
    show_improvements(desk)


if __name__ == "__main__":
    main()
