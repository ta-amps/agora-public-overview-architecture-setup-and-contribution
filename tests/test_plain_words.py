"""Owner, October 31, 2026: "DO NOT INCLUDE SYNTHETIC." Crawl everything Agora serves as text and fail on the word.

Pages and nouns say what was made up, and which tests and tasks we wrote, in plain words. The few places that keep
the word are listed below with the reason each cannot change on Agora's side; every other hit fails.
"""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

SITE = Path(__file__).resolve().parents[1] / "site"
WORD = re.compile(r"synthetic", re.I)
TEXT = {".html", ".txt", ".json", ".js", ".css", ".svg", ".md", ".xml", ".webmanifest"}

# Kept on purpose, each with its reason. Each entry is (path, exact count, reason).
KEPT = {
    # Eranos's verifier requires a visible SYNTHETIC mark on every fixture's sample_input; the Studio sends these
    # presets to the live /api/practice, so the mark stays until Eranos accepts a plain-words mark.
    "studio/studio.js": 6,
    # File names inside other hackathon projects' repositories, quoted as their scan found them.
    "content/ecosystem-catalog.json": 2,
    "library/index.html": 2,
}


def frozen() -> set[Path]:
    """Dated deck versions and pinned drafts: byte-identical history that the build never writes."""
    out = set()
    decks = json.loads((SITE / "decks.json").read_text(encoding="utf-8"))
    for version in decks["versions"]:
        out.add((SITE / version["path"]).resolve())
    drafts = json.loads((SITE / "content" / "earlier-drafts.json").read_text(encoding="utf-8"))
    for group in drafts["groups"]:
        for item in group["items"]:
            if "html_sha256" in item:
                out.add((SITE / item["href"]).resolve())
    return out


class PlainWords(unittest.TestCase):
    def test_nothing_agora_writes_says_synthetic(self):
        held = frozen()
        hits = {}
        for path in sorted(SITE.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in TEXT:
                continue
            rel = path.relative_to(SITE)
            if rel.parts[0] in {"evidence", "video"} and rel.name != "index.html":
                continue  # dated records and the films' own caption files, byte for byte as they were made
            if any(folder == path.resolve() or folder in path.resolve().parents for folder in held):
                continue
            count = len(WORD.findall(path.read_text(encoding="utf-8", errors="replace")))
            if count:
                hits[rel.as_posix()] = count
        unexpected = {p: n for p, n in hits.items() if KEPT.get(p) != n}
        self.assertEqual({}, unexpected)


if __name__ == "__main__":
    unittest.main()
