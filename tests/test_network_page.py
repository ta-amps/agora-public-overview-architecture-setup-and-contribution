"""The network page (/network/) and the Right now / Live capacity strips: built from their noun, light only, reading
Herma's GET /q/network and nothing else, with the land as a dot matrix and the projection the script uses. Drop into Agora's tests/."""

import importlib.util
import json
import math
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("build_site", ROOT / "scripts/build_site.py")
build = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(build)
SOURCE = "https://herma.teleionlabs.com/q/network"
COPY = ROOT.parents[2] / "coordination-2026-10-31" / "claude-design-copy.v1.json"  # beside this checkout in the working notes


def block(page: str, cls: str) -> dict:
    found = re.search(rf'<script type="application/json" class="{cls}">(.*?)</script>', page, re.S)
    return json.loads(found.group(1))


def equal_earth(lon: float, lat: float) -> tuple[float, float]:
    a1, a2, a3, a4, m = 1.340264, -0.081106, 0.000893, 0.003796, math.sqrt(3) / 2
    lam, phi = math.radians(lon), math.radians(lat)
    theta = math.asin(m * math.sin(phi))
    t2, t6 = theta * theta, theta ** 6
    return lam * math.cos(theta) / (m * (a1 + 3 * a2 * t2 + t6 * (7 * a3 + 9 * a4 * t2))), theta * (a1 + a2 * t2 + t6 * (a3 + a4 * t2))


class NetworkPage(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.nouns = build.Nouns()
        cls.outputs = build.outputs_for(cls.nouns)
        cls.page = cls.outputs[build.SITE / "network" / "index.html"]
        cls.words = cls.nouns.network_page
        cls.script = (build.SITE / "assets" / "network.js").read_text(encoding="utf-8")

    def test_the_page_is_light_only_and_runs_no_inline_code_of_its_own(self) -> None:
        self.assertEqual(1, self.page.count('<meta name="color-scheme" content="only light">'))
        css = (build.SITE / "assets" / "network.css").read_text(encoding="utf-8")
        self.assertIn("color-scheme: only light;", css)
        self.assertNotRegex(css, r"prefers-color-scheme\s*:\s*dark")
        main = self.page[self.page.index('<main id="main">'):self.page.index("</main>")]
        self.assertEqual([], re.findall(r"<script(?![^>]*(?:\ssrc=|type=\"application/json\"))[^>]*>", main))
        self.assertNotRegex(main, r"\son[a-z]+=|\sstyle=")
        self.assertEqual(1, self.page.count('<script src="../assets/network.js" defer></script>'))

    def test_it_reads_only_hermas_network_answer_and_keeps_nothing(self) -> None:
        self.assertEqual(SOURCE, self.words["source"])
        self.assertIn(f'data-source="{SOURCE}"', self.page)
        self.assertEqual(2, len(re.findall(r"\bfetch\(", self.script)))  # the source, and a data-geo file only off Agora
        self.assertEqual(2, self.script.count('credentials: "omit"'))
        self.assertIsNone(re.search(r"\b(XMLHttpRequest|sendBeacon|WebSocket|localStorage|sessionStorage)\b|\beval\s*\(|new Function", self.script))
        self.assertNotIn("cookie", self.script.lower())
        self.assertNotIn("innerHTML", self.script, "answers carry text written by workers and producers: it is only ever set as text")

    def test_every_word_comes_from_the_noun_and_the_answer_fills_the_rest(self) -> None:
        self.assertEqual({k: v for k, v in self.words.items() if k != "about"}, block(self.page, "nw-words"))
        for heading in (self.words["heading"], self.words["feed"]["title"], self.words["table"]["centers_caption"], self.words["how"]["heading"], self.words["eyebrow"]):
            self.assertIn(build.text(heading), self.page)
        self.assertNotIn("model_names", block(self.page, "nw-words"), "model names, cities and kinds come with the answer")
        self.assertIn(self.words["herma"]["contribution"], json.dumps(self.words))

    def test_the_copy_follows_the_design_contract_in_american_spelling(self) -> None:
        if not COPY.is_file():
            self.skipTest("the design copy contract sits beside this checkout in the working notes")
        agora = json.loads(COPY.read_text(encoding="utf-8"))["surfaces"]["agora"]
        us = lambda s: s.replace("data centres", "data centers").replace("Data centres", "Data centers").replace("data centre", "data center").replace("Data centre", "Data center")
        w = self.words
        pairs = {
            "network.h1": w["heading"], "network.lede": w["lead"], "network.replay": w["controls"]["replay"], "network.replay.stop": w["controls"]["replay_stop"],
            "network.pause": w["controls"]["pause"], "network.resume": w["controls"]["resume"], "network.table": w["controls"]["table"], "network.map": w["controls"]["map"],
            "network.legend.dc": w["legend"]["data_center"], "network.legend.continent": w["legend"]["continent"], "network.dc.card.note": w["data_center"]["card_note"],
            "network.dc.card.counts": w["data_center"]["card_counts"], "network.callout": w["callout"], "network.quiet": w["quiet"], "network.empty": w["empty"],
            "network.error": w["error"]["text"], "network.error.link": w["error"]["link"], "network.feed.title": w["feed"]["title"], "network.feed.title.quiet": w["feed"]["title_quiet"],
            "network.feed.row": w["feed"]["row"], "network.feed.row.continent": w["feed"]["row_continent"], "network.feed.model.declared": w["feed"]["model_declared"],
            "network.feed.model.none": w["feed"]["model_none"], "network.feed.who.volunteer": w["feed"]["who"]["volunteer"], "network.feed.who.dedicated": w["feed"]["who"]["dedicated"],
            "network.feed.place": w["feed"]["place"], "network.feed.place.none": w["feed"]["place_none"], "network.filter.label": w["filter"]["label"],
            "network.filter.all": w["filter"]["all"], "network.filter.nonprofit": w["filter"]["nonprofit"], "network.filter.shared": w["filter"]["shared"],
            "network.filter.check": w["filter"]["check"], "network.filter.own": w["filter"]["own"], "network.filter.none": w["filter"]["none"],
            "network.table.dc.caption": w["table"]["centers_caption"], "network.table.claims.caption": w["table"]["claims_caption"], "network.shown": w["shown"]["text"],
            "network.shown.link": w["shown"]["link"], "network.herma.link": w["shown"]["herma"], "network.dc.aria": w["data_center"]["aria"], "network.dc.card.title": w["data_center"]["card_title"],
        }
        for key, ours in pairs.items():
            theirs = us(agora[key]).replace("{data_centres}", "{data_centers}")
            self.assertEqual(theirs, ours.replace(" ↗", ""), key)
        self.assertEqual(us(agora["network.totals.big"]).replace("{data_centres}", "{data_centers}"), w["totals"]["big"])
        self.assertEqual(us(agora["network.totals.sub"]), w["totals"]["sub"])

    def test_the_land_is_a_dot_matrix_and_the_projection_is_the_one_the_script_uses(self) -> None:
        geo = block(self.page, "nw-geo")
        self.assertEqual({"viewbox", "projection", "continents"}, set(geo))
        self.assertRegex(self.page, r'<path class="nw-land" d="M[0-9Mmh. -]{5000,}"')
        # The constants in the page's geography are the Equal Earth numbers the script reads; the script's own coefficients match.
        for name, value in zip(("A1", "A2", "A3", "A4"), (1.340264, -0.081106, 0.000893, 0.003796)):
            self.assertRegex(self.script, rf"{name} = {re.escape(str(value))}")
        p = geo["projection"]
        self.assertAlmostEqual(equal_earth(180, 0)[0], p["x_max"], places=5)
        self.assertAlmostEqual(equal_earth(0, p["lat_max"])[1], p["y_top"], places=5)
        self.assertAlmostEqual(1000 / (2 * p["x_max"]), p["scale"], places=4)
        self.assertEqual([0, 0, p["width"], p["height"]], geo["viewbox"])
        self.assertEqual({"NA", "SA", "EU", "AF", "AS", "OC", "AN"}, set(geo["continents"]))
        for x, y in geo["continents"].values():
            self.assertTrue(0 <= x <= p["width"] and 0 <= y <= p["height"])
        self.assertNotRegex(json.dumps(geo), r"\b[0-9a-f]{12,}\b")

    def test_the_strips_are_the_same_map_in_a_small_box(self) -> None:
        for site, eyebrow in (("eranos", "Right now"), ("teleion", "Live capacity")):
            strip = build.network_strip(self.nouns, site)
            self.assertIn('data-mode="strip"', strip)
            self.assertIn(f'data-site="{site}"', strip)
            self.assertIn(build.text(eyebrow), strip)
            self.assertIn(f'href="{self.words["strip"]["href"]}"', strip)
            self.assertEqual(block(self.page, "nw-geo"), block(strip, "nw-geo"))


if __name__ == "__main__":
    unittest.main()
