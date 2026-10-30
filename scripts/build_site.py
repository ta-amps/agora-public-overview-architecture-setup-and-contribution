"""Build the static showcase site from its sources. Stdlib only, except --pdf.

What it does:
  * Builds the v4 web deck, site/decks/2026-10-29/v4/index.html, from its source/ folder
    (deck.json, slides/*.html, updates.json, claims.json). The custom elements of the slide
    format (<x-shape>, <x-icon>) become inline SVG, and each slide's <aside> becomes its notes.
  * Builds v3 as v2 with one narrow change: one point added on slide 2, beneath the training
    point. v1 and v2 are never written.
  * Writes the shared head, header, docs sidebar and footer into every page between marker
    comments, with relative links for the page's depth.
  * Adds v3 and v4 to site/decks.json, leaving the earlier entries byte-identical.

Usage:
  python3 scripts/build_site.py            write the outputs
  python3 scripts/build_site.py --check    fail when an output is stale (no writes; make check runs it)
  python3 scripts/build_site.py --pdf      also print the v4 deck to PDF with headless Chromium
                                           (needs the Playwright package; set CHROMIUM_PATH to use
                                           an installed browser)

Nothing here touches the network, except --pdf, where the page loads its web fonts.
"""
from __future__ import annotations

import argparse
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
DECKS = SITE / "decks" / "2026-10-29"
V2_PAGE = DECKS / "v2" / "index.html"
V3_PAGE = DECKS / "v3" / "index.html"
V4_DIR = DECKS / "v4"
V4_PAGE = V4_DIR / "index.html"
STANDALONE = {SITE / "storyboards" / "2026-10-29" / "eranos-video-v1" / "index.html"}
# Published pages keep the footer they were published with: the v4 deck, whose page hash and printed PDF
# are recorded, and the dated two-video storyboard draft. Every other page gets the current footer.
PUBLISHED_FOOTER = {V4_PAGE, SITE / "storyboards" / "2026-10-29" / "two-videos" / "index.html"}
SOURCE = V4_DIR / "source"
MANIFEST = SITE / "decks.json"
PDF_NAME = "ta-amps-hackathon-v4.pdf"
DECK_HREF = "decks/2026-10-29/v4/"
PAGES_PREFIX = "/agora-public-overview-architecture-setup-and-contribution/"
SOURCE_URL = "https://github.com/ta-amps/agora-public-overview-architecture-setup-and-contribution"
# Published pages keep the source link they were published with, from before the repository was renamed.
PUBLISHED_SOURCE_URL = "https://github.com/ta-amps/agora"
CANVAS_W, CANVAS_H = 1920, 1080

FONTS = ("https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700"
         "&family=JetBrains+Mono:wght@400;600&family=Space+Grotesk:wght@400..700&display=swap")

# Lucide icons (ISC license, see site/THIRD-PARTY-NOTICES.txt), the three the deck names.
ICONS = {
    "Users": ('<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><path d="M16 3.128a4 4 0 0 1 0 7.744"/>'
              '<path d="M22 21v-2a4 4 0 0 0-3-3.87"/><circle cx="9" cy="7" r="4"/>'),
    "Book": '<path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H19a1 1 0 0 1 1 1v18a1 1 0 0 1-1 1H6.5a1 1 0 0 1 0-5H20"/>',
    "ThumbsUp": ('<path d="M15 5.88 14 10h5.83a2 2 0 0 1 1.92 2.56l-2.33 8A2 2 0 0 1 17.5 22H4a2 2 0 0 1-2-2v-8'
                 'a2 2 0 0 1 2-2h2.76a2 2 0 0 0 1.79-1.11L12 2a3.13 3.13 0 0 1 3 3.88Z"/><path d="M7 10v12"/>'),
}

NAV = [("deck", DECK_HREF, "Deck"), ("storyboards", "storyboards/", "Storyboard"),
       ("docs", "docs/", "Docs"), ("contribute", "contribute/", "Contribute")]

DOCS = [("docs/", "Overview"), ("docs/how-it-works/", "How it works"),
        ("docs/surfaces-and-seed-packs/", "The map"), ("docs/connect/", "Connect an agent"),
        ("docs/seed-pack-ideas/", "Seed pack ideas"),
        ("docs/status/", "Status and evidence"), ("docs/roadmap/", "Roadmap")]

MARK = ('<svg width="28" height="28" viewBox="0 0 32 32" aria-hidden="true" focusable="false">'
        '<rect x="0" y="0" width="14" height="14" rx="3" fill="var(--color-noun)"/>'
        '<rect x="18" y="0" width="14" height="14" rx="3" fill="var(--color-verb)"/>'
        '<rect x="0" y="18" width="14" height="14" rx="3" fill="var(--color-rule-strong)"/>'
        '<rect x="18" y="18" width="14" height="14" rx="3" fill="var(--color-noun)"/></svg>')

MODE_SCRIPT = ('<script>try{var m=localStorage.getItem("ta-amps-mode");'
               'if(m==="dark"||m==="light")document.documentElement.dataset.mode=m}catch(e){}'
               'document.documentElement.classList.add("js")</script>')

# v3 is v2 plus one point on slide 2, beneath the training point. Each pair must match exactly once.
V3_POINT = ('<p style="font-size:30px;line-height:1.4;color:#3B4252">Today’s AI doesn’t break work into small, '
            'atomic, decentralized pieces in a graph that many workers can claim, check and finish.</p>')
V3_EDITS = [
    ("<title>ta-amps · Hackathon draft v2</title>", "<title>ta-amps · Hackathon draft v3</title>"),
    ("<strong>ta-amps · Hackathon deck · v2</strong><span>Qualified draft · experiments and limits remain explicit.",
     "<strong>ta-amps · Hackathon deck · v3</strong><span>v2 plus one point on slide 2 · experiments and limits "
     "remain explicit."),
    ("<p style=\"font-size:26px;line-height:1.4;color:#C8D0DC\">New models help, but current tools, reusable code and "
     "durable queues still need external systems.</p>\n</div>\n</div>\n",
     "<p style=\"font-size:26px;line-height:1.4;color:#C8D0DC\">New models help, but current tools, reusable code and "
     "durable queues still need external systems.</p>\n</div>\n</div>\n" + V3_POINT + "\n"),
]


class BuildError(Exception):
    pass


def fail(message: str) -> None:
    raise BuildError(message)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# Shared page chrome -------------------------------------------------------------------------

def prefix_for(page: Path) -> str:
    if page.relative_to(SITE).as_posix() == "404.html":
        return PAGES_PREFIX  # GitHub Pages serves this page at any missing path, so its links are absolute.
    depth = len(page.relative_to(SITE).parts) - 1
    return "../" * depth


def section_for(page: Path) -> str:
    parts = page.relative_to(SITE).parts
    first = parts[0] if len(parts) > 1 else "home"
    return {"decks": "deck"}.get(first, first)


def head_block(prefix: str) -> str:
    return "\n".join([
        '<link rel="preconnect" href="https://fonts.googleapis.com">',
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>',
        f'<link rel="stylesheet" href="{html.escape(FONTS)}">',
        f'<link rel="stylesheet" href="{prefix}assets/site.css">',
        f'<link rel="icon" href="{prefix}assets/mark.svg" type="image/svg+xml">',
        MODE_SCRIPT,
    ])


def header_block(page: Path, prefix: str) -> str:
    section = section_for(page)
    rel = page.relative_to(SITE).as_posix()
    items = []
    for key, href, label in NAV:
        current = ""
        if key == section:
            current = ' aria-current="page"' if rel == href + "index.html" else ' aria-current="true"'
        items.append(f'<li><a href="{prefix}{href}"{current}>{label}</a></li>')
    home = prefix or "./"
    return "\n".join([
        '<a class="skip-link" href="#main">Skip to content</a>',
        '<header class="site-header">',
        '<div class="wrap">',
        f'<a class="wordmark" href="{home}">{MARK}<span>ta-amps</span></a>',
        '<nav class="site-nav" aria-label="Site">',
        "<ul>" + "".join(items) + "</ul>",
        "</nav>",
        '<button class="mode-toggle" type="button" data-mode-toggle aria-pressed="false" hidden>Dark mode</button>',
        "</div>",
        "</header>",
    ])


def footer_block(prefix: str, published: bool = False) -> str:
    site_links = [(DECK_HREF, "Draft deck"), ("decks/", "All deck versions"), ("storyboards/", "Video storyboard"),
                  ("docs/", "Docs"), ("docs/connect/", "Connect an agent"), ("docs/status/", "Status and evidence"),
                  ("contribute/", "Contribute")]
    outside = [("https://eranos.ta-amps.workers.dev", "Eranos"),
               ("https://github.com/ta-amps", "ta-amps on GitHub"),
               (PUBLISHED_SOURCE_URL if published else SOURCE_URL, "Source of this site"),
               (prefix + "THIRD-PARTY-NOTICES.txt", "Third-party notices")]
    if published:
        # A published page keeps the footer it was published with (see PUBLISHED_FOOTER).
        site_links = [link for link in site_links if link[0] != "docs/connect/"]
        outside = [("https://home.ta-amps.workers.dev", "Home portal")] + outside
    first = "".join(f'<li><a href="{prefix}{href}">{label}</a></li>' for href, label in site_links)
    second = "".join(f'<li><a href="{href}">{label}</a></li>' for href, label in outside)
    return "\n".join([
        '<footer class="site-footer">',
        '<div class="wrap">',
        '<nav aria-label="Footer">',
        f"<ul>{first}</ul>",
        "</nav>",
        f'<ul aria-label="Elsewhere">{second}</ul>',
        "<p>A snapshot of October 29, 2026. Drafts and plans are labelled; publishing them here does not "
        "certify any claim. Text and code are under the MIT license.</p>",
        "</div>",
        "</footer>",
        f'<script src="{prefix}assets/site.js" defer></script>',
    ])


def docnav_block(page: Path) -> str:
    here = page.parent
    items = []
    for target, label in DOCS:
        rel = os.path.relpath(SITE / target, here).replace(os.sep, "/")
        href = "./" if rel == "." else rel + "/"
        current = ' aria-current="page"' if page == SITE / target / "index.html" else ""
        items.append(f'<li><a href="{href}"{current}>{label}</a></li>')
    return '<nav class="doc-nav" aria-label="Docs">\n<h2>Docs</h2>\n<ul>' + "".join(items) + "</ul>\n</nav>"


def replace_block(text: str, name: str, content: str, page: Path) -> str:
    start, end = f"<!-- site:{name} -->", f"<!-- /site:{name} -->"
    if text.count(start) != 1 or text.count(end) != 1:
        fail(f"{page.relative_to(ROOT)}: needs exactly one {start} ... {end} block")
    before, rest = text.split(start, 1)
    _, after = rest.split(end, 1)
    return f"{before}{start}\n{content}\n{end}{after}"


def render_page(page: Path, text: str) -> str:
    prefix = prefix_for(page)
    text = replace_block(text, "head", head_block(prefix), page)
    text = replace_block(text, "header", header_block(page, prefix), page)
    if "<!-- site:docnav -->" in text:
        text = replace_block(text, "docnav", docnav_block(page), page)
    return replace_block(text, "footer", footer_block(prefix, page in PUBLISHED_FOOTER), page)


# v4 deck ----------------------------------------------------------------------------------------

STYLE_PART = re.compile(r"\s*([a-z-]+)\s*:\s*([^;]+)")


def style_map(style: str) -> dict[str, str]:
    return {m.group(1): m.group(2).strip() for m in STYLE_PART.finditer(style)}


def px(value: str | None, what: str) -> int:
    match = re.fullmatch(r"(\d+)px", value or "")
    if not match:
        fail(f"{what}: expected a pixel size, found {value!r}")
    return int(match.group(1))


def shape_svg(match: re.Match) -> str:
    kind, style = match.group(1), style_map(match.group(2))
    if kind != "arrow-right":
        fail(f"unsupported x-shape kind {kind!r}")
    w, h = px(style.get("width"), "x-shape width"), px(style.get("height"), "x-shape height")
    fill = style.get("background")
    if not fill:
        fail("x-shape needs a background colour")
    # The outline the slide format draws for arrow-right: a shaft at 25 to 75% height, the head from 62%.
    sx, y1, y2 = round(w * 0.62, 2), round(h * 0.25, 2), round(h * 0.75, 2)
    path = f"M0 {y1}H{sx}V0L{w} {h / 2:g}L{sx} {h}V{y2}H0Z"
    return (f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" aria-hidden="true" focusable="false" '
            f'style="display:block;flex-shrink:0"><path d="{path}" fill="{html.escape(fill)}"/></svg>')


def icon_svg(match: re.Match) -> str:
    name, style = match.group(1), match.group(2)
    if name not in ICONS:
        fail(f"unsupported x-icon {name!r}")
    return ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
            f'stroke-linejoin="round" aria-hidden="true" focusable="false" style="{html.escape(style)};'
            f'display:block;flex-shrink:0">{ICONS[name]}</svg>')


def plain_text(fragment: str) -> str:
    fragment = re.sub(r"<br\s*/?>", " ", fragment)
    fragment = re.sub(r"<[^>]+>", "", fragment)
    return re.sub(r"\s+", " ", html.unescape(fragment)).strip()


def load_slide(name: str) -> dict:
    path = SOURCE / "slides" / f"{name}.html"
    if not path.is_file():
        fail(f"missing slide source {path.relative_to(ROOT)}")
    text = path.read_text(encoding="utf-8").strip()
    opening = re.match(r'<section\s+id="([a-z0-9-]+)"([^>]*)>', text)
    if not opening or not text.endswith("</section>") or opening.group(1) != name:
        fail(f"{name}: a slide is one <section id=\"{name}\"> element")
    style = re.search(r'\sstyle="([^"]*)"', opening.group(2))
    inner = text[opening.end():-len("</section>")]
    asides = re.findall(r"<aside>(.*?)</aside>", inner, re.S)
    if len(asides) != 1:
        fail(f"{name}: expected one <aside> with speaker notes")
    inner = re.sub(r"\s*<aside>.*?</aside>\s*", "\n", inner, flags=re.S)
    inner = re.sub(r'<x-shape kind="([a-z-]+)" style="([^"]*)"></x-shape>', shape_svg, inner)
    inner = re.sub(r'<x-icon name="([A-Za-z]+)" style="([^"]*)"></x-icon>', icon_svg, inner)
    if "<x-" in inner:
        fail(f"{name}: unconverted custom element")
    heading = re.search(r"<h([12])\b[^>]*>(.*?)</h\1>", inner, re.S)
    if not heading:
        fail(f"{name}: slide needs an h1 or h2 title")
    return {"name": name, "style": style.group(1) if style else "", "inner": inner.strip(),
            "notes": asides[0].strip(), "title": plain_text(heading.group(2))}


def deck_sources() -> tuple[dict, list[dict], dict, dict]:
    deck = json.loads((SOURCE / "deck.json").read_text(encoding="utf-8"))
    updates = json.loads((SOURCE / "updates.json").read_text(encoding="utf-8"))
    claims = json.loads((SOURCE / "claims.json").read_text(encoding="utf-8"))
    order = deck["order"]
    if len(order) != len(set(order)):
        fail("deck.json lists a slide twice")
    slides = [load_slide(name) for name in order]
    unknown = set(updates["slides"]) - set(order)
    if unknown:
        fail("updates.json names unknown slides: " + ", ".join(sorted(unknown)))
    for claim in claims["claims"]:
        if claim["status"] not in {"measured", "pending", "planned"}:
            fail(f"claims.json: unknown status {claim['status']!r}")
    return deck, slides, updates, claims


def deck_sections(deck: dict, slides: list[dict]) -> list[dict]:
    index = {s["name"]: i for i, s in enumerate(slides)}
    starts = sorted((index[v["start"]], key, v["description"]) for key, v in deck["sections"].items())
    sections = []
    for n, (start, key, description) in enumerate(starts):
        stop = starts[n + 1][0] if n + 1 < len(starts) else len(slides)
        group = "Appendix" if description.lower().startswith("appendix") else "Core"
        text = re.sub(r"^(core|appendix):\s*", "", description, flags=re.I)
        sections.append({"key": key, "start": start, "stop": stop, "group": group, "text": text})
    return sections


def core_count(deck: dict, slides: list[dict]) -> int:
    return sum(s["stop"] - s["start"] for s in deck_sections(deck, slides) if s["group"] == "Core")


def claim_rows(claims: dict) -> str:
    rows = []
    for claim in claims["claims"]:
        source = html.escape(claim["source"])
        if claim.get("link"):
            source += f" {html.escape(claim['link'])}"
        rows.append(f'<tr><th scope="row">{html.escape(claim["where"])}</th><td>{html.escape(claim["number"])}</td>'
                    f'<td><span class="claim-status {claim["status"]}">{claim["status"].capitalize()}</span></td>'
                    f"<td>{source}</td></tr>")
    return "".join(rows)


def claim_list(claims: dict) -> str:
    items = []
    for claim in claims["claims"]:
        link = f' <a href="{html.escape(claim["link"])}">Evidence</a>' if claim.get("link") else ""
        items.append(f'<li><div class="claim-head"><span class="claim-status {claim["status"]}">'
                     f'{claim["status"].capitalize()}</span><span class="claim-where">{html.escape(claim["where"])}</span></div>'
                     f'<p class="claim-number">{html.escape(claim["number"])}</p>'
                     f'<p class="claim-source">{html.escape(claim["source"])}{link}</p></li>')
    return '<ul class="claim-list">' + "".join(items) + "</ul>"


def render_deck(deck: dict, slides: list[dict], updates: dict, claims: dict) -> str:
    prefix = prefix_for(V4_PAGE)
    sections = deck_sections(deck, slides)
    total = len(slides)
    core = core_count(deck, slides)
    appendix = total - core

    outline = []
    for group in ("Core", "Appendix"):
        parts = [s for s in sections if s["group"] == group]
        if not parts:
            continue
        outline.append(f'<div class="outline-group"><h2>{group}</h2>')
        for part in parts:
            outline.append(f'<p class="outline-about">{html.escape(part["text"])}</p><ol start="{part["start"] + 1}">')
            for i in range(part["start"], part["stop"]):
                outline.append(f'<li><a href="#slide-{i + 1}" data-goto="{i}">{html.escape(slides[i]["title"])}</a></li>')
            outline.append("</ol>")
        outline.append("</div>")

    body = []
    for i, slide in enumerate(slides):
        label = f"{i + 1} of {total}: {slide['title']}"
        update = updates["slides"].get(slide["name"])
        update_html = (f'<p class="slide-update"><strong>Since this draft:</strong> {html.escape(update)}</p>'
                       if update else "")
        body.append("\n".join([
            f'<section class="slide" id="slide-{i + 1}" aria-roledescription="slide" '
            f'aria-label="{html.escape(label)}" data-name="{slide["name"]}">',
            '<div class="slide-frame">',
            f'<div class="slide-canvas" style="{html.escape(slide["style"])}">',
            slide["inner"],
            "</div>",
            "</div>",
            update_html,
            f'<div class="slide-notes"><h2>Speaker notes</h2><p>{slide["notes"]}</p></div>',
            "</section>",
        ]))

    changes = "".join(
        f"<li><strong>Slide {i + 1}, {html.escape(s['title'])}.</strong> {html.escape(updates['slides'][s['name']])}</li>"
        for i, s in enumerate(slides) if s["name"] in updates["slides"])

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Deck v4, draft for feedback | ta-amps</title>
<meta name="description" content="Version 4 of the ta-amps hackathon deck, a draft for feedback: {core} core slides and a {appendix}-slide appendix, with speaker notes, updates since the draft, a claim review and a PDF.">
<!-- site:head -->
<!-- /site:head -->
<link rel="stylesheet" href="viewer.css">
</head>
<body class="deck-page">
<!-- site:header -->
<!-- /site:header -->
<main id="main" class="deck" data-total="{total}">
<div class="wrap deck-bar">
<div class="deck-heading">
<h1>Deck v4, a draft for feedback</h1>
<p>October 29, 2026, evening. {core} core slides and a {appendix}-slide appendix, including a new Eranos slide and the latest wording.</p>
</div>
<div class="deck-tools">
<button class="tool" type="button" data-outline-toggle aria-expanded="false" aria-controls="deck-outline" hidden>Outline</button>
<button class="tool" type="button" data-notes-toggle aria-pressed="false" hidden>Speaker notes</button>
<a class="button secondary" href="{PDF_NAME}" download>Download PDF</a>
</div>
</div>
<nav class="wrap deck-outline" id="deck-outline" aria-label="Slide outline">
{''.join(outline)}
</nav>
<div class="deck-stage" data-stage>
{chr(10).join(body)}
</div>
<div class="wrap deck-controls" data-controls hidden>
<button class="tool" type="button" data-prev>Previous</button>
<p class="deck-counter"><span data-current>1</span> of {total}</p>
<button class="tool" type="button" data-next>Next</button>
</div>
<p class="wrap deck-help" data-help hidden>Use the arrow keys or swipe to change slides. <kbd>N</kbd> shows the speaker notes and <kbd>O</kbd> the outline.</p>
<div class="wrap deck-intro">
<p>A draft for feedback, so some slides describe plans. Where a fact changed after the draft, a note under the slide says so. Every earlier version stays on the <a href="{prefix}decks/">deck versions</a> page, unchanged.</p>
</div>
<section class="wrap deck-claims" id="claim-review" aria-labelledby="claims-title">
<h2 id="claims-title">Claim review: every number in this deck</h2>
<p>{html.escape(claims["about"])} Methods and failures are in the <a href="{html.escape(claims["status_report"])}">dated status report</a>.</p>
{claim_list(claims)}
</section>
<section class="print-colophon" aria-label="About this PDF">
<h2>About this draft</h2>
<p>ta-amps deck v4, October 29, 2026, evening. A draft for feedback: publishing it does not certify any claim.</p>
<h3>Since this draft</h3>
<ul>{changes}</ul>
<p>Web version with speaker notes: https://ta-amps.github.io/agora/{DECK_HREF}</p>
</section>
<section class="print-colophon print-claims" aria-label="Claim review for this PDF">
<h2>Claim review: every number in this deck</h2>
<table>
<thead><tr><th scope="col">Where</th><th scope="col">Number</th><th scope="col">Status</th><th scope="col">Source</th></tr></thead>
<tbody>{claim_rows(claims)}</tbody>
</table>
</section>
</main>
<!-- site:footer -->
<!-- /site:footer -->
<script src="viewer.js" defer></script>
</body>
</html>
"""


# v3 deck ----------------------------------------------------------------------------------------

def render_v3() -> str:
    text = V2_PAGE.read_text(encoding="utf-8")
    for old, new in V3_EDITS:
        if text.count(old) != 1:
            fail("v3: an edit no longer matches v2 exactly once: " + old[:60])
        text = text.replace(old, new)
    return text


# Manifest ---------------------------------------------------------------------------------------

def manifest_text(v3_html: bytes, v4_html: bytes, deck: dict, slides: list[dict], pdf: dict | None) -> str:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    previous = {v["version"]: v for v in data["versions"]}
    v3 = {
        "version": "v3",
        "label": "Qualified draft plus the atomic-work point",
        "slides": 18,
        "core_slides": 8,
        "appendix_slides": 10,
        "path": "decks/2026-10-29/v3/",
        "html_sha256": sha256(v3_html),
        "derived_from": "v2",
        "change": "Slide 2 adds one point beneath the training point: today's AI doesn't break work into small, "
                  "atomic, decentralized pieces in a graph that many workers can claim, check and finish. "
                  "Nothing else in the slides changes.",
        "downloads": previous.get("v3", {}).get("downloads", []),
        "download_note": previous.get("v3", {}).get(
            "download_note", "Browser only. No PowerPoint or PDF has been made for v3."),
    }
    core = core_count(deck, slides)
    v4 = {
        "version": "v4",
        "label": "Draft for feedback",
        "slides": len(slides),
        "core_slides": core,
        "appendix_slides": len(slides) - core,
        "path": DECK_HREF,
        "html_sha256": sha256(v4_html),
        "source": DECK_HREF + "source/",
        "claim_review": DECK_HREF + "source/claims.json",
        "unbranded": True,
        "downloads": [pdf] if pdf else previous.get("v4", {}).get("downloads", []),
    }
    data["versions"] = [v for v in data["versions"] if v["version"] not in {"v3", "v4"}] + [v3, v4]
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


# PDF --------------------------------------------------------------------------------------------

def render_pdf(v4_sha: str) -> dict:
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
    out = V4_DIR / PDF_NAME
    try:
        with sync_playwright() as p:
            launch = {"executable_path": os.environ["CHROMIUM_PATH"]} if os.environ.get("CHROMIUM_PATH") else {}
            browser = p.chromium.launch(**launch)
            page = browser.new_page(viewport={"width": CANVAS_W, "height": CANVAS_H})
            page.goto(f"http://127.0.0.1:{server.server_port}/{DECK_HREF}", wait_until="networkidle")
            page.emulate_media(media="print")
            page.evaluate("document.fonts.ready")
            missing = page.evaluate("""() => ['Space Grotesk', 'IBM Plex Sans', 'JetBrains Mono']
                .filter(f => !document.fonts.check('16px "' + f + '"'))""")
            if missing:
                fail("web fonts did not load: " + ", ".join(missing))
            page.evaluate("document.title = 'ta-amps deck v4, a draft for feedback (October 29, 2026)'")
            page.pdf(path=str(out), prefer_css_page_size=True, print_background=True, tagged=True, outline=False)
            browser.close()
    finally:
        server.shutdown()
    data = out.read_bytes()
    return {"format": "pdf", "path": DECK_HREF + PDF_NAME, "sha256": sha256(data), "bytes": len(data),
            "printed_from_html_sha256": v4_sha}


# Main ---------------------------------------------------------------------------------------------

def pages() -> list[Path]:
    frozen = {DECKS / "v1" / "index.html", V2_PAGE, V3_PAGE, V4_PAGE} | STANDALONE
    return sorted(p for p in SITE.rglob("*.html")
                  if "source" not in p.relative_to(SITE).parts and p not in frozen)


def build(check: bool, pdf: bool) -> list[str]:
    deck, slides, updates, claims = deck_sources()
    outputs: dict[Path, str] = {}
    outputs[V3_PAGE] = render_v3()
    outputs[V4_PAGE] = render_page(V4_PAGE, render_deck(deck, slides, updates, claims))
    for page in pages():
        outputs[page] = render_page(page, page.read_text(encoding="utf-8"))
    v4_bytes = outputs[V4_PAGE].encode("utf-8")
    pdf_entry = None
    if pdf and not check:
        V4_PAGE.write_text(outputs[V4_PAGE], encoding="utf-8")
        pdf_entry = render_pdf(sha256(v4_bytes))
    outputs[MANIFEST] = manifest_text(outputs[V3_PAGE].encode("utf-8"), v4_bytes, deck, slides, pdf_entry)

    stale = []
    for path, text in outputs.items():
        current = path.read_text(encoding="utf-8") if path.exists() else None
        if current != text:
            stale.append(path.relative_to(ROOT).as_posix())
            if not check:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding="utf-8")
    entry = json.loads(outputs[MANIFEST])
    v4 = next(v for v in entry["versions"] if v["version"] == "v4")
    if not v4["downloads"]:
        stale.append(DECK_HREF + PDF_NAME + " (missing; run --pdf)")
    for download in v4["downloads"]:
        if download.get("printed_from_html_sha256") != v4["html_sha256"]:
            stale.append(download["path"] + " (printed from an older deck page; run --pdf)")
    return stale


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--check", action="store_true", help="report stale outputs without writing")
    parser.add_argument("--pdf", action="store_true", help="also render the v4 deck PDF")
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
