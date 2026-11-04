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
SOURCE = "https://shim.teleionlabs.com/q/network"
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
        us = lambda s: s.replace("Her" + "ma's", "the model shim's").replace("Her" + "ma", "Teleion Fabric's model shim").replace("Tess" + "era", "Teleion Fabric").replace("data centres", "data centers").replace("Data centres", "Data centers").replace("data centre", "data center").replace("Data centre", "Data center")
        # Our counts pick a singular or plural word ({n:one:many}, the lead, Nov 2); the contract writes the plural.
        plural = lambda s: re.sub(r"\{(\w+):[^:{}]*:([^:{}]*)\}", r"\2", s)
        w = json.loads(plural(json.dumps(self.words, ensure_ascii=False)))
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
        # The contract's words for these three still describe the old rule (2 workers in the window). Since Tessera
        # places each claim by who was there in the 15 minutes before it, the page says so; INTEGRATE.md lists them.
        reworded = {
            # The lead, Nov 2 (honesty): Herma marks every connected worker "volunteer", and many are run by our own team,
            # so the page says "Connected AI" until Herma tells them apart; Claude Design updates the contract.
            "network.feed.who.volunteer": "Connected AI",
            "network.lede": "Every worker reaches the shared queue through Cloudflare's network. Each dot is a data center where 2 or more workers were busy within 15 minutes of each other in the last 24 hours; the list shows what they claimed.",
            "network.dc.card.counts": "{workers} workers there together · {claims} Tasks claimed together there in the last 24 hours",
            "network.shown": "Shown: the Cloudflare data center each claim came through, the kind of Task, the model that ran and when. Never shown: IP addresses, where anyone lives, or anything else that identifies a person. A claim shows at its data center only when another worker had come through it in the 15 minutes before; otherwise it counts under the continent. Connected workers can turn this off.",
        }
        for key, ours in pairs.items():
            if key in reworded:
                self.assertEqual(reworded[key], ours, key)
                continue
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

    def test_it_reads_at_most_once_a_minute_and_keeps_the_legend_readable(self) -> None:
        # Review of 214a0afa (Nov 2), B2: one read a minute at most, from the noun and a floor in the code; a returning
        # tab waits out the minute; a 429 waits at least a minute; nothing reads while the tab is hidden.
        script = (ROOT / "site/assets/network.js").read_text(encoding="utf-8")
        self.assertGreaterEqual(self.words["refresh_seconds"], 60)
        self.assertIn("Math.max(60, num(this.words.refresh_seconds) || 60) * 1000", script)
        self.assertIn("const wait = Math.min(Math.max(60, seconds || 0), 3600);", script)  # a minute to an hour
        self.assertIn("if (since >= self.refresh) self.load(); else self.schedule(self.refresh - since);", script)
        self.assertIn("if (document.hidden) { clearTimeout(self.timer); self.timer = 0; return; }", script)
        self.assertNotRegex(json.dumps(self.words), r"every 30 seconds")
        # Singular forms wherever a count is shown (1 worker, 1 Task, 1 data center, 1 continent), filled by the script.
        self.assertIn("if (one !== undefined) return Number(values[key]) === 1 ? one : many;", script)
        for template, forms in ((self.words["totals"]["big"], ("{workers:worker:workers}", "{data_centers:data center:data centers}")),
                                (self.words["totals"]["sub"], ("{continents:continent:continents}", "{claims:Task:Tasks}")),
                                (self.words["data_center"]["card_counts"], ("{workers:worker:workers}", "{claims:Task:Tasks}")),
                                (self.words["map_aria"]["some"], ("{claims:Task:Tasks}",))):
            for form in forms:
                self.assertIn(form, template)
        self.assertIn('make("h2", "nw-card-title"', script)  # the open card's title sits under the page's h1
        self.assertIn("fill(this.words.map_aria.center, { city: c.city, workers: c.workers })", script)
        self.assertIn("{workers:worker:workers}", self.words["map_aria"]["center"])
        # After 3 not-found answers in a row it reads on its own every 5 minutes, and the first success resets that.
        self.assertIn("const MISSES_BEFORE_BACKOFF = 3, BACKOFF_MS = 5 * 60 * 1000;", script)
        self.assertIn("self.misses = (self.misses || 0) + 1;", script)  # any failed read: 4xx, 5xx, network or CORS
        self.assertIn("const backoff = self.misses >= MISSES_BEFORE_BACKOFF ? BACKOFF_MS : 0;", script)
        self.assertIn("self.schedule(Math.max(self.refresh, backoff));", script)
        self.assertIn('if (response.status === 429 || (response.status === 503 && retry)) {', script)
        self.assertIn("self.misses = 0;  // the first success ends any back-off", script)
        # B1: the failed state dims only the map stage; the legend keeps its full contrast.
        css = (ROOT / "site/assets/network.css").read_text(encoding="utf-8")
        self.assertIn(".nw[data-failed] .nw-stage { opacity: 0.75; }", css)
        self.assertNotIn(".nw[data-failed] .nw-map {", css)

    def test_rows_herma_marks_volunteer_never_say_volunteer(self) -> None:
        # The lead, Nov 2: Herma sends worker_kind "volunteer" for every connected worker, and many are our own team's
        # agents, so nothing the page shows for such rows says "volunteer": the chip is "Connected AI", the rules line
        # and the map note are neutral, and the script maps any other worker_kind to that same chip.
        self.assertEqual("Connected AI", self.words["feed"]["who"]["volunteer"])
        self.assertEqual("Dedicated worker", self.words["feed"]["who"]["dedicated"])
        self.assertNotRegex(json.dumps(self.words, ensure_ascii=False), r"(?i)volunteer'?s?\b(?! *\":)")
        visible = re.sub(r"<script\b.*?</script>", " ", self.page, flags=re.S)
        self.assertNotRegex(re.sub(r"<[^>]+>", " ", visible), r"(?i)volunteer")

    def test_the_strips_are_the_same_map_in_a_small_box(self) -> None:
        for site, eyebrow in (("eranos", "Right now"), ("teleion", "Live capacity")):
            strip = build.network_strip(self.nouns, site)
            self.assertIn('data-mode="strip"', strip)
            self.assertIn(f'data-site="{site}"', strip)
            self.assertIn(build.text(eyebrow), strip)
            self.assertIn(f'href="{self.words["strip"]["href"]}"', strip)
            self.assertEqual(block(self.page, "nw-geo"), block(strip, "nw-geo"))


try:
    from playwright.sync_api import sync_playwright
except ImportError:  # the CI runner has no browser
    sync_playwright = None

STUB = """(() => { window.__reads = []; const real = window.fetch.bind(window);
  window.fetch = (input, init) => { const url = typeof input === "string" ? input : input.url;
    if (!String(url).includes("/q/network")) return real(input, init);
    window.__reads.push(Date.now());
    return Promise.resolve(new Response("{}", { status: %(status)d, headers: { "retry-after": %(ra)s } })); }; })();"""


@unittest.skipIf(sync_playwright is None, "needs the Playwright package")
class RetryAfterInBrowser(unittest.TestCase):
    """The review of c09566d: a Retry-After the browser's timer cannot hold made the page read in a tight loop."""

    @classmethod
    def setUpClass(cls) -> None:
        import threading
        from functools import partial
        import sys
        from http.server import ThreadingHTTPServer
        sys.path.insert(0, str(ROOT / "scripts"))
        import light_check
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), partial(light_check.Quiet, directory=str(ROOT / "site")))
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.browser.close()
        cls.pw.stop()
        cls.server.shutdown()

    def open(self, status: int, retry_after: str, clock: bool = False):
        ctx = self.browser.new_context()
        self.addCleanup(ctx.close)
        page = ctx.new_page()
        if clock:
            page.clock.install()
        page.add_init_script(STUB % {"status": status, "ra": json.dumps(retry_after)})
        page.route("**/*", lambda route: route.continue_() if route.request.url.startswith(self.base) else route.abort())
        page.goto(self.base + "/network/", wait_until="load")
        return page

    def test_a_huge_retry_after_reads_once_in_four_seconds_of_real_time(self) -> None:
        for status, value in ((429, "2147484"), (503, "4000000"), (503, "1e12"), (503, "Fri, 31 Dec 9999 23:59:59 GMT")):
            with self.subTest(status=status, retry_after=value):
                page = self.open(status, value)
                page.wait_for_timeout(4000)
                self.assertEqual(1, page.evaluate("window.__reads.length"))

    def test_a_day_long_retry_after_waits_an_hour_and_the_busy_line_says_so(self) -> None:
        page = self.open(429, "86400", clock=True)
        page.clock.run_for(2000)
        self.assertEqual(1, page.evaluate("window.__reads.length"))
        line = page.locator(".nw [data-status], .nw-status").first.inner_text()
        self.assertIn("It tries again in an hour.", line)  # review nit, Nov 2: not "3600 seconds"
        self.assertNotIn("3600", line)
        page.clock.run_for(3600 * 1000 - 5000)
        self.assertEqual(1, page.evaluate("window.__reads.length"))
        page.clock.run_for(10000)
        self.assertEqual(2, page.evaluate("window.__reads.length"))

    def test_a_wait_under_the_cap_still_says_its_seconds(self) -> None:
        for status, value, said in ((429, "120", "120 seconds"), (429, "3599", "3599 seconds"), (503, "90", "90 seconds")):
            with self.subTest(status=status, retry_after=value):
                page = self.open(status, value, clock=True)
                page.clock.run_for(2000)
                line = page.locator(".nw [data-status], .nw-status").first.inner_text()
                self.assertIn(f"It tries again in {said}.", line)
                self.assertNotIn("an hour", line)

    def test_a_delay_that_is_not_a_number_waits_a_minute(self) -> None:
        # Review nit, Nov 2: schedule() once turned a value that is not a number into 0, an immediate read.
        for value in ("undefined", "NaN", "null", "'soon'", "({})", "[]"):
            with self.subTest(value=value):
                page = self.open(500, "", clock=True)
                page.clock.run_for(2000)
                self.assertEqual(1, page.evaluate("window.__reads.length"))
                page.evaluate(f"document.querySelector('[data-network]').taNetwork.schedule({value})")
                page.clock.run_for(1000)
                self.assertEqual(1, page.evaluate("window.__reads.length"), "read at once")
                page.clock.run_for(57000)
                self.assertEqual(1, page.evaluate("window.__reads.length"), "read before the minute")
                page.clock.run_for(3000)
                self.assertEqual(2, page.evaluate("window.__reads.length"), "no read after the minute")


if __name__ == "__main__":
    unittest.main()
