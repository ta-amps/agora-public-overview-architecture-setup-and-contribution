"""unittest tests for shift_scheduler (synthetic data only)."""

import csv
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shift_scheduler import (  # noqa: E402
    SHIFTS,
    build_schedule,
    check_coverage,
    load_volunteers,
)

DATA_CSV = os.path.join(os.path.dirname(__file__), "..", "data",
                         "availability.csv")


def make_volunteers():
    return [
        {"volunteer_id": "L1", "display_name": "Lead One", "role": "lead",
         "max_shifts": 6, "available": set(SHIFTS)},
        {"volunteer_id": "L2", "display_name": "Lead Two", "role": "lead",
         "max_shifts": 6, "available": set(SHIFTS)},
        {"volunteer_id": "G1", "display_name": "Gen One", "role": "general",
         "max_shifts": 6, "available": set(SHIFTS)},
        {"volunteer_id": "G2", "display_name": "Gen Two", "role": "general",
         "max_shifts": 6, "available": set(SHIFTS)},
    ]


def full_schedule(volunteers):
    sched = []
    for shift in SHIFTS:
        for v in volunteers:
            sched.append({"shift": shift, "volunteer_id": v["volunteer_id"],
                          "display_name": v["display_name"], "role": v["role"]})
    return sched


class TestSyntheticSchedule(unittest.TestCase):
    def test_synthetic_csv_yields_zero_violations(self):
        volunteers = load_volunteers(DATA_CSV)
        schedule = build_schedule(volunteers)
        self.assertIsNotNone(schedule,
                             "expected a valid schedule for synthetic CSV")
        self.assertEqual(check_coverage(schedule, volunteers), [])
        # Deterministic: same input gives same schedule.
        again = build_schedule(volunteers)
        self.assertEqual(schedule, again)

    def test_cli_and_output_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "schedule.csv")
            proc = subprocess.run(
                [sys.executable, "shift_scheduler.py", DATA_CSV,
                 "--out", out],
                cwd=os.path.join(os.path.dirname(__file__), ".."),
                capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn("violations: 0", proc.stdout)
            with open(out, newline="", encoding="utf-8") as fh:
                rows = list(csv.DictReader(fh))
            self.assertEqual(
                [r for r in rows][:1][0].keys() if rows else set(),
                {"shift", "volunteer_id", "display_name", "role"})
            volunteers = load_volunteers(DATA_CSV)
            self.assertEqual(check_coverage(rows, volunteers), [])


class TestCheckCoverageRules(unittest.TestCase):
    def test_unavailable_volunteer_reported(self):
        volunteers = make_volunteers()
        sched = full_schedule(volunteers)
        sched[0] = {"shift": "Mon-AM", "volunteer_id": "G1",
                    "display_name": "Gen One", "role": "general"}
        volunteers[2]["available"] = set(SHIFTS) - {"Mon-AM"}
        violations = check_coverage(sched, volunteers)
        self.assertTrue(any("not available" in v for v in violations),
                        violations)

    def test_over_max_shifts_reported(self):
        volunteers = make_volunteers()
        volunteers[0]["max_shifts"] = 1
        sched = full_schedule(volunteers)
        violations = check_coverage(sched, volunteers)
        self.assertTrue(any("max" in v for v in violations), violations)

    def test_no_lead_reported(self):
        volunteers = make_volunteers()
        sched = []
        for shift in SHIFTS:
            sched.append({"shift": shift, "volunteer_id": "G1",
                          "display_name": "Gen One", "role": "general"})
            sched.append({"shift": shift, "volunteer_id": "G2",
                          "display_name": "Gen Two", "role": "general"})
        violations = check_coverage(sched, volunteers)
        self.assertTrue(any("lead" in v for v in violations), violations)

    def test_both_shifts_same_day_reported(self):
        volunteers = make_volunteers()
        sched = []
        for shift in SHIFTS:
            if shift in ("Mon-AM", "Mon-PM"):
                sched.append({"shift": shift, "volunteer_id": "L1",
                              "display_name": "Lead One", "role": "lead"})
                sched.append({"shift": shift, "volunteer_id": "G1",
                              "display_name": "Gen One", "role": "general"})
            else:
                sched.append({"shift": shift, "volunteer_id": "L2",
                              "display_name": "Lead Two", "role": "lead"})
                sched.append({"shift": shift, "volunteer_id": "G2",
                              "display_name": "Gen Two", "role": "general"})
        violations = check_coverage(sched, volunteers)
        self.assertTrue(any("both shifts" in v for v in violations),
                        violations)

    def test_fewer_than_two_reported(self):
        volunteers = make_volunteers()
        sched = [{"shift": "Mon-AM", "volunteer_id": "L1",
                  "display_name": "Lead One", "role": "lead"}]
        violations = check_coverage(sched, volunteers)
        self.assertTrue(any("Mon-AM" in v for v in violations), violations)

    def test_impossible_input_reported_not_silently_scheduled(self):
        volunteers = [
            {"volunteer_id": "L1", "display_name": "Lead One",
             "role": "lead", "max_shifts": 1, "available": {"Mon-AM"}},
        ]
        self.assertIsNone(build_schedule(volunteers))
        with tempfile.TemporaryDirectory() as tmp:
            inp = os.path.join(tmp, "impossible.csv")
            with open(inp, "w", newline="", encoding="utf-8") as fh:
                w = csv.writer(fh)
                w.writerow(["volunteer_id", "display_name", "role",
                            "max_shifts", "available"])
                w.writerow(["L1", "Lead One", "lead", "1", "Mon-AM"])
            proc = subprocess.run(
                [sys.executable, "shift_scheduler.py", inp,
                 "--out", os.path.join(tmp, "o.csv")],
                cwd=os.path.join(os.path.dirname(__file__), ".."),
                capture_output=True, text=True)
            self.assertEqual(proc.returncode, 2,
                             proc.stdout + proc.stderr)
            self.assertIn("no valid schedule", proc.stdout.lower())


if __name__ == "__main__":
    unittest.main()
