"""Build site/content/explorer.json from site/content/library.json and a seed-packs checkout.

Extracts searchable Seed Packs, Tasks (verbs), and Task Objects (nouns) from the seed-pack
library, alongside the authored UI labels and the Agent Harness Research Feeds panel.
Stdlib only; touches no network.

Usage:
  python3 scripts/sync_explorer.py --library PATH
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIBRARY_JSON = ROOT / "site" / "content" / "library.json"
OUT_JSON = ROOT / "site" / "content" / "explorer.json"
ALL_HARNESSES = ["muse-code", "opencode", "pi", "harness-square"]


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").replace("\u2014", "--")).strip()


def ceiling_for_verb(task: dict) -> str:
    brief = task.get("brief") or {}
    if brief.get("claimant") == "human":
        return "human-gated"
    ex = brief.get("execution") or {}
    net = ex.get("network") or {}
    mode = net.get("mode", "") if isinstance(net, dict) else str(net)
    if mode in {"none", "local_only"}:
        return "local-only"
    if mode == "read_only":
        return "read-only"
    return "write-internal"


def harnesses_for_verb(task: dict, pack_id: str) -> list[str]:
    brief = task.get("brief") or {}
    if brief.get("claimant") == "human":
        return []
    kind = task.get("kind", "")
    if kind in {"verb.benchmark_harness", "verb.fetch_feed", "verb.probe_source"} or "harness" in pack_id:
        return ["harness-square", "muse-code", "opencode", "pi"]
    if kind in {"verb.compile_dag", "verb.solve_draft"}:
        return ["muse-code", "opencode", "pi", "harness-square"]
    return list(ALL_HARNESSES)


def harnesses_for_pack(pack: dict, category_id: str) -> list[str]:
    pid = pack["id"]
    if "harness" in pid or category_id in {"learning-and-evaluation", "architecture-and-discovery"}:
        return ["harness-square", "muse-code", "opencode", "pi"]
    if pack.get("kit"):
        return ["muse-code", "opencode", "pi"]
    return list(ALL_HARNESSES)


def build_explorer(library: dict, packs_dir: Path | None) -> dict:
    cat_by_pack = {
        pid: {"id": cat["id"], "short": cat["short"], "name": cat["name"]}
        for cat in library["categories"]
        for pid in cat["packs"]
    }
    commit = library["source"]["commit"]
    repo = library["source"]["repository"]

    pack_items: list[dict] = []
    verb_items: list[dict] = []
    noun_items: list[dict] = []

    for pack in library["packs"]:
        pid = pack["id"]
        cat = cat_by_pack[pid]
        p_harnesses = harnesses_for_pack(pack, cat["id"])
        p_ceiling = "local-only" if pack["kit"] else "write-internal"
        pack_items.append({
            "kind": "pack",
            "id": f"pack:{pid}",
            "pack_id": pid,
            "title": clean(pack["title"]),
            "summary": clean(pack["purpose"]),
            "subtype": "agent-kit" if pack["kit"] else ("code-tested" if pack["code"] else "seed-pack"),
            "category": cat["id"],
            "category_label": cat["short"],
            "ceiling": p_ceiling,
            "harnesses": p_harnesses,
            "nouns": pack["nouns"],
            "verbs": pack["verbs"],
            "url": pack["url"],
            "anchor": f"#{pid}",
        })

        if packs_dir is None or not (packs_dir / pid).is_dir():
            continue

        vj = packs_dir / pid / "verbs.json"
        if vj.is_file():
            vdata = json.loads(vj.read_text(encoding="utf-8"))
            for task in vdata.get("tasks", []):
                brief = task.get("brief") or {}
                tid = clean(brief.get("template_id") or "")
                title = clean(brief.get("title") or tid or pid)
                summary = clean(brief.get("plain_summary") or brief.get("outcome") or pack["purpose"])
                if len(summary) > 190:
                    summary = summary[:187].rstrip() + "..."
                verb_items.append({
                    "kind": "verb",
                    "id": f"verb:{tid or (pid + '.' + str(len(verb_items)))}",
                    "pack_id": pid,
                    "pack_title": clean(pack["title"]),
                    "title": title,
                    "summary": summary,
                    "subtype": clean(task.get("kind") or "verb.solve_draft"),
                    "category": cat["id"],
                    "category_label": cat["short"],
                    "ceiling": ceiling_for_verb(task),
                    "harnesses": harnesses_for_verb(task, pid),
                    "url": f"{repo}/blob/{commit}/packs/{pid}/verbs.json",
                    "anchor": f"#{pid}",
                })

        nj = packs_dir / pid / "nouns.json"
        if nj.is_file():
            ndata = json.loads(nj.read_text(encoding="utf-8"))
            picked = 0
            seen_roles: set[str] = set()
            records = ndata.get("records", [])
            # First pass: prefer distinct non-pack roles; second pass: fill up to 4 per pack.
            for pass_num in (1, 2):
                for rec in records:
                    if picked >= 4:
                        break
                    val = rec.get("value") or {}
                    role = clean(val.get("role") or "record")
                    if role == "pack":
                        continue
                    if pass_num == 1 and role in seen_roles:
                        continue
                    key = clean(rec.get("key") or "")
                    nid = f"noun:{key}"
                    if any(x["id"] == nid for x in noun_items):
                        continue
                    seen_roles.add(role)
                    picked += 1
                    title = clean(val.get("title") or key)
                    summary = clean(
                        val.get("category_reason")
                        or val.get("rule")
                        or val.get("purpose")
                        or val.get("summary")
                        or pack["purpose"]
                    )
                    if len(summary) > 190:
                        summary = summary[:187].rstrip() + "..."
                    ncat = clean(val.get("category_id") or "noun.skill_pack")
                    nceil = "read-only" if ncat in {"noun.feed_source", "noun.public_source"} else p_ceiling
                    noun_items.append({
                        "kind": "noun",
                        "id": nid,
                        "pack_id": pid,
                        "pack_title": clean(pack["title"]),
                        "title": title,
                        "summary": summary,
                        "subtype": f"{ncat} · {role}",
                        "category": cat["id"],
                        "category_label": cat["short"],
                        "ceiling": nceil,
                        "harnesses": p_harnesses,
                        "url": f"{repo}/blob/{commit}/packs/{pid}/nouns.json",
                        "anchor": f"#{pid}",
                    })

    return {
        "about": "Interactive Task and Task-Object Explorer noun for site/library/index.html, plus the Agent Harness Research Feeds panel. Generated deterministically by scripts/sync_explorer.py; rendered offline by scripts/build_site.py.",
        "jump_links": [
            {"href": "#explorer", "label": "Interactive Task & Task-Object Explorer"},
            {"href": "#harness-feeds", "label": "Agent Harness Research Feeds"},
            {"href": "#ecosystem-explorer", "label": "Meta Hackathon 2026 Ecosystem Explorer"}
        ],
        "heading": "Interactive Task & Task-Object Explorer",
        "lead": "Tasks and Task Objects -- on the wire, verbs are tasks and nouns are task objects. Search and filter proposed Seed Packs, atomic Tasks, reusable Task Objects, and decomposed Meta Hackathon 2026 repositories right in your browser with zero network calls.",
        "proposal_note": "Honesty boundary: every seed pack, task template, task object, and hackathon decomposition below is an offline proposal or static public-source mapping -- none is claimed as an installed runtime service or reproduced upstream benchmark.",
        "tabs_label": "Explorer catalog view",
        "tabs": {
            "library": "Seed Packs, Tasks & Task Objects",
            "ecosystem": "Meta Hackathon 2026 Ecosystem"
        },
        "controls": {
            "search_label": "Keyword",
            "search_placeholder": "Search tasks, task objects, packs, MCP tools, LoRA, SAM, nonprofit...",
            "kind_label": "Artifact type",
            "category_label": "Category",
            "ceiling_label": "Effect ceiling",
            "harness_label": "Harness compatibility",
            "reset": "Reset filters",
            "show_more": "Show more results",
            "all_categories": "All categories",
            "noscript": "Enable JavaScript to use instant multi-faceted search across Tasks, Task Objects, and the Meta Hackathon 2026 ecosystem, or browse every seed pack by category below."
        },
        "kinds": [
            {"id": "all", "label": "All Packs, Tasks & Task Objects"},
            {"id": "pack", "label": "Seed Packs"},
            {"id": "verb", "label": "Tasks (verbs)"},
            {"id": "noun", "label": "Task Objects (nouns)"}
        ],
        "eco_kinds": [
            {"id": "all", "label": "All hackathon repositories"},
            {"id": "open-weights", "label": "Open Weights / LoRA stack"},
            {"id": "Track 1", "label": "Track 1"},
            {"id": "Track 2", "label": "Track 2"}
        ],
        "ceilings": [
            {"id": "all", "label": "All effect ceilings"},
            {"id": "local-only", "label": "Local / Offline only"},
            {"id": "read-only", "label": "Read-only public network"},
            {"id": "write-internal", "label": "Scoped internal store"},
            {"id": "human-gated", "label": "Human-gated approval"}
        ],
        "harnesses": [
            {"id": "all", "label": "All harnesses"},
            {"id": "muse-code", "label": "Muse Code"},
            {"id": "opencode", "label": "OpenCode"},
            {"id": "pi", "label": "Pi"},
            {"id": "harness-square", "label": "Harness Square"}
        ],
        "labels": {
            "pack": "Seed Pack",
            "verb": "Task (verb)",
            "noun": "Task Object (noun)",
            "project": "Hackathon Project",
            "proposal": "Proposal",
            "scan_mapping": "Public-scan decomposition",
            "ceiling_prefix": "Ceiling:",
            "harnesses_prefix": "Harnesses:",
            "human_only": "Human steward",
            "tasks_label": "Candidate Tasks (verbs):",
            "objects_label": "Candidate Task Objects (nouns):",
            "models_label": "Meta & AI stack:",
            "pack_ref": "In pack:",
            "open_card": "Jump to pack",
            "open_source": "View JSON source",
            "open_repo": "Open repository",
            "empty": "No matching Tasks, Task Objects, or repositories found. Try broadening a filter or clearing the search box."
        },
        "harness_feeds": {
            "kicker": "Encapsulating Feed Task Objects · HarnessTax & Routing",
            "heading": "Agent Harness Research Feeds",
            "lead": "An Agent Harness Research Feed is an encapsulating Feed Task Object (noun.feed_source / noun:harness.feed on the wire) that bundles dated capability profiles, reproducible trial receipts, and measured HarnessTax -- the static system-prompt and tool-schema token overhead paid on every turn -- across configurable coding harnesses. Because empirical benchmarks (arXiv 2311.10054, 2512.05858, 2508.19764, 2602.12285, 2402.10962) show expert role-play adds zero factual accuracy while irrelevant or demographic persona fluff degrades agent performance by 26-30% and instructions drift within 8 turns, ta-amps separates routing descriptions from permissions ('hierarchy routes, it never authorizes') and puts precision into Task Objects, output contracts, scoped tool limits, and context shims.",
            "status_note": "Status: Live daily service checks run for our own endpoints today; Herma ships PROV-HARNESS-FEEDS-GUIDE for zero-weight context shimming, while automated external GitHub/paper feed collectors remain proposed.",
            "harnesses": [
                {
                    "id": "harness-square",
                    "name": "Harness Square",
                    "role": "Comparative evaluation & HarnessTax baseline",
                    "detail": "Tracks structured harness profiles, static prompt/tool-schema token overhead (HarnessTax), and paired trial receipts under pinned task conditions."
                },
                {
                    "id": "muse-code",
                    "name": "Muse Code",
                    "role": "Native Meta coding harness (X-Herma-Harness: muse-code)",
                    "detail": "Verified end-to-end claiming leased Tasks on the shared Tessera queue and receiving caller-scoped Herma context shims over /v1/responses and /v1/chat/completions."
                },
                {
                    "id": "opencode",
                    "name": "OpenCode",
                    "role": "Configurable open-source terminal & swarm harness",
                    "detail": "Completed native scoped task lifecycles on Tessera and scales horizontally across up to 256 concurrent workers over sharded queues (q01..q16) with inline Herma routing."
                },
                {
                    "id": "pi",
                    "name": "Pi",
                    "role": "Multi-process swarm & lightweight worker harness",
                    "detail": "Completed native worker lifecycles and multi-process concurrency runs against leased Tessera queues with fenced SHA-256 receipts (verifier != builder)."
                }
            ],
            "routing": {
                "heading": "Horizontal Swarm + 4-Tier Vertical Compute Cascade",
                "lead": "Up to 256 concurrent OpenCode and multi-harness workers shard leased Tasks across Tessera queues (q01..q16, SQLite/Durable Object shards, CAS blobs) with independent verification (verifier != builder), turning verified traces and rejected-attempt tombstones (DPO pairs) into training data for a four-tier cascade:",
                "rules": [
                    {
                        "mode": "Tier 0 · Deterministic Herma Rules (< 2 ms)",
                        "when": "Capability firewall, volatile facts, and JSON repair",
                        "outcome": "Executes inline at zero LLM token spend; deterministic repair alone lifted unchanged Llama 3.2 3B from 52.0% to 64.7% on our synthetic holdout."
                    },
                    {
                        "mode": "Tier 1 · Local Llama 3.2 1B & 3B Modular PEFT LoRAs",
                        "when": "Hot-swappable specialist Task Objects on a single local GPU",
                        "outcome": "Routes across composable PEFT adapters (shim-router, lora-as-memory, task-decomposer, verifier-dpo) with zero per-turn HarnessTax (1B: 12.0% -> 50.7%; 3B: 52.0% -> 72.7% on synthetic holdouts)."
                    },
                    {
                        "mode": "Tier 2 · Kaggle 2xT4 Muse Glimmer 30B NF4 QLoRA",
                        "when": "30B open-weights reasoning & LoRAs as Parametric Memory",
                        "outcome": "4-bit NF4 QLoRA adapter trained on free Kaggle 2xT4 GPUs lifted tool-call accuracy from 93.3% to 99.3% (149/150) on a fresh seed-20261030 holdout."
                    },
                    {
                        "mode": "Tier 3 · Frontier Meta Muse Spark 1.3 & Muse Wonder 1.0",
                        "when": "Novel multi-step synthesis & cross-agent review",
                        "outcome": "Reserved for frontier synthesis in Standard mode (ContributorTierRefusedError blocks contributor tiers); verified receipts distill back down into Tier 1 and Tier 2 adapters."
                    }
                ]
            }
        },
        "ecosystem_callout": {
            "kicker": "Public-source decomposition · 707 repositories",
            "heading": "Meta Hackathon 2026 Ecosystem Explorer",
            "summary": "Every public repository in the Meta Global AI Developer Hackathon 2026 directory decomposed into candidate Tasks (verbs) and Task Objects (nouns) by category, Meta AI stack, effect ceiling, and harness compatibility.",
            "button": "Open Ecosystem Explorer tab",
            "evidence_href": "https://github.com/ta-amps/agora-public-overview-architecture-setup-and-contribution/tree/main/evidence/hackathon-repo-scan-2026-10-29",
            "evidence_label": "Read the 739-repo scan receipt"
        },
        "counts": {
            "packs": len(pack_items),
            "verbs": len(verb_items),
            "nouns": len(noun_items),
            "total": len(pack_items) + len(verb_items) + len(noun_items)
        },
        "items": pack_items + verb_items + noun_items,
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--library", type=Path, required=True, help="Path to seed-packs-library-of-nouns-and-verbs")
    args = parser.parse_args(argv)
    library = json.loads(LIBRARY_JSON.read_text(encoding="utf-8"))
    packs_dir = args.library / "packs"
    if not packs_dir.is_dir():
        print(f"sync_explorer: {packs_dir} not found", file=sys.stderr)
        return 1
    out = build_explorer(library, packs_dir)
    OUT_JSON.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"sync_explorer: wrote {OUT_JSON.relative_to(ROOT)} ({out['counts']['packs']} packs, "
          f"{out['counts']['verbs']} verbs, {out['counts']['nouns']} nouns)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
