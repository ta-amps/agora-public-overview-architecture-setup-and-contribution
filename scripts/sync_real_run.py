"""Write the replay noun, site/content/real-run.json, and the run's public evidence from one recorded run folder.

A run folder is the local record of one real run, and it is private: it holds key prefixes and local addresses.
  * run-facts.json           the run id, its start, the fabric, the Tessera revision, the harnesses and the model;
  * trace.jsonl              every call the two workers made, in order, each with its seq number;
  * final-readback.json      Tessera's own records, read back at the end: the tasks, results, receipts, nouns and
                             the append-only event log;
  * public-e2e-receipt.json  the run's public receipt, with its privacy and spend guardrails;
  * setup-calls.jsonl        the setup calls before the workers started. It is read to confirm that the requester
                             signed itself up, and it is never copied.

The script refuses, before it reads anything else, unless the public receipt says synthetic_data_only and that no
private or nonprofit data and no raw credential was sent. It then refuses when the run is not one request split
into a build and a review, or when a recorded hash does not recompute: each kit file's SHA-256, the draft digest over
them, the input noun's SHA-256, and both of Tessera's receipts, which are SHA-256 over the canonical JSON of the
result, as Tessera's receiptHash computes them.

What it writes:
  * site/content/real-run.json: the run's facts and its five steps. Each step has what happened in plain words, the
    actor, the task ids, the state changes, one hash with what it is, its receipt file, and the trace seq numbers and
    Tessera event numbers it comes from. The state changes follow Tessera's own state machine at the run's revision:
    a task is created ready, or waiting when it depends on another; a claim leases it; a split makes it wait for its
    children; a finished dependency or the last finished child makes it ready; a submit records its state after;
  * site/evidence/real-run-<run id>/: run-facts.json and trace.jsonl unchanged; tessera-readback.json, the sections
    of final-readback.json the replay needs, each unchanged; steps/<n>-<id>.json, one receipt file per step that
    copies the trace lines, Tessera events and records the step comes from; and kit/, the four files the builder
    stored, whose bytes are their nouns' content.

Everything it would write is scanned for /home/, tan_, tsk_, hmk_ and Bearer first, and nothing is written when one
appears. Stdlib only, and no network.

Usage:
  python3 scripts/sync_real_run.py RUN_FOLDER            write the noun and the evidence
  python3 scripts/sync_real_run.py RUN_FOLDER --check    fail when they differ from what the folder gives
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
NOUN = SITE / "content" / "real-run.json"
FORMAT = "ta-amps.real-run-replay.v1"
STEP_FORMAT = "ta-amps.real-run-step-receipt.v1"
FORBIDDEN = ("/home/", "tan_", "tsk_", "hmk_", "Bearer")
# Sections of final-readback.json the replay leaves out: the access audit (hashed client addresses and request ids),
# the queue counts, and the requester's view, which repeats the request record.
LEFT_OUT = ("audit", "counts", "requester_view")
RUN_ID = re.compile(r"\d{8}T\d{6}Z\Z")


class SyncError(Exception):
    pass


def fail(message: str) -> None:
    raise SyncError(message)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_json(path: Path) -> dict:
    if not path.is_file():
        fail(f"missing {path.name}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        fail(f"{path.name} is not JSON: {error}")


def read_lines(path: Path) -> list[dict]:
    if not path.is_file():
        fail(f"missing {path.name}")
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def canonical(value) -> str:
    """Tessera's canonicalJson: sorted keys, no spaces, strings as JSON.stringify writes them."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def receipt_hash(result: dict) -> str:
    """Tessera's receiptHash(task_id, fencing_token, ok, output, error) over a stored result."""
    body = {"error": None if result["error"] is None else str(result["error"]),
            "fencing_token": int(result["fencing_token"]), "ok": bool(result["ok"]),
            "output": result["output"], "task_id": str(result["task_id"])}
    return sha256(canonical(body).encode("utf-8"))


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


# The guard -----------------------------------------------------------------------------------------

def guard(folder: Path) -> dict:
    """The public receipt must say the run used synthetic data only and sent no private data or credential."""
    receipt = read_json(folder / "public-e2e-receipt.json")
    rails = receipt.get("privacy_and_spend_guardrails") or {}
    require(receipt.get("synthetic_data_only") is True, "the receipt does not say synthetic_data_only; refusing")
    require(rails.get("private_or_ngo_data_sent") is False, "the receipt does not say that no private data was sent; refusing")
    require(rails.get("raw_credentials_included") is False, "the receipt does not say that no credential was included; refusing")
    return receipt


# Reading the run -----------------------------------------------------------------------------------

class Run:
    def __init__(self, folder: Path) -> None:
        self.folder = folder
        self.receipt = guard(folder)
        self.facts = read_json(folder / "run-facts.json")
        self.run_id = self.facts.get("run_id", "")
        require(bool(RUN_ID.fullmatch(self.run_id)), "run-facts.json needs a run id like 20261031T065341Z")
        runs = [r for r in self.receipt.get("completed_e2e_runs", []) if r.get("run_id") == self.run_id]
        require(len(runs) == 1, f"the public receipt lists run {self.run_id} {len(runs)} times, not once")
        self.entry = runs[0]
        self.trace_bytes = (folder / "trace.jsonl").read_bytes() if (folder / "trace.jsonl").is_file() else b""
        self.trace = read_lines(folder / "trace.jsonl")
        self.readback = read_json(folder / "final-readback.json")
        self.setup = read_lines(folder / "setup-calls.jsonl")
        self.events = self.readback["events"]["events"]
        verbs = self.entry["verbs"]
        self.request_id = verbs["request"]["task_id"]
        self.build_id = verbs["build"]["task_id"]
        self.review_id = verbs["review"]["task_id"]
        self.check_shape()

    def check_shape(self) -> None:
        brief = self.readback["request"]["brief"]
        require(brief.get("synthetic") is True, "the request brief is not marked synthetic; refusing")
        for record in self.readback["nouns:kit.inputs"]["records"]:
            require(record["value"].get("synthetic") is True, "an input noun is not marked synthetic; refusing")
        require(self.entry["principals"]["builder_neq_reviewer"] is True and
                self.entry["principals"]["builder_key_id"] != self.entry["principals"]["reviewer_key_id"],
                "the builder and the reviewer must hold different keys")
        require([row["seq"] for row in self.trace] == list(range(1, len(self.trace) + 1)),
                "trace.jsonl must number its events 1, 2, 3 and so on")
        require([e["seq"] for e in self.events] == list(range(1, len(self.events) + 1)),
                "the event log must number its events 1, 2, 3 and so on")
        for part, task_id in (("request", self.request_id), ("build", self.build_id), ("review", self.review_id)):
            require(self.readback[part]["task_id"] == task_id, f"the readback's {part} is another task")
        require(self.readback["build"]["parent_id"] == self.request_id and
                self.readback["review"]["parent_id"] == self.request_id, "build and review must be the request's children")
        filed = [c for c in self.setup if c["path"] == "/v1/session/requester" and c["status"] == 201]
        require(len(filed) == 1 and filed[0]["actor"].startswith("requester (self-serve"),
                "the requester must have signed itself up once")
        asked = [c for c in self.setup if c["actor"] == "requester" and c["method"] == "POST"
                 and c["path"].endswith("/v1/tasks") and c["status"] == 201]
        require(len(asked) == 1 and asked[0]["request"]["kind"] == "request", "the requester must have filed one request")

    def role(self, row: dict) -> str:
        ends = row["from"] + " " + row["to"]
        if "(builder)" in ends:
            return "builder"
        if "(reviewer)" in ends:
            return "reviewer"
        fail(f"trace event {row['seq']} belongs to neither worker")


# Checking the hashes -------------------------------------------------------------------------------

def check_hashes(run: Run) -> dict:
    """Recompute every hash the replay shows, and return them."""
    rb, entry = run.readback, run.entry
    results = {}
    for part, task_id in (("build", run.build_id), ("review", run.review_id)):
        listed = rb[f"{part}_results"]["results"]
        require(len(listed) == 1, f"the {part} task needs exactly one result")
        result = listed[0]
        computed = receipt_hash(result)
        recorded = {result["receipt_hash"], entry["verbs"][part]["receipt_hash"]}
        recorded |= {x["receipt_hash"] for x in rb[f"{part}_executions"]["executions"]}
        recorded |= {x["receipt_hash"] for x in rb[f"{part}_execution_records"]}
        recorded |= {e["detail"]["receipt_hash"] for e in run.events if e["type"] == "submitted" and e["task_id"] == task_id}
        recorded |= {r["receipt_hash"] for r in run.trace if r["op"] == "submit" and r.get("verb_id") == task_id
                     and r["kind"] == "response" and r.get("outcome") == "ok"}
        require(recorded == {computed}, f"the {part} receipt does not recompute: {sorted(recorded)} vs {computed}")
        results[part] = result
    output = json.loads(results["build"]["output"])
    files = output["draft"]["files"]
    store = output["draft"]["store"]
    nouns = {r["key"]: r for r in rb[f"nouns:{store}"]["records"]}
    kit = {}
    for path, pin in sorted(files.items()):
        record = nouns.get(pin["key"])
        require(record is not None and record["version"] == pin["version"], f"no noun {pin['key']} at its version")
        value = json.loads(record["value"])
        content = value["content"].encode("utf-8")
        require(value["path"] == path and sha256(content) == pin["sha256"] == value["sha256"],
                f"{path} does not hash to its recorded SHA-256")
        listed = [n for n in entry["nouns"]["kit_deliverable_nouns"] if n["path"] == path]
        require(len(listed) == 1 and listed[0]["sha256"] == pin["sha256"] and listed[0]["content_bytes"] == len(content),
                f"the public receipt disagrees about {path}")
        kit[path] = {"key": pin["key"], "sha256": pin["sha256"], "bytes": len(content), "content": content}
    digest = sha256(canonical({path: pin["sha256"] for path, pin in files.items()}).encode("utf-8"))
    review_out = json.loads(results["review"]["output"])
    require(digest == output["blob_sha256"] == review_out["draft_sha256"] == entry["verbs"]["build"]["submitted_output"]["blob_sha256"],
            "the draft digest does not recompute from the four files")
    brief = rb["build"]["brief"]
    pin = brief["input_noun"]
    inputs = [r for r in rb[f"nouns:{pin['store']}"]["records"] if r["key"] == pin["key"] and r["version"] == pin["version"]]
    require(len(inputs) == 1, "the build brief names an input noun the readback does not hold")
    csv = inputs[0]["value"][pin["field"]].encode("utf-8")
    require(sha256(csv) == pin["sha256"] == kit[pin["save_as"]]["sha256"], "the input noun does not hash to its recorded SHA-256")
    return {"results": results, "output": output, "review": review_out, "kit": kit, "digest": digest,
            "input": {"store": pin["store"], "key": pin["key"], "version": pin["version"], "sha256": pin["sha256"]},
            "store": store}


# Steps --------------------------------------------------------------------------------------------

def review_store(run: Run) -> str:
    stores = {n["store"] for n in run.entry["nouns"]["review_nouns"]}
    require(len(stores) == 1, "the review must store its verdict in one store")
    return stores.pop()


def event_step(run: Run, event: dict, stores: dict) -> int | None:
    """Which replayed step a Tessera event belongs to; None for setup, such as keys and queues."""
    kind, task = event["type"], event["task_id"]
    if kind in {"key_issued", "queue_defined"}:
        return None
    if kind in {"enqueued", "split"} or (kind == "claimed" and task == run.request_id):
        return 1
    if kind == "records_written":
        written = {w["store"] for w in event["detail"]["writes"]}
        for step, store in ((1, stores["input"]), (2, stores["kit"]), (4, stores["review"])):
            if written == {store}:
                return step
    if kind in {"claimed", "heartbeat"} and task == run.build_id:
        return 2
    if (kind == "submitted" and task == run.build_id) or (kind == "dependencies_met" and task == run.review_id):
        return 3
    if kind in {"claimed", "heartbeat", "submitted"} and task == run.review_id:
        return 4
    if kind == "parent_ready" and task == run.request_id:
        return 5
    fail(f"Tessera event {event['seq']} ({kind}) does not fit a request split into a build and a review")


# Tessera's state machine at the run's revision (deploy/cloudflare/cloud_store.js).
def state_change(event: dict) -> tuple[str | None, str] | None:
    kind, detail = event["type"], event["detail"]
    if kind == "enqueued":
        return None, "waiting" if detail.get("depends_on") else "ready"
    if kind == "claimed":
        return "ready", "leased"
    if kind == "split":
        return "leased", "waiting"
    if kind in {"dependencies_met", "parent_ready"}:
        return "waiting", "ready"
    if kind == "submitted":
        return "leased", detail["state_after"]
    return None


def utc(seconds: float) -> str:
    when = dt.datetime.fromtimestamp(seconds, dt.timezone.utc)
    return when.strftime("%Y-%m-%dT%H:%M:%S.") + f"{when.microsecond // 1000:03d}Z"


def build_steps(run: Run, hashes: dict, folder_rel: str) -> tuple[list[dict], dict, dict]:
    rb, entry, facts = run.readback, run.entry, run.facts
    kinds = {run.request_id: "request", run.build_id: "build", run.review_id: "review"}
    stores = {"input": hashes["input"]["store"], "kit": hashes["store"], "review": review_store(run)}
    by_step: dict[int, list[dict]] = {n: [] for n in range(1, 6)}
    for event in run.events:
        step = event_step(run, event, stores)
        if step:
            by_step[step].append(event)
    builder = [r for r in run.trace if run.role(r) == "builder"]
    reviewer = [r for r in run.trace if run.role(r) == "reviewer"]
    first_submit = next(r["seq"] for r in builder if r["op"] == "submit")
    trace = {1: [], 2: [r for r in builder if r["seq"] < first_submit], 3: [r for r in builder if r["seq"] >= first_submit],
             4: reviewer, 5: []}
    require(len(builder) + len(reviewer) == len(run.trace), "every trace event belongs to one worker")

    # Every task's states, step by step, must end where the readback says it ended.
    chains: dict[str, list[str]] = {}
    changes: dict[int, list[dict]] = {}
    for step in range(1, 6):
        per_task: dict[str, dict] = {}
        for event in by_step[step]:
            change = state_change(event)
            if not change or event["task_id"] not in kinds:
                continue
            before, after = change
            task = event["task_id"]
            chain = chains.setdefault(task, [])
            require((before is None and not chain) or (chain and chain[-1] == before),
                    f"Tessera event {event['seq']} moves {kinds[task]} from {before}, but it was {chain[-1] if chain else 'new'}")
            item = per_task.setdefault(task, {"task": task, "kind": kinds[task], "new": before is None,
                                              "states": [before] if before else [], "events": []})
            item["states"].append(after)
            item["events"].append(event["seq"])
            chain.append(after)
        changes[step] = sorted(per_task.values(), key=lambda item: list(kinds).index(item["task"]))
    for part, task in (("request", run.request_id), ("build", run.build_id), ("review", run.review_id)):
        require(chains[task][-1] == rb[part]["state"], f"the {part} task ends {chains[task][-1]}, the readback says {rb[part]['state']}")

    builder_side, reviewer_side = entry["harnesses"]["builder"], entry["harnesses"]["reviewer"]
    keys = entry["principals"]
    model = facts["model"]
    require(entry["meta_api_usage"]["model"] == model, "the receipt names another model")
    calls = {step: sum(1 for r in trace[step] if r["op"] == "model call" and r["kind"] == "response") for step in trace}
    by_role = entry["meta_api_usage"]["by_role"]
    require(calls[2] + calls[3] == by_role["builder"]["calls"] and calls[4] == by_role["reviewer"]["calls"],
            "the trace's model calls disagree with the receipt")
    for step in trace:
        for r in trace[step]:
            if r["op"] == "model call" and r["kind"] == "response":
                require(r["from"] == f"meta model api ({model})", f"trace event {r['seq']} called another model")
    first_claim = [r for r in builder if r["op"] == "claim" and r["kind"] == "response"]
    require(first_claim[0].get("outcome") == "no_lease" and first_claim[-1].get("outcome") == "ok",
            "the replay's words expect the builder's first claim to come back empty")
    submits = [r for r in trace[3] if r["op"] == "submit" and r["kind"] == "response"]
    require([r.get("outcome") for r in submits] == ["error", "ok"] and submits[0].get("error_code") == "invalid_request",
            "the replay's words expect one refused submit, then an accepted one")
    review_checks = hashes["review"]["checks"]
    require(hashes["review"]["verdict"] == "approve" and hashes["review"]["approved"] is True,
            "the replay's words expect the review to approve")
    title = rb["request"]["brief"]["title"]
    org = rb["request"]["brief"]["organization_type"]

    def actor_worker(side: dict, role: str, key: str) -> str:
        return f"{side['program']} {side['version']}, the {role}, key {key}, calling {model}"

    files = sorted(hashes["kit"])
    steps = [
        {
            "n": 1, "id": "request",
            "title": "The request became two tasks",
            "text": (f"A {org.lower()}, made up for this run, signed itself up with no operator and asked for a kit that "
                     "turns its volunteers’ availability into a weekly shift schedule. A fixed script, with no "
                     "model, claimed the request, saved the availability list as a noun and split the request into "
                     "two tasks: a build, and a review that waits for it."),
            "actor": (f"The requester, key {keys['requester_key_id']}, then the classify step, key "
                      f"{keys['classifier_key_id']}: a fixed script with no model"),
            "hash": {"value": hashes["input"]["sha256"], "kind": "noun",
                     "label": "SHA-256 of the availability noun"},
        },
        {
            "n": 2, "id": "build",
            "title": "The builder made four nouns",
            "text": ("The builder\u2019s first claim came back empty, and its second got the build. It read the "
                     "availability noun, wrote a scheduler, its tests and a README, and stored them with the "
                     "availability list as four nouns, each with its SHA-256. One digest covers all four."),
            "actor": actor_worker(builder_side, "builder", keys["builder_key_id"]),
            "hash": {"value": hashes["digest"], "kind": "digest", "label": "Digest of the four nouns"},
        },
        {
            "n": 3, "id": "build-receipt",
            "title": "Tessera wrote the build’s receipt",
            "text": ("Tessera turned down the builder’s first submit as an invalid request. The builder submitted "
                     "again, and Tessera accepted it, wrote a receipt and marked the build done. That released the "
                     "review, which had been waiting for the build."),
            "actor": actor_worker(builder_side, "builder", keys["builder_key_id"]),
            "hash": {"value": hashes["results"]["build"]["receipt_hash"], "kind": "receipt",
                     "label": "Tessera’s receipt for the build"},
        },
        {
            "n": 4, "id": "review",
            "title": "A different agent reviewed it",
            "text": (f"The reviewer, holding its own key, claimed the review and read all four nouns. It reported that "
                     f"the kit’s {review_checks['tests_run']} tests pass, that the scheduler finds "
                     f"{review_checks['coverage_violations']} coverage violations and that every digest matches. It "
                     "stored its verdict as a noun and submitted it: approve. Tessera wrote a receipt and marked the "
                     "review done."),
            "actor": actor_worker(reviewer_side, "reviewer", keys["reviewer_key_id"]),
            "hash": {"value": hashes["results"]["review"]["receipt_hash"], "kind": "receipt",
                     "label": "Tessera’s receipt for the review"},
        },
        {
            "n": 5, "id": "held",
            "title": "The request waits for a person",
            "text": ("With both tasks done, Tessera put the request back to ready. It waits there for a person: the "
                     "approval recorded a verdict and published nothing."),
            "actor": "Tessera, on the review’s submit",
            "hash": {"value": hashes["results"]["review"]["receipt_hash"], "kind": "receipt",
                     "label": "The review’s receipt, which released the request"},
        },
    ]
    for step in steps:
        n = step["n"]
        events = by_step[n]
        rows = trace[n]
        moments = [e["ts"] for e in events] + [r["t"] for r in rows]
        step.update({
            "at_utc": utc(min(moments)),
            "tasks": sorted({c["task"] for c in changes[n]} | {e["task_id"] for e in events if e["task_id"] in kinds},
                            key=list(kinds).index),
            "changes": [{k: v for k, v in c.items()} for c in changes[n]],
            "receipt": f"{folder_rel}/steps/{n}-{step['id']}.json",
            "trace": [r["seq"] for r in rows],
            "events": [e["seq"] for e in events],
            "model_calls": calls[n],
        })
        require(bool(step["trace"] or step["events"]), f"step {n} comes from no recorded event")
    steps[0]["request_title"] = title
    steps[0]["request_label"] = title.split(": ", 1)[1] if title.startswith("SYNTHETIC: ") else title
    steps[1]["nouns"] = [{"path": path, "sha256": hashes["kit"][path]["sha256"], "bytes": hashes["kit"][path]["bytes"],
                          "file": f"{folder_rel}/kit/{path}"} for path in files]
    steps[3]["verdict"] = {"store": stores["review"], "verdict": hashes["review"]["verdict"],
                           "tests_run": review_checks["tests_run"],
                           "coverage_violations": review_checks["coverage_violations"],
                           "digests_match": review_checks["digests_match"]}
    return steps, by_step, trace


# The step receipt files ------------------------------------------------------------------------------

def step_records(run: Run, hashes: dict, n: int) -> dict:
    rb = run.readback
    if n == 1:
        pin = hashes["input"]
        return {"input noun": next(r for r in rb[f"nouns:{pin['store']}"]["records"] if r["key"] == pin["key"]),
                "build task, as the split created it (final record)": rb["build"],
                "review task, as the split created it (final record)": rb["review"]}
    if n == 2:
        return {"kit nouns": [r for r in rb[f"nouns:{hashes['store']}"]["records"]
                              if r["key"] in {v["key"] for v in hashes["kit"].values()}],
                "build result, which pins the four nouns and their digest": rb["build_results"]["results"][0]}
    if n == 3:
        return {"build result": rb["build_results"]["results"][0], "build execution": rb["build_executions"]["executions"][0],
                "build execution record": rb["build_execution_records"][0]}
    if n == 4:
        return {"review result": rb["review_results"]["results"][0], "review execution": rb["review_executions"]["executions"][0],
                "review execution record": rb["review_execution_records"][0],
                "review noun": rb["nouns:" + review_store(run)]["records"]}
    return {"request task (final record)": rb["request"], "review result": rb["review_results"]["results"][0]}


CHECKS = {
    "noun": "sha256 of the csv field of the input noun below. kit/data/availability.csv holds the same bytes.",
    "digest": ("sha256 of json.dumps({path: sha256}, sort_keys=True, separators=(',', ':')) over the four kit files, "
               "as the build brief's output contract defines it."),
    "receipt": ("sha256 of the canonical JSON of {error, fencing_token, ok, output, task_id} from the result below "
                "(sorted keys, no spaces), as Tessera's receiptHash computes it."),
}


def step_file(run: Run, hashes: dict, step: dict, by_step: dict, trace: dict) -> dict:
    n = step["n"]
    return {
        "format": STEP_FORMAT,
        "run_id": run.run_id,
        "step": n,
        "id": step["id"],
        "hash": {"value": step["hash"]["value"], "kind": step["hash"]["kind"], "recompute": CHECKS[step["hash"]["kind"]]},
        "copied_from": {"trace": "../trace.jsonl", "tessera": "../tessera-readback.json"},
        "trace": trace[n],
        "tessera_events": by_step[n],
        "records": step_records(run, hashes, n),
    }


# Writing ------------------------------------------------------------------------------------------

def dumps(value) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False) + "\n"


def outputs(folder: Path) -> dict[Path, bytes]:
    run = Run(folder)
    hashes = check_hashes(run)
    folder_rel = f"evidence/real-run-{run.run_id}"
    out_dir = SITE / folder_rel
    steps, by_step, trace = build_steps(run, hashes, folder_rel)
    readback = {
        "about": ("Tessera's own records of run " + run.run_id + ", read back at the end of the run. Each section "
                  "below is copied unchanged from the run's final-readback.json. The sections named in left_out are "
                  "not needed to check the replay."),
        "source": {"file": "final-readback.json", "sha256": sha256((folder / "final-readback.json").read_bytes()),
                   "bytes": (folder / "final-readback.json").stat().st_size},
        "left_out": [k for k in LEFT_OUT if k in run.readback],
        "sections": {k: v for k, v in run.readback.items() if k not in LEFT_OUT},
    }
    files: dict[Path, bytes] = {
        out_dir / "run-facts.json": (folder / "run-facts.json").read_bytes(),
        out_dir / "trace.jsonl": run.trace_bytes,
        out_dir / "tessera-readback.json": dumps(readback).encode("utf-8"),
    }
    for path, item in hashes["kit"].items():
        files[out_dir / "kit" / path] = item["content"]
    for step in steps:
        files[SITE / step["receipt"]] = dumps(step_file(run, hashes, step, by_step, trace)).encode("utf-8")
    entry, facts = run.entry, run.facts
    usage = entry["meta_api_usage"]
    noun = {
        "about": ("One recorded run, replayed on the how-it-works page. scripts/sync_real_run.py writes this noun and "
                  "the files under site/evidence/real-run-" + run.run_id + "/ from the run's own folder, and checks "
                  "every hash it shows. Its words describe what the records show."),
        "format": FORMAT,
        "run": {
            "id": run.run_id,
            "started_utc": facts["started_utc"],
            "fabric": entry["fabric"],
            "tessera_revision": entry["tessera_source_revision"],
            "tessera_repository": facts["tessera_repo"],
            "model": facts["model"],
            "builder": dict(entry["harnesses"]["builder"], key_id=entry["principals"]["builder_key_id"]),
            "reviewer": dict(entry["harnesses"]["reviewer"], key_id=entry["principals"]["reviewer_key_id"]),
            "builder_is_not_reviewer": entry["principals"]["builder_neq_reviewer"],
            "synthetic_data_only": run.receipt["synthetic_data_only"],
            "private_or_ngo_data_sent": run.receipt["privacy_and_spend_guardrails"]["private_or_ngo_data_sent"],
            "raw_credentials_included": run.receipt["privacy_and_spend_guardrails"]["raw_credentials_included"],
            "held_for_person": entry["held_for_person"],
            "trace_events": len(run.trace),
            "model_calls": usage["total_calls"],
            "spend": {"total_actual_usd": usage["total_actual_usd"],
                      "total_conservative_usd": usage["total_conservative_usd"], "cap_usd": usage["cap_usd"]},
            "final_states": {part: run.readback[part]["state"] for part in ("request", "build", "review")},
        },
        "receipt": "evidence/real-e2e-meta-2026-10-31/public-e2e-receipt.json",
        "files": {
            "facts": f"{folder_rel}/run-facts.json",
            "trace": f"{folder_rel}/trace.jsonl",
            "tessera": f"{folder_rel}/tessera-readback.json",
        },
        "steps": steps,
    }
    published = SITE / noun["receipt"]
    require(published.is_file() and published.read_bytes() == (folder / "public-e2e-receipt.json").read_bytes(),
            f"site/{noun['receipt']} must be the run's public receipt, unchanged")
    files[NOUN] = dumps(noun).encode("utf-8")
    for path, data in files.items():
        text = data.decode("utf-8")
        for needle in FORBIDDEN:
            require(needle not in text, f"{path.relative_to(ROOT)} would contain {needle!r}; refusing")
    return files


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("folder", type=Path, help="the recorded run folder")
    parser.add_argument("--check", action="store_true", help="report stale outputs without writing")
    args = parser.parse_args(argv)
    try:
        files = outputs(args.folder.resolve())
    except (SyncError, KeyError, StopIteration, IndexError, ValueError) as error:
        print(f"sync_real_run: {error.__class__.__name__ if not isinstance(error, SyncError) else 'refused'}: {error}",
              file=sys.stderr)
        return 2
    stale = [p for p, data in files.items() if not p.is_file() or p.read_bytes() != data]
    if args.check:
        if stale:
            print("sync_real_run: stale, run without --check:", file=sys.stderr)
            for path in stale:
                print("  " + path.relative_to(ROOT).as_posix(), file=sys.stderr)
            return 1
        print("sync_real_run: the noun and the evidence match the run folder")
        return 0
    for path in stale:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(files[path])
        print("wrote " + path.relative_to(ROOT).as_posix())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
