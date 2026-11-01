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
        "about": "The library page’s explorer, as one Task Object: search and filters over every seed pack, Task and Task Object, plus the Agent Harness Research Feeds panel. Generated by scripts/sync_explorer.py and rendered offline by scripts/build_site.py.",
        "jump_links": [
            {
                "href": "#explorer",
                "label": "Search Tasks and Task Objects"
            },
            {
                "href": "#harness-feeds",
                "label": "Agent Harness Research Feeds"
            },
            {
                "href": "#ecosystem-explorer",
                "label": "Meta Hackathon 2026 Ecosystem Explorer"
            }
        ],
        "heading": "Search Tasks and Task Objects",
        "lead": "Search and filter the seed packs, their Tasks and Task Objects, and the Meta Hackathon 2026 repositories, right in your browser with no network calls.",
        "proposal_note": "Every seed pack, Task template and Task Object below is a proposal, and every hackathon repository is mapped from its public files only: none is an installed service, and no benchmark here was re-run.",
        "tabs_label": "Explorer catalog view",
        "tabs": {
            "library": "Seed Packs, Tasks & Task Objects",
            "ecosystem": "Meta Hackathon 2026 Ecosystem"
        },
        "controls": {
            "search_label": "Keyword",
            "search_placeholder": "Search Tasks, Task Objects, packs, MCP tools, LoRA, SAM, nonprofit...",
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
            {
                "id": "all",
                "label": "All Packs, Tasks & Task Objects"
            },
            {
                "id": "pack",
                "label": "Seed Packs"
            },
            {
                "id": "verb",
                "label": "Tasks"
            },
            {
                "id": "noun",
                "label": "Task Objects"
            }
        ],
        "eco_kinds": [
            {
                "id": "all",
                "label": "All hackathon repositories"
            },
            {
                "id": "open-weights",
                "label": "Open Weights / LoRA stack"
            },
            {
                "id": "Track 1",
                "label": "Track 1"
            },
            {
                "id": "Track 2",
                "label": "Track 2"
            }
        ],
        "ceilings": [
            {
                "id": "all",
                "label": "All effect ceilings"
            },
            {
                "id": "local-only",
                "label": "Local / Offline only"
            },
            {
                "id": "read-only",
                "label": "Read-only public network"
            },
            {
                "id": "write-internal",
                "label": "Scoped internal store"
            },
            {
                "id": "human-gated",
                "label": "Human-gated approval"
            }
        ],
        "harnesses": [
            {
                "id": "all",
                "label": "All harnesses"
            },
            {
                "id": "muse-code",
                "label": "Muse Code"
            },
            {
                "id": "opencode",
                "label": "OpenCode"
            },
            {
                "id": "pi",
                "label": "Pi"
            },
            {
                "id": "harness-square",
                "label": "Harness Square"
            }
        ],
        "labels": {
            "pack": "Seed Pack",
            "verb": "Task",
            "noun": "Task Object",
            "project": "Hackathon Project",
            "proposal": "Proposal",
            "scan_mapping": "Public-scan decomposition",
            "ceiling_prefix": "Ceiling:",
            "harnesses_prefix": "Harnesses:",
            "human_only": "Human steward",
            "tasks_label": "Candidate Tasks:",
            "objects_label": "Candidate Task Objects:",
            "models_label": "Meta & AI stack:",
            "pack_ref": "In pack:",
            "open_card": "Jump to pack",
            "open_source": "View JSON source",
            "open_repo": "Open repository",
            "empty": "No matching Tasks, Task Objects, or repositories found. Try broadening a filter or clearing the search box."
        },
        "harness_feeds": {
            "kicker": "Feeds about agent harnesses · overhead and routing",
            "heading": "Agent Harness Research Feeds",
            "lead": "A harness research feed is a Task Object that keeps dated profiles of coding harnesses, their trial records, and how many prompt and tool-schema tokens each one adds to every turn. Routing descriptions are kept apart from permissions, since a route never authorizes anything, and precision lives in Task Objects, output contracts, scoped tool limits and context shims.",
            "status_note": "Today a daily check watches our own services, and Herma has a guide for adding harness feeds as context. Collecting outside GitHub and paper feeds automatically is a proposal.",
            "harnesses": [
                {
                    "id": "harness-square",
                    "name": "Harness Square",
                    "role": "Compares harnesses and the overhead each adds",
                    "detail": "Keeps a profile of each harness, the prompt and tool-schema tokens it adds to every turn, and paired trial records under the same task conditions."
                },
                {
                    "id": "muse-code",
                    "name": "Muse Code",
                    "role": "Meta’s coding agent program",
                    "detail": "Claimed leased Tasks on Tessera’s shared queue end to end, and received the caller’s own Herma context over /v1/responses and /v1/chat/completions."
                },
                {
                    "id": "opencode",
                    "name": "OpenCode",
                    "role": "Configurable open-source terminal & swarm harness",
                    "detail": "Completed scoped Task lifecycles on Tessera, with Herma routing inline."
                },
                {
                    "id": "pi",
                    "name": "Pi",
                    "role": "Multi-process swarm & lightweight worker harness",
                    "detail": "Completed worker lifecycles and multi-process runs against leased Tessera queues, with every step recorded and a verifier who is never the builder."
                }
            ],
            "routing": {
                "heading": "Many workers, and a model for each job",
                "lead": "Many workers share leased Tasks across Tessera’s queues, and a different worker verifies each result. Verified results and rejected attempts become training examples for three tiers:",
                "rules": [
                    {
                        "mode": "Tier 0 · Herma’s rules",
                        "when": "Capability firewall, volatile facts and JSON repair",
                        "outcome": "Runs inline, with no model tokens."
                    },
                    {
                        "mode": "Tier 1 · {{model:muse-glimmer-30b:tuned}}",
                        "when": "Tool calls, and recalling the library’s Task Objects from memory",
                        "outcome": "With QLoRA on Kaggle’s free GPUs, tool-call accuracy rose from 93.3% to 99.3% (149 of 150) on a fresh 150-task evaluation."
                    },
                    {
                        "mode": "Tier 2 · Meta’s {{model:muse-spark-1.3}} and {{model:muse-wonder-1.0}}",
                        "when": "New multi-step work and review across agents",
                        "outcome": "Reserved for this work at standard tier; a contributor-tier key is refused here."
                    }
                ]
            }
        },
        "ecosystem_callout": {
            "kicker": "Public-source decomposition · 706 repositories",
            "heading": "Meta Hackathon 2026 Ecosystem Explorer",
            "summary": "The public repositories of the Meta Global AI Developer Hackathon 2026 directory, each mapped to candidate Tasks and Task Objects by category, Meta AI stack, effect ceiling and harness compatibility. One entry is left out.",
            "button": "Open Ecosystem Explorer tab",
            "evidence_href": "https://github.com/ta-amps/agora-public-overview-architecture-setup-and-contribution/tree/main/evidence/hackathon-repo-scan-2026-10-29",
            "evidence_label": "The scan’s record"
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
