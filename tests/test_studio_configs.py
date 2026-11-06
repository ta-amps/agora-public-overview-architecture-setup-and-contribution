"""The copy-paste configs on /studio/ that agents read (review of 1fe2723, Nov 6): public hosts only, no key asked for,
and no old product name in what the page shows. Static: reads site/studio/ with no browser and no network."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

STUDIO = Path(__file__).resolve().parents[1] / "site" / "studio"
JS = (STUDIO / "studio.js").read_text(encoding="utf-8")
HTML = (STUDIO / "index.html").read_text(encoding="utf-8")
OLD = re.compile(r"tessera(?!ct)|herma", re.I)
# Identifiers that stay (headers the shim reads, element ids, internal keys): never shown as words.
KEPT = re.compile(r"X-Herma-Harness|\b(?:node|stat|edge-[a-z]+)-(?:tessera|herma)\b|herma-last-metric", re.I)


def block(name: str) -> str:
    """The template literal that starts at `name: \``."""
    start = JS.index(name + ": `") + len(name) + 3
    return JS[start:JS.index("`", start)]


class StudioConfigs(unittest.TestCase):
    def test_endpoints_are_the_public_hosts(self):
        self.assertIn('tessera: "https://fabric.teleionlabs.com"', JS)
        self.assertIn('herma: "https://shim.teleionlabs.com"', JS)

    def test_harness_configs_ask_for_no_key_and_use_public_hosts(self):
        configs = JS[JS.index("const HARNESS_CONFIGS = {"):]
        configs = configs[:configs.index("\n  };")]
        urls = re.findall(r"https://[a-z0-9.-]+\.[a-z]+[^\s\"'`]*", configs)
        self.assertTrue(urls)
        for url in [u for u in urls if u != "https://opencode.ai/config.json"]:  # the schema line
            self.assertRegex(url, r"^https://(fabric\.teleionlabs\.com|shim\.teleionlabs\.com|eranosforgood\.org)/")
        self.assertNotRegex(configs, r"(?i)authorization|bearer|_TOKEN")
        muse = json.loads(block("muse"))
        self.assertEqual({"teleion-fabric", "teleion-fabric-shim", "eranos"}, set(muse["mcpServers"]))
        self.assertNotIn("headers", muse["mcpServers"]["teleion-fabric"])

    def test_no_old_name_in_shown_text(self):
        html = re.sub(r"(?s)<!--.*?-->", " ", HTML)
        html = re.sub(r"\b(?:id|class|for|data-[a-z-]+)=\"[^\"]*\"", " ", html)
        self.assertEqual([], OLD.findall(KEPT.sub(" ", re.sub(r"<[^>]+>", " ", html))))
        code = re.sub(r"/\*.*?\*/", " ", JS, flags=re.S)
        strings = re.findall(r'"(?:[^"\\\n]|\\.)*"|\'(?:[^\'\\\n]|\\.)*\'|`[^`]*`', code)
        shown = [s for s in strings if OLD.search(KEPT.sub(" ", s)) and s.strip("\"'") not in ("tessera", "herma")
                 and not re.fullmatch(r"[\"'][a-z0-9_.-]+[\"']", s)]
        self.assertEqual([], [s for s in shown if not re.search(r"thermal", s, re.I)])


if __name__ == "__main__":
    unittest.main()
