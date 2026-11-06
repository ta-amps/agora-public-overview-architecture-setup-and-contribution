"""Nov 6: the decks, the brief and the status page use the current addresses, ask for no key, and the old home Worker
(now a redirect) is not checked or linked as a service."""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"


class CurrentAddresses(unittest.TestCase):
    def test_deck_sources_and_brief_name_no_old_address_or_bearer(self):
        files = sorted((SITE / "decks").glob("*/source/slides/*.html")) + [SITE / "agent-brief.txt"]
        for path in files:
            text = path.read_text(encoding="utf-8")
            for bad in ("home.ta-amps", "Bearer", "Authorization", "SESSION_OR_API_KEY"):
                self.assertNotIn(bad, text, f"{path.relative_to(ROOT)}: {bad}")

    def test_roll_your_own_says_no_key_is_needed_and_names_no_internal_words(self):
        deck = (SITE / "decks" / "roll-your-own" / "index.html").read_text(encoding="utf-8")
        self.assertIn('{"mcpServers":{"teleion-fabric":{"type":"http","url":"https://fabric.teleionlabs.com/mcp"}}}', deck)
        self.assertIn("December 31, 2026", deck)
        main = re.sub(r"<[^>]+>", " ", deck.split('<main', 1)[1])
        self.assertIsNone(re.search(r"\b(?:nouns?|verbs?)\b", re.sub(r"https?://\S+", "", main), re.I))

    def test_status_page_checks_the_canonical_hosts(self):
        words = json.loads((SITE / "content" / "status-page.json").read_text(encoding="utf-8"))
        hosts = {s["host"] for s in words["services"]}
        self.assertEqual({"eranosforgood.org", "agora.eranosforgood.org", "fabric.teleionlabs.com", "shim.teleionlabs.com",
                          "teleionlabs.com"}, hosts)
        self.assertNotIn("home.ta-amps", json.dumps(words))


if __name__ == "__main__":
    unittest.main()
