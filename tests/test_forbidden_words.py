"""Owner, Nov 1, 2026 (notes/claude-work-2026-10-31/PROMPT-NOV1-SHIP-DESIGNS.md and -v2.md): the words a reader sees.

A crawl of everything Agora serves as words fails on the owner's banned words: "synthetic"; "noun(s)" and "verb(s)"
(the work is Tasks and Task Objects); "receipt(s)", "sha256" and hashes (pages show people-readable facts and a "Record"
link); the stamps PLANNED, Not yet, Coming soon, Layout preview, Not ready yet and Idea; "prove" and its forms (claim,
do, report); the retired model family the owner no longer shows; nanoMuse outside /models/ (an agent app, not a
model); and "cloud" within five words of "dedicated".

What it reads, as a reader would meet it:
  * every HTML page: its text, the alt, title, aria-label and placeholder values, the meta description and social card
    text, and the prose strings of its JSON data blocks (the library explorer's cards, the agent banner);
  * llms.txt and agent-brief.txt;
  * every page Task Object (site/content/*.json) and the decks list, string values only.

What it leaves alone, each for its reason:
  * the October 29 drafts and other pages the bundle does not serve (UNSERVED below, as in the deploy tooling);
  * dated evidence records under evidence/<folder>/: served byte for byte as they were made, so only their receipt and
    hash fields are tolerated, and the model family and nouns-and-verbs prose are not (RECORDS below);
  * the deck sources, which are crawled as the deck pages they become;
  * code: inside <code>, <pre>, <kbd> and <samp>, and in kind names such as noun.persona or verb.build_agent_kit, API
    names such as search_nouns, and file names such as nouns.json, "noun" and "verb" are identifiers;
  * machine fields of the Task Objects (ids, kinds, addresses, paths, hashes) and third-party repository names;
  * the seed-pack library's exact repository name, which appears only in its addresses and clone commands.

Ownership, for now (the wording-sweep branch, November 1): the test fails only for the files that branch owns, listed in
MINE. A string that one of those pages shows from another builder's Task Object (the shared header and footer, or the
endpoints table a deck embeds from site.json) counts against that Task Object, which the crawl reads too. Every other
hit is printed as a known list for the builder who owns that file, to clear in their branch; the Agora builder tightens
this after merging by making OWNED_ONLY False.
"""
from __future__ import annotations

import html
import json
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
OWNED_ONLY = True

# Pages and files the deploy bundle does not serve (agora/deploy/build_bundle.py UNSERVED), plus the deck sources.
UNSERVED = ("decks/2026-10-29/", "decks/earlier-drafts/", "storyboards/", "video/2026-10-29/", "downloads/",
            "content/earlier-drafts.json", "hub-3d/", "film/compare/")
RECORDS = "evidence/"  # evidence/<folder>/...; evidence/index.html is a page
# Files the wording-sweep branch owns: its pages, its Task Objects and the decks list.
MINE = {
    "evidence/index.html", "learning/index.html", "contribute/index.html", "library/index.html", "decks/index.html",
    "decks/overview-and-architecture/index.html", "decks/public-good-marketplace/index.html",
    "decks/roll-your-own/index.html", "decks/server-workers/index.html", "decks/continuous-learning/index.html",
    "404.html", "decks.json",
    "content/contribute.json", "content/decks-page.json", "content/ecosystem-catalog.json", "content/evidence.json",
    "content/explorer.json", "content/film.json", "content/learning.json", "content/library.json", "content/moved.json",
}

REPO_NAME = "seed-packs-library-of-nouns-and-verbs"
WORD = re.compile(r"[A-Za-z0-9']+")
PATTERNS = {
    "synthetic": re.compile(r"synthetic", re.I),
    "noun": re.compile(r"\bnouns?\b", re.I),
    "verb": re.compile(r"\bverbs?\b", re.I),
    "receipt": re.compile(r"receipt", re.I),
    "sha256": re.compile(r"sha-?256", re.I),
    "hash": re.compile(r"(?<![0-9A-Za-z])[0-9a-fA-F]{12,}(?![0-9A-Za-z])"),
    "short hash": re.compile(r"(?<![0-9A-Za-z#])(?=[0-9a-f]*[0-9])(?=[0-9a-f]*[a-f])[0-9a-f]{7,11}(?![0-9A-Za-z])"),
    "PLANNED": re.compile(r"\bPLANNED\b"),
    "not yet": re.compile(r"\bnot yet\b", re.I),
    "coming soon": re.compile(r"\bcoming soon\b", re.I),
    "layout preview": re.compile(r"\blayout preview\b", re.I),
    "not ready yet": re.compile(r"\bnot ready yet\b", re.I),
    "Idea": re.compile(r"\bIdeas?\b"),
    "prove": re.compile(r"\bprov(?:e|es|ed|ing|en)\b", re.I),
    "retired model family": re.compile(r"l[l]ama", re.I),  # written so that this file itself never says it
    "nanoMuse": re.compile(r"nano\s*muse", re.I),
}
NOUN_VERB = ("noun", "verb")
# Identifiers that keep "noun" and "verb": kind names (noun.persona, verb.build_agent_kit, noun:harness.feed),
# file names (nouns.json) and anything joined with an underscore (search_nouns), which \b already skips.
IDENTIFIER = re.compile(r"\b(?:nouns?|verbs?)(?:[.:][\w.:-]+)|[\w./-]*\w\.(?:json|jsonl|md|txt|py|js|html|css|svg|csv|pdf|ya?ml|toml|sh)\b",
                        re.I)
MACHINE_KEYS = {"id", "ids", "kind", "href", "url", "link", "path", "paths", "src", "anchor", "file", "files", "slide",
                "status", "category", "category_id", "ceiling", "harnesses", "pack_id", "packs", "repo", "record", "body",
                "captions", "poster", "section", "type", "schema", "source_kind", "evidence_href", "requires", "same_as",
                "served", "repository", "commit", "tessera_commit", "committed_at", "workflow", "endpoint", "checked_utc",
                "started_utc", "checked_at", "date", "as_of", "code_id", "tone", "subtype", "format", "provenance",
                "generated_on", "clean_src", "llms", "mcp", "main", "version", "versions", "downloads"}


def dedicated_cloud(text: str) -> int:
    words = [w.lower() for w in WORD.findall(text)]
    dedicated = [i for i, w in enumerate(words) if w == "dedicated"]
    return sum(1 for i, w in enumerate(words) if w in ("cloud", "clouds") and any(abs(i - d) <= 5 for d in dedicated))


class Visible(HTMLParser):
    """The words of one page as a reader meets them, in two piles: prose, and code (pre, code, kbd, samp)."""
    CODE = {"pre", "code", "kbd", "samp"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.prose: list[str] = []
        self.code: list[str] = []
        self.data: list[str] = []
        self.stack: list[str] = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        for key in ("alt", "title", "aria-label", "placeholder"):
            if values.get(key):
                self.prose.append(values[key])
        if tag == "meta" and values.get("content") and (
                values.get("name") in ("description", "twitter:title", "twitter:description")
                or (values.get("property") or "").startswith("og:")):
            self.prose.append(values["content"])
        if tag in ("script", "style"):
            self.stack.append(tag + ("+json" if "json" in (values.get("type") or "") else ""))
        elif tag in self.CODE:
            self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag in ("script", "style") or tag in self.CODE:
            self.stack.pop()

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i].split("+")[0] == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        if not self.stack:
            self.prose.append(data)
        elif self.stack[-1] == "script+json":
            self.data.append(data)
        elif self.stack[-1] in self.CODE:
            self.code.append(data)


def strings_of(value, key: str = "") -> list[str]:
    """The prose strings of a Task Object: every string except machine fields and hash fields."""
    if isinstance(value, dict):
        return [s for k, v in value.items() for s in strings_of(v, k)]
    if isinstance(value, list):
        return [s for v in value for s in strings_of(v, key)]
    if isinstance(value, str) and key not in MACHINE_KEYS and not key.endswith(("sha256", "_hash", "_href", "_url")):
        return [value]
    return []


def count(text: str, code: bool = False) -> dict[str, int]:
    text = html.unescape(text).replace(REPO_NAME, " ")
    plain = IDENTIFIER.sub(" ", text)
    hits = {}
    for name, pattern in PATTERNS.items():
        if code and name in NOUN_VERB:
            continue
        found = len(pattern.findall(plain if name in NOUN_VERB or name == "receipt" else text))
        if found:
            hits[name] = found
    cloud = dedicated_cloud(text)
    if cloud:
        hits["cloud near dedicated"] = cloud
    return hits


def merge(into: dict, more: dict) -> None:
    for key, value in more.items():
        into[key] = into.get(key, 0) + value


def others() -> set[str]:
    """The prose strings of the Task Objects other builders own, so that a page of MINE that shows one does not count
    it twice: the crawl counts it against its own Task Object."""
    out = set()
    for path in sorted((SITE / "content").glob("*.json")):
        rel = path.relative_to(SITE).as_posix()
        if rel not in MINE and not rel.startswith(UNSERVED):
            out |= {" ".join(s.split()) for s in strings_of(json.loads(path.read_text(encoding="utf-8")))}
    return out


def read(rel: str, path: Path, skip: frozenset[str] = frozenset()) -> dict[str, int]:
    hits: dict[str, int] = {}
    if path.suffix == ".html":
        page = Visible()
        page.feed(path.read_text(encoding="utf-8"))
        for text in page.prose:
            if " ".join(html.unescape(text).split()) in skip:
                continue
            merge(hits, count(text))
        for text in page.code:
            merge(hits, count(text, code=True))
        for blob in page.data:
            try:
                data = json.loads(blob)
            except ValueError:
                merge(hits, count(blob))
                continue
            for text in strings_of(data):
                merge(hits, count(text))
    elif path.suffix == ".txt":
        merge(hits, count(path.read_text(encoding="utf-8")))
    elif path.suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        if rel == "decks.json":
            data = {key: value for key, value in data.items() if key != "versions"}  # the frozen drafts' entries
        for text in strings_of(data):
            merge(hits, count(text))
    return allowed(rel, hits)


def allowed(rel: str, hits: dict[str, int]) -> dict[str, int]:
    if rel.startswith("models/"):
        hits = {k: v for k, v in hits.items() if k != "nanoMuse"}  # agent apps are named on Models used, and only there
    return hits


def crawl() -> dict[str, dict[str, int]]:
    found, skip = {}, frozenset(others())
    for path in sorted(SITE.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(SITE).as_posix()
        if rel.startswith(UNSERVED) or "/source/" in f"/{rel}" or rel.startswith(RECORDS) and rel != "evidence/index.html":
            continue
        if path.suffix == ".html" or rel in ("llms.txt", "agent-brief.txt") or rel == "decks.json" \
                or rel.startswith("content/") and path.suffix == ".json":
            hits = read(rel, path, skip if rel in MINE else frozenset())
            if hits:
                found[rel] = hits
    return found


def records() -> dict[str, dict[str, int]]:
    """Dated evidence records: only their receipt and hash fields are tolerated."""
    found = {}
    for path in sorted((SITE / RECORDS).rglob("*")):
        rel = path.relative_to(SITE).as_posix()
        if not path.is_file() or rel == "evidence/index.html" or path.suffix not in (".json", ".md", ".txt", ".csv", ".jsonl"):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        hits = {name: len(pattern.findall(IDENTIFIER.sub(" ", text) if name in NOUN_VERB else text))
                for name, pattern in PATTERNS.items() if name in ("retired model family", "nanoMuse")}
        hits = {k: v for k, v in hits.items() if v}
        if hits:
            found[rel] = hits
    return found


class ForbiddenWords(unittest.TestCase):
    def test_nothing_agora_serves_says_a_banned_word(self):
        found = crawl()
        found.update(records())
        mine = {rel: hits for rel, hits in found.items() if rel in MINE}
        known = {rel: hits for rel, hits in found.items() if rel not in MINE}
        if known:
            print("\nKnown, in files other builders own (clear them in their branches):")
            for rel, hits in sorted(known.items()):
                print(f"  {rel}: " + ", ".join(f"{name} {n}" for name, n in sorted(hits.items())))
        self.assertEqual({}, mine if OWNED_ONLY else found)

    def test_the_crawl_finds_what_it_must(self):
        # The crawl reads what a reader reads: a banned word in each place it looks is found, and code is not prose.
        self.assertEqual({"noun": 1}, count("A noun is a thing."))
        self.assertEqual({}, count("search_nouns, noun.persona, verb.build_agent_kit and nouns.json are names."))
        self.assertEqual({}, count("seed-packs-library-of-nouns-and-verbs"))
        self.assertEqual({}, count("verbs", code=True))
        self.assertEqual({"receipt": 1}, count("every step gets a receipt"))
        self.assertEqual({}, count("production-receipts.json"))
        self.assertEqual({"hash": 1}, count("cdb6aa2fdee9e79cd183672a03e8f4006d49d89b"))
        self.assertEqual({"short hash": 1}, count("merge commit edab4d7"))
        self.assertEqual({}, count("#2A5DB0 and EDC16C39"))
        self.assertEqual({"cloud near dedicated": 1}, count("a dedicated worker in the cloud"))
        self.assertEqual({}, count("a dedicated worker run by ta-amps, far from any talk of clouds in the sky above"))
        self.assertEqual({"Idea": 1, "not yet": 1}, count("Idea: not yet"))
        self.assertEqual({"prove": 2}, count("Prove it, and it is proven."))
        page = Visible()
        page.feed('<p title="a verb">x</p><pre>nouns</pre><script type="application/json">{"a": "receipt"}</script>')
        self.assertEqual(["a verb", "x"], page.prose)
        self.assertEqual(["nouns"], page.code)
        self.assertEqual({}, allowed("models/index.html", {"nanoMuse": 1}))
        self.assertEqual({"nanoMuse": 1}, allowed("index.html", {"nanoMuse": 1}))


if __name__ == "__main__":
    unittest.main()
