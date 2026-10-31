"""Weekly volunteer shift scheduler (synthetic data only).

Reads a volunteer availability CSV, builds a weekly schedule that meets
every coverage rule using deterministic backtracking search, and writes
the schedule as CSV with columns shift,volunteer_id,display_name,role.
"""

import argparse
import csv
import itertools
import sys

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
SLOTS = ["AM", "PM"]
SHIFTS = [d + "-" + s for d in DAYS for s in SLOTS]

SCHEDULE_FIELDS = ["shift", "volunteer_id", "display_name", "role"]


def load_volunteers(path):
    """Read the availability CSV into a list of volunteer dicts."""
    volunteers = []
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            available = set()
            raw = (row.get("available") or "").strip()
            if raw:
                for part in raw.split(";"):
                    part = part.strip()
                    if part:
                        available.add(part)
            volunteers.append(
                {
                    "volunteer_id": (row.get("volunteer_id") or "").strip(),
                    "display_name": (row.get("display_name") or "").strip(),
                    "role": (row.get("role") or "").strip(),
                    "max_shifts": int((row.get("max_shifts") or "0").strip()),
                    "available": available,
                }
            )
    volunteers.sort(key=lambda v: v["volunteer_id"])
    return volunteers


def check_coverage(schedule, volunteers):
    """Return a list of violation strings; empty when every rule holds."""
    violations = []
    by_id = {v["volunteer_id"]: v for v in volunteers}
    by_shift = {s: [] for s in SHIFTS}
    for entry in schedule or []:
        shift = entry.get("shift")
        vid = entry.get("volunteer_id")
        if shift not in by_shift:
            violations.append("unknown shift: %r" % (shift,))
            continue
        if vid not in by_id:
            violations.append("unknown volunteer %r on %s" % (vid, shift))
            continue
        by_shift[shift].append(vid)

    for shift in SHIFTS:
        assigned = by_shift[shift]
        if len(assigned) < 2:
            violations.append(
                "%s has %d volunteer(s); at least 2 required"
                % (shift, len(assigned))
            )
        if not any(
            by_id[vid]["role"] == "lead" for vid in assigned if vid in by_id
        ):
            violations.append("%s has no lead volunteer" % shift)

    counts = {}
    day_of = {}
    for entry in schedule or []:
        shift = entry.get("shift")
        vid = entry.get("volunteer_id")
        if shift not in by_shift or vid not in by_id:
            continue
        counts[vid] = counts.get(vid, 0) + 1
        day = shift.split("-")[0]
        day_of.setdefault(vid, []).append((day, shift))
        if shift not in by_id[vid]["available"]:
            violations.append(
                "%s works %s but is not available for it" % (vid, shift)
            )

    for vid, n in sorted(counts.items()):
        if n > by_id[vid]["max_shifts"]:
            violations.append(
                "%s works %d shifts; max is %d"
                % (vid, n, by_id[vid]["max_shifts"])
            )

    for vid in sorted(day_of):
        seen_days = {}
        for day, shift in day_of[vid]:
            seen_days.setdefault(day, []).append(shift)
        for day in sorted(seen_days):
            if len(seen_days[day]) > 1:
                violations.append(
                    "%s works both shifts on %s" % (vid, day)
                )

    return violations


def build_schedule(volunteers):
    """Build a valid schedule or return None when impossible.

    Assigns exactly 2 volunteers to each of the 12 shifts using
    deterministic depth-first backtracking. Shifts are attempted in order
    of fewest eligible volunteers (ties broken by canonical shift order);
    candidate pairs are tried in sorted volunteer_id order.
    """
    by_id = {v["volunteer_id"]: v for v in volunteers}

    def eligible(shift):
        return sorted(
            vid
            for vid, v in by_id.items()
            if shift in v["available"]
        )

    order = sorted(SHIFTS, key=lambda s: (len(eligible(s)), SHIFTS.index(s)))

    assignment = {}
    counts = {vid: 0 for vid in by_id}
    worked_days = {vid: set() for vid in by_id}

    def candidates_for(shift):
        day = shift.split("-")[0]
        out = []
        for vid in sorted(by_id):
            v = by_id[vid]
            if shift not in v["available"]:
                continue
            if counts[vid] >= v["max_shifts"]:
                continue
            if day in worked_days[vid]:
                continue
            out.append(vid)
        return out

    def feasible_remaining(pos):
        # Forward check: every unassigned shift must still be fillable.
        for j in range(pos, len(order)):
            shift = order[j]
            cands = candidates_for(shift)
            if len(cands) < 2:
                return False
            if not any(by_id[c]["role"] == "lead" for c in cands):
                return False
        return True

    def dfs(pos):
        if pos == len(order):
            return True
        shift = order[pos]
        cands = candidates_for(shift)
        pairs = [
            p
            for p in itertools.combinations(cands, 2)
            if any(by_id[c]["role"] == "lead" for c in p)
        ]
        for a, b in pairs:
            day = shift.split("-")[0]
            assignment[shift] = (a, b)
            counts[a] += 1
            counts[b] += 1
            worked_days[a].add(day)
            worked_days[b].add(day)
            if feasible_remaining(pos + 1) and dfs(pos + 1):
                return True
            counts[a] -= 1
            counts[b] -= 1
            worked_days[a].discard(day)
            worked_days[b].discard(day)
            del assignment[shift]
        return False

    if not dfs(0):
        return None

    schedule = []
    for shift in SHIFTS:
        for vid in sorted(assignment[shift]):
            v = by_id[vid]
            schedule.append(
                {
                    "shift": shift,
                    "volunteer_id": vid,
                    "display_name": v["display_name"],
                    "role": v["role"],
                }
            )
    return schedule


def write_schedule(schedule, path):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=SCHEDULE_FIELDS)
        writer.writeheader()
        for entry in schedule:
            writer.writerow({k: entry.get(k, "") for k in SCHEDULE_FIELDS})


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Build a weekly volunteer shift schedule."
    )
    parser.add_argument("input", help="availability CSV path")
    parser.add_argument(
        "--out", default="schedule.csv", help="output schedule CSV path"
    )
    args = parser.parse_args(argv)

    try:
        volunteers = load_volunteers(args.input)
    except (OSError, ValueError) as exc:
        print("error: cannot read input: %s" % exc)
        return 2

    schedule = build_schedule(volunteers)
    if schedule is None:
        print("error: no valid schedule exists for this input")
        return 2

    write_schedule(schedule, args.out)
    for entry in schedule:
        print(
            "%s,%s,%s,%s"
            % (
                entry["shift"],
                entry["volunteer_id"],
                entry["display_name"],
                entry["role"],
            )
        )
    violations = check_coverage(schedule, volunteers)
    print("violations: %d" % len(violations))
    for v in violations:
        print("violation: %s" % v)
    return 0 if not violations else 1


if __name__ == "__main__":
    sys.exit(main())
