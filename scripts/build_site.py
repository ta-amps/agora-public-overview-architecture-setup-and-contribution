"""Build the static Agora site from its nouns. Stdlib only, except --pdf.

Everything a page says is a noun kept as data, and this script holds only markup:
  * site/agent-brief.txt              the starting brief for any agent, word for word;
  * site/content/site.json            navigation, the agent banner, the endpoints, deck labels, the footer and its
                                      privacy line;
  * site/content/home.json            the home page: the film, a statement in two labelled parts (the use case
                                      and the architecture underneath), the 1x3 product hub, and the decks;
  * site/content/decks-page.json      the decks page;
  * site/content/use-cases.json       the use cases page; each flagship names its library packs by id;
  * site/content/learning.json        the learning page: the loop, measured results with evidence, rules, limits;
  * site/content/library.json         the library page: every seed pack at one pinned commit, by category. Its
                                      measured part comes from scripts/sync_library.py, never from the network;
  * site/content/explorer.json        the interactive Task and Task-Object explorer and Agent Harness Research Feeds;
  * site/content/ecosystem-catalog.json the 707-project Meta Hackathon 2026 public-scan decomposition;
  * site/content/film.json            the full film's transcript and scene descriptions;
  * site/content/earlier-drafts.json  earlier drafts, and the storyboards page;
  * site/content/moved.json           pages that moved, which the not-found page lists;
  * site/content/how-it-works.json    the how-it-works page: why, the map of nouns and verbs, a real run replayed,
                                      Herma and Tessera underneath, and the Meta model results it names from
                                      learning.json by model, so no number is typed twice;
  * site/content/real-run.json        the replayed run: its facts and five steps, each with a hash, a receipt file
                                      under site/evidence/ and the trace and Tessera events it comes from. Only
                                      scripts/sync_real_run.py writes it, from the run's own records;
  * site/content/evidence.json        the evidence page: one line for each served evidence folder and for each
                                      item of the repository's evidence/, and where the last live check is saved.
                                      The build fills each folder's files and the check's answers from the files;
  * site/decks/<deck>/source/         each deck: deck.json, slides/*.html and an optional claims.json.

What it writes:
  * every current deck, site/decks/<deck>/index.html, from its source folder. The slide format's custom
    elements become HTML: <x-shape> and <x-icon> become inline SVG, <x-brief> the starting brief and
    <x-endpoints> the endpoint table. Each slide's <aside> becomes its speaker notes;
  * the home, decks, earlier drafts, storyboards, use cases, learning, library, film, how-it-works, evidence and
    not-found pages;
  * the measured part of site/content/evidence.json: each served folder's files and the last live check's answers,
    read from site/evidence/. Its words stay as written;
  * the shared head, header, agent banner and footer, between marker comments, into every other page
    that is not frozen;
  * the "decks" list in site/decks.json. The frozen "versions" entries stay byte-identical.

Frozen pages are never written: the dated deck versions listed in site/decks.json and the drafts that
site/content/earlier-drafts.json pins with a hash. scripts/check.py checks their bytes.

Usage:
  python3 scripts/build_site.py            write the outputs
  python3 scripts/build_site.py --check    fail when an output is stale (no writes; make check runs it)
  python3 scripts/build_site.py --pdf      also print every current deck to PDF with headless Chromium
                                           (needs the Playwright package; set CHROMIUM_PATH to use
                                           an installed browser)

Nothing here touches the network, except --pdf, where the pages load their web fonts.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import json
import os
import re
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
CONTENT = SITE / "content"
BRIEF = SITE / "agent-brief.txt"
DECKS = SITE / "decks"
MANIFEST = SITE / "decks.json"
# The site is served from the root of agora.ta-amps.workers.dev; the worker redirects the old GitHub Pages path.
PAGES_PREFIX = "/"
CANVAS_W, CANVAS_H = 1920, 1080
# "illustration" marks a number in a worked example that shows how the work is organized, not a measured run.
CLAIM_STATUSES = {"measured", "pending", "planned", "illustration"}
LIBRARY_REPOSITORY = "https://github.com/ta-amps/seed-packs-library-of-nouns-and-verbs"
SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
CATEGORY_ID = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*\Z")  # starts with a letter: the page's style names it
FULL_SHA = re.compile(r"[0-9a-f]{40}\Z")
PACK_FIELDS = {"id", "title", "purpose", "version", "status", "nouns", "verbs", "worked_examples", "kit", "code", "url"}
CODE_FIELDS = {"files", "tests", "workflow"}
# Ids the shared chrome and the library page's own parts use, which no pack or category may take.
LIBRARY_IDS = {"main", "agent-panel", "agent-brief", "agent-brief-title", "agent-brief-status", "categories",
               "library-numbers", "explorer", "explorer-heading", "tab-library", "tab-ecosystem", "exp-query",
               "exp-kind", "exp-category", "exp-ceiling", "exp-harness", "exp-status", "harness-feeds",
               "harness-feeds-heading", "harness-routing-heading", "ecosystem-explorer", "ecosystem-heading",
               "agora-explorer-data"}
USE_PACKS = (2, 5)  # how many library packs a use case names, at least and at most
# F31-005: how many packs each category shows before its "See all" link. The whole list runs past 10,000 px, more than
# Chrome paints in one go at device scale 1.5; site.css holds the same number.
LIBRARY_FIRST = 3

# Lucide icons (ISC license, see site/THIRD-PARTY-NOTICES.txt), the three the slides name.
ICONS = {
    "Users": ('<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><path d="M16 3.128a4 4 0 0 1 0 7.744"/>'
              '<path d="M22 21v-2a4 4 0 0 0-3-3.87"/><circle cx="9" cy="7" r="4"/>'),
    "Book": '<path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H19a1 1 0 0 1 1 1v18a1 1 0 0 1-1 1H6.5a1 1 0 0 1 0-5H20"/>',
    "ThumbsUp": ('<path d="M15 5.88 14 10h5.83a2 2 0 0 1 1.92 2.56l-2.33 8A2 2 0 0 1 17.5 22H4a2 2 0 0 1-2-2v-8'
                 'a2 2 0 0 1 2-2h2.76a2 2 0 0 0 1.79-1.11L12 2a3.13 3.13 0 0 1 3 3.88Z"/><path d="M7 10v12"/>'),
}

MARK = ('<svg width="26" height="26" viewBox="0 0 100 100" aria-hidden="true" focusable="false">'
        '<rect x="0" y="0" width="44" height="44" rx="10" fill="var(--color-noun)"/>'
        '<rect x="56" y="0" width="44" height="44" rx="10" fill="var(--color-verb)"/>'
        '<rect x="0" y="56" width="44" height="44" rx="10" fill="var(--color-ink)"/>'
        '<rect x="56" y="56" width="44" height="44" rx="10" fill="var(--color-noun)"/></svg>')
# The agent banner's robot head, drawn for the AgentBanner board, and the header's menu lines.
AGENT_ICON = ('<svg class="agent-fallback-icon" viewBox="0 0 40 40" width="18" height="18" aria-hidden="true" '
              'focusable="false"><circle cx="20" cy="20" r="17" fill="none" stroke="currentColor" stroke-width="2.6"/>'
              '<path d="M20 12v-3h-3" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round"/>'
              '<rect x="12" y="14" width="16" height="12" rx="3" fill="none" stroke="currentColor" stroke-width="2.6"/>'
              '<path d="M17 19v2M23 19v2" stroke="currentColor" stroke-width="2.6" stroke-linecap="round"/></svg>')
MENU_ICON = ('<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" focusable="false">'
             '<path d="M4 7h16M4 12h16M4 17h16" fill="none" stroke="currentColor" stroke-width="2" '
             'stroke-linecap="round"/></svg>')

# Plain shapes drawn for this site: two sheets for copying, a chevron for showing more and the decks' block arrow for the learning loop.
COPY_ICON = ('<svg viewBox="0 0 20 20" width="16" height="16" aria-hidden="true" focusable="false">'
             '<rect x="6.5" y="6.5" width="10" height="10" rx="2" fill="none" stroke="currentColor" '
             'stroke-width="1.6"/><path d="M13.5 4.5v-.5a1.5 1.5 0 0 0-1.5-1.5H5A1.5 1.5 0 0 0 3.5 4v7A1.5 1.5 '
             '0 0 0 5 12.5h.5" fill="none" stroke="currentColor" stroke-width="1.6"/></svg>')
CHEVRON = ('<svg class="chevron" viewBox="0 0 16 16" width="14" height="14" aria-hidden="true" '
           'focusable="false"><path d="M4 6l4 4 4-4" fill="none" stroke="currentColor" stroke-width="1.75" '
           'stroke-linecap="round" stroke-linejoin="round"/></svg>')
# Angle brackets for a pack that ships its own code and tests.
CODE_GLYPH = ('<svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true" focusable="false">'
              '<path d="M5.5 4.5 2 8l3.5 3.5M10.5 4.5 14 8l-3.5 3.5" fill="none" stroke="currentColor" '
              'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>')


def arrow(cls: str) -> str:
    """The block arrow the slides draw, pointing right; a page's styles turn it to point anywhere else."""
    return (f'<svg class="{cls}" viewBox="0 0 28 24" width="28" height="24" aria-hidden="true" focusable="false">'
            '<path d="M0 6H17.36V0L28 12L17.36 24V18H0Z" fill="currentColor"/></svg>')


JS_CLASS = '<script>document.documentElement.classList.add("js")</script>'  # light only: no stored mode

MONO = "font-family:'JetBrains Mono', 'Courier New', monospace"


class BuildError(Exception):
    pass


def fail(message: str) -> None:
    raise BuildError(message)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def text(value: str) -> str:
    return html.escape(value, quote=False)


def attr(value: str) -> str:
    return html.escape(value, quote=True)


def load_json(path: Path) -> dict:
    if not path.is_file():
        fail(f"missing {path.relative_to(ROOT)}")
    return json.loads(path.read_text(encoding="utf-8"))


def read_brief() -> str:
    raw = BRIEF.read_text(encoding="utf-8")
    if not raw.endswith("\n") or raw.endswith("\n\n") or not raw.strip():
        fail("site/agent-brief.txt must hold the brief and end with exactly one newline")
    return raw[:-1]


# Nouns this build reads ---------------------------------------------------------------------------

class Nouns:
    """Every content noun the pages render, read once."""

    def __init__(self) -> None:
        self.site = load_json(CONTENT / "site.json")
        self.banner = load_json(CONTENT / "agent-banner.json")
        self.tour = load_json(CONTENT / "judge-tour.json")
        self.home = load_json(CONTENT / "home.json")
        self.decks_page = load_json(CONTENT / "decks-page.json")
        self.uses = load_json(CONTENT / "use-cases.json")
        self.film = load_json(CONTENT / "film.json")
        self.learning = load_json(CONTENT / "learning.json")
        self.library = load_json(CONTENT / "library.json")
        check_library(self.library)
        self.explorer = load_json(CONTENT / "explorer.json")
        self.ecosystem = load_json(CONTENT / "ecosystem-catalog.json")
        check_explorer(self.explorer, self.ecosystem)
        self.deploy = load_json(CONTENT / "deploy.json")
        self.contribute = load_json(CONTENT / "contribute.json")
        self.llms = load_json(CONTENT / "llms.json")
        self.links = load_json(CONTENT / "source-links.json")
        self.feed = load_json(CONTENT / "feeds-memory-systems.json")
        self.feed_words = load_json(CONTENT / "feeds-page.json")
        self.how = load_json(CONTENT / "how-it-works.json")
        self.real_run = load_json(CONTENT / "real-run.json")
        self.evidence = load_json(CONTENT / "evidence.json")
        self.drafts = load_json(CONTENT / "earlier-drafts.json")
        self.moved = load_json(CONTENT / "moved.json")
        # The models catalog Task Object (models.meta, a byte-for-byte local copy until Tessera serves it): every model
        # and agent program, and what each is used for. Pages name them only through it.
        self.catalog = load_json(CONTENT / "models.meta.json")
        self.models = {m["id"]: m for group in ("models", "harnesses", "other_makers") for m in self.catalog[group]}
        self.models_page = load_json(CONTENT / "models-page.json")
        self.manifest = load_json(MANIFEST)
        self.brief = read_brief()
        self.frozen = frozen_pages(self.manifest, self.drafts)
        self.decks = [load_deck(deck_id, self.brief, self.site["endpoints"], self.feed) for deck_id in self.site["decks"]]


def frozen_pages(manifest: dict, drafts: dict) -> set[Path]:
    pages = {SITE / version["path"] / "index.html" for version in manifest["versions"]}
    for group in drafts["groups"]:
        pages |= {SITE / item["href"] / "index.html" for item in group["items"] if "html_sha256" in item}
    return pages


def whole(value, what: str, least: int) -> int:
    if type(value) is not int or value < least:
        fail(f"library.json: {what} must be a whole number of at least {least}")
    return value


def words_of(value, what: str) -> str:
    if not isinstance(value, str) or not value.strip():
        fail(f"library.json: {what} needs words")
    return value


def check_library(library: dict) -> None:
    """The library noun is well formed: one pinned commit of the seed-pack library, every pack with its counts and
    its folder at that commit, totals that are the packs' sums, a status the page has words for, and categories that
    hold every pack exactly once. scripts/sync_library.py writes the measured part and runs this same check."""
    source = library.get("source") or {}
    if source.get("repository") != LIBRARY_REPOSITORY:
        fail("library.json: the source must be the seed-pack library")
    commit = source.get("commit", "")
    if FULL_SHA.fullmatch(commit) is None or FULL_SHA.fullmatch(source.get("tessera_commit", "")) is None:
        fail("library.json: the source needs the library's full commit and the Tessera commit its receipt names")
    try:
        when = dt.datetime.fromisoformat(source.get("committed_at", ""))
    except ValueError:
        when = None
    if when is None or when.tzinfo is None:
        fail("library.json: committed_at must be the commit's date with its time zone")
    words = library["words"]
    packs = library.get("packs")
    if not isinstance(packs, list) or not packs:
        fail("library.json: no packs; run scripts/sync_library.py")
    ids = []
    for pack in packs:
        if not isinstance(pack, dict) or set(pack) != PACK_FIELDS:
            fail(f"library.json: a pack needs exactly the fields {sorted(PACK_FIELDS)}")
        pack_id = pack["id"]
        if not isinstance(pack_id, str) or SLUG.fullmatch(pack_id) is None:
            fail(f"library.json: {pack_id!r} is not a pack id")
        for key in ("title", "purpose", "version"):
            words_of(pack[key], f"{pack_id}'s {key}")
        if pack["purpose"].lower().startswith("a collection of nouns and verbs"):
            fail(f"library.json: {pack_id}'s purpose leaves out the opening the library puts on every pack")
        if pack["status"] not in words["status"]:
            fail(f"library.json: {pack_id} has the status {pack['status']!r}, which the page has no words for")
        whole(pack["nouns"], f"{pack_id}'s nouns", 1)
        whole(pack["verbs"], f"{pack_id}'s verbs", 1)
        whole(pack["worked_examples"], f"{pack_id}'s worked examples", 0)
        if type(pack["kit"]) is not bool:
            fail(f"library.json: {pack_id}'s kit is true or false")
        code = pack["code"]
        if code is not None:
            if not isinstance(code, dict) or set(code) != CODE_FIELDS:
                fail(f"library.json: {pack_id}'s code needs exactly {sorted(CODE_FIELDS)}")
            whole(code["files"], f"{pack_id}'s code files", 1)
            whole(code["tests"], f"{pack_id}'s test files", 1)
            if not str(code["workflow"]).startswith(".github/workflows/"):
                fail(f"library.json: {pack_id}'s code needs the CI workflow that tests it")
        if pack["url"] != f"{LIBRARY_REPOSITORY}/tree/{commit}/packs/{pack_id}":
            fail(f"library.json: {pack_id} must link to its folder at the pinned commit")
        ids.append(pack_id)
    if len(set(ids)) != len(ids):
        fail("library.json: a pack is listed twice")
    totals = {"packs": len(packs), "nouns": sum(p["nouns"] for p in packs), "verbs": sum(p["verbs"] for p in packs),
              "worked_examples": sum(p["worked_examples"] for p in packs),
              "with_code": sum(1 for p in packs if p["code"])}
    if library.get("totals") != totals:
        fail(f"library.json: the totals must be the packs' sums, {totals}")
    categories = library.get("categories")
    if not isinstance(categories, list) or not categories:
        fail("library.json: no categories")
    names = [category.get("id") for category in categories]
    if any(not isinstance(name, str) or CATEGORY_ID.fullmatch(name) is None for name in names) or \
            len(set(names)) != len(names):
        fail("library.json: every category needs its own id, starting with a letter")
    taken = (set(names) & set(ids)) | ((set(names) | set(ids)) & LIBRARY_IDS)
    if taken:
        fail("library.json: a category and a pack, or the page itself, share the id " + ", ".join(sorted(taken)))
    for category in categories:
        for key in ("name", "short", "intro"):
            words_of(category.get(key), f"the {category['id']} category's {key}")
        if not isinstance(category.get("packs"), list) or not category["packs"]:
            fail(f"library.json: the {category['id']} category holds no packs")
    placed = [pack_id for category in categories for pack_id in category["packs"]]
    if len(placed) != len(set(placed)) or set(placed) != set(ids):
        fail("library.json: every pack sits in exactly one category, and every category entry is a pack")


def check_explorer(explorer: dict, ecosystem: dict) -> None:
    """Validate explorer.json and ecosystem-catalog.json counts and honesty status."""
    items = explorer.get("items")
    if not isinstance(items, list) or not items:
        fail("explorer.json: items must be a non-empty list; run scripts/sync_explorer.py")
    counts = {
        "packs": sum(1 for item in items if item.get("kind") == "pack"),
        "verbs": sum(1 for item in items if item.get("kind") == "verb"),
        "nouns": sum(1 for item in items if item.get("kind") == "noun"),
        "total": len(items),
    }
    if explorer.get("counts") != counts:
        fail(f"explorer.json: counts must match items, {counts}")
    if not isinstance(explorer.get("harness_feeds", {}).get("harnesses"), list) or not explorer["harness_feeds"]["harnesses"]:
        fail("explorer.json: harness_feeds needs harnesses")
    if ecosystem.get("status") != "unexecuted_public_scan_mapping":
        fail("ecosystem-catalog.json: status must remain unexecuted_public_scan_mapping")
    projects = ecosystem.get("projects")
    if not isinstance(projects, list) or not projects or ecosystem.get("project_count") != len(projects):
        fail("ecosystem-catalog.json: project_count must match non-empty projects list")


# Shared page chrome -------------------------------------------------------------------------------

def prefix_for(page: Path) -> str:
    if page.relative_to(SITE).as_posix() == "404.html":
        return PAGES_PREFIX  # the worker serves this page at any missing path, so its links are absolute.
    depth = len(page.relative_to(SITE).parts) - 1
    return "../" * depth


def link(prefix: str, target: str) -> str:
    return attr(prefix + target) if prefix + target else "./"


def section_for(page: Path) -> str:
    parts = page.relative_to(SITE).parts
    if parts == ("404.html",):
        return ""  # a missing page belongs to no section
    first = parts[0] if len(parts) > 1 else "home"
    return {"storyboards": "decks", "video": "decks"}.get(first, first)


def head_block(prefix: str, nouns: Nouns | None = None) -> str:
    share = nouns.site["share"] if nouns else None
    tags = [] if not share else [
        f'<meta property="og:site_name" content="{attr(share["site_name"])}">',
        f'<meta property="og:image" content="{attr(share["image"])}">',
        f'<meta property="og:image:width" content="{int(share["width"])}">',
        f'<meta property="og:image:height" content="{int(share["height"])}">',
        f'<meta property="og:image:alt" content="{attr(share["alt"])}">',
        '<meta name="twitter:card" content="summary_large_image">',
    ]
    return "\n".join(tags + [
        '<meta name="color-scheme" content="light">',
        f'<link rel="stylesheet" href="{prefix}assets/fonts.css">',
        f'<link rel="stylesheet" href="{prefix}assets/tokens.css">',
        f'<link rel="stylesheet" href="{prefix}assets/site.css">',
        f'<link rel="icon" href="{prefix}assets/mark.svg" type="image/svg+xml">',
        JS_CLASS,
    ])


def header_block(page: Path, prefix: str, nouns: Nouns) -> str:
    """The skip link, the agent banner above everything, then the header the SiteHeader board draws: the mark and
    name, five links, and Eranos in the first screen. On a phone the links fold behind a Menu button."""
    site, header = nouns.site, nouns.site["header"]
    section = section_for(page)
    rel = page.relative_to(SITE).as_posix()
    items = []
    for item in site["nav"]:
        current = ""
        if item["section"] == section:
            current = ' aria-current="page"' if rel == item["href"] + "index.html" else ' aria-current="true"'
        items.append(f'<li><a href="{link(prefix, item["href"])}"{current}>{text(item["label"])}</a></li>')
    return "\n".join([
        f'<a class="skip-link" href="#main">{text(site["skip_link"])}</a>',
        banner_block(prefix, nouns),
        '<header class="site-header">',
        '<div class="wrap">',
        f'<a class="wordmark" href="{link(prefix, "")}">{MARK}<span>{text(header["brand"])}</span></a>',
        f'<button class="menu-toggle" type="button" data-menu-toggle aria-expanded="false" aria-controls="site-nav" '
        f'data-open="{attr(header["menu_close"])}" data-closed="{attr(header["menu"])}" hidden>{MENU_ICON}'
        f'<span>{text(header["menu"])}</span></button>',
        f'<nav class="site-nav" id="site-nav" aria-label="{attr(header["nav_label"])}" data-menu>',
        "<ul>" + "".join(items) + "</ul>",
        "</nav>",
        f'<a class="eranos-link" href="{attr(header["eranos_href"])}" aria-label="{attr(header["eranos_aria"])}">'
        f'<span class="long">{text(header["eranos_label"])}</span><span class="short">{text(header["eranos_short"])}</span></a>',
        "</div>",
        "</header>",
        tour_block(prefix, nouns),
    ])


def tour_block(prefix: str, nouns: Nouns) -> str:
    """The 45-second tour for judges (the JudgeTour board): a strip under the header that the shared
    <ta-judge-tour> element shows only with ?tour=judge, every word from the judge-tour noun."""
    data = {k: v for k, v in nouns.tour.items() if k != "about"}
    raw = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    raw = raw.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    return "\n".join([
        '<ta-judge-tour class="judge-tour" data-host="agora.ta-amps.workers.dev" hidden>',
        f'<script type="application/json">{raw}</script>',
        "</ta-judge-tour>",
        f'<script src="{prefix}assets/judge-tour.js" defer></script>',
    ])


def banner_json(nouns: Nouns) -> str:
    """The agent-banner noun as the JSON the element reads, safe inside a script element."""
    data = {k: v for k, v in nouns.banner.items() if k not in {"about", "fallback"}}
    raw = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return raw.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def banner_block(prefix: str, nouns: Nouns) -> str:
    """The agent banner: one thin line above the header. The shared <ta-agent-banner> element renders every word
    from the embedded noun; without scripts, the line and a link to llms.txt stay."""
    banner = nouns.banner
    return "\n".join([
        '<ta-agent-banner class="agent-banner" data-site="agora" data-own-keys>',
        f'<script type="application/json">{banner_json(nouns)}</script>',
        f'<p class="agent-fallback">{AGENT_ICON}<span class="agent-fallback-lead"><b>{text(banner["lead_strong"])}</b> '
        f'{text(banner["lead"])}</span> <a href="{prefix}llms.txt">{text(banner["fallback"])}</a></p>',
        "</ta-agent-banner>",
        f'<script src="{prefix}assets/agent-banner.js" defer></script>',
    ])


def footer_block(prefix: str, nouns: Nouns) -> str:
    footer = nouns.site["footer"]
    links = [f'<li><a href="{link(prefix, item["href"])}">{text(item["label"])}</a></li>' for item in footer["links"]]
    links += [f'<li><a href="{attr(prefix + item["href"]) if item.get("local") else attr(item["href"])}">'
              f'{text(item["label"])}</a></li>' for item in footer["outside"]]
    return "\n".join([
        '<footer class="site-footer">',
        '<div class="wrap">',
        f'<p class="footer-note">{text(footer["note"])}</p>',
        f'<nav aria-label="{attr(footer["nav_label"])}">',
        "<ul>" + "".join(links) + "</ul>",
        "</nav>",
        f'<p class="footer-privacy">{text(footer["privacy"])}</p>',
        "</div>",
        "</footer>",
        f'<script src="{prefix}assets/site.js" defer></script>',
    ])


def replace_block(content: str, name: str, block: str, page: Path) -> str:
    start, end = f"<!-- site:{name} -->", f"<!-- /site:{name} -->"
    if content.count(start) != 1 or content.count(end) != 1:
        fail(f"{page.relative_to(ROOT)}: needs exactly one {start} ... {end} block")
    before, rest = content.split(start, 1)
    _, after = rest.split(end, 1)
    return f"{before}{start}\n{block}\n{end}{after}"


def render_page(page: Path, content: str, nouns: Nouns) -> str:
    prefix = prefix_for(page)
    if "<!-- site:head -->" not in content:
        # A page that keeps its own head and header, such as the Studio, still gets the agent banner first, and the
        # judge tour under it (the Studio is the tour's live-queue step).
        return replace_block(content, "banner", banner_block(prefix, nouns) + "\n" + tour_block(prefix, nouns), page)
    content = replace_block(content, "head", head_block(prefix, nouns), page)
    content = replace_block(content, "header", header_block(page, prefix, nouns), page)
    return replace_block(content, "footer", footer_block(prefix, nouns), page)


def page_shell(title: str, description: str, main: str, extra_head: str = "", body_class: str = "",
               extra_body: str = "", robots: str = "") -> str:
    """A generated page with empty chrome blocks, which render_page fills."""
    head = [
        "<!doctype html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{text(title)}</title>",
    ]
    if description:
        head.append(f'<meta name="description" content="{attr(description)}">')
    if robots:
        head.append(f'<meta name="robots" content="{attr(robots)}">')
    head += ["<!-- site:head -->", "<!-- /site:head -->"]
    if extra_head:
        head.append(extra_head)
    body = f'<body class="{body_class}">' if body_class else "<body>"
    return "\n".join(head + [
        "</head>",
        body,
        "<!-- site:header -->",
        "<!-- /site:header -->",
        main,
        "<!-- site:footer -->",
        "<!-- /site:footer -->",
    ] + ([extra_body] if extra_body else []) + ["</body>", "</html>", ""])


# Links into the retired GitHub organization --------------------------------------------------------

GITHUB_LINK = re.compile(r"https://github\.com/ta-amps(?:/(?P<repo>[A-Za-z0-9._-]+?)(?P<dotgit>\.git)?"
                         r"(?:/(?P<kind>[a-z]+)(?:/(?P<rest>[^\s\"'<>)\]]*))?)?)?(?=[\s\"'<>)\]]|/?$|/[\s\"'<>)\]])/?")
PAGES_LINK = re.compile(r"https://ta-amps\.github\.io/[A-Za-z0-9._-]+/")
FULL_OR_SHORT_SHA = re.compile(r"[0-9a-f]{7,40}\Z")


def source_link(match: re.Match, links: dict) -> str:
    """One GitHub address, as the address of the same thing in Agora's source mirror (see source-links.json)."""
    repo, kind, rest = match.group("repo"), match.group("kind"), match.group("rest") or ""
    mirror = links["mirror"]
    if repo and repo in links["heads"] and repo not in links["mirrored"]:
        return match.group(0)  # not mirrored on Agora (yet to be swept): its GitHub page, as written
    if not repo:
        return mirror if links["mirrored"] else match.group(0)
    if repo not in links["heads"]:
        fail(f"a link names a repository the source mirror does not hold: {match.group(0)}")
    if not kind and match.group("dotgit"):
        # A clone address: git clones the same repository from Agora's git mirror over plain HTTP.
        if repo in links["git_held_back"]:
            fail(f"a clone address names a repository whose git mirror is not published: {match.group(0)}")
        return f"{links['git_mirror']}{repo}.git"
    if not kind:
        return f"{mirror}{repo}/"
    rest, _, query = rest.partition("?")
    rest = rest.split("#", 1)[0]
    if kind in ("tree", "blob", "commit"):
        ref, _, path = rest.partition("/")
        if FULL_OR_SHORT_SHA.match(ref) and len(ref) == 40:
            sha = ref
        elif ref in ("main", "HEAD") or (kind == "commit" and FULL_OR_SHORT_SHA.match(ref)):
            sha = links["heads"][repo] if ref in ("main", "HEAD") else ref
        else:
            fail(f"a link names a branch or short commit the source mirror cannot pin: {match.group(0)}")
        if kind == "commit" or not path:
            return f"{mirror}{repo}/{sha[:12]}/"
        return f"{mirror}{repo}/{sha[:12]}/{path.rstrip('/')}" + ("/" if kind == "tree" else "")
    if kind == "pull":
        number = rest.split("/", 1)[0]
        sha = links["pulls"].get(f"{repo}#{number}")
        if not sha:
            fail(f"a link names a pull request without a recorded merge commit: {match.group(0)}")
        return f"{mirror}{repo}/{sha[:12]}/"
    if kind == "issues":
        form = re.search(r"(?:^|&)template=([A-Za-z0-9._-]+)", query)
        if form:
            target = links["forms"].get(f"{repo}/{form.group(1)}")
            if not target:
                fail(f"a link names an issue form without a new home: {match.group(0)}")
            return target
        return f"{mirror}{repo}/"
    if kind == "releases" and rest.startswith("download/"):
        tag, _, name = rest[len("download/"):].partition("/")
        folder = links["releases"].get(f"{repo}/{tag}")
        if not folder or not (SITE / folder.strip("/") / name).is_file():
            fail(f"a link names a release file this site does not serve: {match.group(0)}")
        return folder + name
    fail(f"a link into GitHub has no home in the source mirror: {match.group(0)}")
    return ""


def repoint(content: str, links: dict) -> str:
    """Every link into the retired GitHub organization or its Pages sites, as the link that works now."""
    content = GITHUB_LINK.sub(lambda m: source_link(m, links), content)
    for old, new in links["pages"].items():
        content = content.replace(old, new)
    if PAGES_LINK.search(content):
        fail(f"a link to a GitHub Pages site has no new home: {PAGES_LINK.search(content).group(0)}")
    return content


# Plain words instead of "synthetic" (owner, October 31: "DO NOT INCLUDE SYNTHETIC") ---------------------------

# The owner's style for anything about tests: tests, evaluations, accuracy, performance; data and cases are examples.
PLAIN_RULES = [
    (re.compile(r"\bsynthetic_disclosure\b"), "example_data_disclosure"),  # a video check's name, shown in a table
    (re.compile(r"\bsynthetic examples\b", re.I), "examples"),
    (re.compile(r"\ba synthetic voice\b", re.I), "an AI voice"),
    (re.compile(r"\bsynthetic voice\b", re.I), "AI voice"),
    (re.compile(r"\bsynthetic[- ]only\b", re.I), "example-data-only"),
    (re.compile(r"\banything synthetic\b", re.I), "anything made up"),
    (re.compile(r"\b(?:a )?frozen, synthetic tool-call test of 150 rows\b", re.I), "a fixed 150-task evaluation"),
    (re.compile(r"\bscored on synthetic tests\b", re.I), "measured on our evaluations"),
    (re.compile(r"\bsynthetic 150-row test\b", re.I), "150-task evaluation"),
    (re.compile(r"\bsynthetic tool-call tests?\b", re.I), "tool-call evaluation"),
    (re.compile(r"\bsynthetic (pre-registered )?holdouts\b", re.I), r"\1held-out evaluations"),
    (re.compile(r"\bsynthetic (pre-registered )?holdout\b", re.I), r"\1held-out evaluation"),
    (re.compile(r"\bsynthetic test (cases|data)\b", re.I), r"example test \1"),
    (re.compile(r"\bsynthetic (tests|evaluations)\b", re.I), "our evaluations"),
    (re.compile(r"\bsynthetic test\b", re.I), "our evaluation"),
    (re.compile(r"\bsynthetic tasks\b", re.I), "our evaluation tasks"),
    (re.compile(r"\ba synthetic task\b", re.I), "an evaluation task"),
    (re.compile(r"\bsynthetic task\b", re.I), "evaluation task"),
    (re.compile(r"\bsynthetic (normalized )?benchmark(s?)\b", re.I), r"our \1benchmark\2"),
    (re.compile(r"\bsynthetic ((?:slot )?templates|(?:template |training )?rows)\b", re.I), r"\1"),
    (re.compile(r"\bis synthetic\b", re.I), "is made up"),
    (re.compile(r"\ba synthetic\b", re.I), "an example"),
    (re.compile(r"\bsynthetic\b", re.I), "example"),
]


def _match_case(found: str, replacement: str) -> str:
    if found.isupper() and len(found) > 1:
        return replacement.upper()
    if found[:1].isupper():
        return replacement[:1].upper() + replacement[1:]
    return replacement


MODEL_TOKEN = re.compile(r"\{\{model:([a-z0-9./_-]+?)(:tuned)?\}\}")
TIER_SUFFIXES = ("-contributor", "-standard")


def meta_models(content: str, models: dict) -> str:
    """Models by name (owner, Nov 1: name the specific models, never hand-typed): every {{model:<id>}} in a page renders
    as that entry's display name in the models catalog (site/content/models.meta.json), and {{model:<id>:tuned}} as its
    tuned name. A run's declared id with a tier suffix (muse-spark-1.3-contributor) names its model. An id the
    catalog does not hold stops the build."""
    def name(match: re.Match) -> str:
        key = match.group(1)
        entry = models.get(key) or next((models.get(key[:-len(t)]) for t in TIER_SUFFIXES if key.endswith(t)), None)
        if not entry:
            fail(f"a page names a model the models catalog does not hold: {key}")
        if match.group(2):
            if "display_tuned" not in entry:
                fail(f"the models catalog has no tuned name for {key}")
            return entry["display_tuned"]
        return entry["display"]
    return MODEL_TOKEN.sub(name, content)


def plain_words(content: str) -> str:
    """Every "synthetic" a page or noun would show, in the owner's plain words with the same honesty: tests become
    our evaluations, data and cases become example data and cases, a synthetic voice an AI voice."""
    for pattern, replacement in PLAIN_RULES:
        content = pattern.sub(lambda m: _match_case(m.group(0), m.expand(replacement)), content)
    return content.replace("example-data-only", "example data only").replace("Example-data-only", "Example data only") \
        .replace("EXAMPLE-DATA-ONLY", "EXAMPLE DATA ONLY")


# Slides --------------------------------------------------------------------------------------------

STYLE_PART = re.compile(r"\s*([a-z-]+)\s*:\s*([^;]+)")
SLIDE_LINK = re.compile(r'<a\b[^>]*?\shref="([^"]*)"[^>]*>(.*?)</a>', re.S)


def style_map(style: str) -> dict[str, str]:
    return {m.group(1): m.group(2).strip() for m in STYLE_PART.finditer(style)}


def px(value: str | None, what: str) -> int:
    match = re.fullmatch(r"(\d+)px", value or "")
    if not match:
        fail(f"{what}: expected a pixel size, found {value!r}")
    return int(match.group(1))


def shape_svg(match: re.Match) -> str:
    kind, style = match.group(1), style_map(match.group(2))
    w, h = px(style.get("width"), "x-shape width"), px(style.get("height"), "x-shape height")
    fill = style.get("background")
    if not fill:
        fail("x-shape needs a background colour")
    if kind == "arrow-right":
        # The outline the slide format draws for arrow-right: a shaft at 25 to 75% height, the head from 62%.
        sx, y1, y2 = round(w * 0.62, 2), round(h * 0.25, 2), round(h * 0.75, 2)
        path = f"M0 {y1}H{sx}V0L{w} {h / 2:g}L{sx} {h}V{y2}H0Z"
    elif kind == "arrow-down":
        # The same arrow, pointing down: a shaft at 25 to 75% width, the head from 62% height.
        sy, x1, x2 = round(h * 0.62, 2), round(w * 0.25, 2), round(w * 0.75, 2)
        path = f"M{x1} 0H{x2}V{sy}H{w}L{w / 2:g} {h}L0 {sy}H{x1}Z"
    else:
        fail(f"unsupported x-shape kind {kind!r}")
    return (f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" aria-hidden="true" focusable="false" '
            f'style="display:block;flex-shrink:0"><path d="{path}" fill="{html.escape(fill)}"/></svg>')


def icon_svg(match: re.Match) -> str:
    name, style = match.group(1), match.group(2)
    if name not in ICONS:
        fail(f"unsupported x-icon {name!r}")
    return ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
            f'stroke-linejoin="round" aria-hidden="true" focusable="false" style="{html.escape(style)};'
            f'display:block;flex-shrink:0">{ICONS[name]}</svg>')


def brief_html(style: str, brief: str) -> str:
    return f'<pre id="slide-brief" style="{attr(style)}">{text(brief)}</pre>'


def endpoints_html(style: str, endpoints: dict) -> str:
    """The endpoint table for a slide: name, what it is, MCP and llms.txt, at the slide's own scale."""
    widths = ("width:10%", "width:27%", "width:30%", "width:33%")
    cell = f"{MONO};font-size:19px;line-height:1.35"
    head = "".join(f'<th style="{w}">{text(c)}</th>' for c, w in zip(endpoints["columns"], widths))
    rows = "".join(
        f'<tr><td><b>{text(r["name"])}</b></td><td>{text(r["what"])}</td>'
        f'<td style="{cell}">{text(r["mcp"])}</td>'
        f'<td style="{cell}"><a href="{attr(r["llms"])}" style="color:#2A5DB0;text-decoration:none">'
        f'{text(r["llms"])}</a></td></tr>' for r in endpoints["rows"])
    return f'<table style="{attr(style)}"><tr style="background:#EDE8DC">{head}</tr>{rows}</table>'


def plain_text(fragment: str) -> str:
    fragment = re.sub(r"<br\s*/?>", " ", fragment)
    fragment = re.sub(r"<[^>]+>", "", fragment)
    return re.sub(r"\s+", " ", html.unescape(fragment)).strip()


def load_slide(source: Path, name: str, brief: str | None = None, endpoints: dict | None = None,
               feed: dict | None = None) -> dict:
    """One slide of the v4 format: a <section> with inline styles, custom elements and one <aside>."""
    path = source / "slides" / f"{name}.html"
    if not path.is_file():
        fail(f"missing slide source {path.relative_to(ROOT)}")
    content = path.read_text(encoding="utf-8").strip()
    opening = re.match(r'<section\s+id="([a-z0-9-]+)"([^>]*)>', content)
    if not opening or not content.endswith("</section>") or opening.group(1) != name:
        fail(f"{name}: a slide is one <section id=\"{name}\"> element")
    style = re.search(r'\sstyle="([^"]*)"', opening.group(2))
    inner = content[opening.end():-len("</section>")]
    asides = re.findall(r"<aside>(.*?)</aside>", inner, re.S)
    if len(asides) != 1:
        fail(f"{name}: expected one <aside> with speaker notes")
    inner = re.sub(r"\s*<aside>.*?</aside>\s*", "\n", inner, flags=re.S)
    inner = re.sub(r'<x-shape kind="([a-z-]+)" style="([^"]*)"></x-shape>', shape_svg, inner)
    inner = FEED_TAG.sub(lambda m: feed_status(m, feed), inner)
    inner = re.sub(r'<x-icon name="([A-Za-z]+)" style="([^"]*)"></x-icon>', icon_svg, inner)
    copy = None
    brief_tag = re.compile(r'<x-brief style="([^"]*)"></x-brief>')
    if brief_tag.search(inner):
        if brief is None or len(brief_tag.findall(inner)) != 1:
            fail(f"{name}: a slide shows the starting brief once, from site/agent-brief.txt")
        inner = brief_tag.sub(lambda m: brief_html(m.group(1), brief), inner)
        copy = "slide-brief"
    endpoint_tag = re.compile(r'<x-endpoints style="([^"]*)"></x-endpoints>')
    if endpoint_tag.search(inner):
        if endpoints is None:
            fail(f"{name}: no endpoints to show")
        inner = endpoint_tag.sub(lambda m: endpoints_html(m.group(1), endpoints), inner)
    if "<x-" in inner:
        fail(f"{name}: unconverted custom element")
    heading = re.search(r"<h([12])\b[^>]*>(.*?)</h\1>", inner, re.S)
    if not heading:
        fail(f"{name}: slide needs an h1 or h2 title")
    links = [(href, plain_text(label)) for href, label in SLIDE_LINK.findall(inner)]
    return {"name": name, "style": style.group(1) if style else "", "inner": inner.strip(),
            "notes": asides[0].strip(), "title": plain_text(heading.group(2)), "links": links, "copy": copy}


SLIDE_MARK_CAPTION = re.compile(
    r'<svg aria-label="ta-amps mark"[^>]*>.*?</svg>\s*<p style="position:absolute;left:176px;bottom:\d+px;([^"]*)">(.*?)</p>', re.S)
DARK_INKS = {"#8C96A6", "#9AA3B2", "#C8D0DC", "#A3ABB9"}


def slide_footer(inner: str, deck_title: str, number: int) -> str:
    """The Deck-Content board's one-line footer: a rule, then the mark, ta-amps, the deck and the slide's own caption
    on the left, and the slide number on the right. It replaces the slide's mark and caption."""
    match = SLIDE_MARK_CAPTION.search(inner)
    if not match:
        fail(f"{deck_title}: slide {number} has no mark and caption for the footer")
    ink = re.search(r"color:(#[0-9A-Fa-f]{6})", match.group(1))
    ink = ink.group(1).upper() if ink else "#5E6472"
    dark = ink in DARK_INKS
    rule, mark = ("#2C3443", ("#6FA3F0", "#F0884F", "#C8D0DC")) if dark else ("#E2DCCF", ("#2A5DB0", "#B8541F", "#11161F"))
    svg = (f'<svg aria-hidden="true" width="24" height="24" viewBox="0 0 32 32" style="flex:none">'
           f'<rect x="0" y="0" width="14" height="14" rx="3" fill="{mark[0]}"/><rect x="18" y="0" width="14" height="14" rx="3" fill="{mark[1]}"/>'
           f'<rect x="0" y="18" width="14" height="14" rx="3" fill="{mark[2]}"/><rect x="18" y="18" width="14" height="14" rx="3" fill="{mark[0]}"/></svg>')
    foot = (f'<div class="slide-foot" style="position:absolute;left:128px;right:96px;bottom:48px;display:flex;'
            f'justify-content:space-between;align-items:center;gap:24px;font-size:22px;line-height:1.3;color:{ink};'
            f'border-top:1px solid {rule};padding-top:16px">'
            f'<span style="display:flex;align-items:center;gap:14px;min-width:0">{svg}'
            f'<span>ta-amps · {text(deck_title)} · {match.group(2)}</span></span>'
            f"<span class=\"slide-no\" style=\"font-family:'JetBrains Mono', 'Courier New', monospace\">{number}</span></div>")
    return inner[:match.start()] + foot + inner[match.end():]


FEED_TAG = re.compile(r'<x-feed-status kind="(line|row)" style="([^"]*)"></x-feed-status>')


def feed_status(match: re.Match, feed: dict | None) -> str:
    """The memory-systems feed's schedule and last run, drawn on a slide only once its scans run on hosted Tessera;
    until then the element draws nothing, so no slide says a feed runs when it does not."""
    if not feed or not feed_hosted(feed):
        return ""
    last = feed["last_run"]
    words = (f"The memory-systems feed runs {text(last['schedule'].split(' (')[0])}; last run {text(last['at'][:16].replace('T', ' '))}"
             f"&nbsp;UTC, receipt {text(last['receipt_hash'][:12])}.")
    if match.group(1) == "line":
        return f'<p style="{attr(match.group(2))}">{words}</p>'
    return (f'<div style="{attr(match.group(2))}"><p style="width:170px;text-align:center;background:#15281D;color:#7FD3A0;'
            f'border-radius:999px;padding:6px 0;font-size:22px;font-weight:600">Live</p>'
            f'<p style="flex:1;font-size:27px;line-height:1.4;color:#F5F2EA">{words}</p></div>')


def load_deck(deck_id: str, brief: str, endpoints: dict, feed: dict | None = None) -> dict:
    folder = DECKS / deck_id
    source = folder / "source"
    spec = load_json(source / "deck.json")
    order = spec["order"]
    if len(order) != len(set(order)):
        fail(f"{deck_id}: deck.json lists a slide twice")
    if spec.get("cover") != order[0]:
        fail(f"{deck_id}: the cover must be the first slide")
    slides = [load_slide(source, name, brief, endpoints, feed) for name in order]
    for number, slide in enumerate(slides, 1):
        slide["inner"] = slide_footer(slide["inner"], spec["title"], number)
    if sum(1 for s in slides if s["copy"]) > 1:
        fail(f"{deck_id}: the starting brief appears on one slide at most")
    cover = slides[0]
    if re.search(r"<(a|button)\b|\sid=", cover["inner"]):
        fail(f"{deck_id}: the cover becomes a thumbnail, so it holds no links, buttons or ids")
    claims = None
    if (source / "claims.json").exists():
        claims = load_json(source / "claims.json")
        for claim in claims["claims"]:
            if claim["status"] not in CLAIM_STATUSES:
                fail(f"{deck_id}: claims.json has an unknown status {claim['status']!r}")
            if claim["slide"] not in order:
                fail(f"{deck_id}: claims.json names an unknown slide {claim['slide']!r}")
    index = {name: i for i, name in enumerate(order)}
    starts = sorted((index[part["start"]], part["description"]) for part in spec["sections"].values())
    if not starts or starts[0][0] != 0:
        fail(f"{deck_id}: the first section must start at the cover")
    sections = [{"start": start, "stop": starts[n + 1][0] if n + 1 < len(starts) else len(slides), "text": label}
                for n, (start, label) in enumerate(starts)]
    return {"id": deck_id, "folder": folder, "page": folder / "index.html", "spec": spec, "slides": slides,
            "claims": claims, "sections": sections, "pdf_name": spec["page"]["pdf"]}


def render_slide(i: int, slide: dict, total: int, ui: dict, sources: str = "") -> str:
    label = f"{i + 1} {ui['of']} {total}: {slide['title']}"
    parts = [
        f'<section class="slide" id="slide-{i + 1}" aria-roledescription="slide" aria-label="{attr(label)}" '
        f'data-name="{slide["name"]}">',
        f'<div class="slide-frame" id="{slide["name"]}">',
        f'<div class="slide-canvas" style="{attr(slide["style"])}">',
        slide["inner"],
        "</div>",
        "</div>",
    ]
    if slide["copy"]:
        parts.append(f'<div class="slide-actions"><button class="button" type="button" data-copy="{slide["copy"]}" '
                     f'data-copied="{attr(ui["copied"])}" data-selected="{attr(ui["selected"])}" hidden>'
                     f'{COPY_ICON}<span>{text(ui["copy_brief"])}</span></button>'
                     f'<span class="copy-status" id="{slide["copy"]}-status" role="status"></span></div>')
    if slide["links"]:
        items = "".join(f'<li><a href="{attr(href)}">{text(label)}</a></li>' for href, label in slide["links"])
        parts.append(f'<div class="slide-links"><h2>{text(ui["links_heading"])}</h2><ul>{items}</ul></div>')
    parts += [f'<div class="slide-notes"><h2>{text(ui["notes"])}</h2><p>{slide["notes"]}</p>{sources}</div>',
              "</section>"]
    return "\n".join(parts)


def slide_sources(name: str, deck: dict, ui: dict) -> str:
    """Every number on one slide, with its source: shown with the speaker notes, never under the slides."""
    claims = [claim for claim in (deck["claims"] or {"claims": []})["claims"] if claim["slide"] == name]
    items = []
    for claim in claims:
        evidence = (f' <a href="{attr(claim["link"])}">{text(ui["evidence"])}</a>' if claim.get("link") else "")
        items.append(f'<li><span class="claim-status {claim["status"]}">{text(claim["status"].capitalize())}</span> '
                     f'{text(claim["number"])}. {text(claim["source"])}{evidence}</li>')
    return f'<ul class="slide-sources">{"".join(items)}</ul>' if items else ""


def render_deck(deck: dict, nouns: Nouns) -> str:
    ui = nouns.site["deck"]
    spec, slides = deck["spec"], deck["slides"]
    page = spec["page"]
    total = len(slides)
    outline = "".join(
        f'<div class="outline-group"><h2>{text(part["text"])}</h2><ol start="{part["start"] + 1}">'
        + "".join(f'<li><a href="#slide-{i + 1}" data-goto="{i}">{text(slides[i]["title"])}</a></li>'
                  for i in range(part["start"], part["stop"]))
        + "</ol></div>" for part in deck["sections"])
    body = "\n".join(render_slide(i, slide, total, ui, slide_sources(slide["name"], deck, ui))
                     for i, slide in enumerate(slides))
    main = "\n".join(filter(None, [
        f'<main id="main" class="deck" data-total="{total}">',
        '<div class="wrap deck-bar">',
        '<div class="deck-heading">',
        f'<p class="deck-kicker">{total} {text(ui["slides"])} · {text(page["date_text"])}</p>',
        f"<h1>{text(page['heading'])}</h1>",
        f"<p>{text(page['summary'])}</p>",
        "</div>",
        '<div class="deck-tools">',
        f'<button class="tool" type="button" data-outline-toggle aria-expanded="false" aria-controls="deck-outline" '
        f'hidden>{text(ui["outline"])}</button>',
        f'<button class="tool" type="button" data-notes-toggle aria-pressed="false" hidden>{text(ui["notes"])}</button>',
        f'<button class="tool" type="button" data-large-toggle aria-pressed="false" hidden>{text(ui["larger"])}</button>',
        f'<button class="tool" type="button" data-full-toggle data-exit="{attr(ui["exit_full_screen"])}" hidden>'
        f'{text(ui["full_screen"])}</button>',
        f'<a class="button secondary" href="{attr(deck["pdf_name"])}" download>{text(ui["pdf"])}</a>',
        "</div>",
        "</div>",
        f'<nav class="wrap deck-outline" id="deck-outline" aria-label="{attr(ui["outline"])}">',
        outline,
        "</nav>",
        '<div class="deck-stage" data-stage>',
        body,
        "</div>",
        '<div class="wrap deck-controls" data-controls hidden>',
        f'<button class="tool" type="button" data-prev>{text(ui["previous"])}</button>',
        f'<p class="deck-counter"><span data-current>1</span> {text(ui["of"])} {total}</p>',
        f'<button class="tool" type="button" data-next>{text(ui["next"])}</button>',
        "</div>",
        f'<div class="wrap deck-help" data-help hidden><p>{ui["help_html"]}</p>'
        f'<label class="deck-keys"><input type="checkbox" data-keys-toggle checked> {text(ui["letter_keys"])}</label></div>',
        f'<p class="visually-hidden" aria-live="polite" data-announce data-prefix="{attr(ui["announce"])}"></p>',
        "</main>",
    ]))
    prefix = prefix_for(deck["page"])
    return page_shell(page["title"], page["description"], main,
                      extra_head=f'<link rel="stylesheet" href="{prefix}assets/viewer.css">',
                      body_class="deck-page", extra_body=f'<script src="{prefix}assets/viewer.js" defer></script>')


def main_of(page: str) -> str:
    """The <main> element of a deck page: the part its PDF is printed from."""
    start, end = page.find("<main"), page.find("</main>")
    if start < 0 or end < 0:
        fail("a deck page needs one <main> element")
    return page[start:end + len("</main>")]


# Pages made from content nouns -------------------------------------------------------------------

def mark_kinds(sentence: str) -> str:
    """Colour the words nouns and verbs, as the site's key does: nouns blue, verbs rust."""
    sentence = re.sub(r"\bnouns\b", '<span class="noun-word">nouns</span>', text(sentence), count=1)
    return re.sub(r"\bverbs\b", '<span class="verb-word">verbs</span>', sentence, count=1)


def keep_together(escaped: str) -> str:
    """Keep hyphenated words, such as two-sided, on one line."""
    return re.sub(r"\b(\w+(?:-\w+)+)\b", r'<span class="nowrap">\1</span>', escaped)


def deck_card(deck: dict, prefix: str, ui: dict, level: int) -> str:
    """A deck's card: its cover as a live thumbnail, its title and its one-line summary."""
    spec, cover = deck["spec"], deck["slides"][0]
    href = f"{prefix}decks/{deck['id']}/"
    return "\n".join([
        '<li class="deck-card">',
        f'<div class="deck-thumb" aria-hidden="true" data-thumb><div class="thumb-canvas" '
        f'style="{attr(cover["style"])}">{cover["inner"]}</div></div>',
        '<div class="deck-card-body">',
        f'<p class="deck-card-meta">{len(deck["slides"])} {text(ui["slides"])}</p>',
        f'<h{level} class="deck-card-title"><a class="deck-card-link" href="{href}">{text(spec["title"])}</a></h{level}>',
        f'<p class="deck-card-summary">{text(spec["page"]["summary"])}</p>',
        f'<p class="deck-card-foot"><span class="deck-card-cta" aria-hidden="true">{text(ui["view"])}{CHEVRON}</span>'
        f'<a class="deck-card-pdf" href="{href}{attr(deck["pdf_name"])}" '
        f'aria-label="{attr(spec["title"] + ", " + ui["pdf_short"])}">{text(ui["pdf_short"])}</a></p>',
        "</div>",
        "</li>",
    ])


def film_cuts(videos: dict) -> tuple[dict, str]:
    """The film's default cut, and the buttons that switch between cuts when there is more than one."""
    cuts = videos["cuts"]
    for cut in cuts:
        for key in ("src", "captions", "poster"):
            if not (SITE / cut[key]).is_file():
                fail(f"home.json: the {cut['id']} cut's {key} is missing: {cut[key]}")
        if cut.get("clean_src") and not (SITE / cut["clean_src"]).is_file():
            fail(f"home.json: the {cut['id']} cut's clean_src is missing: {cut['clean_src']}")
    default = next((cut for cut in cuts if cut["id"] == videos["default"]), None)
    if default is None:
        fail(f"home.json: the default cut {videos['default']!r} is not one of the cuts")
    if len(cuts) < 2:
        return default, ""
    buttons = "".join(
        f'<button class="film-cut" type="button" aria-pressed="{"true" if cut is default else "false"}" '
        f'data-cut="{attr(cut["id"])}" data-src="{attr(cut["src"])}"'
        + (f' data-clean-src="{attr(cut["clean_src"])}"' if cut.get("clean_src") else "")
        + f' data-type="{attr(cut["type"])}" '
        f'data-captions="{attr(cut["captions"])}" data-poster="{attr(cut["poster"])}" '
        f'data-title="{attr(cut["title"])}" data-label="{attr(cut["label"])}">{text(cut["tab"])}</button>'
        for cut in cuts)
    cc_toggle = (
        '<button class="film-cc" type="button" aria-pressed="true" data-film-cc '
        'data-label-on="Captions · On" data-label-off="Captions · Off">Captions · On</button>'
    )
    return default, f'<div class="film-cuts" role="group" aria-label="{attr(videos["choose"])}" data-film-cuts hidden>{buttons}{cc_toggle}</div>'


def other_cut_links(videos: dict, default: dict) -> str:
    """Without JavaScript the cut buttons stay hidden, so the other cuts are plain links to their files."""
    return "".join(
        f'<span data-no-script> · <a href="{attr(cut["src"])}">{text(cut["tab"])}</a></span>'
        for cut in videos["cuts"] if cut is not default)


def use_anchor(name: str) -> str:
    """The id of a use case on the use cases page, from its name."""
    return "use-" + re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def film_made_ready(start: dict) -> bool:
    """The film's production page is linked only once its production trace noun exists and says it is final."""
    noun = ROOT / start["film_made"]["requires"]
    return noun.is_file() and json.loads(noun.read_text(encoding="utf-8")).get("status") == "final"


def render_home(nouns: Nouns) -> str:
    """The home page, as the Agora-Home board lays it out: the film first, then Start here with the two public
    sites, then the decks, then the use cases."""
    home, ui = nouns.home, nouns.site["deck"]
    videos, start, uses = home["videos"], home["start"], home["uses"]
    video, selector = film_cuts(videos)
    others = other_cut_links(videos, video) if selector else ""
    cards = "\n".join(deck_card(deck, "", ui, 3) for deck in nouns.decks)
    doors = "".join(
        f'<li><a class="start-card {attr(card["tone"])}" href="{attr(card["href"])}">'
        f'<span class="start-name">{MARK}<span>{text(card["name"])}</span></span>'
        f'<span class="start-host">{text(card["host"])}</span>'
        f'<span class="start-line">{text(card["line"])}</span></a></li>'
        for card in start["cards"])
    made = (f'<p class="start-made"><a href="{attr(start["film_made"]["href"])}">{text(start["film_made"]["label"])}</a></p>'
            if film_made_ready(start) else "")
    use_cards = "".join(
        f'<li><a class="home-use" href="use-cases/#{use_anchor(item["name"])}">'
        + (f'<span class="home-use-live">{text(uses["live"])}</span>' if item["home"].get("live_href") else "")
        + f'<b>{text(item["home"]["title"])}</b><span>{text(item["home"]["line"])}</span></a></li>'
        for item in nouns.uses["flagships"] if item.get("home"))
    main = "\n".join(filter(None, [
        '<main id="main">',
        f'<section class="film{" has-cuts" if selector else ""}" aria-labelledby="film-label">',
        '<div class="film-stage">',
        f'<video class="film-video" controls playsinline preload="metadata" poster="{attr(video["poster"])}" '
        f'aria-label="{attr(video["title"])}" data-captions-default'
        + (f' data-open-captions data-open-src="{attr(video["src"])}" data-clean-src="{attr(video["clean_src"])}"'
           if video.get("clean_src") else "")
        + ">",
        f'<source src="{attr(video["src"])}" type="{attr(video["type"])}">',
        f'<track kind="captions" src="{attr(video["captions"])}" srclang="{attr(videos["captions_lang"])}" '
        f'label="{attr(videos["captions_label"])}" default>',
        f'<p>{text(videos["fallback"])} <a href="{attr(video["src"])}">{text(videos["fallback_link"])}</a></p>',
        "</video>",
        '<div class="film-caption-bar" data-film-caption-bar hidden aria-hidden="true">'
        '<span class="film-caption-pill" data-film-caption-pill></span></div>',
        "</div>",
        selector,
        f'<p class="film-label"><span id="film-label">{text(video["label"])}</span>'
        + others
        + (f' · <a href="{attr(videos["outline"]["href"])}">{text(videos["outline"]["label"])}</a>' if videos.get("outline") else "")
        + "</p>",
        "</section>",
        f'<section class="start" id="start" aria-label="{attr(start["label"])}">',
        '<div class="wrap start-wrap">',
        f'<h1>{text(start["heading"])}</h1>',
        f'<ul class="start-cards">{doors}</ul>',
        made,
        "</div>",
        "</section>",
        '<section class="deck-band" id="decks" aria-labelledby="home-decks">',
        '<div class="wrap">',
        f'<div class="band-head"><h2 class="band-title" id="home-decks">{text(home["decks_heading"])}</h2></div>',
        f'<ul class="deck-cards">\n{cards}\n</ul>',
        "</div>",
        "</section>",
        '<section class="home-uses" id="use-cases" aria-labelledby="home-uses">',
        '<div class="wrap">',
        f'<div class="band-head"><h2 class="band-title" id="home-uses">{text(uses["heading"])}</h2>'
        f'<p>{text(uses["lead"])}</p></div>',
        f'<ul class="home-use-cards">{use_cards}</ul>',
        f'<p class="home-uses-all"><a href="use-cases/">{text(uses["all"])}</a></p>',
        "</div>",
        "</section>",
        "</main>",
    ]))
    return page_shell(home["title"], home["description"], main, body_class="home")


def page_head(heading: str, lead: str = "", crumb: tuple[str, str] | None = None, dateline: str = "") -> str:
    parts = ['<div class="wrap page-head">']
    if crumb:
        parts.append(f'<p class="crumbs"><a href="{crumb[0]}">{text(crumb[1])}</a></p>')
    parts.append(f"<h1>{text(heading)}</h1>")
    if lead:
        parts.append(f'<p class="lead">{text(lead)}</p>')
    if dateline:
        parts.append(f'<p class="dateline">{text(dateline)}</p>')
    parts.append("</div>")
    return "\n".join(parts)


def render_decks_index(nouns: Nouns) -> str:
    page, ui = nouns.decks_page, nouns.site["deck"]
    cards = "\n".join(deck_card(deck, "../", ui, 2) for deck in nouns.decks)
    main = "\n".join([
        '<main id="main">',
        page_head(page["heading"], page["lead"]),
        '<div class="wrap deck-index">',
        f'<ul class="deck-cards">\n{cards}\n</ul>',
        # Review, October 31: the October 29 drafts are kept in git but no longer served, so nothing links them.
        "</div>",
        "</main>",
    ])
    return page_shell(page["title"], page["description"], main)


def draft_item(item: dict, prefix: str, level: int) -> str:
    return (f'<li class="draft"><h{level} class="draft-title"><a href="{prefix}{attr(item["href"])}">'
            f'{text(item["title"])}</a></h{level}><p>{text(item["about"])}</p></li>')


def render_earlier(nouns: Nouns) -> str:
    page = nouns.drafts
    prefix = "../../"
    versions = {v["version"]: v for v in nouns.manifest["versions"]}
    info = page["deck_versions"]
    decks = []
    for item in info["items"]:
        version = versions[item["version"]]
        links = []
        for download in version["downloads"]:
            target = prefix + download["path"] if "path" in download else download["url"]
            links.append(f'<a href="{attr(target)}">{text(info["formats"][download["format"]])}</a>')
        links += [f'<a href="{prefix}{attr(extra["href"])}">{text(extra["label"])}</a>' for extra in item.get("extra", [])]
        decks.append(f'<li class="draft"><h3 class="draft-title"><a href="{prefix}{attr(version["path"])}">'
                     f'{text(item["title"])}</a></h3>'
                     f'<p class="item-meta">{version["slides"]} {text(info["slides"])}</p>'
                     f'<p>{text(item["about"])}</p>'
                     f'<p class="draft-links">{" · ".join(links)}</p></li>')
    groups = [f'<section class="draft-group" aria-labelledby="drafts-decks"><h2 id="drafts-decks">'
              f'{text(info["heading"])}</h2><ul class="draft-list">{"".join(decks)}</ul></section>']
    for group in page["groups"]:
        items = "".join(draft_item(item, prefix, 3) for item in group["items"])
        groups.append(f'<section class="draft-group" aria-labelledby="drafts-{group["id"]}"><h2 id="drafts-{group["id"]}">'
                      f'{text(group["heading"])}</h2><ul class="draft-list">{items}</ul></section>')
    notes = "".join(f'<p>{text(note["text"])} <a href="{prefix}{attr(note["href"])}">{text(note["label"])}</a></p>'
                    if not note["href"].startswith("https://") else
                    f'<p>{text(note["text"])} <a href="{attr(note["href"])}">{text(note["label"])}</a></p>'
                    for note in page["notes"])
    main = "\n".join([
        '<main id="main">',
        page_head(page["heading"], page["lead"], ("../", page["crumb"]), page["dateline"]),
        '<div class="wrap drafts">',
        "\n".join(groups),
        f'<div class="drafts-notes">{notes}</div>',
        "</div>",
        "</main>",
    ])
    return page_shell(page["title"], page["description"], main)


def film_board(board: dict | None) -> str:
    """The storyboard image, linked to its full size, when the film noun has one."""
    if not board:
        return ""
    if not (SITE / board["src"]).is_file():
        fail(f"film.json: the storyboard is missing: {board['src']}")
    src = attr("../" + board["src"])
    return (f'<figure class="film-board"><a href="{src}"><img src="{src}" alt="{attr(board["alt"])}" '
            f'width="{board["width"]}" height="{board["height"]}" loading="lazy" decoding="async"></a>'
            f'<figcaption>{text(board["caption"])} <a href="{src}">{text(board["link"])}</a></figcaption></figure>')


def render_film(nouns: Nouns) -> str:
    """The full film's transcript and scene descriptions: its acts, and every narration line, word for word as its
    captions give it, with its time and what is on screen. It is the film's text alternative, and says so, along with
    the note that there is no separate audio-described cut yet."""
    film = nouns.film
    sections = []
    for act in film["acts"]:
        rows = "".join(
            f'<li class="film-line"><p class="film-at">{text(line["at"])}</p>'
            f'<div><p class="film-words"><span class="visually-hidden">{text(film["words_label"])}: </span>'
            f'{text(line["words"])}</p>'
            + (f'<p class="film-picture"><span class="film-picture-label">{text(film["picture_label"])}</span> '
               f'{text(line["picture"])}</p>' if line["picture"] else "")
            + '</div></li>'
            for line in film["lines"] if line["act"] == act["id"])
        sections.append(f'<section class="film-act" aria-labelledby="act-{act["id"]}">'
                        f'<h2 id="act-{act["id"]}"><span class="film-act-time">{text(act["from"])}–{text(act["to"])}</span> '
                        f'{text(act["name"])}</h2><ol class="film-lines">{rows}</ol></section>')
    main = "\n".join([
        '<main id="main">',
        page_head(film["heading"], film["lead"], ("../", film["crumb"]), film["audio_description"]),
        '<div class="wrap film-outline">',
        film_board(film.get("storyboard")),
        "\n".join(sections),
        f'<p class="film-note">{text(film["note"])}'
        + (f' <a href="{attr(film["evidence"]["href"])}">{text(film["evidence"]["label"])}</a>' if film.get("evidence") else "")
        + "</p>",
        "</div>",
        "</main>",
    ])
    return page_shell(film["title"], film["description"], main)


def render_storyboards(nouns: Nouns) -> str:
    page = nouns.drafts["storyboards_page"]
    prefix = "../"
    groups = {group["id"]: group for group in nouns.drafts["groups"]}
    sections = []
    for key in page["groups"]:
        group = groups[key]
        items = "".join(draft_item(item, prefix, 3) for item in group["items"])
        sections.append(f'<section class="draft-group" aria-labelledby="boards-{key}"><h2 id="boards-{key}">'
                        f'{text(group["heading"])}</h2><ul class="draft-list">{items}</ul></section>')
    main = "\n".join([
        '<main id="main">',
        page_head(page["heading"], page["lead"], ("../decks/earlier-drafts/", page["crumb"])),
        '<div class="wrap drafts">',
        "\n".join(sections),
        "</div>",
        "</main>",
    ])
    return page_shell(page["title"], page["description"], main)


def chips(items: list[str], kind: str) -> str:
    return f'<ul class="chips {kind}">' + "".join(f"<li>{text(item)}</li>" for item in items) + "</ul>"


def pack_links(ids: list[str], library: dict, prefix: str, what: str) -> str:
    """A use case's library packs by title, each linking to its card on the library page. The titles come from the
    library noun, so a use case names its packs by id only."""
    packs = {pack["id"]: pack for pack in library["packs"]}
    low, high = USE_PACKS
    if not isinstance(ids, list) or not low <= len(ids) <= high or len(set(ids)) != len(ids):
        fail(f"use-cases.json: {what} names {low} to {high} different library packs")
    unknown = [pack_id for pack_id in ids if pack_id not in packs]
    if unknown:
        fail(f"use-cases.json: {what} names packs the library does not have: {', '.join(unknown)}")
    return ('<ul class="chips pack">' + "".join(f'<li><a href="{prefix}library/#{attr(pack_id)}">'
                                                f'{text(packs[pack_id]["title"])}</a></li>' for pack_id in ids) + "</ul>")


def use_terms(item: dict, uses: dict, library: dict, prefix: str) -> str:
    return ('<dl class="use-terms">'
            f'<div><dt class="noun-word">{text(uses["nouns_label"])}</dt><dd>{chips(item["nouns"], "noun")}</dd></div>'
            f'<div><dt class="verb-word">{text(uses["verbs_label"])}</dt><dd>{chips(item["verbs"], "verb")}</dd></div>'
            f'<div><dt class="pack-word">{text(uses["packs_label"])}</dt>'
            f'<dd>{pack_links(item["packs"], library, prefix, item["name"])}</dd></div>'
            "</dl>")


def use_href(href: str, prefix: str) -> str:
    """A link on the use cases page: an outside address as it is, a page of this site from the page's folder."""
    return attr(href) if href.startswith("https://") else prefix + attr(href)


def use_link(link: dict, prefix: str) -> str:
    return f'<a class="use-link" href="{use_href(link["href"], prefix)}">{text(link["label"])}{CHEVRON}</a>'


def flagship_card(item: dict, uses: dict, library: dict, prefix: str, lead: bool) -> str:
    """One flagship idea: its name, a line or two, example nouns and verbs, the library packs that hold them, and
    where to read more. The first one leads, with buttons. An idea has no status and no evidence."""
    rest = f' <span class="use-name-rest">{text(item["rest"])}</span>' if item.get("rest") else ""
    if lead:
        links = "".join(f'<a class="button{" secondary" if n else ""}" href="{use_href(link["href"], prefix)}">'
                        f'{text(link["label"])}</a>' for n, link in enumerate(item["links"]))
    else:
        links = "".join(use_link(link, prefix) for link in item["links"])
    detail = f'<p class="use-detail">{text(item["detail"])}</p>' if item.get("detail") else ""
    return "\n".join([
        f'<li class="use-card{" use-lead" if lead else ""}" id="{use_anchor(item["name"])}">',
        '<div class="use-head">',
        f"<h2>{text(item['name'])}{rest}</h2>",
        f'<div class="use-text"><p class="use-line">{text(item["line"])}</p>{detail}</div>',
        "</div>",
        use_terms(item, uses, library, prefix),
        f'<p class="use-links">{links}</p>',
        "</li>",
    ])


def render_use_cases(nouns: Nouns) -> str:
    uses = nouns.uses
    prefix = "../"
    cards = [flagship_card(item, uses, nouns.library, prefix, lead=n == 0) for n, item in enumerate(uses["flagships"])]
    fields = uses["fields"]
    main = "\n".join([
        '<main id="main">',
        page_head(uses["heading"], uses["lead"]),
        '<div class="wrap use-wrap">',
        '<ul class="use-grid">',
        "\n".join(cards),
        "</ul>",
        '<section class="use-fields" aria-labelledby="use-fields-title">',
        '<div class="use-head">',
        f'<h2 id="use-fields-title">{text(fields["name"])}</h2>',
        f'<p class="use-line">{text(fields["line"])}</p>',
        "</div>",
        chips(fields["items"], "plain"),
        f'<p class="use-links">{use_link(fields["link"], prefix)}</p>',
        "</section>",
        "</div>",
        "</main>",
    ])
    return page_shell(uses["title"], uses["description"], main)


def learn_part(key: str, heading: str, lead: str, body: str) -> str:
    """One section of the learning page: its heading, an optional lead, then its body."""
    intro = f"<p>{text(lead)}</p>" if lead else ""
    return (f'<section class="learn-part" aria-labelledby="{key}"><div class="learn-head"><h2 id="{key}">'
            f"{text(heading)}</h2>{intro}</div>{body}</section>")


def render_learning(nouns: Nouns) -> str:
    """The learning page: what continuous learning means here, the loop, the measured results with their evidence,
    the safety rules, the limits and how to run it. A page of Agora, not a surface of its own. Every word comes from
    site/content/learning.json, and every measured result links to public evidence. The loop's step numbers are a
    CSS counter, so the ordered list carries them."""
    page = nouns.learning
    prefix = "../"
    meaning, loop, results, run = page["meaning"], page["loop"], page["results"], page["run"]
    for item in results["items"]:
        if not item.get("link", "").startswith("https://github.com/ta-amps/"):
            fail(f"learning.json: the {item['model']} result needs a public evidence link")
    means = "".join(
        f'<li class="learn-mean {attr(item["kind"])}"><p class="learn-kind">{text(meaning["kinds"][item["kind"]])}</p>'
        f'<h3>{text(item["name"])}</h3><p class="learn-text">{text(item["text"])}</p></li>' for item in meaning["items"])
    steps = "".join(
        f'<li class="loop-step"><h3 class="loop-verb">{text(step["verb"])}</h3>'
        f'<p class="loop-noun"><span class="visually-hidden">{text(loop["leaves"])} </span>{text(step["noun"])}</p>'
        f'<p class="loop-text">{text(step["text"])}</p>{arrow("loop-arrow")}</li>' for step in loop["steps"])
    cards = "".join(
        f'<li class="result"><p class="result-model">{text(item["model"])}</p>'
        f'<p class="result-figure"><span class="result-before">{text(item["before"])}</span>'
        f'<span class="visually-hidden"> {text(results["to"])} </span>{arrow("result-arrow")}'
        f'<span class="result-after">{text(item["after"])}</span></p>'
        f'<p class="result-line">{text(item["line"])}</p>'
        f'<p class="result-evidence"><span>{text(results["evidence"])}</span> '
        f'<a href="{attr(item["link"])}">{text(item["source"])}</a></p></li>' for item in results["items"])
    rules = "".join(f"<li><h3>{text(rule['name'])}</h3><p>{text(rule['text'])}</p></li>" for rule in page["safety"]["items"])
    limits = "".join(f"<li>{text(limit)}</li>" for limit in page["limits"]["items"])
    main = "\n".join([
        '<main id="main">',
        '<div class="wrap page-head">',
        f"<h1>{text(page['heading'])}</h1>",
        f'<p class="lead">{text(page["lead"])}</p>',
        f'<p class="dateline">{text(page["dateline"])}</p>',
        f'<p class="learn-actions"><a class="button secondary" href="{use_href(page["deck"]["href"], prefix)}">'
        f'{text(page["deck"]["label"])}</a></p>',
        "</div>",
        '<div class="wrap learn">',
        learn_part("meaning", meaning["heading"], "",
                   f'<ol class="learn-means">{means}</ol><p class="learn-note">{text(meaning["note"])}</p>'),
        learn_part("loop", loop["heading"], loop["lead"],
                   f'<ol class="loop">{steps}</ol><p class="loop-back">{text(loop["back"])}</p>'),
        learn_part("results", results["heading"], results["lead"], f'<ul class="results">{cards}</ul>'),
        learn_part("safety", page["safety"]["heading"], page["safety"]["lead"], f'<ul class="safety">{rules}</ul>'),
        learn_part("limits", page["limits"]["heading"], "", f'<ul class="learn-limits">{limits}</ul>'),
        '<section class="learn-run" aria-labelledby="run">',
        '<div class="learn-run-text">',
        f'<h2 id="run">{text(run["heading"])}</h2>',
        f'<p>{text(run["text"])}</p>',
        f'<p>{text(run["pack"])}</p>',
        "</div>",
        f'<p class="use-links">{"".join(use_link(item, prefix) for item in run["links"])}</p>',
        "</section>",
        "</div>",
        "</main>",
    ])
    return page_shell(page["title"], page["description"], main)


def human_date(iso: str) -> str:
    when = dt.datetime.fromisoformat(iso)
    return f"{when:%B} {when.day}, {when.year}"


def counted(n: int, one: str, many: str, cls: str = "") -> str:
    """A count and its word. The number sits in its own element, so every word on the page is the noun's."""
    klass = f' class="{cls}"' if cls else ""
    return f'<span{klass}><span class="lib-n">{n:,}</span> {text(one if n == 1 else many)}</span>'


def pack_card(pack: dict, words: dict) -> str:
    """One pack: its status, its title linking to its folder at the pinned commit, its one-line purpose, its noun and
    verb counts, and a badge when it ships its own code and tests. The whole card is the title's link."""
    kinds = [words["status"][pack["status"]]] + ([words["kit"]] if pack["kit"] else [])
    badge = f'<span class="lib-badge">{CODE_GLYPH}{text(words["badge"])}</span>' if pack["code"] else ""
    return "\n".join([
        f'<li class="lib-card" id="{pack["id"]}">',
        '<p class="lib-card-meta"><span class="lib-card-kind">'
        + " ".join(f"<span>{text(kind)}</span>" for kind in kinds) + f"</span> {badge}</p>",
        f'<h3 class="lib-card-title"><a class="lib-card-link" href="{attr(pack["url"])}" '
        f'aria-label="{attr(pack["title"] + " " + words["on_github"])}">{text(pack["title"])}</a></h3>',
        f'<p class="lib-card-purpose">{text(pack["purpose"])}</p>',
        '<p class="lib-card-foot"><span class="lib-card-counts">'
        + counted(pack["nouns"], words["noun"], words["nouns"], "noun-word") + " "
        + counted(pack["verbs"], words["verb"], words["verbs"], "verb-word")
        + f'</span> <span class="lib-card-cta" aria-hidden="true">{text(words["github"])}{CHEVRON}</span></p>',
        "</li>",
    ])


def explorer_section(explorer: dict, ecosystem: dict, library: dict) -> str:
    ctrl = explorer["controls"]
    kind_opts = "".join(
        f'<option value="{attr(k["id"])}" data-scope="library">{text(k["label"])}</option>'
        for k in explorer["kinds"]
    ) + "".join(
        f'<option value="{attr(k["id"])}" data-scope="ecosystem" hidden>{text(k["label"])}</option>'
        for k in explorer["eco_kinds"]
    )
    cat_opts = f'<option value="all">{text(ctrl["all_categories"])}</option>' + "".join(
        f'<option value="{attr(cat["id"])}" data-scope="library">{text(cat["short"])}</option>'
        for cat in library["categories"]
    ) + "".join(
        f'<option value="{attr(ecat["id"])}" data-scope="ecosystem" hidden>{text(ecat["label"])}</option>'
        for ecat in ecosystem["categories"]
    )
    ceil_opts = "".join(f'<option value="{attr(c["id"])}">{text(c["label"])}</option>' for c in explorer["ceilings"])
    harn_opts = "".join(f'<option value="{attr(h["id"])}">{text(h["label"])}</option>' for h in explorer["harnesses"])
    return "\n".join([
        '<section class="exp-shell" id="explorer" aria-labelledby="explorer-heading">',
        '<div class="exp-head">',
        f'<h2 id="explorer-heading">{text(explorer["heading"])}</h2>',
        f'<p class="exp-lead">{text(explorer["lead"])}</p>',
        f'<p class="exp-note">{text(explorer["proposal_note"])}</p>',
        "</div>",
        f'<div class="exp-tabs" role="tablist" aria-label="{attr(explorer["tabs_label"])}">',
        '<button class="exp-tab" type="button" role="tab" id="tab-library" aria-selected="true" data-exp-tab="library">'
        f'<span>{text(explorer["tabs"]["library"])}</span> <span class="exp-tab-n">{explorer["counts"]["total"]:,}</span></button>',
        '<button class="exp-tab" type="button" role="tab" id="tab-ecosystem" aria-selected="false" data-exp-tab="ecosystem">'
        f'<span>{text(explorer["tabs"]["ecosystem"])}</span> <span class="exp-tab-n">{ecosystem["project_count"]:,}</span></button>',
        "</div>",
        '<div class="exp-controls" data-exp-controls hidden>',
        '<label class="exp-field exp-field-wide" for="exp-query">'
        f'<span>{text(ctrl["search_label"])}</span>'
        f'<input id="exp-query" type="search" placeholder="{attr(ctrl["search_placeholder"])}" autocomplete="off" data-exp-query>'
        "</label>",
        f'<label class="exp-field" for="exp-kind"><span>{text(ctrl["kind_label"])}</span>'
        f'<select id="exp-kind" data-exp-kind>{kind_opts}</select></label>',
        f'<label class="exp-field" for="exp-category"><span>{text(ctrl["category_label"])}</span>'
        f'<select id="exp-category" data-exp-category>{cat_opts}</select></label>',
        f'<label class="exp-field" for="exp-ceiling"><span>{text(ctrl["ceiling_label"])}</span>'
        f'<select id="exp-ceiling" data-exp-ceiling>{ceil_opts}</select></label>',
        f'<label class="exp-field" for="exp-harness"><span>{text(ctrl["harness_label"])}</span>'
        f'<select id="exp-harness" data-exp-harness>{harn_opts}</select></label>',
        f'<button class="button secondary exp-reset" type="button" data-exp-reset>{text(ctrl["reset"])}</button>',
        "</div>",
        '<p class="exp-status" id="exp-status" role="status" aria-live="polite" data-exp-status></p>',
        f'<p class="exp-noscript" data-no-script>{text(ctrl["noscript"])}</p>',
        '<ul class="exp-results" data-exp-results></ul>',
        f'<div class="exp-more-wrap"><button class="button secondary" type="button" data-exp-more hidden>{text(ctrl["show_more"])}</button></div>',
        "</section>",
    ])


def harness_feeds_section(explorer: dict) -> str:
    hf = explorer["harness_feeds"]
    cards = "".join(
        '<li class="harness-card">'
        f'<h3>{text(item["name"])}</h3>'
        f'<p class="harness-role">{text(item["role"])}</p>'
        f'<p class="harness-detail">{text(item["detail"])}</p>'
        "</li>"
        for item in hf["harnesses"]
    )
    rules = "".join(
        '<li class="routing-item">'
        f'<p class="routing-mode">{text(rule["mode"])}</p>'
        f'<p class="routing-when">{text(rule["when"])}</p>'
        f'<p class="routing-outcome">{text(rule["outcome"])}</p>'
        "</li>"
        for rule in hf["routing"]["rules"]
    )
    return "\n".join([
        '<section class="harness-panel" id="harness-feeds" aria-labelledby="harness-feeds-heading">',
        '<div class="harness-head">',
        f'<p class="exp-kicker">{text(hf["kicker"])}</p>',
        f'<h2 id="harness-feeds-heading">{text(hf["heading"])}</h2>',
        f'<p class="exp-lead">{text(hf["lead"])}</p>',
        f'<p class="exp-note">{text(hf["status_note"])}</p>',
        "</div>",
        f'<ul class="harness-grid">{cards}</ul>',
        '<div class="harness-routing">',
        f'<h3 id="harness-routing-heading">{text(hf["routing"]["heading"])}</h3>',
        f'<p class="harness-routing-lead">{text(hf["routing"]["lead"])}</p>',
        f'<ol class="routing-list">{rules}</ol>',
        "</div>",
        "</section>",
    ])


def ecosystem_banner_section(explorer: dict, ecosystem: dict) -> str:
    call = explorer["ecosystem_callout"]
    return "\n".join([
        '<section class="eco-banner" id="ecosystem-explorer" aria-labelledby="ecosystem-heading">',
        '<div class="eco-banner-text">',
        f'<p class="exp-kicker">{text(call["kicker"])}</p>',
        f'<h2 id="ecosystem-heading">{text(call["heading"])}</h2>',
        f'<p>{text(call["summary"])}</p>',
        f'<p class="eco-honesty">{text(ecosystem["honesty_note"])}</p>',
        "</div>",
        '<div class="eco-banner-actions">',
        f'<button class="button" type="button" data-open-ecosystem hidden>{text(call["button"])}</button>',
        f'<a class="use-link" href="{attr(call["evidence_href"])}">{text(call["evidence_label"])}{CHEVRON}</a>',
        "</div>",
        "</section>",
    ])


def explorer_payload_script(explorer: dict, ecosystem: dict) -> str:
    payload = {
        "labels": explorer["labels"],
        "harnesses": {h["id"]: h["label"] for h in explorer["harnesses"] if h["id"] != "all"},
        "ceilings": {c["id"]: c["label"] for c in explorer["ceilings"] if c["id"] != "all"},
        "items": explorer["items"],
        "projects": ecosystem["projects"],
    }
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    return f'<script type="application/json" id="agora-explorer-data">{encoded}</script>'


def render_library(nouns: Nouns) -> str:
    """The library page: every seed pack at one pinned commit of the library, grouped by category, under the totals
    measured at that commit, plus the interactive Task & Task-Object Explorer, Agent Harness Research Feeds, and the
    Meta Hackathon 2026 Ecosystem Explorer. Every word comes from library.json, explorer.json, and
    ecosystem-catalog.json. A category link shows only that category through :target without needing a script."""
    library, explorer, ecosystem = nouns.library, nouns.explorer, nouns.ecosystem
    words, source, totals = library["words"], library["source"], library["totals"]
    packs = {pack["id"]: pack for pack in library["packs"]}
    commit = source["commit"]
    stats = "".join(
        f'<li class="lib-stat{" " + kind if kind else ""}"><span class="lib-stat-n">{totals[key]:,}</span> '
        f'<span class="lib-stat-label">{text(words["stats"][key])}</span></li>'
        for key, kind in (("packs", ""), ("nouns", "noun"), ("verbs", "verb"), ("worked_examples", ""),
                          ("with_code", "")))
    filters = [f'<li><a href="#categories">{text(words["all"])} <span class="lib-filter-n">{totals["packs"]:,}</span>'
               "</a></li>"]
    filters += [f'<li><a href="#{category["id"]}">{text(category["short"])} '
                f'<span class="lib-filter-n">{len(category["packs"]):,}</span></a></li>'
                for category in library["categories"]]
    groups = []
    for category in library["categories"]:
        key = category["id"]
        cards = "\n".join(pack_card(packs[pack_id], words) for pack_id in category["packs"])
        groups.append("\n".join([
            f'<section class="lib-group" id="{key}" aria-labelledby="{key}-title">',
            '<div class="lib-group-body">',
            '<div class="lib-group-head">',
            f'<h2 id="{key}-title">{text(category["name"])} <span class="lib-group-count">'
            f'{counted(len(category["packs"]), words["pack"], words["packs"])}</span></h2>',
            f'<p class="lib-group-intro">{text(category["intro"])}</p>',
            f'<a class="lib-show-all" href="#categories">{text(words["show_all"])}</a>',
            "</div>",
            f'<ul class="lib-cards">\n{cards}\n</ul>',
            (f'<a class="lib-see-all" href="#{key}">{text(words["see_all"])} '
             f'{counted(len(category["packs"]), words["pack"], words["packs"])}</a>'
             if len(category["packs"]) > LIBRARY_FIRST else ""),
            "</div>",
            "</section>",
        ]))
    on_show = ",".join(f'.library:has(#{category["id"]}:target) .lib-filter a[href="#{category["id"]}"]'
                       for category in library["categories"])
    tree = f"{LIBRARY_REPOSITORY}/tree/{commit}"
    receipt = f"{LIBRARY_REPOSITORY}/blob/{commit}/packs/VALIDATION.json"
    jump_links = "".join(use_link(item, "") for item in explorer["jump_links"])
    ext_links = "".join(use_link(item, "../") for item in words["links"])
    main = "\n".join([
        '<main id="main">',
        page_head(library["heading"], library["lead"], dateline=library["dateline"]),
        '<div class="wrap library">',
        '<section class="lib-summary" aria-labelledby="library-numbers">',
        f'<h2 class="visually-hidden" id="library-numbers">{text(words["numbers_label"])}</h2>',
        f'<ul class="lib-stats">{stats}</ul>',
        '<div class="lib-about">',
        f'<p class="lib-source">{text(words["counted"])} <a href="{attr(tree)}"><code>{commit[:7]}</code></a> · '
        f'<time datetime="{attr(source["committed_at"])}">{human_date(source["committed_at"])}</time></p>',
        f'<p class="lib-source">{text(words["checked"])} <a href="{attr(receipt)}">{text(words["receipt"])}</a></p>',
        f'<p class="lib-legend"><span class="lib-badge">{CODE_GLYPH}{text(words["badge"])}</span> '
        f'<span>{text(words["badge_note"])}</span></p>',
        "</div>",
        f'<p class="use-links">{jump_links}{ext_links}</p>',
        "</section>",
        explorer_section(explorer, ecosystem, library),
        harness_feeds_section(explorer),
        ecosystem_banner_section(explorer, ecosystem),
        '<div class="lib-groups">',
        f'<nav class="lib-filter" id="categories" aria-label="{attr(words["filter_label"])}"><ul>{"".join(filters)}'
        "</ul></nav>",
        "\n".join(groups),
        "</div>",
        "</div>",
        "</main>",
    ])
    return page_shell(library["title"], library["description"], main,
                      extra_head=f"<style>{on_show}{{--on:1}}</style>",
                      extra_body=explorer_payload_script(explorer, ecosystem))


def deploy_code_block(code_id: str, commands: str, copy_labels: dict) -> str:
    return "\n".join([
        '<div class="deploy-code-wrap">',
        '<div class="deploy-code-bar">',
        f'<button class="agent-copy deploy-copy" type="button" data-copy="{attr(code_id)}" '
        f'data-copied="{attr(copy_labels["copied"])}" data-selected="{attr(copy_labels["selected"])}" '
        f'data-status-copied="{attr(copy_labels["status_copied"])}" '
        f'data-status-selected="{attr(copy_labels["status_selected"])}" hidden>'
        f'{COPY_ICON}<span>{text(copy_labels["copy"])}</span></button>',
        f'<span class="visually-hidden" id="{attr(code_id)}-status" role="status"></span>',
        "</div>",
        f'<pre class="deploy-pre" id="{attr(code_id)}" tabindex="0"><code>{text(commands)}</code></pre>',
        "</div>",
    ])


def render_deploy(nouns: Nouns) -> str:
    page = nouns.deploy
    prefix = prefix_for(SITE / "deploy" / "index.html")
    copy_labels = page["copy_labels"]
    quick = "".join(use_link(item, prefix) for item in page["quick_links"])
    slices = "".join(
        f'<li class="deploy-card" id="{attr(item["id"])}">'
        f'<p class="deploy-badge">{text(item["badge"])}</p>'
        f'<h3>{text(item["title"])}</h3>'
        f'<p class="deploy-summary">{text(item["summary"])}</p>'
        f'<p class="deploy-when">{text(item["when"])}</p>'
        + deploy_code_block(item["code_id"], item["commands"], copy_labels)
        + "</li>"
        for item in page["slices"]["items"]
    )
    surfaces = "".join(
        '<li class="deploy-card">'
        f'<h3>{text(item["title"])}</h3>'
        f'<p class="deploy-summary">{text(item["detail"])}</p>'
        + deploy_code_block(item["code_id"], item["commands"], copy_labels)
        + "</li>"
        for item in page["surfaces"]["items"]
    )
    rules = "".join(
        f'<li><h3>{text(rule["name"])}</h3><p>{text(rule["text"])}</p></li>'
        for rule in page["security"]["items"]
    )
    verify = page["verify"]
    main = "\n".join([
        '<main id="main">',
        '<div class="wrap page-head">',
        f'<h1>{text(page["heading"])}</h1>',
        f'<p class="lead">{text(page["lead"])}</p>',
        f'<p class="dateline">{text(page["dateline"])}</p>',
        f'<p class="use-links">{quick}</p>',
        "</div>",
        '<div class="wrap learn deploy-page">',
        learn_part("slices", page["slices"]["heading"], page["slices"]["lead"], f'<ul class="deploy-grid">{slices}</ul>'),
        learn_part("surfaces", page["surfaces"]["heading"], page["surfaces"]["lead"], f'<ul class="deploy-grid">{surfaces}</ul>'),
        learn_part("security", page["security"]["heading"], page["security"]["lead"], f'<ul class="safety">{rules}</ul>'),
        learn_part("verify", verify["heading"], verify["text"],
                   deploy_code_block(verify["code_id"], verify["commands"], copy_labels)),
        "</div>",
        "</main>",
    ])
    return page_shell(page["title"], page["description"], main)


def live_doors(section: dict) -> list[dict]:
    """The doors of a section that a recorded live check showed answering. The build refuses a door without one."""
    doors = section.get("doors", [])
    for door in doors:
        check = door.get("check") or {}
        if not (200 <= int(check.get("status", 0)) < 300 and re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ",
                                                                            check.get("checked_utc", ""))):
            fail(f"contribute: the door {door.get('endpoint')} has no passing live check")
        if not door["endpoint"].startswith("https://"):
            fail(f"contribute: the door {door['endpoint']} is not an https address")
    return doors


def render_models(nouns: Nouns) -> str:
    """The models page (owner, Nov 1: "a page Models used that explains how we use each model and emphasize on the
    meta models with a * for fallback to other models"). Everything it names comes from the models catalog Task
    Object; site/content/models-page.json holds only its words. Display rules: Meta's models first and emphasized,
    agent programs never called models, an asterisk on other makers, and only uses that are live or measured."""
    page, catalog, prefix = nouns.models_page, nouns.catalog, "../"
    shown = ("live", "measured")

    def uses_of(entry: dict) -> str:
        items = []
        for use in entry.get("uses", []):
            if use.get("state") not in shown:
                continue
            record = page["records"].get(use.get("evidence", ""))
            if use.get("evidence") and use["state"] == "measured" and not record:
                fail(f"models page: no served record for {use['evidence']}")
            link_ = f' <a class="models-record" href="{link(prefix, record)}">{text(page["record"])}</a>' if record else ""
            items.append(f'<li><span class="models-state models-{attr(use["state"])}">{text(page["states"][use["state"]])}</span> '
                         f"{text(use['text'])}.{link_}</li>")
        return f'<ul class="models-uses" aria-label="{attr(page["uses"])}">{"".join(items)}</ul>' if items else ""

    def card(entry: dict, kind: str) -> str:
        name = entry.get("display_tuned") if kind == "meta" and entry.get("display_tuned") else entry["display"]
        star = '<span class="models-star" aria-hidden="true">*</span>' if entry.get("asterisk") else ""
        facts = [(page["maker"], entry.get("maker", ""))]
        if entry.get("access"):
            facts.append((page["access"], entry["access"]))
        dl = "".join(f"<dt>{text(k)}</dt><dd>{text(v)}</dd>" for k, v in facts if v)
        summary = f'<p class="models-summary">{text(entry["summary"])}</p>' if entry.get("summary") else ""
        return (f'<li class="models-card models-{kind}"><h3>{text(name)}{star}</h3>{summary}'
                f'<dl class="models-facts">{dl}</dl>{uses_of(entry)}</li>')

    meta = [m for m in catalog["models"] if m.get("maker") == "Meta"]
    others = [m for m in catalog["models"] if m.get("maker") != "Meta"] + catalog["other_makers"]
    for entry in others:
        if not entry.get("asterisk"):
            fail(f"models page: {entry['id']} is not Meta's and has no asterisk")
    main = "\n".join([
        '<main id="main">',
        page_head(page["heading"], page["lead"]),
        '<div class="wrap models-page">',
        learn_part("models-meta", page["meta_heading"], page["meta_lead"],
                   '<ul class="models-list models-list-meta">' + "".join(card(m, "meta") for m in meta) + "</ul>"),
        learn_part("models-programs", page["harness_heading"], page["harness_lead"],
                   '<ul class="models-list">' + "".join(card(h, "program") for h in catalog["harnesses"]) + "</ul>"),
        learn_part("models-other", page["other_heading"], page["other_lead"],
                   '<ul class="models-list">' + "".join(card(o, "other") for o in others) + "</ul>"
                   + f'<p class="models-footnote">{text(page["footnote"])}</p>'),
        "</div>",
        "</main>",
    ])
    return page_shell(page["title"], page["description"], main)


def render_contribute(nouns: Nouns) -> str:
    """The contribute page: the ways in that work today, each door with the live check that showed it answering.
    A section with nothing that works yet is left out rather than promised."""
    page = nouns.contribute
    prefix = prefix_for(SITE / "contribute" / "index.html")
    labels = page["copy_labels"]
    parts = []
    for section in page["sections"]:
        doors = live_doors(section)
        body = []
        if section.get("steps"):
            body.append('<ol class="contribute-steps">' + "".join(f"<li>{text(step)}</li>" for step in section["steps"]) + "</ol>")
        if section.get("code"):
            body.append(deploy_code_block(section["code_id"], section["code"], labels))
        if section.get("repos"):
            commands = "\n".join(section["clone_prefix"] + repo + ".git" for repo in section["repos"])
            body.append(deploy_code_block(section["code_id"], commands, labels))
            body.append(f'<p class="contribute-source"><a href="{link(prefix, section["source_href"])}">'
                        f'{text(section["source_label"])}</a></p>')
        if doors:
            rows = "".join(
                f'<li class="door"><span class="door-name">{text(door["name"])}</span>'
                f'<code class="door-endpoint">{text(door["endpoint"])}</code>'
                f'<span class="door-what">{text(door["what"])}</span>'
                f'<span class="door-check">{text(page["checked_label"])} {text(door["check"]["checked_utc"])}: '
                f'{text(door["check"]["method"])} {text(door["check"]["kind"])}, HTTP {int(door["check"]["status"])}</span></li>'
                for door in doors)
            body.append(f'<ul class="doors">{rows}</ul>')
        if section.get("note"):
            body.append(f'<p class="contribute-note">{text(section["note"])}</p>')
        if not body:
            continue  # nothing in this section works yet, so the page does not show it
        parts.append(learn_part(section["id"], section["heading"], section["lead"], "\n".join(body)))
    main = "\n".join([
        '<main id="main">',
        '<div class="wrap page-head">',
        f'<h1>{text(page["heading"])}</h1>',
        f'<p class="lead">{text(page["lead"])}</p>',
        f'<p class="dateline">{text(page["dateline"])}</p>',
        "</div>",
        '<div class="wrap learn contribute-page">',
        *parts,
        "</div>",
        "</main>",
    ])
    return page_shell(page["title"], page["description"], main)


def render_llms(nouns: Nouns, built: set[Path]) -> str:
    """Agora's llms.txt, from its noun, the endpoints noun and the pages that exist. The build refuses a page
    the site does not have."""
    page = nouns.llms
    origin = page["origin"].rstrip("/") + "/"
    lines = [f"# {page['title']}", "", f"> {page['summary']}", "", f"## {page['do_title']}", ""]
    lines += [f"- {item}" for item in page["do"]]
    lines += ["", f"## {page['pages_title']}", ""]
    for item in page["pages"]:
        target = SITE / item["path"] / "index.html"
        if target not in built and not target.is_file():
            fail(f"llms.txt names a page the site does not have: /{item['path']}")
        lines.append(f"- [{item['label']}]({origin}{item['path']}): {item['what']}")
    lines += ["", f"## {page['endpoints_title']}", ""]
    for row in nouns.site["endpoints"]["rows"]:
        lines.append(f"- {row['name']}: {row['what']}. MCP {row['mcp']}; llms.txt {row['llms']}")
    lines += ["", f"## {page['source_title']}", ""] + [f"- {item}" for item in page["source"]]
    lines += ["", f"## {page['rules_title']}", ""] + [f"- {item}" for item in page["rules"]]
    lines += ["", f"## {page['brief_title']}", "", page["brief_note"], ""]
    return "\n".join(lines)


FEED_TOP_ITEMS = 40  # memory systems listed under Everything gathered, most stars first


def feed_hosted(feed: dict) -> bool:
    """The feed's scans ran on hosted Tessera, so its schedule is real and the decks may say so."""
    return feed["source"].get("hosted") is True


def short_hash(value: str) -> str:
    return f'<code title="{attr(value)}">{text(value[:12])}</code>'


def render_feed(nouns: Nouns) -> str:
    """The memory-systems feed page, from the feed's own data noun: where and when it scanned, the count with its
    exact search, which project fits which setup, the quoted benchmark claims and what was gathered."""
    feed, words = nouns.feed, nouns.feed_words
    last, count = feed["last_run"], feed["count"]
    hosted = feed_hosted(feed)
    where = words["where_hosted"] if hosted else words["where_local"]
    facts = [(words["last_scan"], f'<time datetime="{attr(last["at"])}">{text(last["at"])}</time>'),
             (words["scan_id"], f'<code>{text(last["scan_id"])}</code>'),
             (words["receipt"], short_hash(last["receipt_hash"]))]
    if hosted:
        facts.insert(1, (words["schedule"], text(last["schedule"])))
    facts.append((words["scans"], ", ".join(f'<code>{text(scan["scan_id"])}</code>' for scan in feed["scans"])))
    fact_list = "".join(f"<div><dt>{text(k)}</dt><dd>{v}</dd></div>" for k, v in facts)
    secondary = "; ".join(f'{text(item["label"])}: {int(item["total_count"]):,}' for item in count.get("secondary", []))
    candidates = {i["repo"]: i for i in feed["items"]} | {c["repo"]: c for c in feed["candidates"]}

    def candidate(repo: str) -> str:
        c = candidates.get(repo)
        if not c:
            fail(f"feed: setup names a candidate the data does not hold: {repo}")
        claims = "".join(f'<li><span class="feed-metric">{text(cl["metric"])}</span> '
                         f'<q>{text(cl["quote"])}</q> <a href="{attr(cl["source_url"])}">source</a></li>'
                         for cl in c.get("claims", []))
        claims = f'<ul class="feed-claims">{claims}</ul>' if claims else f'<p class="feed-none">{text(words["not_reported"])}</p>'
        meta = " · ".join(text(str(x)) for x in (f'{int(c["stars"]):,} {words["stars"]}', c.get("licence") or "", c.get("language") or "",
                                                 c.get("hosting") or "", f'{words["last_commit"]} {str(c.get("last_commit_at") or "")[:10]}') if x)
        return (f'<li class="feed-pick"><a href="{attr(c["url"])}">{text(repo)}</a><p class="feed-meta">{meta}</p>{claims}</li>')

    setups = "".join(
        f'<details class="feed-setup"{" open" if n == 0 else ""}><summary>{text(setup["label"])} '
        f'<span class="feed-fit">{int(setup["fit_count"]):,} {text(words["fits_count"])}</span></summary>'
        f'<ol class="feed-picks">{"".join(candidate(repo) for repo in setup["candidates"])}</ol></details>'
        for n, setup in enumerate(feed["setups"]))
    claim_rows = "".join(
        f'<tr><td><a href="{attr(cl["url"])}">{text(cl["source"])}</a></td><td>{text(cl["metric"])}</td>'
        f'<td><q>{text(cl["quote"])}</q></td></tr>' for cl in feed["claims"])
    memory = sorted((i for i in feed["items"] if i.get("memory_system")), key=lambda i: -int(i.get("stars") or 0))
    item_rows = "".join(
        f'<tr><td><a href="{attr(i["url"])}">{text(i["repo"])}</a></td><td>{int(i.get("stars") or 0):,}</td>'
        f'<td>{text(i.get("licence") or "")}</td><td>{text(i.get("language") or "")}</td>'
        f'<td>{text(str(i.get("last_commit_at") or "")[:10])}</td></tr>' for i in memory[:FEED_TOP_ITEMS])
    papers = "".join(f'<li><a href="{attr(p["url"])}">{text(p["title"])}</a> <span>{text(p["arxiv_id"])} · '
                     f'{text(p["published"][:10])}</span></li>' for p in feed["papers"])
    answer = feed["answer_example"]
    head = lambda cols: "<tr>" + "".join(f"<th scope=\"col\">{text(c)}</th>" for c in cols) + "</tr>"
    main = "\n".join([
        '<main id="main">',
        page_head(words["heading"], words["lead"], dateline=where),
        '<div class="wrap learn feed-page">',
        f'<dl class="feed-facts">{fact_list}</dl>',
        learn_part("count", words["count_heading"], "",
                   f'<p class="feed-count"><b>{int(count["total_count"]):,}</b> {text(words["count_line"])} '
                   f'<time datetime="{attr(count["window_utc"]["end"])}">{text(count["window_utc"]["end"])}</time></p>'
                   f'<p class="feed-query">{text(words["count_query"])}: <a href="{attr(count["url"])}"><code>{text(count["query"])}</code></a></p>'
                   f'<p class="feed-small">{text(count["reading"])} {text(words["count_secondary"])} {secondary}. '
                   f'{text(words["count_response"])} {short_hash(count["response_sha256"])}</p>'),
        # Feed rank is dated: the order holds only as of the scan that stored it (claims audit, November 1).
        learn_part("fits", words["fits_heading"], words["fits_lead"].replace("{as_of}", str(last["at"])[:10]),
                   f'<div class="feed-setups">{setups}</div>'),
        learn_part("ask", words["answer_heading"], "",
                   f'<p class="feed-question"><q>{text(answer["question"])}</q></p><p class="feed-small">{text(words["answer_label"])}</p>'
                   f'<pre class="feed-answer">{text(answer["text"])}</pre>'),
        learn_part("claims", words["claims_heading"], words["claims_lead"],
                   f'<div class="feed-table"><table>{head(words["claims_cols"])}{claim_rows}</table></div>'),
        learn_part("gathered", words["items_heading"], "",
                   f'<p class="feed-small">{len(memory):,} {text(words["items_summary"])} {int(feed["item_count"]):,} '
                   f'{text(words["items_summary_tail"])}</p>'
                   f'<div class="feed-table"><table>{head(words["items_cols"])}{item_rows}</table></div>'),
        learn_part("papers", words["papers_heading"], "", f'<ul class="feed-papers">{papers}</ul>'),
        learn_part("how", words["how_heading"], "", '<ol class="contribute-steps">' + "".join(f"<li>{text(x)}</li>" for x in words["how"]) + "</ol>"),
        "</div>",
        "</main>",
    ])
    return page_shell(words["title"], words["description"], main)


def render_not_found(nouns: Nouns) -> str:
    """One shared not-found page, as the NotFound board draws it: the missing address, where things live now, and
    the promise the worker keeps by redirecting every listed old address."""
    moved = nouns.moved
    page = moved["not_found"]
    prefix = PAGES_PREFIX
    grouped: dict[str, list[dict]] = {}
    for item in moved["pages"]:
        grouped.setdefault(item["to"], []).append(item)  # one entry per new home, naming every old address
    items = []
    for to, group in grouped.items():
        olds = f" {text(page['and'])} ".join(f"<code>/{text(item['from'])}</code>" for item in group)
        items.append(f'<li><a href="{prefix}{attr(to)}"><b>{text(group[0]["what"])}</b>'
                     f'<span>{text(page["was"])} {olds}. {text(group[0]["note"])}</span></a></li>')
    items.append(f'<li><a href="{prefix}"><b>{text(page["home"])}</b><span>{text(page["home_note"])}</span></a></li>')
    main = "\n".join([
        '<main id="main">',
        '<div class="wrap not-found">',
        f'<p class="nf-code">{text(page["code"])}<span data-missing-path></span></p>',
        f"<h1>{text(page['heading'])}</h1>",
        f'<p class="lead">{text(page["lead"])}</p>',
        f'<ul class="nf-list">{"".join(items)}</ul>',
        f'<p class="nf-note">{text(page["redirect_note"])}</p>',
        "</div>",
        "</main>",
    ])
    return page_shell(page["title"], "", main, robots="noindex")


# How it works and evidence -----------------------------------------------------------------------

HOW_PAGE = SITE / "how-it-works" / "index.html"
EVIDENCE_DIR = SITE / "evidence"
EVIDENCE_PAGE = EVIDENCE_DIR / "index.html"
EVIDENCE_NOUN = CONTENT / "evidence.json"
REPO_EVIDENCE = ROOT / "evidence"
# Labels that stamp a page instead of saying what works. Neither page, nor the run it replays, carries one.
STAMPS = ("planned", "not yet", "coming soon", "illustration", "synthetic example")
REPLAY_IDS = ("request", "build", "build-receipt", "review", "held")
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
ISO_DAY = re.compile(r"\d{4}-\d{2}-\d{2}\Z")
NAME_DAY = re.compile(r"(\d{4})-?(\d{2})-?(\d{2})(?:T\d{6}Z)?(?:\.json)?\Z")
# A thin arrow with a head, as the design board draws its edges; the page's styles turn it to point down.
RR_ARROW = ('<svg class="rr-arrow" viewBox="0 0 40 12" width="40" height="12" aria-hidden="true" focusable="false">'
            '<path d="M1 6H33" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>'
            '<path d="M30 1.5 39 6l-9 4.5z" fill="currentColor"/></svg>')
CHECK_ICON = ('<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true" focusable="false">'
              '<circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" stroke-width="2.5"/>'
              '<path d="m8.5 12 2.5 2.5 4.5-5" fill="none" stroke="currentColor" stroke-width="2.5" '
              'stroke-linecap="round" stroke-linejoin="round"/></svg>')


def strings_in(value) -> list[str]:
    if isinstance(value, str):
        return [value]
    items = value.values() if isinstance(value, dict) else value if isinstance(value, list) else []
    return [found for item in items for found in strings_in(item)]


def no_stamps(noun: dict, what: str) -> None:
    for value in strings_in(noun):
        for stamp in STAMPS:
            if stamp in value.lower():
                fail(f"{what}: {stamp!r} stamps the page; say what works instead")


def seq_ranges(seqs: list[int]) -> str:
    """Event numbers as runs: 1, 2, 3, 5 reads 1–3, 5."""
    parts, start = [], None
    for i, n in enumerate(seqs):
        start = n if start is None else start
        if i + 1 == len(seqs) or seqs[i + 1] != n + 1:
            parts.append(str(start) if start == n else f"{start}–{n}")
            start = None
    return ", ".join(parts)


def recorded_number(value) -> str:
    """A number exactly as its record writes it."""
    return json.dumps(value)


def check_real_run(run: dict) -> dict[str, dict]:
    """The replay noun as scripts/sync_real_run.py writes it. Returns its steps by id."""
    facts = run["run"]
    if not (facts["made_up_data_only"] is True and facts["private_or_ngo_data_sent"] is False
            and facts["raw_credentials_included"] is False):
        fail("real-run.json: the replay shows only a synthetic run that sent no private data and no credential")
    steps = run["steps"]
    if [s["id"] for s in steps] != list(REPLAY_IDS) or [s["n"] for s in steps] != list(range(1, len(REPLAY_IDS) + 1)):
        fail("real-run.json: the replay needs its five steps, in order: " + ", ".join(REPLAY_IDS))
    for step in steps:
        receipt = (SITE / step["receipt"]).resolve()
        if not HEX64.fullmatch(step["hash"]["value"]):
            fail(f"real-run.json: step {step['n']} needs a SHA-256")
        if not receipt.is_relative_to(SITE.resolve()) or not receipt.is_file():
            fail(f"real-run.json: step {step['n']}'s receipt is not a file of the site")
        if step["hash"]["value"] not in receipt.read_text(encoding="utf-8"):
            fail(f"real-run.json: step {step['n']}'s hash is not in its receipt file")
        if not (step["trace"] or step["events"]):
            fail(f"real-run.json: step {step['n']} comes from no recorded event")
    for path in run["files"].values():
        if not (SITE / path).is_file():
            fail(f"real-run.json: {path} is not a file of the site")
    no_stamps(run, "real-run.json")
    return {step["id"]: step for step in steps}


def how_toc(toc: dict) -> str:
    items = "".join(f'<li><a href="#{attr(item["href"])}">{text(item["label"])}</a></li>' for item in toc["items"])
    return f'<nav class="how-toc" aria-label="{attr(toc["label"])}"><ul>{items}</ul></nav>'


def how_why(why: dict) -> str:
    for line in why["lines"]:
        if line["kind"] not in {"noun", "verb"}:
            fail("how-it-works.json: a highlighted word is a noun or a verb colour")
    lines = "".join(f'<span class="how-line">{text(line["before"])}<span class="{line["kind"]}-word">'
                    f'{text(line["word"])}</span>{text(line["after"])}</span>' for line in why["lines"])
    items = "".join(f'<li><h3>{text(item["name"])}</h3><p>{text(item["text"])}</p></li>' for item in why["items"])
    under = why["under"]
    return "\n".join([
        '<section class="how-band how-why" id="why" aria-labelledby="why-heading">',
        '<div class="wrap how-why-wrap">',
        f'<h2 class="how-statement" id="why-heading">{lines}</h2>',
        f'<ul class="how-why-list">{items}</ul>',
        f'<p class="how-under"><strong>{text(under["strong"])}</strong> {text(under["text"])}</p>',
        "</div>",
        "</section>",
    ])


def how_map(words: dict) -> str:
    def side(part: dict, kind: str) -> str:
        chips_html = "".join(f"<li>{text(item)}</li>" for item in part["items"])
        return (f'<div class="how-side {kind}"><h3 class="how-big">{text(part["name"])}</h3>'
                f'<p class="how-side-text"><strong>{text(part["label"])}</strong> {text(part["text"])}</p>'
                f'<ul class="how-chips {kind}">{chips_html}</ul></div>')
    notes = "".join(f"<li><strong>{text(note['name'])}</strong> {text(note['text'])}</li>" for note in words["notes"])
    return "\n".join([
        '<section class="how-map" id="map" aria-labelledby="map-heading">',
        '<div class="wrap">',
        f'<h2 class="visually-hidden" id="map-heading">{text(words["heading"])}</h2>',
        f'<div class="how-sides">{side(words["verbs"], "verb")}{side(words["nouns"], "noun")}</div>',
        f'<ul class="how-notes">{notes}</ul>',
        "</div>",
        "</section>",
    ])


def state_track(steps: list[dict]) -> tuple[dict[str, dict[str, str]], dict[str, str]]:
    """Each task's state after each step that changed it, and each task's kind."""
    track: dict[str, dict[str, str]] = {}
    kinds: dict[str, str] = {}
    for step in steps:
        for change in step["changes"]:
            track.setdefault(change["task"], {})[str(step["n"])] = change["states"][-1]
            kinds[change["task"]] = change["kind"]
    return track, kinds


def replay_stage(words: dict, run: dict, steps: dict[str, dict]) -> str:
    """The run as the design board draws it: verbs as rust pills, nouns as blue tiles with their hashes, receipts,
    and the request held for a person. Each part carries the step it appears at, and each task its state after each
    step, for the replay script. Without the script the stage shows the run's end. The ordered list below says the
    same in words, so the stage is hidden from assistive technology."""
    dw, facts = words["diagram"], run["run"]
    track, kinds = state_track(run["steps"])
    task_of = {kind: task for task, kind in kinds.items()}
    for kind in ("request", "build", "review"):
        if kind not in task_of:
            fail(f"real-run.json: the replay needs a {kind} task")

    def final(task: str) -> str:
        states = track[task]
        return states[max(states, key=int)]

    def verb(kind: str, name: str, extra: str = "") -> str:
        task = task_of[kind]
        states = attr(json.dumps(track[task], separators=(",", ":")))
        return (f'<div class="rr-verb{extra}" data-state="{attr(final(task))}"><span class="rr-kind">{text(kind)}</span>'
                f'<span class="rr-name">{text(name)}</span><span class="rr-state" data-state="{attr(final(task))}" '
                f'data-states="{states}">{text(final(task))}</span></div>')

    def link(at: int) -> str:
        return f'<span class="rr-link" data-at="{at}">{RR_ARROW}</span>'

    def receipt(at: int, value: str) -> str:
        return (f'<div class="rr-receipt" data-at="{at}"><span class="rr-receipt-label">{CHECK_ICON}'
                f'{text(dw["receipt"])}</span><code>{text(value[:8])}…</code></div>')

    at = {key: step["n"] for key, step in steps.items()}
    nouns = "".join(f'<li class="rr-noun"><span class="rr-file">{text(noun["path"])}</span>'
                    f'<code class="rr-sha">{text(dw["sha"])} {text(noun["sha256"][:8])}…</code></li>'
                    for noun in steps["build"]["nouns"])
    verdict = steps["review"]["verdict"]
    return "\n".join([
        '<div class="rr-stage" data-rr-stage aria-hidden="true">',
        f'<div class="rr-request" data-at="{at["request"]}">'
        + verb("request", steps["request"]["request_label"], " rr-verb-request") + "</div>",
        f'<div class="rr-lanes" data-at="{at["request"]}">',
        '<div class="rr-lane rr-lane-build">',
        verb("build", facts["builder"]["program"]),
        link(at["build"]),
        f'<ul class="rr-nouns" data-at="{at["build"]}">{nouns}</ul>',
        link(at["build-receipt"]),
        receipt(at["build-receipt"], steps["build-receipt"]["hash"]["value"]),
        "</div>",
        '<div class="rr-lane rr-lane-review">',
        verb("review", facts["reviewer"]["program"]),
        link(at["review"]),
        f'<div class="rr-noun rr-verdict" data-at="{at["review"]}"><span class="rr-file">{text(dw["verdict"])}: '
        f'{text(verdict["verdict"])}</span><span class="rr-sha">{verdict["tests_run"]} {text(dw["tests"])} · '
        f'{verdict["coverage_violations"]} {text(dw["violations"])}</span></div>',
        link(at["review"]),
        receipt(at["review"], steps["review"]["hash"]["value"]),
        "</div>",
        "</div>",
        f'<div class="rr-held" data-at="{at["held"]}">{RR_ARROW}<p class="rr-held-box"><strong>{text(dw["held"])}</strong>'
        f'<span>{text(dw["held_text"])}</span></p></div>',
        "</div>",
    ])


def replay_step(step: dict, words: dict, prefix: str, kinds: dict[str, str]) -> str:
    """One step in words: when, what happened, the actor, the tasks, the state changes, its hash, the events it comes
    from and its receipt file."""
    labels = words["labels"]
    tasks = "".join(f'<li><code>{text(task)}</code> {text(kinds[task])}</li>' for task in step["tasks"])
    changes = "".join(
        f'<li>{text(change["kind"])}{" (" + text(labels["new"]) + ")" if change["new"] else ""}: '
        + " → ".join(text(state) for state in change["states"]) + "</li>" for change in step["changes"])
    source = []
    if step["trace"]:
        source.append(f'{text(labels["trace"])} {seq_ranges(step["trace"])}')
    if step["events"]:
        source.append(f'{text(labels["events"])} {seq_ranges(step["events"])}')
    if step["model_calls"]:
        source.append(f'{step["model_calls"]} {text(labels["calls"])}')
    rows = [(labels["actor"], text(step["actor"])), (labels["tasks"], f'<ul class="rr-list">{tasks}</ul>')]
    if changes:
        rows.append((labels["state"], f'<ul class="rr-list">{changes}</ul>'))
    rows.append((step["hash"]["label"], f'<code class="rr-hash">{text(step["hash"]["value"])}</code>'))
    rows.append((labels["from"], " · ".join(source)))
    meta = "".join(f"<div><dt>{text(name)}</dt><dd>{value}</dd></div>" for name, value in rows)
    return (f'<li class="rr-step" data-rr-step="{step["n"]}" id="step-{attr(step["id"])}">'
            f'<p class="rr-when"><time datetime="{attr(step["at_utc"])}">{text(step["at_utc"][11:19])}</time> '
            f'{text(labels["utc"])}</p>'
            f'<h3 class="rr-title">{text(step["title"])}</h3>'
            f'<p class="rr-text">{text(step["text"])}</p>'
            f'<dl class="rr-meta">{meta}</dl>'
            f'<p class="rr-open"><a class="use-link" href="{prefix}{attr(step["receipt"])}">{text(labels["open"])}'
            f"{CHEVRON}</a></p></li>")


def how_run(words: dict, run: dict, prefix: str) -> str:
    steps = check_real_run(run)
    facts, fw, labels = run["run"], words["facts"], words["labels"]
    _, kinds = state_track(run["steps"])
    spend = facts["spend"]
    started = facts["started_utc"]
    fact_rows = [
        (fw["when"], f'<time datetime="{attr(started)}">{text(human_date(started))}, {text(started[11:19])}</time> '
                     f'{text(labels["utc"])}'),
        (fw["where"], text(facts["fabric"])),
        (fw["revision"], f'<a href="{attr(facts["tessera_repository"])}/tree/{attr(facts["tessera_revision"])}">'
                         f'<code>{text(facts["tessera_revision"])}</code></a>'),
        (fw["builder"], f'{text(facts["builder"]["program"])} {text(facts["builder"]["version"])} · '
                        f'{text(fw["key"])} <code>{text(facts["builder"]["key_id"])}</code>'),
        (fw["reviewer"], f'{text(facts["reviewer"]["program"])} {text(facts["reviewer"]["version"])} · '
                         f'{text(fw["key"])} <code>{text(facts["reviewer"]["key_id"])}</code>'),
        (fw["model"], f'<code>{text(facts["model"])}</code>'),
        (fw["data"], text(fw["data_text"])),
        (fw["spend"], f'{recorded_number(spend["total_actual_usd"])} {text(fw["usd"])} {text(fw["actual"])} · '
                      f'{recorded_number(spend["total_conservative_usd"])} {text(fw["usd"])} {text(fw["conservative"])} '
                      f'· {text(fw["cap"])} {recorded_number(spend["cap_usd"])} {text(fw["usd"])}'),
        (fw["records"], f'{facts["trace_events"]} {text(fw["trace_events"])} · {facts["model_calls"]} '
                        f'{text(fw["model_calls"])}'),
    ]
    fact_list = "".join(f"<div><dt>{text(name)}</dt><dd>{value}</dd></div>" for name, value in fact_rows)
    legend = "".join(f'<li><span class="rr-state" data-state="{attr(item["state"])}">{text(item["state"])}</span> '
                     f'{text(item["text"])}</li>' for item in words["legend"])
    files = {**run["files"], "receipt": run["receipt"]}
    file_links = "".join(use_link({"href": files[item["key"]], "label": item["label"]}, prefix) for item in words["files"])
    step_items = "".join(replay_step(step, words, prefix, kinds) for step in run["steps"])
    return "\n".join([
        '<section class="how-band how-run" id="run" aria-labelledby="run-heading">',
        '<div class="wrap">',
        '<div class="rr-head">',
        f'<h2 id="run-heading">{text(words["heading"])}</h2>',
        f'<p class="rr-id">{text(words["run_label"])} <code>{text(facts["id"])}</code> · '
        f'{text(words["from_receipts"])}<button class="button secondary rr-replay" type="button" data-rr-replay '
        f'aria-controls="run-steps" hidden>{text(words["replay"])}</button></p>',
        "</div>",
        f'<p class="rr-lead">{text(words["lead"])}</p>',
        f'<dl class="rr-facts">{fact_list}</dl>',
        replay_stage(words, run, steps),
        f'<div class="rr-legend"><p>{text(words["legend_label"])}</p><ul>{legend}</ul></div>',
        f'<h3 class="visually-hidden" id="run-steps-heading">{text(words["steps_label"])}</h3>',
        f'<ol class="rr-steps" id="run-steps" aria-labelledby="run-steps-heading">{step_items}</ol>',
        f'<p class="visually-hidden" role="status" data-rr-status data-step-word="{attr(labels["step"])}" '
        f'data-of-word="{attr(labels["of"])}"></p>',
        f'<p class="rr-check">{text(words["check"])}</p>',
        f'<div class="rr-files"><p>{text(words["files_label"])}</p><p class="use-links">{file_links}</p></div>',
        "</div>",
        "</section>",
    ])


def how_underneath(words: dict) -> str:
    herma, tessera = words["herma"], words["tessera"]
    parts = " · ".join(text(item) for item in tessera["items"])
    return "\n".join([
        '<section class="how-under-part" id="underneath" aria-labelledby="underneath-heading">',
        '<div class="wrap">',
        f'<h2 id="underneath-heading">{text(words["heading"])}</h2>',
        '<div class="ud-stage">',
        f'<p class="ud-node ud-harness">{text(words["harness"])}</p>',
        f'<span class="ud-link">{RR_ARROW}</span>',
        f'<p class="ud-node ud-herma"><strong>{text(herma["name"])}</strong><span>{text(herma["text"])}</span></p>',
        f'<span class="ud-link">{RR_ARROW}</span>',
        f'<p class="ud-node ud-model">{text(words["model"])}</p>',
        f'<p class="ud-edge">{RR_ARROW}<span>{text(words["edge"])}</span></p>',
        f'<p class="ud-tessera"><strong>{text(tessera["name"])}</strong><span>{parts}</span></p>',
        "</div>",
        f'<p class="ud-note">{text(words["note"])}</p>',
        f'<p class="ud-note">{text(words["run_note"])}</p>',
        "</div>",
        "</section>",
    ])


def how_meta(words: dict, run: dict, learning: dict, prefix: str) -> str:
    """The measured results the page names, from the learning noun by model: its numbers, line and source. A result
    whose evidence this site serves links to the served copy."""
    items = {item["model"]: item for item in learning["results"]["items"]}
    cards = []
    for pick in words["results"]:
        item = items.get(pick["model"])
        if item is None:
            fail(f"how-it-works.json: learning.json has no result for {pick['model']}")
        if "served" in pick:
            if not (SITE / pick["served"]).is_file():
                fail(f"how-it-works.json: {pick['served']} is not a file of the site")
            href = prefix + attr(pick["served"])
        elif item["link"].startswith("https://github.com/ta-amps/"):
            href = attr(item["link"])
        else:
            fail(f"how-it-works.json: the {pick['model']} result needs public evidence")
        cards.append(
            f'<li class="how-result"><p class="how-result-model">{text(item["model"])}</p>'
            f'<p class="how-result-figure"><span class="how-result-before">{text(item["before"])}</span>'
            f'<span class="visually-hidden"> {text(words["to"])} </span>{RR_ARROW}'
            f'<span class="how-result-after">{text(item["after"])}</span></p>'
            f'<p class="how-result-line">{text(item["line"])}</p>'
            f'<p class="how-result-evidence"><span>{text(words["evidence"])}</span> '
            f'<a href="{href}">{text(item["source"])}</a></p></li>')
    links = "".join(use_link(item, prefix) for item in words["links"])
    return "\n".join([
        '<section class="how-meta" id="meta-models" aria-labelledby="meta-heading">',
        '<div class="wrap">',
        '<div class="how-meta-head">',
        f'<h2 id="meta-heading">{text(words["heading"])}</h2>',
        f'<p>{text(words["lead_before"])} <code>{text(run["run"]["model"])}</code> {text(words["lead_after"])}</p>',
        "</div>",
        f'<ul class="how-results">{"".join(cards)}</ul>',
        f'<p class="use-links how-meta-links">{links}</p>',
        "</div>",
        "</section>",
    ])


def render_how_it_works(nouns: Nouns) -> str:
    """The how-it-works page, after the design board: why, the map, a real run replayed from its receipts, what sits
    underneath, and the Meta models. Every word comes from site/content/how-it-works.json; the run and its words from
    site/content/real-run.json; the results from site/content/learning.json. The replay script animates the stage and
    marks the current step; without it the page shows the run's end and every step in order."""
    page = nouns.how
    no_stamps(page, "how-it-works.json")
    prefix = prefix_for(HOW_PAGE)
    main = "\n".join([
        '<main id="main" class="how">',
        '<div class="wrap page-head how-head">',
        f"<h1>{text(page['heading'])}</h1>",
        f'<p class="lead">{text(page["lead"])}</p>',
        how_toc(page["toc"]),
        "</div>",
        how_why(page["why"]),
        how_map(page["map"]),
        how_run(page["run"], nouns.real_run, prefix),
        how_underneath(page["underneath"]),
        how_meta(page["meta"], nouns.real_run, nouns.learning, prefix),
        "</main>",
    ])
    return page_shell(page["title"], page["description"], main,
                      extra_head=f'<link rel="stylesheet" href="{prefix}assets/how-it-works.css">',
                      extra_body=f'<script src="{prefix}assets/how-it-works.js" defer></script>')


def folder_day(name: str) -> str | None:
    """The date a dated evidence name ends with, as YYYY-MM-DD."""
    found = NAME_DAY.search(name)
    return f"{found.group(1)}-{found.group(2)}-{found.group(3)}" if found else None


def same_files(a: Path, b: Path) -> bool:
    files_a = {p.relative_to(a).as_posix(): p for p in a.rglob("*") if p.is_file()}
    files_b = {p.relative_to(b).as_posix(): p for p in b.rglob("*") if p.is_file()}
    return set(files_a) == set(files_b) and all(files_a[k].read_bytes() == files_b[k].read_bytes() for k in files_a)


def fill_evidence(noun: dict) -> dict:
    """The evidence noun with its measured parts filled from the files: each served folder's files and the last live
    check's answers. A served folder without a line, a line without a folder, an item of the repository's evidence/
    without a line, a copy that differs from its served folder, or a saved answer that changed stops the build."""
    page = json.loads(json.dumps(noun))
    no_stamps(page, "evidence.json")
    served = page["served"]["folders"]
    ids = [folder["id"] for folder in served]
    on_disk = sorted(p.name for p in EVIDENCE_DIR.iterdir() if p.is_dir())
    missing, extra = sorted(set(on_disk) - set(ids)), sorted(set(ids) - set(on_disk))
    if missing:
        fail("evidence.json: describe each served evidence folder in one line: " + ", ".join(missing))
    if extra or len(ids) != len(set(ids)):
        fail("evidence.json: these lines name no served folder, or name one twice: " + ", ".join(extra or ids))
    days = []
    for folder in served:
        if not ISO_DAY.fullmatch(folder["date"]) or folder_day(folder["id"]) not in {None, folder["date"]}:
            fail(f"evidence.json: {folder['id']} needs the date its name carries")
        days.append(folder["date"])
        root = EVIDENCE_DIR / folder["id"]
        folder["files"] = [{"path": p.relative_to(root).as_posix(), "bytes": p.stat().st_size}
                           for p in sorted(root.rglob("*")) if p.is_file()]
    if days != sorted(days, reverse=True):
        fail("evidence.json: served folders go newest first")
    items = page["source"]["items"]
    named = [item["path"].rstrip("/") for item in items]
    repo = sorted("evidence/" + p.name for p in REPO_EVIDENCE.iterdir())
    if sorted(named) != repo:
        fail("evidence.json: give each item of the repository's evidence/ one line: "
             + ", ".join(sorted(set(repo) ^ set(named))))
    for item in items:
        path = ROOT / item["path"]
        if folder_day(path.name) not in {None, item["date"]}:
            fail(f"evidence.json: {item['path']} needs the date its name carries")
        if "same_as" in item:
            if item["same_as"] not in ids or not same_files(path, EVIDENCE_DIR / item["same_as"]):
                fail(f"evidence.json: {item['path']} is no longer the same as its served folder; give it its own line")
        elif not item.get("line"):
            fail(f"evidence.json: {item['path']} needs its line")
    live = page["live"]
    record_path = SITE / live["record"]
    record = load_json(record_path)
    checks = []
    for check in record["checks"]:
        fields = None
        if check["body"]:
            body = (record_path.parent / check["body"]).read_bytes()
            if sha256(body) != check["body_sha256"]:
                fail(f"evidence.json: the saved answer {check['body']} changed after the check")
            answer = json.loads(body)
            fields = {key: answer[key] for key in live["fields"] if key in answer}
        checks.append({"name": check["name"], "url": check["url"], "started_utc": check["started_utc"],
                       "http_status": check["http_status"],
                       "body": f"{Path(live['record']).parent.as_posix()}/{check['body']}" if check["body"] else None,
                       "fields": fields})
    live["snapshot"] = {"checked_at": record["checked_at"], "how": record["how"], "checks": checks}
    return page


def evidence_text(nouns: Nouns) -> str:
    return json.dumps(fill_evidence(nouns.evidence), indent=2, ensure_ascii=False) + "\n"


def size_of(n: int) -> str:
    return f"{n} B" if n < 1024 else f"{n / 1024:.1f} KB" if n < 1024 * 1024 else f"{n / 1024 / 1024:.1f} MB"


def evidence_files(folder: dict, words: dict, prefix: str) -> str:
    """A served folder's files: the top-level ones in a row, each subfolder behind a disclosure."""
    def one(path: str, size: int, base: str) -> str:
        return (f'<li><a href="{prefix}evidence/{attr(folder["id"])}/{attr(path)}">{text(path[len(base):])}</a>'
                f' <span class="ev-size">{size_of(size)}</span></li>')
    top = [f for f in folder["files"] if "/" not in f["path"]]
    groups: dict[str, list[dict]] = {}
    for f in folder["files"]:
        if "/" in f["path"]:
            groups.setdefault(f["path"].split("/", 1)[0], []).append(f)
    parts = [f'<ul class="ev-files">{"".join(one(f["path"], f["bytes"], "") for f in top)}</ul>'] if top else []
    for name, files in groups.items():
        count = f'{len(files)} {text(words["one_file"] if len(files) == 1 else words["many_files"])}'
        parts.append(f'<details class="ev-group"><summary>{CHEVRON}<code>{text(name)}/</code> · {count}</summary>'
                     f'<ul class="ev-files">{"".join(one(f["path"], f["bytes"], name + "/") for f in files)}</ul>'
                     "</details>")
    return "".join(parts)


def render_evidence(nouns: Nouns) -> str:
    """The evidence page: the last live check with its time, every served evidence folder with its date, one line
    and its files, and the evidence that is only in the source download, named by path and never linked. Every word
    comes from site/content/evidence.json; the files and answers are filled from the files themselves."""
    page = fill_evidence(nouns.evidence)
    prefix = prefix_for(EVIDENCE_PAGE)
    live, served, source = page["live"], page["served"], page["source"]
    snap = live["snapshot"]
    checked = snap["checked_at"]
    rows = []
    for check in snap["checks"]:
        fields = check["fields"] or {}
        answer = " · ".join(f"{text(key)}: {text(value if isinstance(value, str) else json.dumps(value))}"
                                for key, value in fields.items())
        saved = (f'<a href="{prefix}{attr(check["body"])}">{text(live["saved"])}</a>' if check["body"] else "")
        note = live["notes"].get(check["url"], "")
        rows.append(
            f'<li class="ev-check{" ev-ok" if check["http_status"] == 200 and fields.get("ok") is True else ""}">'
            f'<p class="ev-check-name">{text(check["name"])}</p><p class="ev-check-url"><code>{text(check["url"])}</code></p>'
            f'<p class="ev-check-answer"><strong>{text(live["http"])} {check["http_status"]}</strong>'
            f'{" · " + answer if answer else ""}</p>'
            + (f'<p class="ev-check-note">{text(note)}</p>' if note else "")
            + (f'<p class="ev-check-saved">{saved}</p>' if saved else "") + "</li>")
    folders = []
    for folder in served["folders"]:
        link_html = f'<p class="ev-also">{use_link(folder["link"], prefix)}</p>' if "link" in folder else ""
        folders.append(
            f'<li class="ev-folder" id="{attr(folder["id"])}">'
            f'<p class="ev-date"><time datetime="{attr(folder["date"])}">{text(human_date(folder["date"]))}</time>'
            f' · <code>{text(folder["id"])}/</code></p>'
            f'<h3>{text(folder["title"])}</h3><p class="ev-line">{text(folder["line"])}</p>'
            f'<div class="ev-files-wrap"><p class="ev-files-label">{text(served["files"])}</p>'
            f'{evidence_files(folder, served, prefix)}</div>{link_html}</li>')
    items = []
    for item in source["items"]:
        line = (f'{text(source["same"])} <a href="#{attr(item["same_as"])}"><code>{text(item["same_as"])}/</code></a>.'
                if "same_as" in item else text(item["line"]))
        items.append(f'<li><p class="ev-date"><time datetime="{attr(item["date"])}">{text(human_date(item["date"]))}'
                     f'</time></p><p><code>{text(item["path"])}</code></p><p class="ev-line">{line}</p></li>')
    main = "\n".join([
        '<main id="main" class="ev">',
        '<div class="wrap page-head ev-head">',
        f"<h1>{text(page['heading'])}</h1>",
        f'<p class="lead">{text(page["lead"])}</p>',
        how_toc(page["toc"]),
        "</div>",
        '<div class="wrap ev-body">',
        '<section class="ev-part ev-live" id="live" aria-labelledby="live-heading">',
        f'<h2 id="live-heading">{text(live["heading"])}</h2>',
        f'<p class="ev-lead">{text(live["lead"])}</p>',
        f'<p class="ev-checked">{text(live["checked"])} <time datetime="{attr(checked)}">'
        f'{text(human_date(checked))} {text(live["at"])} {text(checked[11:16])}</time> {text(live["utc"])}</p>',
        f'<ul class="ev-checks">{"".join(rows)}</ul>',
        "</section>",
        '<section class="ev-part" id="served" aria-labelledby="served-heading">',
        f'<h2 id="served-heading">{text(served["heading"])}</h2>',
        f'<p class="ev-lead">{text(served["lead"])}</p>',
        f'<ol class="ev-folders">{"".join(folders)}</ol>',
        "</section>",
        '<section class="ev-part" id="source" aria-labelledby="source-heading">',
        f'<h2 id="source-heading">{text(source["heading"])}</h2>',
        f'<p class="ev-lead">{text(source["lead"])}</p>',
        f'<p class="use-links">{use_link(source["link"], prefix)}</p>',
        f'<ul class="ev-source">{"".join(items)}</ul>',
        "</section>",
        "</div>",
        "</main>",
    ])
    return page_shell(page["title"], page["description"], main,
                      extra_head=f'<link rel="stylesheet" href="{prefix}assets/evidence.css">')


# Manifest ---------------------------------------------------------------------------------------

def manifest_text(nouns: Nouns, pdfs: dict[str, dict]) -> str:
    """site/decks.json with the current decks listed before the frozen versions, which stay as they are."""
    data = nouns.manifest
    previous = {entry["id"]: entry for entry in data.get("decks", [])}
    entries = []
    for deck in nouns.decks:
        spec, deck_id = deck["spec"], deck["id"]
        entry = {"id": deck_id, "title": spec["title"], "date": spec["page"]["date"], "path": f"decks/{deck_id}/",
                 "source": f"decks/{deck_id}/source/", "slides": len(deck["slides"]), "unbranded": True}
        if deck["claims"]:
            entry["claim_review"] = f"decks/{deck_id}/source/claims.json"
        entry["downloads"] = [pdfs[deck_id]] if deck_id in pdfs else previous.get(deck_id, {}).get("downloads", [])
        entries.append(entry)
    out: dict = {}
    for key, value in data.items():
        if key == "decks":
            continue
        if key == "versions":
            out["decks"] = entries
        out[key] = value
    return json.dumps(out, indent=2, ensure_ascii=False) + "\n"


# PDF --------------------------------------------------------------------------------------------

def render_pdfs(decks: list[dict], mains: dict[str, str]) -> dict[str, dict]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        fail("--pdf needs the Playwright package (pip install playwright)")

    class Quiet(SimpleHTTPRequestHandler):
        def log_message(self, *args) -> None:  # keep the build output readable
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Quiet, directory=str(SITE)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    entries = {}
    try:
        with sync_playwright() as p:
            launch = {"executable_path": os.environ["CHROMIUM_PATH"]} if os.environ.get("CHROMIUM_PATH") else {}
            browser = p.chromium.launch(**launch)
            for deck in decks:
                page = browser.new_page(viewport={"width": CANVAS_W, "height": CANVAS_H})
                page.goto(f"http://127.0.0.1:{server.server_port}/decks/{deck['id']}/", wait_until="networkidle")
                page.emulate_media(media="print")
                page.evaluate("document.fonts.ready")
                missing = page.evaluate("""() => ['Space Grotesk', 'IBM Plex Sans', 'JetBrains Mono']
                    .filter(f => !document.fonts.check('16px "' + f + '"'))""")
                if missing:
                    fail("web fonts did not load: " + ", ".join(missing))
                page.evaluate("title => { document.title = title; }", deck["spec"]["page"]["pdf_title"])
                out = deck["folder"] / deck["pdf_name"]
                page.pdf(path=str(out), prefer_css_page_size=True, print_background=True, tagged=True, outline=False)
                page.close()
                data = out.read_bytes()
                entries[deck["id"]] = {"format": "pdf", "path": f"decks/{deck['id']}/{deck['pdf_name']}",
                                       "sha256": sha256(data), "bytes": len(data),
                                       "printed_from_main_sha256": mains[deck["id"]]}
            browser.close()
    finally:
        server.shutdown()
    return entries


# Main ---------------------------------------------------------------------------------------------

def unique_ids(path: Path, content: str) -> None:
    ids = re.findall(r'\sid="([^"]+)"', content)
    repeated = sorted({i for i in ids if ids.count(i) > 1})
    if repeated:
        fail(f"{path.relative_to(ROOT)}: repeated ids {', '.join(repeated)}")


def outputs_for(nouns: Nouns) -> dict[Path, str]:
    generated = {deck["page"]: render_deck(deck, nouns) for deck in nouns.decks}
    generated[SITE / "index.html"] = render_home(nouns)
    generated[DECKS / "index.html"] = render_decks_index(nouns)
    generated[DECKS / "earlier-drafts" / "index.html"] = render_earlier(nouns)
    generated[SITE / "use-cases" / "index.html"] = render_use_cases(nouns)
    generated[SITE / "storyboards" / "index.html"] = render_storyboards(nouns)
    generated[SITE / "film" / "index.html"] = render_film(nouns)
    generated[SITE / "learning" / "index.html"] = render_learning(nouns)
    generated[SITE / "library" / "index.html"] = render_library(nouns)
    generated[SITE / "deploy" / "index.html"] = render_deploy(nouns)
    generated[SITE / "contribute" / "index.html"] = render_contribute(nouns)
    generated[SITE / "models" / "index.html"] = render_models(nouns)
    generated[SITE / "feeds" / "memory-systems" / "index.html"] = render_feed(nouns)
    generated[HOW_PAGE] = render_how_it_works(nouns)
    generated[EVIDENCE_PAGE] = render_evidence(nouns)
    generated[SITE / "404.html"] = render_not_found(nouns)
    if set(generated) & nouns.frozen:
        fail("a frozen page is never written")
    written = sorted(
        p for p in SITE.rglob("*.html")
        if "source" not in p.relative_to(SITE).parts
        and p not in generated
        and p not in nouns.frozen
        and not (bool({"studio", "hub-3d", "compare"} & set(p.relative_to(SITE).parts))
                 and not {"<!-- site:head -->", "<!-- site:banner -->"} & set(re.findall(r"<!-- site:(?:head|banner) -->", p.read_text(encoding="utf-8"))))
    )
    outputs = {path: render_page(path, content, nouns) for path, content in generated.items()}
    for path in written:
        outputs[path] = render_page(path, path.read_text(encoding="utf-8"), nouns)
    for path, content in outputs.items():
        unique_ids(path, content)
    outputs[SITE / "llms.txt"] = render_llms(nouns, set(outputs))
    return {path: plain_words(repoint(meta_models(content, nouns.models), nouns.links)) for path, content in outputs.items()}


def build(check: bool, pdf: bool) -> list[str]:
    nouns = Nouns()
    outputs = outputs_for(nouns)
    mains = {deck["id"]: sha256(main_of(outputs[deck["page"]]).encode("utf-8")) for deck in nouns.decks}
    pdfs: dict[str, dict] = {}
    if pdf and not check:
        for path, content in outputs.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        pdfs = render_pdfs(nouns.decks, mains)
    outputs[MANIFEST] = manifest_text(nouns, pdfs)
    outputs[EVIDENCE_NOUN] = evidence_text(nouns)

    stale = []
    for path, content in outputs.items():
        current = path.read_text(encoding="utf-8") if path.exists() else None
        if current != content:
            stale.append(path.relative_to(ROOT).as_posix())
            if not check:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
    for entry in json.loads(outputs[MANIFEST])["decks"]:
        deck = next(d for d in nouns.decks if d["id"] == entry["id"])
        if not entry["downloads"]:
            stale.append(f"{entry['path']}{deck['pdf_name']} (missing; run --pdf)")
        for download in entry["downloads"]:
            if download.get("printed_from_main_sha256") != mains[entry["id"]]:
                stale.append(download["path"] + " (printed from an older deck; run --pdf)")
    return stale


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--check", action="store_true", help="report stale outputs without writing")
    parser.add_argument("--pdf", action="store_true", help="also print every current deck to PDF")
    args = parser.parse_args(argv)
    try:
        stale = build(args.check, args.pdf)
    except BuildError as error:
        print(f"build_site: {error}", file=sys.stderr)
        return 2
    if args.check:
        if stale:
            print("build_site: stale outputs, run python3 scripts/build_site.py:", file=sys.stderr)
            for item in stale:
                print("  " + item, file=sys.stderr)
            return 1
        print("build_site: outputs are up to date")
        return 0
    pdf_stale = [s for s in stale if s.endswith("--pdf)")]
    for item in stale:
        print(("needs --pdf: " if item in pdf_stale else "wrote ") + item)
    return 1 if pdf_stale else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
