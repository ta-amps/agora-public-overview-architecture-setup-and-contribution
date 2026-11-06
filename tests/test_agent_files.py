"""The files agents copy values from (QA sweep, Nov 6): connect.json, /.well-known/agent.json and /.well-known/mcp.json,
and the display rules for other makers' models and plain Task words."""
import json
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import build_site as build  # noqa: E402

SITE = Path(__file__).resolve().parent.parent / "site"
MCP = {"teleion-fabric": "https://fabric.teleionlabs.com/mcp", "teleion-fabric-shim": "https://shim.teleionlabs.com/mcp",
       "eranos": "https://eranosforgood.org/mcp"}
OLD = re.compile(r"tessera|herma|ta-amps\.workers\.dev|bearer|authorization", re.I)
# The build's own filter, and the one non-Meta voice model the catalog names (the page shows it as a general phrase).
OTHER_MAKER = build.OTHER_MAKER_MODEL
KOKORO = re.compile(r"\bKokoro\b", re.I)


def load(name):
    return json.loads((SITE / name).read_text(encoding="utf-8"))


class AgentFiles(unittest.TestCase):
    def test_mcp_lists_point_to_the_three_real_servers(self):
        for doc in (load("connect.json")["mcp"], load(".well-known/mcp.json")["mcpServers"]):
            self.assertEqual(MCP, {k: v["url"] for k, v in doc.items()})
            for v in doc.values():
                self.assertEqual("http", v["type"])
                self.assertTrue(v["description"].endswith("No key through December 31, 2026."))

    def test_no_auth_and_the_free_window_end(self):
        c = load("connect.json")
        self.assertEqual("none", c["authentication"])
        self.assertEqual("2026-12-31T23:59:59-05:00", c["free_until"])
        self.assertIn("11:59:59 PM Eastern on December 31, 2026", c["free_until_text"])
        self.assertEqual("none", load(".well-known/mcp.json")["authentication"])
        self.assertEqual(c["free_until"], load(".well-known/mcp.json")["free_until"])
        self.assertEqual(c["free_until"], load(".well-known/agent.json")["free_until"])
        card = load(".well-known/agent.json")
        self.assertFalse(card["authentication"]["required"])
        self.assertEqual("https://agora.eranosforgood.org/.well-known/mcp.json", card["mcp"])

    def test_agora_claims_no_mcp_of_its_own(self):
        for doc in (load("connect.json"), load(".well-known/mcp.json"), load(".well-known/agent.json")):
            text = json.dumps(doc)
            self.assertNotIn("agora.eranosforgood.org/mcp", text)
            self.assertIn("no MCP server of its own", text)

    def test_no_old_name_or_header(self):
        for name in ("connect.json", ".well-known/mcp.json", ".well-known/agent.json"):
            self.assertIsNone(OLD.search((SITE / name).read_text(encoding="utf-8")), name)

    def test_llms_txt_names_the_agent_files(self):
        llms = (SITE / "llms.txt").read_text(encoding="utf-8")
        for url in ("https://agora.eranosforgood.org/llms-full.txt", "https://agora.eranosforgood.org/connect.json",
                    "https://agora.eranosforgood.org/.well-known/agent.json",
                    "https://agora.eranosforgood.org/.well-known/mcp.json", "https://agora.eranosforgood.org/models.txt"):
            self.assertIn(url, llms)


class DisplayRules(unittest.TestCase):
    def visible(self, html):
        html = re.sub(r"<(script|style)\b.*?</\1>", " ", html, flags=re.S | re.I)
        return re.sub(r"<[^>]+>", " ", html)

    def test_models_page_names_no_other_makers_model(self):
        text = self.visible((SITE / "models" / "index.html").read_text(encoding="utf-8"))
        self.assertIsNone(OTHER_MAKER.search(text))
        self.assertIsNone(KOKORO.search(text))
        self.assertIn("A hosted fallback provider (switched off)", text)

    def test_feed_pages_name_no_other_makers_model(self):
        for page in (SITE / "feeds").glob("*/index.html"):
            self.assertIsNone(OTHER_MAKER.search(self.visible(page.read_text(encoding="utf-8"))), page)

    def test_studio_says_task_words(self):
        text = self.visible((SITE / "studio" / "index.html").read_text(encoding="utf-8"))
        self.assertIsNone(re.search(r"\b(noun|verb)\.[a-z_]+", text))
        self.assertNotIn("Anthropic", text)


if __name__ == "__main__":
    unittest.main()
