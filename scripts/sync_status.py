"""Check every ta-amps service once, read-only, and write the status noun, site/content/status.json.

The services and the public address each one is checked at are listed in site/content/status-page.json. For each,
this script makes one GET with no credentials, no cookies, a timeout and one try, and keeps only what the answer
showed: its HTTP status, how long it took, whether a JSON health answer said ok, and the state that maps to. It also
reads the agent endpoints' daily check (its status address) and keeps the last run, its result and the next run.
It never sends a POST, never opens the Studio, and never asks for a session or a key.

scripts/build_site.py renders /status/ and /status.json from the noun, so the page and the JSON always agree. What a
person writes, such as recent problems, stays in status-page.json; this script never touches it.

Usage:
  python3 scripts/sync_status.py           check now and write site/content/status.json
  python3 scripts/sync_status.py --print   check now and print the noun, writing nothing
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import socket
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORDS = ROOT / "site" / "content" / "status-page.json"
NOUN = ROOT / "site" / "content" / "status.json"
FORMAT = "ta-amps.agora.status.v1"
AGENT = "ta-amps-agora-status/1 (one read-only GET per service)"
MOST = 2 * 1024 * 1024  # bytes read from any answer


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def utc_of(value) -> str | None:
    """A time the daily check wrote, as an ISO second in UTC, or None when it is not a time."""
    if isinstance(value, (int, float)) and value > 1e9:
        return dt.datetime.fromtimestamp(value, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if isinstance(value, str):
        try:
            when = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        if when.tzinfo is None:
            return None
        return when.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return None


def get(url: str, timeout: float) -> dict:
    """One GET, no credentials and one try. The answer's status, time and body, or why there was none."""
    if not url.startswith("https://"):
        raise SystemExit(f"sync_status: {url} is not an https address")
    request = urllib.request.Request(url, method="GET", headers={"User-Agent": AGENT,
                                                                 "Accept": "application/json, text/plain;q=0.9, */*;q=0.5"})
    started = time.monotonic()
    at = utc_now()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as answer:
            body = answer.read(MOST)
            status = answer.status
    except urllib.error.HTTPError as error:
        return {"checked_at": at, "http_status": error.code, "seconds": round(time.monotonic() - started, 3),
                "body": None, "error": f"HTTP {error.code}"}
    except (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError, OSError) as error:
        reason = getattr(error, "reason", error)
        timed_out = isinstance(reason, (socket.timeout, TimeoutError)) or "timed out" in str(reason)
        return {"checked_at": at, "http_status": None, "seconds": round(time.monotonic() - started, 3),
                "body": None, "error": "timed out" if timed_out else "no connection"}
    return {"checked_at": at, "http_status": status, "seconds": round(time.monotonic() - started, 3), "body": body,
            "error": None}


def health_ok(body: bytes | None) -> bool | None:
    """What a JSON health answer says about itself: its ok field, or None when it has none."""
    try:
        data = json.loads(body or b"")
    except ValueError:
        return None
    if isinstance(data, dict) and isinstance(data.get("ok"), bool):
        return data["ok"]
    return None


def state_of(answer: dict, ok: bool | None, slow_after: float) -> str:
    status = answer["http_status"]
    if status is None or not 200 <= status < 300 or ok is False:
        return "not_answering"
    return "slow" if answer["seconds"] > slow_after else "answering"


def check_service(service: dict, timeout: float, slow_after: float) -> dict:
    answer = get(service["check"], timeout)
    ok = health_ok(answer["body"]) if service["kind"] == "json" and answer["error"] is None else None
    row = {"id": service["id"], "url": service["check"], "checked_at": answer["checked_at"],
           "http_status": answer["http_status"], "seconds": answer["seconds"], "ok": ok,
           "state": state_of(answer, ok, slow_after)}
    if answer["error"]:
        row["error"] = answer["error"]
    return row


def daily_check(url: str, timeout: float) -> dict:
    """The agent endpoints' daily check of the live services, as its status address reports it."""
    answer = get(url, timeout)
    row = {"url": url, "checked_at": answer["checked_at"], "http_status": answer["http_status"]}
    if answer["error"] or answer["body"] is None:
        row["error"] = answer["error"] or "no answer"
        return row
    try:
        data = json.loads(answer["body"])
    except ValueError:
        row["error"] = "not JSON"
        return row
    row.update(read_daily(data))
    return row


def read_daily(data) -> dict:
    """From the daily check's status answer: the latest run's end, state and trigger, how many of the services it
    checked were healthy, the next scheduled run and the time the checks stop. A field the answer does not give
    stays out, so nothing is filled in by guess."""
    found: dict = {}
    if not isinstance(data, dict):
        return found
    latest = data.get("latest") if isinstance(data.get("latest"), dict) else {}
    when = utc_of(latest.get("finished_at"))
    if when:
        found["last_run"] = when
    for key in ("status", "trigger"):
        if isinstance(latest.get(key), str):
            found[key] = latest[key]
    surfaces = latest.get("surfaces")
    if isinstance(surfaces, dict) and surfaces and all(isinstance(v, str) for v in surfaces.values()):
        found["healthy"] = sum(1 for v in surfaces.values() if v == "healthy")
        found["total"] = len(surfaces)
    cadence = data.get("cadence") if isinstance(data.get("cadence"), dict) else {}
    upcoming = utc_of(cadence.get("next_scheduled_at"))
    if upcoming:
        found["next_run"] = upcoming
    if isinstance(cadence.get("interval_hours"), int):
        found["every_hours"] = cadence["interval_hours"]
    stops = utc_of(data.get("stop_at"))
    if stops:
        found["stops_at"] = stops
    return found


def noun(words: dict) -> dict:
    timeout, slow_after = float(words["timeout_seconds"]), float(words["slow_after_seconds"])
    started = utc_now()
    services = [check_service(service, timeout, slow_after) for service in words["services"]]
    return {
        "about": ("The status of every ta-amps service, written by scripts/sync_status.py from one read-only GET of "
                  "each public address in status-page.json, with no credentials and one try. scripts/build_site.py "
                  "renders /status/ and /status.json from it. Nothing here is a measurement of uptime."),
        "format": FORMAT,
        "checked_at": started,
        "how": f"one GET of each address, no credentials, a {int(timeout)}-second timeout and one try",
        "services": services,
        "daily": daily_check(words["daily"]["check"], timeout),
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--print", action="store_true", help="print the noun instead of writing it")
    args = parser.parse_args(argv)
    words = json.loads(WORDS.read_text(encoding="utf-8"))
    text = json.dumps(noun(words), indent=2, ensure_ascii=False) + "\n"
    if args.print:
        sys.stdout.write(text)
        return 0
    NOUN.write_text(text, encoding="utf-8")
    print(f"sync_status: wrote {NOUN.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
