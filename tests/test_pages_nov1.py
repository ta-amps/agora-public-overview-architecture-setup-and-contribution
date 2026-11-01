"""The pages of November 1, 2026: judges, status and /status.json, security and /.well-known/security.txt,
accessibility, the 1,000 test scenarios and the partner compute cards, against the owner's rules for this round.

Every page is rendered from its noun; every number comes from a record the page names; no page shows a hash, a
receipt, an agent app, Llama, "synthetic", nouns or verbs, or a stamp; trust pages say only what a check keeps true.
The build tests are offline. The browser test, like test_viewer_browser, serves site/ on 127.0.0.1, aborts every
other request and is skipped without Playwright."""
from __future__ import annotations

import datetime as dt
import importlib.util
import json
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
SPEC = importlib.util.spec_from_file_location("build_site_nov1", ROOT / "scripts/build_site.py")
build = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(build)

try:
    from test_viewer_browser import LocalSite, sync_playwright
except ImportError:  # run as tests.test_pages_nov1 from the repository root
    from tests.test_viewer_browser import LocalSite, sync_playwright

PAGES = {
    "judges": SITE / "judges" / "index.html",
    "status": SITE / "status" / "index.html",
    "security": SITE / "security" / "index.html",
    "accessibility": SITE / "accessibility" / "index.html",
    "scenarios": SITE / "scenarios" / "index.html",
    "feeds": SITE / "feeds" / "index.html",
    "deploy": SITE / "deploy" / "index.html",
    "how": SITE / "how-it-works" / "index.html",
}
# The owner's grep gate for this round, on visible text (v2 brief, Nov 1).
BANNED = re.compile(r"llama|synthetic|nanomuse|muse code|\bnouns?\b|\bverbs?\b|receipt|sha-?256|\b[0-9a-f]{12,}\b|"
                    r"\bprove[sd]?\b|planned|not yet|layout preview|coming soon|not ready yet|\bidea\b|illustration|"
                    r"placeholder|not run yet", re.I)
CLOUDY = re.compile(r"dedicated[^.]{0,40}\bcloud\b|\bcloud\b[^.]{0,40}dedicated", re.I)
MINE = ("home.json", "how-it-works.json", "real-run.json", "deploy.json", "llms.json", "feeds-page.json",
        "status-page.json", "status.json", "judges.json", "security.json", "accessibility.json", "scenarios.json")
PRIVACY = "We don't accept private information at this stage."


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


def visible(page: str) -> str:
    return " ".join(shown(page).text)


def strings(value) -> list[str]:
    if isinstance(value, str):
        return [value]
    items = value.values() if isinstance(value, dict) else value if isinstance(value, list) else []
    return [found for item in items for found in strings(item)]


class Pages(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nouns = build.Nouns()
        cls.outputs = build.outputs_for(cls.nouns)

    # Every page, against the round's rules -----------------------------------------------------------------------

    def test_every_new_page_is_built_and_listed_for_agents(self):
        for path in PAGES.values():
            self.assertIn(path, self.outputs, path)
        for row in build.ran_feeds(self.nouns):
            self.assertIn(SITE / "feeds" / row["id"] / "index.html", self.outputs)
        self.assertIn(build.STATUS_JSON, self.outputs)
        self.assertIn(build.SECURITY_TXT, self.outputs)
        llms = self.outputs[SITE / "llms.txt"]
        for path in ("judges/", "status/", "security/", "accessibility/", "scenarios/", "feeds/", "models/"):
            self.assertIn(f"https://agora.ta-amps.workers.dev/{path})", llms, path)
        self.assertNotIn("agora.ta-amps.workers.dev/film/)", llms)  # the film is withdrawn until its new cut

    def test_no_page_shows_a_banned_word_a_hash_or_a_stamp(self):
        for name, path in PAGES.items():
            text = visible(self.outputs[path])
            self.assertIsNone(BANNED.search(text), (name, BANNED.search(text) and BANNED.search(text).group(0)))
            self.assertIsNone(CLOUDY.search(text), name)
        for row in build.ran_feeds(self.nouns):
            text = visible(self.outputs[SITE / "feeds" / row["id"] / "index.html"])
            self.assertIsNone(BANNED.search(text), row["id"])
        # The home page's own parts (its decks' covers are the decks' own words).
        home = self.outputs[SITE / "index.html"]
        start = home[home.index('<section class="start'):home.index('<section class="deck-band"')]
        parser = Shown()
        parser.feed(start)
        self.assertIsNone(BANNED.search(" ".join(parser.text)))

    def test_the_nouns_these_pages_serve_say_no_banned_word(self):
        # The lead's bundle grep covers served JSON too: every string of these nouns, their about texts included.
        words = re.compile(r"\bnouns?\b|\bverbs?\b|receipt|sha256|[0-9a-f]{12,}|llama|synthetic|nanomuse|muse code", re.I)
        for name in MINE:
            text = (build.CONTENT / name).read_text(encoding="utf-8")
            found = words.search(text)
            self.assertIsNone(found, (name, found and found.group(0)))

    def test_pages_set_no_inline_style_and_load_their_own_styles(self):
        for name, path in PAGES.items():
            page = self.outputs[path]
            self.assertNotIn(' style="', build.main_of(page), name)
            css = "how-it-works.css" if name == "how" else "pages.css"
            self.assertIn(f'href="../assets/{css}"', page, name)
        css = (SITE / "assets" / "pages.css").read_text(encoding="utf-8")
        self.assertNotIn("prefers-color-scheme: dark", css)
        self.assertNotIn('data-mode="dark"', css)
        # Text is at least 14 px; 13 px only where the font is mono.
        for rule in re.findall(r"[^{}]+\{[^{}]+\}", css):
            for size in re.findall(r"font-size:\s*([0-9.]+)rem", rule):
                if float(size) < 0.875:
                    self.assertIn("mono", rule, rule)
                    self.assertGreaterEqual(float(size), 0.8125, rule)
        for n in range(0, 101, 5):
            self.assertIn(f".pct-{n} {{ width: {n}%" if n else ".pct-0 { width: 0;", css)

    def test_the_privacy_line_is_the_owners_exactly(self):
        for name in ("judges", "security", "feeds"):
            text = visible(self.outputs[PAGES[name]])
            if "private information" in text:
                self.assertIn(PRIVACY, text, name)
        self.assertIn(PRIVACY, visible(self.outputs[PAGES["judges"]]))

    # Judges ------------------------------------------------------------------------------------------------------

    def test_the_judges_page_links_the_tour_the_example_the_studio_and_eranos(self):
        page = self.outputs[PAGES["judges"]]
        hrefs = shown(page).hrefs
        self.assertIn('<a class="button" href="?tour=judge" data-judge-tour>Take the 45-second tour →</a>', page)
        self.assertIn("https://eranos.ta-amps.workers.dev/requests/REQ-INTAKE-07?replay=1", hrefs)
        self.assertIn("../studio/", hrefs)
        self.assertIn("https://eranos.ta-amps.workers.dev/", hrefs)
        self.assertIn("../models/", hrefs)
        self.assertNotIn("../film/", hrefs)  # withdrawn until its new cut

    def test_what_is_real_is_filled_from_records_or_says_what_has_not_happened(self):
        rows = build.judges_rows(self.nouns)
        self.assertEqual(len(self.nouns.judges["rows"]), len(rows))
        text = visible(self.outputs[PAGES["judges"]])
        run = self.nouns.real_run["run"]
        facts = self.nouns.scenarios["facts"]
        self.assertIn(f"On {build.human_date(run['started_utc'])}, a dedicated worker run by ta-amps built a kit", text)
        self.assertIn(f"{facts['evaluated']:,} test scenarios", text)
        self.assertIn(f"from seed {facts['seed']}: {facts['approved_direct']:,} approved as asked", text)
        latest = max(r["last_run"]["at"] for r in build.ran_feeds(self.nouns))
        self.assertIn(f"{len(build.ran_feeds(self.nouns))} categories", text)
        self.assertIn(build.human_date(latest), text)
        self.assertIn("Nothing in it was sent, built or run", text)
        # A filled row whose record no longer matches its words stops the build.
        nouns = type(self.nouns).__new__(type(self.nouns))
        nouns.__dict__.update(self.nouns.__dict__)
        nouns.deploy = json.loads(json.dumps(self.nouns.deploy))
        nouns.deploy["partners"]["facts"]["modal"]["live_credentials_present"] = True
        with self.assertRaises(build.BuildError):
            build.judges_rows(nouns)

    # Status ------------------------------------------------------------------------------------------------------

    def test_the_status_page_and_status_json_agree(self):
        page = self.outputs[PAGES["status"]]
        data = json.loads(self.outputs[build.STATUS_JSON])
        self.assertEqual({"eranos", "agora", "tessera", "herma", "home"}, {s["id"] for s in data["services"]})
        text = visible(page)
        for service in data["services"]:
            self.assertIn(service["name"], text)
            self.assertIn(service["label"], text)
            if service["checked_at"]:
                self.assertIn(f'datetime="{service["checked_at"]}"', page)
        self.assertIn(self.nouns.status_words["overall"][data["overall"]]["title"], text)
        noun = self.nouns.status
        self.assertEqual(noun["checked_at"], data["checked_at"])
        for row, service in zip(noun["services"], data["services"]):
            self.assertEqual((row["id"], row["state"], row["checked_at"]), (service["id"], service["state"], service["checked_at"]))
        # The daily check row links its record and shows its times; no hash and no uptime figure anywhere.
        self.assertIn(self.nouns.status_words["daily"]["check"], shown(page).hrefs)
        if noun["daily"].get("last_run"):
            self.assertIn(f'datetime="{noun["daily"]["last_run"]}"', page)
        for blob in (text, self.outputs[build.STATUS_JSON]):
            self.assertNotIn("%", blob)
            self.assertNotIn("uptime", blob.lower())
            self.assertIsNone(re.search(r"[0-9a-f]{12,}", blob))
            self.assertNotIn("Not run yet", blob)

    def test_sync_status_only_reads(self):
        script = (ROOT / "scripts" / "sync_status.py").read_text(encoding="utf-8")
        code = script.split('"""', 2)[2]  # the code, after the docstring that says what it never does
        self.assertIn('method="GET"', code)
        for word in ("POST", "PUT", "DELETE", "Authorization", "Cookie", "session", "studio", "/v1/keys"):
            self.assertNotIn(word.lower(), code.lower(), word)
        for service in self.nouns.status_words["services"]:
            self.assertRegex(service["check"], r"^https://[a-z]+\.ta-amps\.workers\.dev/")
        self.assertRegex(self.nouns.status_words["daily"]["check"], r"^https://home\.ta-amps\.workers\.dev/")

    def test_a_service_state_needs_words_and_a_failed_check_says_so(self):
        nouns = type(self.nouns).__new__(type(self.nouns))
        nouns.__dict__.update(self.nouns.__dict__)
        nouns.status = json.loads(json.dumps(self.nouns.status))
        nouns.status["services"][2]["state"] = "not_answering"
        view = build.status_view(nouns)
        self.assertEqual("not_answering", view["overall"])
        self.assertIn("Not answering", visible(build.render_status(nouns)))
        nouns.status["services"][2]["state"] = "on fire"
        with self.assertRaises(build.BuildError):
            build.status_view(nouns)
        nouns.status = {}
        self.assertEqual("no_run", build.status_view(nouns)["overall"])
        self.assertIn("No run recorded", visible(build.render_status(nouns)))

    # Security, accessibility and security.txt -------------------------------------------------------------------

    def test_security_txt_follows_rfc_9116(self):
        txt = self.outputs[build.SECURITY_TXT]
        fields = dict(line.split(": ", 1) for line in txt.splitlines() if line and not line.startswith("#"))
        self.assertTrue(fields["Contact"].startswith("https://"))
        self.assertEqual(1, txt.count("\nExpires: "))
        expires = dt.datetime.fromisoformat(fields["Expires"].replace("Z", "+00:00"))
        written = dt.datetime.fromisoformat(self.nouns.security["updated"] + "T00:00:00+00:00")
        self.assertLess(written, expires)
        self.assertLessEqual(expires - written, dt.timedelta(days=365))
        self.assertGreater(expires, dt.datetime.now(dt.timezone.utc), "renew security.txt: its Expires has passed")
        self.assertEqual("https://agora.ta-amps.workers.dev/.well-known/security.txt", fields["Canonical"])
        # The Contact is a real address this site serves, never a made-up mailbox.
        self.assertEqual("https://agora.ta-amps.workers.dev/security/", fields["Contact"])
        self.assertIn(PAGES["security"], self.outputs)
        self.assertNotIn("@", txt)
        self.assertIn("../.well-known/security.txt", shown(self.outputs[PAGES["security"]]).hrefs)

    def test_every_trust_line_that_states_a_fact_names_a_check_that_holds(self):
        checks = {
            "no outside hosts": self.no_outside_hosts,
            "no cookies": self.no_cookies,
            "publication scan": self.publication_scan,
            "builder is not reviewer": self.checker_is_not_builder,
            "privacy line": lambda: None,
            "skip link": self.skip_links,
            "focus ring": self.focus_ring,
            "contrast": self.contrast,
            "reduced motion": self.reduced_motion,
        }
        for noun in (self.nouns.security, self.nouns.accessibility):
            for block in noun["blocks"]:
                for item in block["items"]:
                    if isinstance(item, dict):
                        self.assertIn(item["proof_by"], checks, item["text"])
                        checks[item["proof_by"]]()
                        if item["proof_by"] == "privacy line":
                            self.assertEqual(PRIVACY, item["text"])
        for name in ("security", "accessibility"):
            text = visible(self.outputs[PAGES[name]])
            self.assertIn("owner decision that is still open", text)  # no made-up contact

    def no_outside_hosts(self):
        loads = re.compile(r'<(?:link|script|img|video|source|track|iframe)\b[^>]*?\s(?:href|src)="(https?://[^"/]+)', re.I)
        hosts = {h for path, page in self.outputs.items() if path.suffix == ".html" for h in loads.findall(page)}
        self.assertEqual(set(), hosts)

    def no_cookies(self):
        for path in (SITE / "assets").glob("*.js"):
            self.assertNotIn("cookie", path.read_text(encoding="utf-8").lower(), path.name)

    def publication_scan(self):
        check = (ROOT / "scripts" / "check.py").read_text(encoding="utf-8")
        for name in ("GitHub token", "service token", "private key", "local home path"):
            self.assertIn(f'"{name}"', check)

    def checker_is_not_builder(self):
        run = self.nouns.real_run
        self.assertIs(True, run["run"]["builder_is_not_reviewer"])
        self.assertEqual(["builder", "reviewer"], [s["by"] for s in run["steps"] if s["id"] in ("build", "review")])

    def skip_links(self):
        for path in list(PAGES.values()) + [SITE / "index.html"]:
            page = self.outputs[path]
            self.assertLess(page.index('class="skip-link"'), page.index("<ta-agent-banner "), path)
            self.assertIn('href="#main"', page)

    def focus_ring(self):
        tokens = (SITE / "assets" / "tokens.css").read_text(encoding="utf-8")
        self.assertRegex(tokens, r":focus-visible \{ outline: 3px solid var\(--focus\)")

    def contrast(self):
        tokens = (SITE / "assets" / "tokens.css").read_text(encoding="utf-8")
        values = dict(re.findall(r"(--[a-z0-9-]+):\s*(#[0-9A-Fa-f]{6})", tokens))

        def luminance(colour: str) -> float:
            channels = [int(colour[i:i + 2], 16) / 255 for i in (1, 3, 5)]
            r, g, b = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
            return 0.2126 * r + 0.7152 * g + 0.0722 * b
        for fg in ("--text", "--text-2", "--text-3", "--link"):
            a, b = sorted((luminance(values[fg]), luminance(values["--bg"])), reverse=True)
            self.assertGreaterEqual((a + 0.05) / (b + 0.05), 4.5, fg)

    def reduced_motion(self):
        css = (SITE / "assets" / "how-it-works.css").read_text(encoding="utf-8")
        self.assertIn("transition: none", css[css.index("@media (prefers-reduced-motion: reduce)"):])

    # Scenarios ---------------------------------------------------------------------------------------------------

    def test_every_scenario_number_comes_from_the_copied_facts(self):
        facts = self.nouns.scenarios["facts"]
        text = visible(self.outputs[PAGES["scenarios"]])
        numbers = set()
        for value in strings(json.loads(json.dumps(facts))) + [json.dumps(facts)]:
            numbers |= set(re.findall(r"\d+(?:\.\d+)?", value))
        # Sums and shares the page works out from the facts: the reasons' total and each stakeholder's share.
        numbers.add(str(sum(facts["block_reasons"].values())))
        numbers |= {str(round(100 * r["blocked"] / r["scenarios"])) for r in facts["stakeholders"]}
        allowed = numbers | {"1,000", "10", "12", "2.2"}  # 1,000 with its comma; 10¹²; WCAG 2.2 in a title
        for found in re.findall(r"\d[\d,.]*", text):
            plain = found.rstrip(".,")
            if plain.replace(",", "") in numbers or plain in allowed:
                continue
            self.fail(f"the scenarios page shows a number its facts do not hold: {found}")
        for key in ("approved_direct", "approved_partitioned", "blocked"):
            self.assertIn(f"{facts[key]:,}", text)
        self.assertIn(f"seed {facts['seed']}", text)
        self.assertIn("1,000 test scenarios", text)
        self.assertIn("These are local checks", text)
        self.assertIn("10¹²", text)

    def test_the_copied_facts_match_their_source_record(self):
        source = ROOT / "evidence" / "sira-are-cascade-2026-10-31" / "scenario_matrix_1000_digest.json"
        if not source.is_file():
            self.skipTest("the source record is not in this checkout")
        record = json.loads(source.read_text(encoding="utf-8"))
        facts = self.nouns.scenarios["facts"]
        agg = record["aggregate_metrics"]
        self.assertEqual((record["mode"], record["seed"], record["evaluated_lhs_episodes"]),
                         (facts["mode"], facts["seed"], facts["evaluated"]))
        self.assertEqual(10 ** facts["addressable_combinations_power_of_ten"], record["addressable_tuple_space"])
        self.assertEqual((agg["approved_direct_count"], agg["approved_partitioned_count"], agg["blocked_count"]),
                         (facts["approved_direct"], facts["approved_partitioned"], facts["blocked"]))
        self.assertEqual(agg["block_reasons"], facts["block_reasons"])
        self.assertEqual([(r["position"], r["episodes"], r["blocked"]) for r in record["stakeholder_breakdown"]],
                         [(r["position"], r["scenarios"], r["blocked"]) for r in facts["stakeholders"]])
        self.assertEqual([(r["episodes"], r["approved_direct"], r["approved_partitioned"], r["blocked"])
                          for r in record["domain_breakdown"]],
                         [(r["scenarios"], r["approved_direct"], r["approved_partitioned"], r["blocked"]) for r in facts["domains"]])
        for verdict, sample in facts["samples"].items():
            episode = record["sample_episodes"][verdict]
            self.assertEqual([episode["tuple"][k] for k in ("env_id", "method_id", "persona_id", "stakeholder_id")], sample["ids"])
            self.assertEqual(episode["block_reasons"], sample["block_reasons"])

    # Partner compute ---------------------------------------------------------------------------------------------

    def test_partner_cards_are_offline_checks_with_no_numbers_and_no_record_line(self):
        page = self.outputs[PAGES["deploy"]]
        cards = page[page.index('<ul class="partner-cards">'):page.index('<p class="partner-never">')]
        words_only = re.sub(r"<pre\b.*?</pre>", "", cards, flags=re.S)
        parser = Shown()
        parser.feed(words_only)
        text = " ".join(parser.text)
        for name in ("Modal", "Baseten", "Fireworks"):
            self.assertIn(name, text)
        self.assertEqual(3, text.count("Offline check"))
        self.assertIsNone(re.search(r"\d", text.replace("30B", "")), "the cards show no number")
        self.assertNotIn("receipt", page.lower())
        self.assertNotIn("film/compare", page)
        self.assertNotIn("sira-are-cascade", page)
        # Each checked line needs its copied fact true; a false one stops the build.
        nouns = type(self.nouns).__new__(type(self.nouns))
        nouns.__dict__.update(self.nouns.__dict__)
        nouns.deploy = json.loads(json.dumps(self.nouns.deploy))
        nouns.deploy["partners"]["facts"]["baseten"]["checks"]["respected_2m_tpm_ceiling"] = False
        with self.assertRaises(build.BuildError):
            build.render_deploy(nouns)

    def test_the_deploy_page_names_no_old_model_and_no_hand_written_mirror(self):
        raw = (build.CONTENT / "deploy.json").read_text(encoding="utf-8")
        self.assertNotIn("llama", raw.lower())
        self.assertNotIn("agora.ta-amps.workers.dev/source/", raw)
        self.assertNotIn("agora.ta-amps.workers.dev/git/", raw)
        self.assertIn('id="slice-partners"', self.outputs[PAGES["deploy"]])


@unittest.skipIf(sync_playwright is None, "needs the Playwright package")
class JudgesInBrowser(LocalSite):
    def test_the_tour_button_adds_tour_judge_and_opens_the_tour(self):
        ctx = self.browser.new_context(viewport={"width": 1280, "height": 800})
        self.addCleanup(ctx.close)
        page = ctx.new_page()
        page.route("**/*", lambda route: route.continue_() if route.request.url.startswith(self.base) else route.abort())
        page.goto(self.base + "judges/", wait_until="domcontentloaded")
        self.assertTrue(page.evaluate("document.querySelector('ta-judge-tour').hidden"))
        page.click("a[data-judge-tour]")
        page.wait_for_url("**/judges/?tour=judge")
        self.assertIn("?tour=judge", page.url)
        page.wait_for_selector('ta-judge-tour[data-active="true"]', state="attached")
        self.assertEqual("1", page.locator("ta-judge-tour").get_attribute("data-step"))
        # Light only: the page stays on paper even when the system asks for dark.
        dark = self.browser.new_context(color_scheme="dark")
        self.addCleanup(dark.close)
        other = dark.new_page()
        other.route("**/*", lambda route: route.continue_() if route.request.url.startswith(self.base) else route.abort())
        other.goto(self.base + "judges/", wait_until="domcontentloaded")
        background = other.evaluate("""() => {
            const body = getComputedStyle(document.body).backgroundColor;
            return body === 'rgba(0, 0, 0, 0)' ? getComputedStyle(document.documentElement).backgroundColor : body;
        }""")
        self.assertEqual("rgb(245, 242, 234)", background)


if __name__ == "__main__":
    unittest.main()
