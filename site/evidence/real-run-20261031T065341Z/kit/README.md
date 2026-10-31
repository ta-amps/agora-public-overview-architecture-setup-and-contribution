# Volunteer Shift Schedule Kit (synthetic data only)

Small kit for a fictional food pantry example. It turns a volunteer
availability CSV into a weekly shift schedule that meets the coverage
rules below. Everything here was built and tested on **synthetic data
only** — all names are placeholders like "Volunteer 01". No real names
or contact details are used anywhere.

## What the kit does

`shift_scheduler.py` (Python 3 standard library only) reads the
availability CSV, searches for a weekly assignment with deterministic
backtracking search, writes the schedule as CSV, and checks it against
every coverage rule.

## Input format

`data/availability.csv` has columns:

- `volunteer_id` — e.g. `V01`
- `display_name` — placeholder name, e.g. `Volunteer 01`
- `role` — `lead` or `general`
- `max_shifts` — most shifts this volunteer works in the week
- `available` — shifts separated by `;`, each written `Day-Slot`
  (e.g. `Mon-PM;Tue-PM;Thu-AM`)

## Coverage rules

- Shifts are Mon, Tue, Wed, Thu, Fri and Sat, each with an AM and a PM
  slot: 12 shifts, written `Day-Slot` (for example `Mon-AM`).
- Every shift has at least 2 volunteers.
- Every shift has at least 1 volunteer whose role is `lead`.
- A volunteer works only shifts listed in their `available` column.
- No volunteer works more shifts in the week than their `max_shifts`.
- No volunteer works both the AM and the PM shift on the same day.

## How to run it

```sh
python3 shift_scheduler.py data/availability.csv
python3 shift_scheduler.py data/availability.csv --out schedule.csv
```

The program prints the schedule and the number of violations. It exits
`0` only when there are no violations, and exits `2` with a clear
message when no valid schedule exists. Output CSV columns are
`shift,volunteer_id,display_name,role`.

`check_coverage(schedule, volunteers)` is importable from
`shift_scheduler` and returns a list of violation strings (empty when
every rule holds).

## How to run the tests

```sh
python3 -m unittest discover -s tests -v
```

The tests cover: the synthetic CSV yields a schedule with zero
violations; `check_coverage` reports each broken rule (unavailable
volunteer, over `max_shifts`, no lead, both shifts on one day, fewer
than 2 people); and an impossible input is reported, not silently
scheduled.
