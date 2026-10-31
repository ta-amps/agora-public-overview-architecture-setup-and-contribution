"""The how-it-works and evidence pages: rendered from their nouns, every replayed step backed by a served receipt file
whose hash recomputes, no stamp words, and an evidence noun that covers every served evidence folder. Offline."""
import copy
import hashlib
import html
import importlib.util
import json
import re
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


build = load("build_site", ROOT / "scripts/build_site.py")
sync = load("sync_real_run", ROOT / "scripts/sync_real_run.py")

STAMPS = ("planned", "not yet", "coming soon", "illustration", "synthetic example")
FORBIDDEN = ("/home/", "tan_", "tsk_", "hmk_", "Bearer")
MONTHS = {"January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"}


class Shown(HTMLParser):
    """The text a fragment shows, piece by piece, and every href it holds."""

    def __init__(self) -> None:
        super().__init__()
        self.text: list[str] = []
        self.hrefs: list[str] = []

    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            if name == "href":
                self.hrefs.append(value)

    def handle_data(self, data):
        if data.strip():
            self.text.append(data.strip())


def shown(fragment: str) -> Shown:
    parser = Shown()
    parser.feed(fragment)
    parser.close()
    return parser


def words(value: str) -> set[str]:
    return set(re.findall(r"[A-Za-z][A-Za-z’'-]*[A-Za-z]|[A-Za-z]", value))


def strings(value) -> list[str]:
    if isinstance(value, str):
        return [value]
    items = value.values() if isinstance(value, dict) else value if isinstance(value, list) else []
    return [found for item in items for found in strings(item)]


class Pages(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nouns = build.Nouns()
        cls.how = build.render_how_it_works(cls.nouns)
        cls.evidence = build.render_evidence(cls.nouns)
        cls.replay = cls.nouns.real_run
        cls.filled = build.fill_evidence(cls.nouns.evidence)

    # Rendered from their nouns -------------------------------------------------------------------

    def test_both_pages_render_from_their_nouns(self):
        nouns = copy.copy(self.nouns)
        nouns.how = copy.deepcopy(self.nouns.how)
        nouns.how["heading"] = "A heading from data"
        nouns.how["run"]["labels"]["open"] = "A receipt label from data"
        nouns.how["map"]["verbs"]["items"].append("a verb from data")
        page = build.render_how_it_works(nouns)
        for words_ in ("A heading from data", "A receipt label from data", "a verb from data"):
            self.assertIn(words_, page)
        self.assertEqual(len(self.replay["steps"]), page.count("A receipt label from data"))
        nouns.real_run = copy.deepcopy(self.replay)
        nouns.real_run["steps"][0]["title"] = "A step title from data"
        self.assertIn("A step title from data", build.render_how_it_works(nouns))
        nouns.evidence = copy.deepcopy(self.nouns.evidence)
        nouns.evidence["served"]["folders"][0]["line"] = "A line from data"
        nouns.evidence["source"]["items"][0]["line"] = "A source line from data"
        page = build.render_evidence(nouns)
        self.assertIn("A line from data", page)
        self.assertIn("A source line from data", page)

    def test_every_word_shown_comes_from_a_noun(self):
        # The pages' own words, outside the shared header and footer: each is a word of the page's nouns, or a month
        # in a date the page formats.
        how_words = set().union(*(words(s) for s in strings(self.nouns.how) + strings(self.replay)
                                  + strings(self.nouns.learning["results"])))
        for piece in shown(build.main_of(self.how)).text:
            self.assertLessEqual(words(piece) - MONTHS, how_words, piece)
        # The evidence page also shows the saved answers' values, such as true, and file sizes.
        evidence_words = set().union(*(words(s) for s in strings(self.filled)))
        for piece in shown(build.main_of(self.evidence)).text:
            self.assertLessEqual(words(piece) - MONTHS - {"B", "KB", "MB", "true", "false"}, evidence_words, piece)

    def test_the_build_writes_both_pages_and_fills_the_evidence_noun(self):
        outputs = build.outputs_for(self.nouns)
        self.assertEqual(self.how, build.render_how_it_works(self.nouns))
        self.assertIn(build.HOW_PAGE, outputs)
        self.assertIn(build.EVIDENCE_PAGE, outputs)
        on_disk = json.loads(build.EVIDENCE_NOUN.read_text(encoding="utf-8"))
        self.assertEqual(self.filled, on_disk, "run python3 scripts/build_site.py to refill site/content/evidence.json")

    # No stamps --------------------------------------------------------------------------------

    def test_there_are_no_stamp_words(self):
        for name, page in (("how", self.how), ("evidence", self.evidence)):
            text = " ".join(shown(build.main_of(page)).text).lower()
            for stamp in STAMPS:
                self.assertNotIn(stamp, text, (name, stamp))
        for noun in (self.nouns.how, self.replay, self.nouns.evidence):
            for value in strings(noun):
                for stamp in STAMPS:
                    self.assertNotIn(stamp, value.lower(), value)
        nouns = copy.copy(self.nouns)
        nouns.how = copy.deepcopy(self.nouns.how)
        nouns.how["lead"] = "This part is coming soon."
        with self.assertRaises(build.BuildError):
            build.render_how_it_works(nouns)

    # The replay -------------------------------------------------------------------------------

    def test_the_replay_shows_the_recorded_run_and_says_where_it_ran(self):
        facts = self.replay["run"]
        self.assertEqual("20261031T065341Z", facts["id"])
        self.assertTrue(facts["made_up_data_only"])
        self.assertFalse(facts["private_or_ngo_data_sent"])
        self.assertFalse(facts["raw_credentials_included"])
        self.assertTrue(facts["fabric"].startswith("local Tessera"), "the run is never shown as hosted Tessera")
        main = build.main_of(self.how)
        self.assertIn(html.escape(facts["fabric"], quote=False), main)
        self.assertIn(facts["model"], main)
        self.assertIn("not the hosted service", self.nouns.how["run"]["lead"])
        self.assertNotIn("data-cleaning", main)  # the board's fixture never shows

    def test_spend_appears_only_as_the_receipt_records_it(self):
        receipt = json.loads((SITE / self.replay["receipt"]).read_text(encoding="utf-8"))
        entry = next(r for r in receipt["completed_e2e_runs"] if r["run_id"] == self.replay["run"]["id"])
        usage = entry["meta_api_usage"]
        spend = self.replay["run"]["spend"]
        self.assertEqual((usage["total_actual_usd"], usage["total_conservative_usd"], usage["cap_usd"]),
                         (spend["total_actual_usd"], spend["total_conservative_usd"], spend["cap_usd"]))
        main = build.main_of(self.how)
        for value in spend.values():
            self.assertIn(json.dumps(value) + " ", main)
        # No other dollar figure is on the page.
        self.assertNotRegex(" ".join(shown(main).text), r"\$")

    def test_every_replay_step_links_a_receipt_file_of_the_site_and_its_events(self):
        main = build.main_of(self.how)
        trace = {json.loads(line)["seq"]: json.loads(line)
                 for line in (SITE / self.replay["files"]["trace"]).read_text(encoding="utf-8").splitlines()}
        readback = json.loads((SITE / self.replay["files"]["tessera"]).read_text(encoding="utf-8"))
        events = {e["seq"]: e for e in readback["sections"]["events"]["events"]}
        self.assertEqual([1, 2, 3, 4, 5], [step["n"] for step in self.replay["steps"]])
        for step in self.replay["steps"]:
            receipt = (SITE / step["receipt"]).resolve()
            self.assertTrue(receipt.is_relative_to(SITE.resolve()) and receipt.is_file(), step["id"])
            self.assertIn(f'href="../{html.escape(step["receipt"])}"', main)
            record = json.loads(receipt.read_text(encoding="utf-8"))
            self.assertEqual(step["hash"]["value"], record["hash"]["value"])
            self.assertTrue(step["trace"] or step["events"], step["id"])
            # The receipt copies, unchanged, the trace lines and Tessera events the step names.
            self.assertEqual([trace[n] for n in step["trace"]], record["trace"])
            self.assertEqual([events[n] for n in step["events"]], record["tessera_events"])

    def test_every_hash_shown_appears_in_its_evidence_file(self):
        main = build.main_of(self.how)
        folder = SITE / self.replay["files"]["trace"].rsplit("/", 1)[0]
        published = " ".join(p.read_text(encoding="utf-8") for p in folder.rglob("*.json"))
        full = re.findall(r'<code class="rr-hash">([0-9a-f]{64})</code>', main)
        self.assertEqual([step["hash"]["value"] for step in self.replay["steps"]], full)
        for step in self.replay["steps"]:
            self.assertIn(step["hash"]["value"], (SITE / step["receipt"]).read_text(encoding="utf-8"), step["id"])
        short = re.findall(r"([0-9a-f]{8})\u2026", main)
        self.assertGreaterEqual(len(short), 6)
        for prefix in short:
            self.assertRegex(published, prefix + r"[0-9a-f]{56}", prefix)

    def test_the_hashes_recompute_from_the_published_files(self):
        folder = SITE / self.replay["files"]["trace"].rsplit("/", 1)[0]
        readback = json.loads((folder / "tessera-readback.json").read_text(encoding="utf-8"))["sections"]
        steps = {step["id"]: step for step in self.replay["steps"]}
        # Tessera's receipts: SHA-256 over the canonical JSON of each stored result.
        for part, step_id in (("build", "build-receipt"), ("review", "review")):
            result = readback[f"{part}_results"]["results"][0]
            self.assertEqual(steps[step_id]["hash"]["value"], sync.receipt_hash(result))
        self.assertEqual(steps["held"]["hash"]["value"], steps["review"]["hash"]["value"])
        # Each kit file hashes to its recorded SHA-256, and the digest covers the four.
        pins = {}
        for noun in steps["build"]["nouns"]:
            data = (SITE / noun["file"]).read_bytes()
            self.assertEqual(noun["sha256"], hashlib.sha256(data).hexdigest(), noun["path"])
            self.assertEqual(noun["bytes"], len(data))
            pins[noun["path"]] = noun["sha256"]
        digest = hashlib.sha256(json.dumps(pins, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        self.assertEqual(steps["build"]["hash"]["value"], digest)
        # The input noun's hash is the availability list's.
        self.assertEqual(steps["request"]["hash"]["value"], pins["data/availability.csv"])

    def test_the_published_run_files_hold_no_private_strings(self):
        folder = SITE / self.replay["files"]["trace"].rsplit("/", 1)[0]
        paths = list(folder.rglob("*")) + [build.CONTENT / "real-run.json"]
        for path in paths:
            if path.is_file():
                text = path.read_text(encoding="utf-8")
                for needle in FORBIDDEN:
                    self.assertNotIn(needle, text, (path.name, needle))

    def test_without_script_the_page_lists_every_step_and_shows_the_end(self):
        main = build.main_of(self.how)
        steps = re.findall(r'<li class="rr-step" data-rr-step="(\d)"', main)
        self.assertEqual(["1", "2", "3", "4", "5"], steps)
        self.assertIn('<ol class="rr-steps" id="run-steps"', main)
        self.assertRegex(main, r'<button class="button secondary rr-replay"[^>]*\shidden>')
        # The stage starts at the run's end: every task in its final state.
        finals = self.replay["run"]["final_states"]
        for kind in ("request", "build", "review"):
            self.assertRegex(main, rf'<span class="rr-kind">{kind}</span><span class="rr-name">[^<]+</span>'
                                   rf'<span class="rr-state" data-state="{finals[kind]}"')
        self.assertNotIn("rr-off", main)

    def test_the_replay_script_stays_offline_and_respects_reduced_motion(self):
        script = (SITE / "assets/how-it-works.js").read_text(encoding="utf-8")
        for call in ("fetch(", "XMLHttpRequest", "import(", "WebSocket", "sendBeacon", "http://", "https://"):
            self.assertNotIn(call, script)
        self.assertIn("[data-rr-replay]", script)
        self.assertIn("button.hidden = false", script)
        css = (SITE / "assets/how-it-works.css").read_text(encoding="utf-8")
        motion = css[css.index("@media (prefers-reduced-motion: reduce)"):]
        self.assertIn("transition: none", motion)
        self.assertIn(".rr-replay[hidden] { display: none; }", css)
        page = self.how
        self.assertIn('<script src="../assets/how-it-works.js" defer></script>', page)

    def test_meta_model_numbers_come_from_the_learning_noun(self):
        results = {item["model"]: item for item in self.nouns.learning["results"]["items"]}
        how = self.nouns.how["meta"]
        typed = json.dumps(self.nouns.how, ensure_ascii=False)
        self.assertNotIn("%", typed, "how-it-works.json types no measured figure")
        main = build.main_of(self.how)
        for pick in how["results"]:
            item = results[pick["model"]]
            for figure in (item["before"], item["after"]):
                self.assertNotIn(figure, typed, pick["model"])
            self.assertIn(f'<span class="how-result-before">{html.escape(item["before"])}</span>', main)
            self.assertIn(f'<span class="how-result-after">{html.escape(item["after"])}</span>', main)
            self.assertIn(html.escape(item["line"], quote=False), main)
            if "served" in pick:
                self.assertTrue((SITE / pick["served"]).is_file(), pick["served"])

    # The evidence page --------------------------------------------------------------------------

    def test_the_evidence_noun_covers_every_served_evidence_folder(self):
        served = sorted(p.name for p in (SITE / "evidence").iterdir() if p.is_dir())
        described = [folder["id"] for folder in self.nouns.evidence["served"]["folders"]]
        self.assertEqual(served, sorted(described))
        main = build.main_of(self.evidence)
        for folder in self.filled["served"]["folders"]:
            self.assertIn(f'id="{folder["id"]}"', main)
            files = sorted(p.relative_to(SITE / "evidence" / folder["id"]).as_posix()
                           for p in (SITE / "evidence" / folder["id"]).rglob("*") if p.is_file())
            self.assertEqual(files, [f["path"] for f in folder["files"]])
            for path in files:
                self.assertIn(f'href="../evidence/{folder["id"]}/{html.escape(path)}"', main)
        # A served folder without a line stops the build.
        nouns = copy.copy(self.nouns)
        nouns.evidence = copy.deepcopy(self.nouns.evidence)
        nouns.evidence["served"]["folders"].pop()
        with self.assertRaises(build.BuildError):
            build.render_evidence(nouns)

    def test_repository_evidence_is_named_in_the_source_download_and_never_linked(self):
        repo = sorted("evidence/" + p.name for p in (ROOT / "evidence").iterdir())
        items = self.nouns.evidence["source"]["items"]
        self.assertEqual(repo, sorted(item["path"].rstrip("/") for item in items))
        main = build.main_of(self.evidence)
        links = shown(main).hrefs
        for item in items:
            self.assertIn(f'<code>{html.escape(item["path"])}</code>', main)
        for href in links:
            if href.startswith("../evidence/"):
                self.assertTrue((SITE / href[3:].split("#")[0]).exists(), href)
        self.assertIn("https://agora.ta-amps.workers.dev/source/", links)

    def test_what_is_live_is_a_dated_snapshot_of_the_saved_check(self):
        live = self.filled["live"]
        record = json.loads((SITE / live["record"]).read_text(encoding="utf-8"))
        snapshot = live["snapshot"]
        self.assertEqual(record["checked_at"], snapshot["checked_at"])
        self.assertRegex(snapshot["checked_at"], r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ\Z")
        main = build.main_of(self.evidence)
        self.assertIn(f'<time datetime="{snapshot["checked_at"]}">', main)
        self.assertIn(live["checked"], main)
        for check, saved in zip(snapshot["checks"], record["checks"]):
            self.assertEqual((check["url"], check["http_status"]), (saved["url"], saved["http_status"]))
            if saved["body"]:
                body = (SITE / live["record"]).parent / saved["body"]
                self.assertEqual(saved["body_sha256"], hashlib.sha256(body.read_bytes()).hexdigest())
                answer = json.loads(body.read_text(encoding="utf-8"))
                self.assertEqual({k: answer[k] for k in check["fields"]}, check["fields"])
        self.assertIn("not a monitor", live["lead"])
        self.assertNotIn("is live now", " ".join(shown(main).text).lower())


class Sync(unittest.TestCase):
    def receipt_folder(self, folder: Path, **changes) -> None:
        receipt = {"synthetic_data_only": True,
                   "privacy_and_spend_guardrails": {"private_or_ngo_data_sent": False, "raw_credentials_included": False}}
        receipt.update({k: v for k, v in changes.items() if k == "synthetic_data_only"})
        receipt["privacy_and_spend_guardrails"].update({k: v for k, v in changes.items() if k != "synthetic_data_only"})
        (folder / "public-e2e-receipt.json").write_text(json.dumps(receipt), encoding="utf-8")

    def test_the_sync_refuses_a_run_that_is_not_synthetic_or_that_sent_private_data(self):
        for changes in ({"synthetic_data_only": False}, {"private_or_ngo_data_sent": True},
                        {"raw_credentials_included": True}, {"synthetic_data_only": None}):
            with tempfile.TemporaryDirectory() as folder:
                self.receipt_folder(Path(folder), **changes)
                with self.assertRaisesRegex(sync.SyncError, "refusing"):
                    sync.outputs(Path(folder))

    def test_the_sync_reads_nothing_else_before_the_guard_passes(self):
        with tempfile.TemporaryDirectory() as folder:
            self.receipt_folder(Path(folder))
            with self.assertRaisesRegex(sync.SyncError, "missing run-facts.json"):
                sync.outputs(Path(folder))

    def test_receipt_hash_is_tesseras(self):
        result = {"task_id": "t_x", "fencing_token": 1, "ok": True, "output": "{\"a\": 1}", "error": None}
        body = '{"error":null,"fencing_token":1,"ok":true,"output":"{\\"a\\": 1}","task_id":"t_x"}'
        self.assertEqual(hashlib.sha256(body.encode()).hexdigest(), sync.receipt_hash(result))


if __name__ == "__main__":
    unittest.main()
