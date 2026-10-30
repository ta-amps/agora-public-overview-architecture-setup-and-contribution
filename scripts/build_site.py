"""Build the static Agora site from its nouns. Stdlib only, except --pdf.

Everything a page says is a noun kept as data, and this script holds only markup:
  * site/agent-brief.txt              the starting brief for any agent, word for word;
  * site/content/site.json            navigation, the agent banner, the endpoints, deck labels, the footer;
  * site/content/home.json            the home page: the draft video, one sentence, the decks;
  * site/content/decks-page.json      the decks page;
  * site/content/use-cases.json       the use cases page;
  * site/content/earlier-drafts.json  earlier drafts, and the storyboards page;
  * site/content/moved.json           pages that moved, which the not-found page lists;
  * site/decks/<deck>/source/         each deck: deck.json, slides/*.html and an optional claims.json.

What it writes:
  * every current deck, site/decks/<deck>/index.html, from its source folder. The slide format's custom
    elements become HTML: <x-shape> and <x-icon> become inline SVG, <x-brief> the starting brief and
    <x-endpoints> the endpoint table. Each slide's <aside> becomes its speaker notes;
  * the home, decks, earlier drafts, storyboards, use cases and not-found pages;
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
PAGES_PREFIX = "/agora-public-overview-architecture-setup-and-contribution/"
CANVAS_W, CANVAS_H = 1920, 1080
CLAIM_STATUSES = {"measured", "pending", "planned"}

FONTS = ("https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700"
         "&family=JetBrains+Mono:wght@400;600&family=Space+Grotesk:wght@400..700&display=swap")

# Lucide icons (ISC license, see site/THIRD-PARTY-NOTICES.txt), the three the slides name.
ICONS = {
    "Users": ('<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><path d="M16 3.128a4 4 0 0 1 0 7.744"/>'
              '<path d="M22 21v-2a4 4 0 0 0-3-3.87"/><circle cx="9" cy="7" r="4"/>'),
    "Book": '<path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H19a1 1 0 0 1 1 1v18a1 1 0 0 1-1 1H6.5a1 1 0 0 1 0-5H20"/>',
    "ThumbsUp": ('<path d="M15 5.88 14 10h5.83a2 2 0 0 1 1.92 2.56l-2.33 8A2 2 0 0 1 17.5 22H4a2 2 0 0 1-2-2v-8'
                 'a2 2 0 0 1 2-2h2.76a2 2 0 0 0 1.79-1.11L12 2a3.13 3.13 0 0 1 3 3.88Z"/><path d="M7 10v12"/>'),
}

MARK = ('<svg width="28" height="28" viewBox="0 0 32 32" aria-hidden="true" focusable="false">'
        '<rect x="0" y="0" width="14" height="14" rx="3" fill="var(--color-noun)"/>'
        '<rect x="18" y="0" width="14" height="14" rx="3" fill="var(--color-verb)"/>'
        '<rect x="0" y="18" width="14" height="14" rx="3" fill="var(--color-rule-strong)"/>'
        '<rect x="18" y="18" width="14" height="14" rx="3" fill="var(--color-noun)"/></svg>')

# Plain shapes drawn for this site: a half-filled circle for light and dark, a terminal for agents,
# two sheets for copying and a chevron for showing more.
THEME_ICON = ('<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" focusable="false">'
              '<circle cx="12" cy="12" r="8.25" fill="none" stroke="currentColor" stroke-width="1.75"/>'
              '<path d="M12 3.75a8.25 8.25 0 0 1 0 16.5z" fill="currentColor"/></svg>')
TERMINAL = ('<svg class="agent-glyph" viewBox="0 0 28 28" width="28" height="28" aria-hidden="true" '
            'focusable="false"><rect x="1" y="3" width="26" height="22" rx="6" class="agent-glyph-box"/>'
            '<path d="M8 10.5l4 3.5-4 3.5" fill="none" class="agent-glyph-verb" stroke-width="2" '
            'stroke-linecap="round" stroke-linejoin="round"/><path d="M14.5 18h5.5" class="agent-glyph-noun" '
            'stroke-width="2" stroke-linecap="round"/></svg>')
COPY_ICON = ('<svg viewBox="0 0 20 20" width="16" height="16" aria-hidden="true" focusable="false">'
             '<rect x="6.5" y="6.5" width="10" height="10" rx="2" fill="none" stroke="currentColor" '
             'stroke-width="1.6"/><path d="M13.5 4.5v-.5a1.5 1.5 0 0 0-1.5-1.5H5A1.5 1.5 0 0 0 3.5 4v7A1.5 1.5 '
             '0 0 0 5 12.5h.5" fill="none" stroke="currentColor" stroke-width="1.6"/></svg>')
CHEVRON = ('<svg class="chevron" viewBox="0 0 16 16" width="14" height="14" aria-hidden="true" '
           'focusable="false"><path d="M4 6l4 4 4-4" fill="none" stroke="currentColor" stroke-width="1.75" '
           'stroke-linecap="round" stroke-linejoin="round"/></svg>')

MODE_SCRIPT = ('<script>try{var m=localStorage.getItem("ta-amps-mode");'
               'if(m==="dark"||m==="light")document.documentElement.dataset.mode=m}catch(e){}'
               'document.documentElement.classList.add("js")</script>')

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
        self.home = load_json(CONTENT / "home.json")
        self.decks_page = load_json(CONTENT / "decks-page.json")
        self.uses = load_json(CONTENT / "use-cases.json")
        self.film = load_json(CONTENT / "film.json")
        self.drafts = load_json(CONTENT / "earlier-drafts.json")
        self.moved = load_json(CONTENT / "moved.json")
        self.manifest = load_json(MANIFEST)
        self.brief = read_brief()
        self.frozen = frozen_pages(self.manifest, self.drafts)
        self.decks = [load_deck(deck_id, self.brief, self.site["endpoints"]) for deck_id in self.site["decks"]]


def frozen_pages(manifest: dict, drafts: dict) -> set[Path]:
    pages = {SITE / version["path"] / "index.html" for version in manifest["versions"]}
    for group in drafts["groups"]:
        pages |= {SITE / item["href"] / "index.html" for item in group["items"] if "html_sha256" in item}
    return pages


# Shared page chrome -------------------------------------------------------------------------------

def prefix_for(page: Path) -> str:
    if page.relative_to(SITE).as_posix() == "404.html":
        return PAGES_PREFIX  # GitHub Pages serves this page at any missing path, so its links are absolute.
    depth = len(page.relative_to(SITE).parts) - 1
    return "../" * depth


def link(prefix: str, target: str) -> str:
    return attr(prefix + target) if prefix + target else "./"


def section_for(page: Path) -> str:
    parts = page.relative_to(SITE).parts
    if parts == ("404.html",):
        return ""  # a missing page belongs to no section
    first = parts[0] if len(parts) > 1 else "home"
    return {"storyboards": "decks", "video": "decks", "film": "home"}.get(first, first)


def head_block(prefix: str) -> str:
    return "\n".join([
        '<link rel="preconnect" href="https://fonts.googleapis.com">',
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>',
        f'<link rel="stylesheet" href="{attr(FONTS)}">',
        f'<link rel="stylesheet" href="{prefix}assets/site.css">',
        f'<link rel="icon" href="{prefix}assets/mark.svg" type="image/svg+xml">',
        MODE_SCRIPT,
    ])


def header_block(page: Path, prefix: str, nouns: Nouns) -> str:
    site = nouns.site
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
        '<header class="site-header">',
        '<div class="wrap">',
        f'<a class="wordmark" href="{link(prefix, "")}">{MARK}<span>{text(site["name"])}</span></a>',
        '<nav class="site-nav" aria-label="Site">',
        "<ul>" + "".join(items) + "</ul>",
        "</nav>",
        f'<button class="mode-toggle" type="button" data-mode-toggle aria-pressed="false" '
        f'aria-label="{attr(site["mode_toggle"])}" hidden>{THEME_ICON}</button>',
        "</div>",
        "</header>",
        banner_block(prefix, nouns),
    ])


def banner_block(prefix: str, nouns: Nouns) -> str:
    """The agent banner: copy the starting brief, or show it with the machine endpoints."""
    banner, endpoints = nouns.site["banner"], nouns.site["endpoints"]["rows"]
    rows = "".join(
        f'<li><span class="agent-endpoint-name">{text(row["name"])}</span>'
        f'<code>{text(row["mcp"])}</code>'
        f'<a href="{attr(row["llms"])}" aria-label="{attr(row["name"] + " llms.txt")}">llms.txt</a></li>'
        for row in endpoints)
    return "\n".join([
        f'<aside class="agent-banner" aria-label="{attr(banner["label"])}" data-own-keys>',
        '<div class="wrap agent-row">',
        TERMINAL,
        f'<p class="agent-lead"><strong>{text(banner["lead_strong"])}</strong> {text(banner["lead"])}</p>',
        '<div class="agent-actions">',
        f'<button class="agent-copy" type="button" data-copy="agent-brief" data-copied="{attr(banner["copied"])}" '
        f'data-selected="{attr(banner["selected"])}" data-status-copied="{attr(banner["status_copied"])}" '
        f'data-status-selected="{attr(banner["status_selected"])}" data-reveal="agent-panel" hidden>'
        f'{COPY_ICON}<span>{text(banner["copy"])}</span></button>',
        f'<button class="agent-show" type="button" data-toggle="agent-panel" aria-expanded="false" '
        f'aria-controls="agent-panel" data-open="{attr(banner["hide"])}" data-closed="{attr(banner["show"])}" hidden>'
        f'<span>{text(banner["show"])}</span>{CHEVRON}</button>',
        f'<a class="agent-no-script" href="{link(prefix, banner["no_script_href"])}" data-no-script>'
        f'{text(banner["no_script"])}</a>',
        "</div>",
        "</div>",
        '<div class="agent-panel" id="agent-panel" hidden>',
        '<div class="wrap agent-panel-grid">',
        '<div class="agent-brief-col">',
        f'<p class="agent-panel-title" id="agent-brief-title">{text(banner["brief_label"])}</p>',
        f'<pre class="agent-brief" id="agent-brief" tabindex="0" aria-labelledby="agent-brief-title">'
        f'{text(nouns.brief)}</pre>',
        "</div>",
        '<div class="agent-side">',
        f'<p class="agent-panel-title">{text(banner["endpoints_title"])}</p>',
        f'<ul class="agent-endpoints">{rows}</ul>',
        f'<p class="agent-fine">{text(banner["fine_print"])} '
        f'<a href="{prefix}agent-brief.txt">{text(banner["plain_text"])}</a></p>',
        "</div>",
        "</div>",
        "</div>",
        '<p class="visually-hidden" id="agent-brief-status" role="status"></p>',
        "</aside>",
    ])


def footer_block(prefix: str, nouns: Nouns) -> str:
    footer = nouns.site["footer"]
    links = [f'<li><a href="{link(prefix, item["href"])}">{text(item["label"])}</a></li>' for item in footer["links"]]
    links += [f'<li><a href="{attr(prefix + item["href"]) if item.get("local") else attr(item["href"])}">'
              f'{text(item["label"])}</a></li>' for item in footer["outside"]]
    return "\n".join([
        '<footer class="site-footer">',
        '<div class="wrap">',
        '<nav aria-label="Footer">',
        "<ul>" + "".join(links) + "</ul>",
        "</nav>",
        f'<p>{text(footer["note"])}</p>',
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
    content = replace_block(content, "head", head_block(prefix), page)
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


def load_slide(source: Path, name: str, brief: str | None = None, endpoints: dict | None = None) -> dict:
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


def load_deck(deck_id: str, brief: str, endpoints: dict) -> dict:
    folder = DECKS / deck_id
    source = folder / "source"
    spec = load_json(source / "deck.json")
    order = spec["order"]
    if len(order) != len(set(order)):
        fail(f"{deck_id}: deck.json lists a slide twice")
    if spec.get("cover") != order[0]:
        fail(f"{deck_id}: the cover must be the first slide")
    slides = [load_slide(source, name, brief, endpoints) for name in order]
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
    ui = nouns.site["deck"] | {"copied": nouns.site["banner"]["copied"], "selected": nouns.site["banner"]["selected"]}
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
        f'<p class="wrap deck-help" data-help hidden>{ui["help_html"]}</p>',
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
    default = next((cut for cut in cuts if cut["id"] == videos["default"]), None)
    if default is None:
        fail(f"home.json: the default cut {videos['default']!r} is not one of the cuts")
    if len(cuts) < 2:
        return default, ""
    buttons = "".join(
        f'<button class="film-cut" type="button" aria-pressed="{"true" if cut is default else "false"}" '
        f'data-cut="{attr(cut["id"])}" data-src="{attr(cut["src"])}" data-type="{attr(cut["type"])}" '
        f'data-captions="{attr(cut["captions"])}" data-poster="{attr(cut["poster"])}" '
        f'data-title="{attr(cut["title"])}" data-label="{attr(cut["label"])}">{text(cut["tab"])}</button>'
        for cut in cuts)
    return default, f'<div class="film-cuts" role="group" aria-label="{attr(videos["choose"])}" data-film-cuts hidden>{buttons}</div>'


def render_home(nouns: Nouns) -> str:
    home, ui = nouns.home, nouns.site["deck"]
    videos = home["videos"]
    video, selector = film_cuts(videos)
    cards = "\n".join(deck_card(deck, "", ui, 3) for deck in nouns.decks)
    main = "\n".join(filter(None, [
        '<main id="main">',
        f'<section class="film{" has-cuts" if selector else ""}" aria-labelledby="film-label">',
        '<div class="film-stage">',
        f'<video class="film-video" controls playsinline preload="metadata" poster="{attr(video["poster"])}" '
        f'aria-label="{attr(video["title"])}" data-captions-default>',
        f'<source src="{attr(video["src"])}" type="{attr(video["type"])}">',
        f'<track kind="captions" src="{attr(video["captions"])}" srclang="{attr(videos["captions_lang"])}" '
        f'label="{attr(videos["captions_label"])}" default>',
        f'<p>{text(videos["fallback"])} <a href="{attr(video["src"])}">{text(videos["fallback_link"])}</a></p>',
        "</video>",
        "</div>",
        selector,
        f'<p class="film-label"><span id="film-label">{text(video["label"])}</span>'
        + (f' · <a href="{attr(videos["outline"]["href"])}">{text(videos["outline"]["label"])}</a>' if videos.get("outline") else "")
        + "</p>",
        "</section>",
        '<section class="statement" aria-labelledby="statement">',
        '<div class="wrap">',
        f'<h1 id="statement"><span class="statement-lead">{mark_kinds(home["statement"]["lead"])}</span> '
        f'<span class="statement-rest">{keep_together(text(home["statement"]["rest"]))}</span></h1>',
        "</div>",
        "</section>",
        '<section class="deck-band" aria-labelledby="home-decks">',
        '<div class="wrap">',
        f'<h2 class="band-title" id="home-decks">{text(home["decks_heading"])}</h2>',
        f'<ul class="deck-cards">\n{cards}\n</ul>',
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
        f'<p class="earlier-link"><a href="earlier-drafts/">{text(page["earlier"])}</a> '
        f'<span>{text(page["earlier_about"])}</span></p>',
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


def render_film(nouns: Nouns) -> str:
    """The full film's outline: its acts, and every narration line with its time and what is on screen."""
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
        page_head(film["heading"], film["lead"], ("../", film["crumb"])),
        '<div class="wrap film-outline">',
        "\n".join(sections),
        f'<p class="film-note">{text(film["note"])}</p>',
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


def use_terms(item: dict, uses: dict) -> str:
    return ('<dl class="use-terms">'
            f'<div><dt class="noun-word">{text(uses["nouns_label"])}</dt><dd>{chips(item["nouns"], "noun")}</dd></div>'
            f'<div><dt class="verb-word">{text(uses["verbs_label"])}</dt><dd>{chips(item["verbs"], "verb")}</dd></div>'
            "</dl>")


def render_use_cases(nouns: Nouns) -> str:
    uses = nouns.uses
    prefix = "../"
    flag = uses["flagship"]
    flag_links = "".join(
        f'<a class="button{" secondary" if n else ""}" href="{attr(item["href"]) if item["href"].startswith("https://") else prefix + attr(item["href"])}">'
        f'{text(item["label"])}</a>' for n, item in enumerate(flag["links"]))
    cards = [
        "\n".join([
            '<li class="use-card flagship">',
            '<div class="use-flag-text">',
            f'<p class="use-kicker">{text(flag["kicker"])}</p>',
            f'<h2>{text(flag["name"])}</h2>',
            f'<p class="use-line">{text(flag["line"])}</p>',
            f'<p class="use-links">{flag_links}</p>',
            "</div>",
            use_terms(flag, uses),
            "</li>",
        ])
    ]
    for idea in uses["ideas"]:
        tag = f'<p class="use-tag">{text(uses["public_label"])}</p>' if idea.get("public") else ""
        cards.append(f'<li class="use-card">{tag}<h2>{text(idea["name"])}</h2><p class="use-line">{text(idea["line"])}</p>'
                     f'{use_terms(idea, uses)}</li>')
    yours = uses["yours"]
    cards.append(f'<li class="use-card yours"><div><h2>{text(yours["name"])}</h2><p class="use-line">{text(yours["line"])}</p></div>'
                 f'<p class="use-links"><a class="use-yours-link" href="{prefix}{attr(yours["link"]["href"])}">'
                 f'{text(yours["link"]["label"])}{CHEVRON}</a></p></li>')
    main = "\n".join([
        '<main id="main">',
        page_head(uses["heading"], uses["lead"]),
        '<div class="wrap use-wrap">',
        '<ul class="use-grid">',
        "\n".join(cards),
        "</ul>",
        "</div>",
        "</main>",
    ])
    return page_shell(uses["title"], uses["description"], main)


def render_not_found(nouns: Nouns) -> str:
    moved = nouns.moved
    page = moved["not_found"]
    prefix = PAGES_PREFIX
    items = "".join(f'<li><a href="{prefix}{attr(item["to"])}">{text(item["what"])}</a> '
                    f'<span>{text(page["was"])} <code>{text(item["from"])}</code></span></li>'
                    for item in moved["pages"])
    main = "\n".join([
        '<main id="main">',
        '<div class="wrap page-head not-found">',
        f"<h1>{text(page['heading'])}</h1>",
        f'<p class="lead">{text(page["lead"])}</p>',
        '<div class="actions">',
        f'<a class="button" href="{prefix}">{text(page["home"])}</a>',
        f'<a class="button secondary" href="{prefix}decks/">{text(page["decks"])}</a>',
        "</div>",
        f'<h2 class="moved-title">{text(page["moved_heading"])}</h2>',
        f'<ul class="moved-list">{items}</ul>',
        "</div>",
        "</main>",
    ])
    return page_shell(page["title"], "", main, robots="noindex")


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
    generated[SITE / "404.html"] = render_not_found(nouns)
    if set(generated) & nouns.frozen:
        fail("a frozen page is never written")
    written = sorted(p for p in SITE.rglob("*.html")
                     if "source" not in p.relative_to(SITE).parts and p not in generated and p not in nouns.frozen)
    outputs = {path: render_page(path, content, nouns) for path, content in generated.items()}
    for path in written:
        outputs[path] = render_page(path, path.read_text(encoding="utf-8"), nouns)
    for path, content in outputs.items():
        unique_ids(path, content)
    return outputs


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
