import unittest
from datetime import datetime, timedelta

from service_desk.data import build_bank_service_desk
from service_desk.models import Incident, Service
from service_desk.simulation import Scenario, simulate_improvement
from service_desk.sla import (apply_money_transfer_policy, build_sla_report, calculate_resolution_time,
                              calculate_response_time, check_sla_compliance, critical_warning)
from service_desk.statistics import generate_incident_statistics

T0 = datetime(2026, 9, 1, 10, 0)


def make_incident(response_min, resolution_min, priority="High"):
    inc = Incident("INC-X", "SVC-01", "test", priority, T0)
    inc.assign("Engineer", T0 + timedelta(minutes=response_min))
    inc.resolve(T0 + timedelta(minutes=resolution_min))
    return inc


class TimeCalculationTest(unittest.TestCase):
    def test_response_and_resolution_time(self):
        inc = make_incident(6, 45)
        self.assertAlmostEqual(calculate_response_time(inc), 0.1)
        self.assertAlmostEqual(calculate_resolution_time(inc), 0.75)

    def test_open_incident_uses_current_time(self):
        inc = Incident("INC-Y", "SVC-01", "open", "Low", T0)
        self.assertAlmostEqual(calculate_resolution_time(inc, now=T0 + timedelta(hours=2)), 2.0)


class SlaComplianceTest(unittest.TestCase):
    def setUp(self):
        self.service = Service("SVC-01", "SBP", "business service", 0.1, 0.25, "Owner", money_transfer=True)

    def test_within_sla(self):
        self.assertTrue(check_sla_compliance(make_incident(5, 15), self.service).met)

    def test_resolution_violation(self):
        check = check_sla_compliance(make_incident(5, 16), self.service)
        self.assertTrue(check.response_met)
        self.assertFalse(check.resolution_met)
        self.assertFalse(check.met)

    def test_response_violation(self):
        self.assertFalse(check_sla_compliance(make_incident(7, 10), self.service).response_met)


class BankDataTest(unittest.TestCase):
    def setUp(self):
        self.desk = build_bank_service_desk()
        apply_money_transfer_policy(self.desk)

    def test_registers_size(self):
        self.assertGreaterEqual(len(self.desk.services), 5)
        self.assertEqual(len(self.desk.incidents), 15)

    def test_transfer_policy_is_15_minutes(self):
        for s in self.desk.services.values():
            if s.money_transfer:
                self.assertLessEqual(s.sla_resolution_time_hours, 0.25)

    def test_report_and_critical_warning(self):
        report = build_sla_report(self.desk)
        self.assertEqual(report.met, 11)
        self.assertAlmostEqual(report.compliance_percent, 73.33, places=2)
        self.assertIsNotNone(critical_warning(report))

    def test_adding_incident_changes_report(self):
        inc = self.desk.open_incident("SVC-05", "Headsets do not work", "Low", T0)
        inc.assign("A. Petrov (L1)", T0 + timedelta(minutes=10))
        inc.resolve(T0 + timedelta(minutes=30), first_contact=True)
        report = build_sla_report(self.desk)
        self.assertEqual(report.total, 16)
        self.assertEqual(report.met, 12)

    def test_statistics(self):
        stats = generate_incident_statistics(self.desk)
        self.assertEqual(sum(stats.count_by_service.values()), 15)
        self.assertEqual(len(stats.top_problem_services), 3)
        self.assertAlmostEqual(stats.first_contact_resolution_percent, 13.33, places=2)


class SimulationTest(unittest.TestCase):
    def setUp(self):
        self.desk = build_bank_service_desk()
        apply_money_transfer_policy(self.desk)

    def test_more_operators_improve_sla_and_keep_original(self):
        result = simulate_improvement(self.desk, Scenario("more staff", operators=3))
        self.assertGreater(result.after.compliance_percent, result.before.compliance_percent)
        self.assertAlmostEqual(build_sla_report(self.desk).compliance_percent, result.before.compliance_percent)

    def test_stricter_targets_reduce_sla(self):
        result = simulate_improvement(self.desk, Scenario("strict", target_changes={"SVC-02": (0.25, 1.0)}))
        self.assertLess(result.after.compliance_percent, result.before.compliance_percent)

    def test_best_scenario_removes_critical_warning(self):
        result = simulate_improvement(self.desk, Scenario(
            "runbooks", operators=3, resolution_reduction=0.7, reduction_services=["SVC-01", "SVC-03"]))
        self.assertIsNone(critical_warning(result.after))


if __name__ == "__main__":
    unittest.main()
