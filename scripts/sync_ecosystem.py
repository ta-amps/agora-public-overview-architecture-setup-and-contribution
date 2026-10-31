"""Build site/content/ecosystem-catalog.json from an ecosystem catalog JSON or Watt-Mind HTML snapshot.

Decomposes public Meta Hackathon 2026 projects into searchable candidate Tasks (verbs)
and Task Objects (nouns) while preserving strict honesty boundaries and scrubbing any
retired/private names or em-dashes. Stdlib only; touches no network.

Usage:
  python3 scripts/sync_ecosystem.py --watt-html PATH
  python3 scripts/sync_ecosystem.py --input PATH
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_JSON = ROOT / "site" / "content" / "ecosystem-catalog.json"
SCAN_SUMMARY = ROOT / "evidence" / "hackathon-repo-scan-2026-10-29" / "summary.json"

# Hashes of retired pack names from scripts/check.py, plus private workspace tokens, so we never write them.
RETIRED_HASHES = {
    "9410a442dd664c9234966c5ecc0ff595431749474bc67b7e2ce5ccaaed7793ec",
    "4322a6b237d4d0f47990bad6edf90913cd88d2a1a6a9698a756b73e4dfd69329",
    "d488476689bd8ff0424956c989ae7508815f2821f9524dfd3ea5aea931911978",
    "5d76fb4d191bc3dfea2db708ba86a7c87cb156280cf926e26614fb5d9a192a35",
    "a115fb901c2be152c2b26269e0138d16337f4b211a8458732a4f7c8122f91d87",
    "eb753cd06e47c3be57ca39cc23f6fb316e745ef871ef3f827c980cf35b8a4279",
    "463e9150436426d958173be7b785f0b61e04496a953b89695bf1eb1533f83842",
    "ef388591c69c5d39efde5c99f777438328749c5718886ab7c6d39c8819e25761",
}
SENSITIVE_RES = (
    re.compile(r"(?:gh[pousr]_|github_pat_)[A-Za-z0-9_]{20,}"),
    re.compile(r"(?:tsk|tan|hmk)_[A-Za-z0-9_-]{24,}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"/(?:home|Users)/[A-Za-z0-9_.-]+/"),
    re.compile(r"https?://[^/\s]+:[^/\s]+@"),
)

CATEGORY_MAPPINGS: dict[str, tuple[list[str], list[str], str, list[str]]] = {
    "Autonomous Agents & Workflows": (
        ["verb.decompose_dag (plan workflow)", "verb.solve_draft (execute step)", "verb.verify_gate (check receipt)"],
        ["noun.skill_pack (agent workflow)", "noun.shim_provision (guardrail)", "noun.eval_run (step trace)"],
        "write-internal",
        ["muse-code", "opencode", "pi", "harness-square"],
    ),
    "Developer Tooling, Infra & Security": (
        ["verb.benchmark_harness (run check)", "verb.verify_gate (audit policy)", "verb.recover_fault (isolate failure)"],
        ["noun.code_node (verifier tool)", "noun.mcp_server (tool surface)", "noun.benchmark_suite (security suite)"],
        "local-only",
        ["harness-square", "muse-code", "opencode", "pi"],
    ),
    "Multimodal Vision & Video (SAM)": (
        ["verb.ingest (decode frames)", "verb.solve_draft (segment regions)", "verb.verify_gate (frame QA)"],
        ["noun.model_spec (SAM / vision mask)", "noun.scene_recipe (visual layout)", "noun.eval_run (QA report)"],
        "local-only",
        ["muse-code", "opencode", "pi"],
    ),
    "Voice, Speech & Audio AI": (
        ["verb.ingest (transcribe audio)", "verb.solve_draft (synthesize voice)", "verb.verify_gate (caption sync)"],
        ["noun.model_spec (speech / wav2vec2)", "noun.public_source (transcript)", "noun.eval_run (word-timing check)"],
        "local-only",
        ["muse-code", "opencode", "pi"],
    ),
    "Healthcare, Civic & Sustainability": (
        ["verb.probe_source (official public data)", "verb.solve_draft (cited brief)", "verb.vote_judge (human-gated review)"],
        ["noun.public_source (cited record)", "noun.skill_pack (local NGO kit)", "noun.eval_run (privacy check)"],
        "human-gated",
        ["muse-code", "opencode", "pi"],
    ),
    "Education & Knowledge Systems": (
        ["verb.situate (map curriculum)", "verb.solve_draft (draft lesson)", "verb.verify_gate (verify citations)"],
        ["noun.skill_pack (study pack)", "noun.feed_source (knowledge feed)", "noun.benchmark_suite (quiz rubric)"],
        "read-only",
        ["muse-code", "opencode", "pi", "harness-square"],
    ),
    "Business, Finance & Operations": (
        ["verb.ingest (normalize ledger)", "verb.solve_draft (structured analysis)", "verb.verify_gate (schema audit)"],
        ["noun.code_node (data pipeline)", "noun.public_source (filing snapshot)", "noun.eval_run (reconciliation)"],
        "write-internal",
        ["muse-code", "opencode", "pi"],
    ),
    "Gaming & Creative Media": (
        ["verb.expand_seed (scene graph)", "verb.compile_dag (asset build)", "verb.verify_gate (render check)"],
        ["noun.scene_recipe (world state)", "noun.motion_profile (timing curve)", "noun.code_node (shader / asset)"],
        "local-only",
        ["muse-code", "opencode"],
    ),
    "Robotics, IoT & Hardware": (
        ["verb.probe_source (sensor read)", "verb.solve_draft (simulate command)", "verb.recover_fault (safe stop)"],
        ["noun.model_spec (device profile)", "noun.recovery_playbook (stop rule)", "noun.eval_run (telemetry log)"],
        "human-gated",
        ["opencode", "pi"],
    ),
    "General & Emerging Applications": (
        ["verb.problemize (scope brief)", "verb.solve_draft (draft output)", "verb.verify_gate (acceptance check)"],
        ["noun.skill_pack (starter bundle)", "noun.code_node (helper module)", "noun.eval_run (smoke receipt)"],
        "write-internal",
        ["muse-code", "opencode", "pi", "harness-square"],
    ),
}

MODEL_LABELS = {
    "spark": "Muse Spark",
    "wonder": "Muse Wonder",
    "glimmer": "Muse Glimmer",
    "code": "Muse Code",
    "sam": "Meta SAM",
    "weights": "Open Weights / LoRA",
    "meta_api": "Meta API",
    "llama": "Meta Llama",
}


def has_forbidden_token(text: str) -> bool:
    low = text.lower()
    for word in re.findall(r"[a-z0-9]+", low):
        if hashlib.sha256(word.encode("utf-8")).hexdigest() in RETIRED_HASHES:
            return True
    if "loop" in low and "engine" in low and re.search(r"\bloop\s+engine\b", low):
        return True
    return any(pat.search(text) is not None for pat in SENSITIVE_RES)


def clean(value: object) -> str:
    s = re.sub(r"\s+", " ", str(value or "").replace("\u2014", "--")).strip()
    return s


def slugify_cat(cat: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", cat.lower()).strip("-")
    return s or "general"


def format_task_item(v: object) -> tuple[str, str]:
    if isinstance(v, dict):
        vcat = clean(v.get("verb_category") or "")
        name = clean(v.get("name") or v.get("title") or v.get("task_id") or v.get("id") or "")
        if vcat and name:
            return vcat, f"{vcat} ({name})"
        label = clean(v.get("title") or v.get("name") or v.get("task_id") or v.get("id") or "")
        return label.split(" ", 1)[0], label
    s = clean(v)
    return s.split(" ", 1)[0], s


def format_object_item(n: object) -> tuple[str, str, bool]:
    if isinstance(n, dict):
        ncat = clean(n.get("noun_category") or "")
        facet = clean(n.get("source_facet") or n.get("title") or n.get("object_id") or n.get("id") or "")
        is_stack = facet.startswith("meta_stack:")
        if ncat and facet:
            return ncat, f"{ncat} ({facet})", is_stack
        label = clean(n.get("title") or n.get("object_id") or n.get("id") or "")
        return label.split(" ", 1)[0], label, is_stack
    s = clean(n)
    return s.split(" ", 1)[0], s, False


def normalize_entry(raw: dict, idx: int) -> dict | None:
    repo = clean(raw.get("repo") or raw.get("full_name") or raw.get("name") or raw.get("n") or "")
    url = clean(raw.get("url") or raw.get("html_url") or raw.get("u") or (f"https://github.com/{repo}" if "/" in repo else ""))
    if not repo or not url.startswith("https://github.com/"):
        return None
    if has_forbidden_token(repo) or has_forbidden_token(url):
        return None

    cat = clean(raw.get("category") or raw.get("domain") or raw.get("c") or "General & Emerging Applications")
    track = clean(raw.get("track") or raw.get("t") or "Community")
    rank = (
        raw.get("directory_rank")
        if isinstance(raw.get("directory_rank"), int)
        else (raw.get("rank") if isinstance(raw.get("rank"), int) else (raw.get("r") if isinstance(raw.get("r"), int) else idx + 1))
    )

    default_verbs, default_nouns, default_ceiling, default_harnesses = CATEGORY_MAPPINGS.get(
        cat, CATEGORY_MAPPINGS["General & Emerging Applications"]
    )

    raw_models = raw.get("meta_stack") or raw.get("meta_models") or raw.get("models") or raw.get("ms") or []
    if isinstance(raw_models, str):
        raw_models = [m.strip() for m in raw_models.split(",") if m.strip()]
    models = []
    for m in raw_models:
        ms = clean(m)
        if ms == "non_meta":
            continue
        label = MODEL_LABELS.get(ms.lower(), ms)
        if label not in models:
            models.append(label)

    raw_verbs = raw.get("tasks") or raw.get("verbs") or raw.get("candidate_tasks")
    if isinstance(raw_verbs, list) and raw_verbs:
        verbs: list[str] = []
        seen_vcats: set[str] = set()
        for pass_num in (1, 2):
            for v in raw_verbs:
                if len(verbs) >= 3:
                    break
                vcat, formatted = format_task_item(v)
                if not formatted or has_forbidden_token(formatted) or formatted in verbs:
                    continue
                if pass_num == 1 and vcat in seen_vcats:
                    continue
                seen_vcats.add(vcat)
                verbs.append(formatted)
        if not verbs:
            verbs = list(default_verbs)
    else:
        verbs = list(default_verbs)

    raw_nouns = raw.get("task_objects") or raw.get("nouns") or raw.get("candidate_task_objects")
    if isinstance(raw_nouns, list) and raw_nouns:
        nouns: list[str] = []
        seen_ncats: set[str] = set()
        for pass_num in (1, 2):
            for n in raw_nouns:
                if len(nouns) >= 3:
                    break
                ncat, formatted, is_stack = format_object_item(n)
                if not formatted or has_forbidden_token(formatted) or formatted in nouns:
                    continue
                if pass_num == 1 and (ncat in seen_ncats or is_stack):
                    continue
                seen_ncats.add(ncat)
                nouns.append(formatted)
        if not nouns:
            nouns = list(default_nouns)
    else:
        nouns = list(default_nouns)
        if any("Open Weights" in m for m in models) and not any("model_spec" in x for x in nouns):
            nouns = ["noun.model_spec (open-weights adapter)"] + nouns[:2]

    ceiling = clean(raw.get("effect_ceiling") or raw.get("ceiling") or default_ceiling)
    if ceiling not in {"local-only", "read-only", "write-internal", "human-gated"}:
        ceiling = default_ceiling

    raw_harnesses = raw.get("harnesses")
    if isinstance(raw_harnesses, list) and raw_harnesses:
        harnesses = [clean(h) for h in raw_harnesses if clean(h) in {"muse-code", "opencode", "pi", "harness-square"}]
    else:
        harnesses = list(default_harnesses)
        if ("Muse Code" in models or raw.get("mcp_adopted")) and "muse-code" not in harnesses:
            harnesses = ["muse-code"] + harnesses

    summary = clean(raw.get("summary") or raw.get("description") or "")
    if not summary or has_forbidden_token(summary):
        bits = [cat, track]
        if raw.get("ow") or raw.get("open_weights") or "Open Weights / LoRA" in models:
            bits.append("open-weights stack")
        if raw.get("dk") or raw.get("has_docker") or raw.get("docker_declared"):
            bits.append("Dockerized")
        if raw.get("ts") or raw.get("has_tests") or raw.get("tests_present"):
            bits.append("test suite")
        if raw.get("lv") or raw.get("live_demo") or raw.get("live_demo_declared"):
            bits.append("live endpoint listed")
        summary = "Public hackathon repository (" + ", ".join(bits) + ") mapped to candidate Tasks and Task Objects."
    if len(summary) > 200:
        summary = summary[:197].rstrip() + "..."

    out = {
        "rank": int(rank),
        "repo": repo,
        "url": url,
        "track": track,
        "category": cat,
        "category_id": slugify_cat(cat),
        "summary": summary,
        "models": models[:6],
        "tasks": verbs[:3],
        "task_objects": nouns[:3],
        "ceiling": ceiling,
        "harnesses": harnesses or ["muse-code", "opencode", "pi"],
    }
    lang = clean(raw.get("primary_language") or "")
    if lang and lang.lower() != "unknown" and not has_forbidden_token(lang):
        out["language"] = lang
    return out


def build_catalog(entries: list[dict], source_kind: str, extra_meta: dict | None = None) -> dict:
    projects: list[dict] = []
    seen: set[str] = set()
    for idx, raw in enumerate(entries):
        if not isinstance(raw, dict):
            continue
        norm = normalize_entry(raw, idx)
        if norm is None or norm["repo"] in seen:
            continue
        seen.add(norm["repo"])
        projects.append(norm)

    cat_counts: dict[str, dict] = {}
    for p in projects:
        cid = p["category_id"]
        if cid not in cat_counts:
            cat_counts[cid] = {"id": cid, "label": p["category"], "count": 0}
        cat_counts[cid]["count"] += 1

    scan_info = {"attempted": 739, "scanned_ok": 705}
    if SCAN_SUMMARY.is_file():
        sdata = json.loads(SCAN_SUMMARY.read_text(encoding="utf-8"))
        scan_info = {
            "attempted": int(sdata.get("scan", {}).get("attempted", 739)),
            "scanned_ok": int(sdata.get("scan", {}).get("scanned_ok", 705)),
        }

    out = {
        "schema": "ta-amps.ecosystem-catalog.v1",
        "status": "unexecuted_public_scan_mapping",
        "source_kind": source_kind,
        "honesty_note": "Static public-directory decomposition only: none of these third-party repositories was executed, endorsed, or admitted into Tessera, and upstream licenses must be checked at each repository's pinned revision before code reuse.",
        "scan_precedent": scan_info,
        "project_count": len(projects),
        "categories": sorted(cat_counts.values(), key=lambda c: (-c["count"], c["label"])),
        "projects": projects,
    }
    if extra_meta:
        out["source_metadata"] = extra_meta
    return out


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--watt-html", type=Path, help="Path to saved Meta Hackathon 2026 directory HTML")
    group.add_argument("--input", type=Path, help="Path to meta-hackathon-707-catalog.json")
    args = parser.parse_args(argv)

    if args.watt_html:
        raw_html = args.watt_html.read_text(encoding="utf-8")
        m = re.search(r"const INITIAL_DATA = (\[.*?\]);\s*\n", raw_html, re.S)
        if not m:
            print("sync_ecosystem: INITIAL_DATA array not found in HTML", file=sys.stderr)
            return 1
        entries = json.loads(m.group(1))
        catalog = build_catalog(entries, "watt_mind_public_directory_2026_10")
    else:
        loaded = json.loads(args.input.read_text(encoding="utf-8"))
        extra_meta = None
        if isinstance(loaded, list):
            entries = loaded
        elif isinstance(loaded, dict):
            entries = (
                loaded.get("projects")
                or loaded.get("repos")
                or loaded.get("repositories")
                or loaded.get("items")
                or loaded.get("catalog")
                or []
            )
            extra_meta = {
                k: loaded[k]
                for k in ("format", "generated_on", "provenance", "projects_sha256", "git_tree_scanned_ok_projects")
                if k in loaded
            }
        else:
            entries = []
        if not entries:
            print("sync_ecosystem: no project entries found in input JSON", file=sys.stderr)
            return 1
        catalog = build_catalog(entries, "meta_hackathon_707_catalog_json", extra_meta=extra_meta)

    OUT_JSON.write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"sync_ecosystem: wrote {OUT_JSON.relative_to(ROOT)} ({catalog['project_count']} projects, "
          f"{len(catalog['categories'])} categories)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
