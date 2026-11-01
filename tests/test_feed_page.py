"""The feeds pages and the decks' feed line, from the dedicated workers' feed data (the AgoraFeeds board, November 1).

The data is copied byte for byte into site/content/feeds/; the pages say where and when each category ran, date the
feed rank, mark quoted numbers as self-reported by the project, and leave out, and count, every third-party entry the
owner's rules keep off the pages. Offline."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("build_site_feed", ROOT / "scripts/build_site.py")
build = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(build)

# The dedicated workers' files as their builder recorded them (functional/builds/memory-feed/REVIEW-MANIFEST.json).
BUILDER_FILES = {
    "agent-harnesses.json": "2fb85d862a866c40d3731bfa4ff1a91cc88e5805ab7e0ec0a0748a8bdc90d163",
    "eval-frameworks.json": "016c6835bba80134c11344978243ed50c70f0106dbd38cf47e55c923c484151f",
    "index.json": "93e803b2dfbe31ea83b290bbc6cbf3559265a52559c6097863975be206e27b2b",
    "memory-systems.json": "f75e2bfa7dd2079ff3cc0b92f4c2e2a47376fd28c1f105693016c984feccb5e5",
    "ocr-llm.json": "e00ee5086214f8e9f6a31c339201ad247f3687da1b5a9561bb4adfd331c3b9bb",
    "pii-redaction.json": "c6369f95418d611d75ed505b253f6b76ff288be99dc32ded1ac4447beb9d1d2f",
}


class Shown(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.text: list[str] = []
        self.hrefs: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1
        self.hrefs += [value for name, value in attrs if name == "href"]

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip and data.strip():
            self.text.append(data.strip())


def shown(page: str) -> Shown:
    parser = Shown()
    parser.feed(build.main_of(page))
    return parser


class Feeds(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nouns = build.Nouns()
        cls.outputs = build.outputs_for(cls.nouns)

    def page(self, key: str | None = None) -> str:
        path = build.SITE / "feeds" / (f"{key}/index.html" if key else "index.html")
        return self.outputs[path]

    def test_the_data_is_the_dedicated_workers_files_byte_for_byte(self):
        for name, digest in BUILDER_FILES.items():
            self.assertEqual(digest, hashlib.sha256((build.FEEDS / name).read_bytes()).hexdigest(), name)
        self.assertEqual(sorted(BUILDER_FILES), sorted(p.name for p in build.FEEDS.iterdir()))

    def test_a_category_appears_only_after_its_first_run(self):
        ran = build.ran_feeds(self.nouns)
        self.assertEqual(5, len(ran))
        for row in ran:
            self.assertIn(build.SITE / "feeds" / row["id"] / "index.html", self.outputs)
        index = shown(self.page())
        for row in ran:
            self.assertIn(f'{row["id"]}/', index.hrefs)
        # A category without a recorded run is left out of the index and gets no page.
        nouns = copy.copy(self.nouns)
        nouns.feeds_index = copy.deepcopy(self.nouns.feeds_index)
        nouns.feeds_index["categories"][0]["last_run"] = {}
        self.assertNotIn(f'href="{nouns.feeds_index["categories"][0]["id"]}/"', build.render_feeds_index(nouns))
        # The memory-systems feed keeps its address.
        self.assertIn(build.SITE / "feeds" / "memory-systems" / "index.html", self.outputs)

    def test_each_page_says_where_and_when_it_ran_and_dates_the_feed_rank(self):
        words = self.nouns.feed_words["category"]
        for row in build.ran_feeds(self.nouns):
            feed = self.nouns.feeds[row["id"]]
            page = self.page(row["id"])
            text = " ".join(shown(page).text)
            self.assertIn(f'datetime="{feed["last_run"]["at"]}"', page)
            where = words["facts"]["where_hosted"] if build.feed_hosted(feed) else words["facts"]["where_local"]
            self.assertIn(build.text(where), page)
            as_of = build.human_date(build.rank_date(feed))
            self.assertIn(f"Feed rank, as of {as_of}", text)
            self.assertIn(f"first in feed rank, as of {as_of}", text)
            self.assertIn(build.text(words["facts"]["who_text"]), page)
            self.assertIsNone(re.search(r"dedicated[^.]{0,40}\bcloud\b|\bcloud\b[^.]{0,40}dedicated", text, re.I), row["id"])
            self.assertIn(feed["count"]["query"], page)

    def test_quoted_numbers_are_self_reported_and_link_their_source(self):
        for row in build.ran_feeds(self.nouns):
            feed, page = self.nouns.feeds[row["id"]], self.page(row["id"])
            for claim in feed["claims"]:
                if not build.may_show(claim):
                    continue
                self.assertIn(f'<a href="{build.attr(claim["url"])}">', page)
                self.assertIn(f'<q>{build.text(claim["quote"])}</q>', page)
            if any(build.may_show(c) for c in feed["claims"]):
                self.assertIn("self-reported by the project", page)

    def test_left_out_entries_are_counted_and_none_is_shown(self):
        unshown = re.compile(r"llama|synthetic|receipt|nanomuse|muse[ -]?code|\bnouns?\b|\bverbs?\b", re.I)
        total = 0
        for row in build.ran_feeds(self.nouns):
            feed, page = self.nouns.feeds[row["id"]], self.page(row["id"])
            seen = shown(page)
            self.assertIsNone(unshown.search(" ".join(seen.text)), row["id"])
            for href in seen.hrefs:
                self.assertIsNone(unshown.search(href), (row["id"], href))
            n = build.left_out(feed)
            total += n
            if n:
                self.assertIn(f"{n:,} entr", " ".join(seen.text))
        self.assertGreater(total, 0)  # the run holds entries the rules keep off, and the pages say so
        # ocr-llm names run-llama/ParseBench; its page never does.
        self.assertIn("run-llama", (build.FEEDS / "ocr-llm.json").read_text(encoding="utf-8"))
        self.assertNotIn("run-llama", self.page("ocr-llm"))

    def test_no_page_shows_a_hash_or_a_receipt(self):
        hexes = re.compile(r"\b[0-9a-f]{12,}\b")
        for row in build.ran_feeds(self.nouns):
            feed, page = self.nouns.feeds[row["id"]], self.page(row["id"])
            text = " ".join(shown(page).text)
            self.assertIsNone(hexes.search(text), row["id"])
            self.assertNotIn(feed["last_run"]["receipt_hash"], page)
            self.assertNotIn(feed["count"]["response_sha256"], page)
            self.assertNotIn("receipt", text.lower())
        self.assertIsNone(hexes.search(" ".join(shown(self.page()).text)))

    def test_which_fits_is_a_light_card_and_never_a_rating(self):
        for page in [self.page()] + [self.page(r["id"]) for r in build.ran_feeds(self.nouns)]:
            self.assertIn('class="pg-card fd-which"', page)
            text = " ".join(shown(page).text).lower()
            self.assertNotIn("rating:", text)
        self.assertIn("We don't accept private information at this stage.", " ".join(shown(self.page()).text))

    def test_the_decks_name_the_feed_schedule_only_once_its_scans_are_hosted(self):
        def lines(feed):
            deck = build.load_deck("server-workers", self.nouns.brief, self.nouns.site["endpoints"], feed)
            return [s["name"] for s in deck["slides"] if "memory-systems feed runs" in s["inner"]]
        expected = ["on-its-own", "status"] if build.feed_hosted(self.nouns.feed) else []
        self.assertEqual(expected, lines(self.nouns.feed))
        hosted = copy.deepcopy(self.nouns.feed)
        hosted["source"]["hosted"] = True
        self.assertEqual(["on-its-own", "status"], lines(hosted))


if __name__ == "__main__":
    unittest.main()
