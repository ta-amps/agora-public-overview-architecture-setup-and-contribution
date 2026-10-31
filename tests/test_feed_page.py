"""The memory-systems feed page and the decks' feed line, from the feed's data noun (October 31, 2026)."""
from __future__ import annotations

import copy
import re
import unittest

from test_build_site import build


class Feed(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nouns = build.Nouns()

    def page(self, nouns=None):
        return build.render_feed(nouns or self.nouns)

    def hosted(self):
        nouns = copy.copy(self.nouns)
        nouns.feed = copy.deepcopy(self.nouns.feed)
        nouns.feed["source"]["hosted"] = True
        return nouns

    def test_the_page_says_where_and_when_it_scanned_and_never_calls_a_local_scan_live(self):
        feed, words = self.nouns.feed, self.nouns.feed_words
        page = self.page()
        self.assertIn(feed["last_run"]["at"], page)
        self.assertIn(feed["last_run"]["receipt_hash"][:12], page)
        self.assertIn(feed["count"]["query"], page)
        if not build.feed_hosted(feed):
            self.assertIn(words["where_local"], page)
            self.assertNotIn(words["schedule"], page)  # no schedule until the scans run on hosted Tessera
            self.assertNotIn("every 6 hours", page)
        hosted = self.page(self.hosted())
        self.assertIn(words["where_hosted"], hosted)
        self.assertIn(feed["last_run"]["schedule"], hosted)

    def test_every_quoted_claim_links_its_own_source(self):
        page = self.page()
        for claim in self.nouns.feed["claims"]:
            self.assertIn(f'<a href="{build.attr(claim["url"])}">', page)
            self.assertIn(f'<q>{build.text(claim["quote"])}</q>', page)

    def test_the_decks_name_the_feed_schedule_only_once_its_scans_are_hosted(self):
        def lines(feed):
            deck = build.load_deck("server-workers", self.nouns.brief, self.nouns.site["endpoints"], feed)
            return [s["name"] for s in deck["slides"] if "memory-systems feed runs" in s["inner"]]
        expected = ["on-its-own", "status"] if build.feed_hosted(self.nouns.feed) else []
        self.assertEqual(expected, lines(self.nouns.feed))
        self.assertEqual(["on-its-own", "status"], lines(self.hosted().feed))

    def test_the_feed_noun_is_the_builders_file_byte_for_byte_shape(self):
        feed = self.nouns.feed
        self.assertEqual("ta-amps.agora.feeds.memory-systems.v1", feed["schema"])
        self.assertRegex(feed["last_run"]["receipt_hash"], r"^[0-9a-f]{64}$")
        self.assertEqual(feed["item_count"], len(feed["items"]))


if __name__ == "__main__":
    unittest.main()
