"""The how-it-works and evidence pages: rendered from their nouns, the replay in people-readable facts (who did each
step by role, the declared model, the lease, every step recorded) from records that recompute, no stamp words, and an
evidence noun that covers every served evidence folder. Offline."""
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
        nouns.how["run"]["labels"]["record"] = "A record label from data"
        nouns.how["map"]["tasks"]["items"].append("a task from data")
        nouns.how["run"]["steps"]["request"]["title"] = "A step title from data"
        page = build.render_how_it_works(nouns)
        for words_ in ("A heading from data", "A record label from data", "a task from data", "A step title from data"):
            self.assertIn(words_, page)
        nouns.evidence = copy.deepcopy(self.nouns.evidence)
        nouns.evidence["served"]["folders"][0]["line"] = "A line from data"
        nouns.evidence["source"]["items"][0]["line"] = "A source line from data"
        page = build.render_evidence(nouns)
        self.assertIn("A line from data", page)
        self.assertIn("A source line from data", page)

    def test_every_word_shown_comes_from_a_noun(self):
        # The page's own words, outside the shared header and footer: each is a word of its nouns (with the model
        # names the catalog gives), a number from its records, or a month in a date the page formats.
        names = " ".join(m["display"] for m in self.nouns.models.values()) + " " + " ".join(
            m.get("display_tuned", "") for m in self.nouns.models.values())
        how_words = set().union(*(words(s) for s in strings(self.nouns.how) + strings(self.replay)
                                  + strings(self.nouns.learning["results"]) + [names]))
        main = build.meta_models(build.main_of(self.how), self.nouns.models)
        for piece in shown(main).text:
            self.assertLessEqual(words(piece) - MONTHS, how_words, piece)
        # The evidence page also shows the saved answers' values, such as true, and file sizes.
        evidence_words = set().union(*(words(s) for s in strings(self.filled)))
        for piece in shown(build.main_of(self.evidence)).text:
            self.assertLessEqual(words(piece) - MONTHS - {"B", "KB", "MB", "true", "false"}, evidence_words, piece)

    def test_the_build_writes_both_pages_and_fills_the_evidence_noun(self):
        outputs = build.outputs_for(self.nouns)
        self.assertEqual(build.plain_words(build.repoint(build.meta_models(build.render_page(build.HOW_PAGE, self.how, self.nouns),
                                                                          self.nouns.models), self.nouns.links)),
                         outputs[build.HOW_PAGE])
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

    def page_text(self) -> str:
        return " ".join(shown(build.meta_models(build.main_of(self.how), self.nouns.models)).text)

    def test_the_replay_shows_the_recorded_run_and_says_where_it_ran(self):
        facts = self.replay["run"]
        self.assertEqual("20261031T065341Z", facts["id"])
        self.assertTrue(facts["made_up_data_only"])
        self.assertFalse(facts["private_or_ngo_data_sent"])
        self.assertFalse(facts["raw_credentials_included"])
        self.assertTrue(facts["builder_is_not_reviewer"])
        self.assertTrue(facts["fabric"].startswith("local Tessera"), "the run is never shown as hosted Tessera")
        text = self.page_text()
        self.assertIn("not the hosted service", text)
        self.assertIn("Muse Spark 1.3, contributor tier, through the Meta API", text)  # the run's declared model
        self.assertEqual("muse-spark-1.3-contributor", facts["model"])
        self.assertIn("Every step is recorded.", text)
        self.assertNotIn("data-cleaning", text)  # the board's fixture never shows

    def test_who_did_each_step_is_said_by_role_with_its_model_and_lease(self):
        # Owner, Nov 1: name models, not agent apps. The builder is a dedicated worker run by ta-amps, the checker a
        # second agent with its own key; both declared Muse Spark 1.3. The leases are the queues' own, from the run.
        text = self.page_text()
        self.assertIn("A dedicated worker run by ta-amps", text)
        self.assertIn("A second agent with its own key", text)
        for app in ("nanoMuse", "Muse Code", "nanomuse", "muse-code"):
            self.assertNotIn(app, text)
            self.assertNotIn(app, build.main_of(self.how))
            self.assertNotIn(app, json.dumps(self.replay))
        leases = {step["id"]: step.get("lease_seconds") for step in self.replay["steps"]}
        self.assertEqual({"request": None, "build": 1800, "build-recorded": 1800, "review": 1500, "held": None}, leases)
        self.assertEqual(2, text.count("30-minute lease on its queue"))
        self.assertEqual(1, text.count("25-minute lease on its queue"))
        self.assertEqual(3, text.count("Muse Spark 1.3, contributor tier") - 1)  # three steps called it, plus the facts

    def test_the_leases_are_tesseras_own(self):
        # The leases in the noun are the lease_seconds of the queues each step's claims, heartbeats and submits were on,
        # in Tessera's events read back after the run (the run's records, kept in the repository).
        readback = json.loads((SITE / self.replay["files"]["tessera"]).read_text(encoding="utf-8"))
        events = {e["seq"]: e for e in readback["sections"]["events"]["events"]}
        queues = {e["queue"]: e["detail"]["lease_seconds"] for e in events.values() if e["type"] == "queue_defined"}
        for step in self.replay["steps"]:
            held = {queues[events[n]["queue"]] for n in step["events"]
                    if events[n]["type"] in ("claimed", "heartbeat", "submitted") and events[n]["queue"] in queues}
            self.assertEqual(held.pop() if held else None, step.get("lease_seconds"), step["id"])

    def test_the_page_and_its_noun_hold_no_hash_receipt_or_key(self):
        hexes = re.compile(r"[0-9a-f]{12,}")
        text = self.page_text()
        self.assertIsNone(hexes.search(text))
        for word in ("receipt", "sha256", "SHA-256", "noun", "verb"):
            self.assertNotIn(word.lower(), text.lower(), word)
        raw = (build.CONTENT / "real-run.json").read_text(encoding="utf-8")
        self.assertIsNone(hexes.search(raw))
        for word in ("receipt", "sha256", "noun", "verb"):
            self.assertNotIn(word, raw, word)
        self.assertIsNone(re.search(r"\bk_[0-9a-f]+\b|\bt_[0-9a-f]{8,}\b", raw))  # no key id and no task id

    def test_the_run_links_its_record_on_the_evidence_page_and_nothing_inside_its_folders(self):
        # The raw run records are not served (their traces name agent apps), so the page links the evidence page's
        # line for the run, and never a file inside those folders.
        main = build.main_of(self.how)
        hrefs = shown(main).hrefs
        self.assertIn("../evidence/#real-run-20261031T065341Z", hrefs)
        for href in hrefs:
            self.assertNotIn("evidence/real-run-", href)
            self.assertNotIn("evidence/real-e2e-meta", href)
        self.assertIn('id="real-run-20261031T065341Z"', self.evidence)

    def test_spend_appears_only_as_the_record_has_it(self):
        records = SITE / "evidence" / "real-e2e-meta-2026-10-31"
        public = next(p for p in sorted(records.glob("*.json")) if "completed_e2e_runs" in p.read_text(encoding="utf-8"))
        entry = next(r for r in json.loads(public.read_text(encoding="utf-8"))["completed_e2e_runs"]
                     if r["run_id"] == self.replay["run"]["id"])
        usage = entry["meta_api_usage"]
        spend = self.replay["run"]["spend"]
        self.assertEqual((usage["total_actual_usd"], usage["total_conservative_usd"], usage["cap_usd"]),
                         (spend["total_actual_usd"], spend["total_conservative_usd"], spend["cap_usd"]))
        main = build.main_of(self.how)
        for value in spend.values():
            self.assertIn(json.dumps(value) + " ", main)
        # No other dollar figure is on the page.
        self.assertNotRegex(" ".join(shown(main).text), r"\$")

    def test_every_step_comes_from_its_recorded_events(self):
        trace = {json.loads(line)["seq"]: json.loads(line)
                 for line in (SITE / self.replay["files"]["trace"]).read_text(encoding="utf-8").splitlines()}
        readback = json.loads((SITE / self.replay["files"]["tessera"]).read_text(encoding="utf-8"))
        events = {e["seq"]: e for e in readback["sections"]["events"]["events"]}
        self.assertEqual([1, 2, 3, 4, 5], [step["n"] for step in self.replay["steps"]])
        for step in self.replay["steps"]:
            self.assertTrue(step["trace"] or step["events"], step["id"])
            records = sorted((SITE / self.replay["files"]["steps"]).glob(f"{step['n']}-*.json"))
            self.assertEqual(1, len(records), step["id"])
            record = json.loads(records[0].read_text(encoding="utf-8"))
            # The step's record copies, unchanged, the trace lines and Tessera events the noun names.
            self.assertEqual([trace[n] for n in step["trace"]], record["trace"])
            self.assertEqual([events[n] for n in step["events"]], record["tessera_events"])

    def test_the_records_recompute(self):
        # The run's records keep each step's hash, and each recomputes from the published files (records, not pages).
        folder = SITE / self.replay["files"]["steps"]
        steps = {int(p.name.split("-", 1)[0]): json.loads(p.read_text(encoding="utf-8")) for p in folder.glob("*.json")}
        readback = json.loads((SITE / self.replay["files"]["tessera"]).read_text(encoding="utf-8"))["sections"]
        for part, n in (("build", 3), ("review", 4)):
            result = readback[f"{part}_results"]["results"][0]
            self.assertEqual(steps[n]["hash"]["value"], sync.receipt_hash(result))
        self.assertEqual(steps[5]["hash"]["value"], steps[4]["hash"]["value"])
        pins = {}
        for item in self.replay["steps"][1]["files"]:
            data = (SITE / item["file"]).read_bytes()
            self.assertEqual(item["bytes"], len(data))
            pins[item["path"]] = hashlib.sha256(data).hexdigest()
        digest = hashlib.sha256(json.dumps(pins, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        self.assertEqual(steps[2]["hash"]["value"], digest)
        self.assertEqual(steps[1]["hash"]["value"], pins["data/availability.csv"])

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
        self.assertIn('classList.contains("rr-task")', script)
        css = (SITE / "assets/how-it-works.css").read_text(encoding="utf-8")
        motion = css[css.index("@media (prefers-reduced-motion: reduce)"):]
        self.assertIn("transition: none", motion)
        self.assertIn(".rr-replay[hidden] { display: none; }", css)
        self.assertNotIn("prefers-color-scheme: dark", css)
        self.assertNotIn('data-mode="dark"', css)
        page = self.how
        self.assertIn('<script src="../assets/how-it-works.js" defer></script>', page)

    def test_meta_model_numbers_come_from_the_learning_noun(self):
        results = {item["model"]: item for item in self.nouns.learning["results"]["items"]}
        how = self.nouns.how["meta"]
        typed = json.dumps(self.nouns.how, ensure_ascii=False)
        self.assertNotIn("%", typed, "how-it-works.json types no measured figure")
        main = build.meta_models(build.main_of(self.how), self.nouns.models)
        for pick in how["results"]:
            item = results[pick["model"]]
            self.assertTrue(build.meta_models(pick["name"], self.nouns.models).startswith("Muse"), "Meta's Muse models only")
            for figure in (item["before"], item["after"]):
                self.assertNotIn(figure, typed, pick["model"])
            self.assertIn(f'<span class="how-result-before">{html.escape(item["before"])}</span>', main)
            self.assertIn(f'<span class="how-result-after">{html.escape(item["after"])}</span>', main)
            if "served" in pick:
                self.assertTrue((SITE / pick["served"]).is_file(), pick["served"])
        self.assertIsNone(re.search(r"l[l]ama", main, re.I))  # the retired family, spelled as a pattern
        self.assertIn("Muse Glimmer 30B, fine-tuned by ta-amps", main)
        self.assertIn("every step runs on Meta’s Muse models", " ".join(shown(main).text).replace("Every", "every"))
        self.assertIn('href="../models/"', main)

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
                if folder.get("raw_files"):
                    # The bundle leaves these raw files out (their traces name an agent app), so the page links the
                    # replay on How it works instead of them (Agora builder, Nov 1).
                    self.assertNotIn(f'href="../evidence/{folder["id"]}/{html.escape(path)}"', main)
                else:
                    self.assertIn(f'href="../evidence/{folder["id"]}/{html.escape(path)}"', main)
        # Review B7/B8: the saved Eranos answer is kept in the repository's evidence folder; nothing served names it.
        self.assertNotIn("eranos-api-health", main)
        self.assertNotIn("eranos-api-health", (SITE / "evidence/live-check-2026-10-31/checks.json").read_text(encoding="utf-8"))
        # A served folder without a line stops the build.
        nouns = copy.copy(self.nouns)
        nouns.evidence = copy.deepcopy(self.nouns.evidence)
        nouns.evidence["served"]["folders"].pop()
        with self.assertRaises(build.BuildError):
            build.render_evidence(nouns)

    def test_repository_evidence_is_named_in_the_repository_on_github_and_never_linked(self):
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
        # Review B8 (Nov 2): Agora serves no repository files, so the link is the repository on GitHub.
        self.assertIn("https://github.com/ta-amps/agora-public-overview-architecture-setup-and-contribution", links)
        self.assertNotIn("source download", main)

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
