"""The Live Studio in a real browser: it never simulates a service, and it says Connected only when it is.

These tests need the Playwright package and its Chromium. Without them they are skipped, as in this
repository's CI, which installs nothing beyond the standard library. Run them locally with
`python -m unittest tests.test_studio_browser -v` from a Python that has Playwright. They serve site/ on
127.0.0.1 and answer every Tessera, Herma and Eranos request from fakes in this file through page.route, so
they make no network calls. Every other request is aborted.
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
import unittest
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

SITE = Path(__file__).resolve().parents[1] / "site"
STUDIO_JS = SITE / "studio" / "studio.js"
WAIT_MS = 30000  # generous: these tests also run on busy machines

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover - depends on the environment
    sync_playwright = None

TESSERA = "tessera.ta-amps.workers.dev"
HERMA = "herma.ta-amps.workers.dev"
ERANOS = "eranos.ta-amps.workers.dev"
CORS = {
    "access-control-allow-origin": "*",
    "access-control-allow-methods": "GET, POST, OPTIONS",
    "access-control-allow-headers": "Authorization, Content-Type, Idempotency-Key, X-Namespace",
    "access-control-expose-headers": "ETag, Retry-After, X-Request-Id",
}
CHECKS = ["track_alignment", "human_only_boundaries", "synthetic_fixtures", "non_accusatory_copy",
          "prohibited_topics", "spdx_license_allowlist", "cited_sources", "deliverable_alignment"]
# Short fixture tokens: real ones are longer, and the page must never print either kind in full.
NEW_TOKEN = "tan_fixture_new"
CACHED_TOKEN = "tan_fixture_old"
TESSERA_BUTTONS = ["#ngo-submit-btn", "#worker-run-all-btn", "#worker-btn-1", "#worker-btn-2", "#worker-btn-3",
                   "#worker-btn-4", "#persona-persist-btn", "#tasks-refresh-btn", "#nouns-refresh-btn",
                   '[data-cli-cmd="ngo submit clinic"]', '[data-cli-cmd="worker claim"]',
                   '[data-cli-cmd="worker conflict"]', '[data-cli-cmd="objects ls"]', '[data-cli-cmd="tasks ls"]']
PAGE_TEXT = "() => document.body.textContent"


def problem(status, code, detail, headers=None):
    return status, headers or {}, {"type": "about:blank", "status": status, "code": code, "detail": detail}


class FakeServices:
    """Answers like the deployed services do (shapes taken from their sources), and records every request."""

    def __init__(self):
        self.requests = []
        self.overrides = []  # (method, host, path regex, handler); the newest match wins
        self.tasks = 0
        self.last_task = None
        self.versions = {}

    def on(self, method, host, pattern, handler):
        self.overrides.insert(0, (method, host, re.compile(pattern), handler))

    def calls(self, method, host, pattern):
        rx = re.compile(pattern)
        return [r for r in self.requests if r["method"] == method and r["host"] == host and rx.search(r["path"])]

    def answer(self, method, host, path, body, headers):
        for m, h, rx, handler in self.overrides:
            if m == method and h == host and rx.search(path):
                return handler(path, body, headers)
        return self.default(method, host, path, body)

    def default(self, method, host, path, body):
        now = time.time()
        if host == TESSERA:
            if path == "/v1/session/anonymous":
                return 201, {}, {"session_token": NEW_TOKEN, "namespace": "demo.a_fixturenew", "principal_id": "a_fixturenew",
                                 "expires_at": now + 3600, "persisted": True}
            if path == "/v1/me":
                return 200, {}, {"principal_kind": "anonymous", "namespace": "demo.a_fixtureold",
                                 "session_expires_at": now + 3000}
            record = re.fullmatch(r"/ns/[^/]+/v1/stores/([^/]+)/records/([^/]+)", path)
            if record:
                key = record.group(1) + "/" + record.group(2)
                expected = body.get("expected_version")
                head = self.versions.get(key, 0)
                if expected is not None and expected != head:
                    return problem(409, "version_conflict", f"expected version {expected}, head is {head}")
                self.versions[key] = head + 1
                return 200, {}, {"store": record.group(1), "key": record.group(2), "version": head + 1}
            if path.endswith("/v1/tasks"):
                self.tasks += 1
                self.last_task = f"t_fixture_{self.tasks}"
                return 201, {}, {"task_id": self.last_task}
            if path.endswith("/v1/tasks/claim"):
                return 200, {}, {"task_id": self.last_task, "fencing_token": 1, "worker": body.get("worker"),
                                 "expires_at": now + 90}
            if path.endswith("/v1/tasks/heartbeat"):
                return problem(409, "stale_lease", "lease is not live")
            if path.endswith("/v1/tasks/submit"):
                return 200, {}, {"task_id": body.get("task_id"), "fencing_token": body.get("fencing_token"),
                                 "ok": True, "receipt_hash": "ab" * 32, "state_after": "done"}
            if path.endswith("/v1/tasks/cancel"):
                return 200, {}, {"task_id": body.get("task_id"), "state": "cancelled"}
            if path == "/mcp":
                tool = body["params"]["name"]
                data = {"put_record": {"record": {"version": 1}}, "search_nouns": {"scents": []},
                        "list_verbs": {"verbs": []}}.get(tool, {})
                return 200, {}, {"jsonrpc": "2.0", "id": body.get("id"),
                                 "result": {"content": [{"type": "text", "text": json.dumps(data)}],
                                            "structuredContent": data, "isError": False}}
        if host == HERMA and path == "/api/preview":
            return 200, {}, {
                "persisted": False, "wire_format": "chat_completions",
                "matches": [{"prov_id": "PROV-FIXTURE-BOUNDARY", "version": 3, "score": 0.5, "matched_tiers": ["keyword"]}],
                "augmented_payload": {"model": "fixture-model", "messages": [
                    {"role": "system", "content": "FIXTURE SYSTEM TEXT: keep crisis steps human_only."},
                    {"role": "user", "content": body.get("prompt")}]},
                "responded_directly": False, "direct_response_text": None, "shimmed_context_refs": []}
        if host == ERANOS and path == "/api/practice":
            return 200, {}, {"passed": True, "persisted": False, "issues": [], "checks_run": CHECKS,
                             "receipt_sha256": "cd" * 32, "receipt_scope": "validation_outcome"}
        return problem(404, "not_found", "no fake for " + method + " " + path)


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *args) -> None:
        pass


@unittest.skipIf(sync_playwright is None, "needs the Playwright package")
class Studio(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Quiet, directory=str(SITE)))
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}/"
        cls.playwright = sync_playwright().start()
        try:
            launch = {"executable_path": os.environ["CHROMIUM_PATH"]} if os.environ.get("CHROMIUM_PATH") else {}
            cls.browser = cls.playwright.chromium.launch(**launch)
        except Exception as error:  # pragma: no cover - no browser installed
            cls.playwright.stop()
            cls.server.shutdown()
            cls.server.server_close()
            raise unittest.SkipTest("needs Playwright's Chromium: " + str(error).splitlines()[0])

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        self.page_errors = []

    def tearDown(self):
        self.assertEqual([], self.page_errors, "the page threw")

    def open(self, fake, cached=None):
        ctx = self.browser.new_context(viewport={"width": 1440, "height": 900})
        self.addCleanup(ctx.close)
        if cached is not None:
            ctx.add_init_script("localStorage.setItem('ta_amps_demo_session_v1', %s)" % json.dumps(json.dumps(cached)))
        page = ctx.new_page()
        page.set_default_timeout(WAIT_MS)
        page.on("pageerror", lambda error: self.page_errors.append(str(error)))

        def handle(route, request):
            url = urlsplit(request.url)
            if request.url.startswith(self.base):
                return route.continue_()
            if url.hostname not in (TESSERA, HERMA, ERANOS):
                return route.abort()
            if request.method == "OPTIONS":
                return route.fulfill(status=204, headers=CORS)
            body = json.loads(request.post_data) if request.post_data else {}
            fake.requests.append({"method": request.method, "host": url.hostname, "path": url.path,
                                  "headers": request.headers, "body": body})
            outcome = fake.answer(request.method, url.hostname, url.path, body, request.headers)
            if outcome == "network-error":
                return route.abort("failed")
            status, headers, payload = outcome
            route.fulfill(status=status, headers={**CORS, "content-type": "application/json", **headers},
                          body=json.dumps(payload))

        page.route("**/*", handle)
        page.goto(self.base + "studio/")
        return page

    def pill_state(self, page, wanted):
        page.wait_for_function("s => document.getElementById('session-pill').dataset.state === s", arg=wanted)

    def assert_no_simulation(self, page):
        text = page.evaluate(PAGE_TEXT)
        for word in ("Fallback", "fallback", "simulat", "Simulat"):
            self.assertNotIn(word, text)
        return text

    def disabled(self, page, selector):
        return page.eval_on_selector(selector, "el => el.disabled")

    def step(self, page, num):
        return page.eval_on_selector("#ngo-step-%d" % num, "el => el.dataset.status")

    # (a) Tessera says no new session: wait honestly, with Tessera's own Retry-After ----------------------------

    def test_a_rate_limited_session_waits_with_retry_after_and_never_says_connected(self):
        fake = FakeServices()
        fake.on("POST", TESSERA, r"^/v1/session/anonymous$", lambda *a: problem(
            429, "rate_limited", "anonymous session mint quota exceeded", {"retry-after": "30"}))
        page = self.open(fake)
        self.pill_state(page, "waiting")
        text = self.assert_no_simulation(page)
        self.assertNotIn("Connected", text)
        pill = page.inner_text("#session-pill")
        self.assertIn("Waiting for a demo session", pill)
        self.assertIn("at most 10 new demo sessions per address per hour", pill)
        self.assertIn("HTTP 429", pill)
        self.assertRegex(pill, r"Trying again in 0:(30|29|28)")
        self.assertTrue(page.is_visible("#session-retry-btn"))
        for selector in TESSERA_BUTTONS:
            self.assertTrue(self.disabled(page, selector), selector + " should be off while waiting")
        page.click("#tab-btn-ngo")
        self.assertIn("off while the page waits for a demo session", page.inner_text("#panel-ngo"))
        # Herma needs no session, so the chat still works.
        self.assertFalse(self.disabled(page, "#chat-send-btn"))
        # Nothing was queued: one mint, and nothing else went to Tessera.
        self.assertEqual(1, len([r for r in fake.requests if r["host"] == TESSERA]))
        # The countdown is live.
        first = page.inner_text("#session-countdown")
        page.wait_for_function("t => document.getElementById('session-countdown').textContent !== t", arg=first)

        # Try now asks again; once Tessera opens a session, the buttons come back.
        fake.on("POST", TESSERA, r"^/v1/session/anonymous$", lambda p, b, h: fake.default("POST", TESSERA, p, b))
        page.click("#session-retry-btn")
        self.pill_state(page, "live")
        self.assertIn("Connected", page.inner_text("#session-pill"))
        for selector in TESSERA_BUTTONS:
            if selector != "#worker-heartbeat-btn":
                self.assertFalse(self.disabled(page, selector), selector + " should be on once live")
        self.assertEqual(2, len(fake.calls("POST", TESSERA, r"^/v1/session/anonymous$")))

    # (b) A session opened by this page, then real-looking answers all the way through ----------------------------

    def test_b_opened_session_is_live_and_the_ngo_run_shows_what_the_services_returned(self):
        fake = FakeServices()
        page = self.open(fake)
        self.pill_state(page, "live")
        pill = page.inner_text("#session-pill")
        self.assertIn("Connected", pill)
        self.assertIn("opened by this page", pill)
        self.assertNotIn(NEW_TOKEN, page.evaluate(PAGE_TEXT))

        page.click("#tab-btn-ngo")
        page.click("#ngo-submit-btn")
        page.wait_for_function("document.getElementById('ngo-pipeline-badge').dataset.state === 'held_for_person'")
        self.assertEqual(["done"] * 5 + ["held"], [self.step(page, n) for n in range(1, 7)])
        steps = page.inner_text("#ngo-steps-list")
        self.assertIn("Tessera enqueued task t_fixture_1", steps)
        self.assertIn("Herma matched PROV-FIXTURE-BOUNDARY v3", steps)
        self.assertIn("Eranos ran 8 checks", steps)
        self.assertIn("state_after done", steps)
        self.assertIn("This browser, as worker agora-studio-browser", steps)
        claim = fake.calls("POST", TESSERA, r"/v1/tasks/claim$")[0]
        self.assertEqual("agora-studio-browser", claim["body"]["worker"])
        self.assertIn("Bearer " + NEW_TOKEN, claim["headers"]["authorization"])
        practice = fake.calls("POST", ERANOS, r"^/api/practice$")[0]["body"]["draft"]
        self.assertEqual(("agora-studio-preset", "a_fixturenew"), (practice["drafted_by"], practice["drafted_by_key"]))
        put = fake.calls("POST", TESSERA, r"^/mcp$")[0]["body"]["params"]
        self.assertEqual(("put_record", "demo.kits"), (put["name"], put["arguments"]["store_name"]))
        self.assert_no_simulation(page)

        # The approval writes a real review Task Object and shows its version.
        page.click("#ngo-approve-btn")
        page.wait_for_function("document.getElementById('ngo-pipeline-badge').dataset.state === 'approved'")
        self.assertIn("Review Task Object stored: demo.reviews/", page.eval_on_selector("#ngo-human-gate", "el => el.textContent"))
        self.assertEqual(1, len(fake.calls("POST", TESSERA, r"/v1/stores/demo\.reviews/records/")))

    # (c) The run stops at the first failed call -------------------------------------------------------------------

    def test_c_a_500_on_step_2_halts_the_run_with_the_real_status(self):
        fake = FakeServices()
        fake.on("POST", TESSERA, r"/v1/tasks$", lambda *a: problem(500, "internal_error", "request could not be completed"))
        page = self.open(fake)
        self.pill_state(page, "live")
        page.click("#tab-btn-ngo")
        page.click("#ngo-submit-btn")
        page.wait_for_function("document.getElementById('ngo-pipeline-badge').dataset.state === 'failed'")
        self.assertEqual("done", self.step(page, 1))
        self.assertEqual("failed", self.step(page, 2))
        self.assertIn("HTTP 500", page.inner_text("#ngo-step-2"))
        self.assertIn("internal_error: request could not be completed", page.inner_text("#ngo-step-2"))
        for n in range(3, 7):
            self.assertNotEqual("done", self.step(page, n))
            self.assertIn("Not run", page.inner_text("#ngo-step-%d" % n))
        self.assertIn("HTTP 500", page.inner_text("#ngo-pipeline-badge"))
        # Nothing after step 2 was sent.
        self.assertEqual([], fake.calls("POST", TESSERA, r"/v1/tasks/(claim|submit)$"))
        self.assertEqual([], [r for r in fake.requests if r["host"] in (HERMA, ERANOS)])
        self.assertTrue(page.eval_on_selector("#ngo-human-gate", "el => el.hidden"))
        self.assert_no_simulation(page)

    # (d) No answer at all: a status-0 entry with the real error, and no made-up text ------------------------------

    def test_d_a_network_failure_is_a_status_0_entry_and_nothing_is_made_up(self):
        fake = FakeServices()
        fake.on("POST", TESSERA, r"^/v1/session/anonymous$", lambda *a: "network-error")
        fake.on("POST", HERMA, r"^/api/preview$", lambda *a: "network-error")
        page = self.open(fake)
        self.pill_state(page, "waiting")
        pill = page.inner_text("#session-pill")
        self.assertIn("no answer from tessera.ta-amps.workers.dev", pill)
        self.assertRegex(pill, r"Trying again in 0:(30|29|28)")  # no Retry-After: the backoff starts at 30 s
        self.assertEqual(1, page.locator('#wire-log-list .w-status[data-code="0"]').count())

        page.fill("#chat-input", "Explain Tasks and Task Objects simply")
        page.click("#chat-send-btn")
        page.wait_for_selector('.chat-turn .shim-card[data-ok="false"]')
        card = page.inner_text(".chat-turn")
        self.assertIn("Herma did not answer the preview: no answer from herma.ta-amps.workers.dev", card)
        self.assertNotIn("matched", card.replace("0 provisions matched", ""))
        self.assertEqual(2, page.locator('#wire-log-list .w-status[data-code="0"]').count())
        text = self.assert_no_simulation(page)
        self.assertNotIn("Connected", text)

    # (e) A saved session is checked before it is called Connected ------------------------------------------------

    def test_e_a_saved_session_rejected_with_401_is_cleared_and_a_new_one_opened(self):
        fake = FakeServices()
        fake.on("GET", TESSERA, r"^/v1/me$", lambda *a: problem(401, "unauthorized", "the key is unknown, expired or revoked"))
        cached = {"session_token": CACHED_TOKEN, "namespace": "demo.a_fixtureold", "expires_at": time.time() + 3000}
        page = self.open(fake, cached=cached)
        self.pill_state(page, "live")
        check = fake.calls("GET", TESSERA, r"^/v1/me$")
        self.assertEqual(1, len(check))
        self.assertEqual("Bearer " + CACHED_TOKEN, check[0]["headers"]["authorization"])
        self.assertEqual(1, len(fake.calls("POST", TESSERA, r"^/v1/session/anonymous$")))
        self.assertIn("opened by this page", page.inner_text("#session-pill"))
        saved = json.loads(page.evaluate("localStorage.getItem('ta_amps_demo_session_v1')"))
        self.assertEqual("demo.a_fixturenew", saved["namespace"])
        self.assertNotIn(CACHED_TOKEN, page.evaluate(PAGE_TEXT))

    def test_e_a_saved_session_tessera_accepts_is_used_without_a_new_mint(self):
        fake = FakeServices()
        cached = {"session_token": CACHED_TOKEN, "namespace": "demo.a_fixtureold", "expires_at": time.time() + 3000}
        page = self.open(fake, cached=cached)
        self.pill_state(page, "live")
        self.assertIn("saved session, checked by this page", page.inner_text("#session-pill"))
        self.assertEqual([], fake.calls("POST", TESSERA, r"^/v1/session/anonymous$"))

    def test_a_401_on_a_later_call_leaves_live_when_no_new_session_opens(self):
        fake = FakeServices()
        page = self.open(fake)
        self.pill_state(page, "live")
        fake.on("POST", TESSERA, r"/v1/stores/", lambda *a: problem(401, "unauthorized", "the key is unknown, expired or revoked"))
        fake.on("POST", TESSERA, r"^/v1/session/anonymous$", lambda *a: problem(
            429, "rate_limited", "anonymous session mint quota exceeded", {"retry-after": "120"}))
        page.click("#tab-btn-ngo")
        page.click("#ngo-submit-btn")
        page.wait_for_function("document.getElementById('ngo-pipeline-badge').dataset.state === 'failed'")
        self.assertIn("HTTP 401", page.inner_text("#ngo-step-1"))
        self.pill_state(page, "waiting")
        self.assertNotIn("Connected", page.evaluate(PAGE_TEXT))
        self.assertRegex(page.inner_text("#session-pill"), r"Trying again in (2:00|1:59|1:58)")
        self.assertIsNone(page.evaluate("localStorage.getItem('ta_amps_demo_session_v1')"))

    # Herma's card holds only what Herma returned -----------------------------------------------------------------

    def test_herma_card_shows_only_what_herma_returned(self):
        fake = FakeServices()
        page = self.open(fake)
        page.fill("#chat-input", "Draft a clinic intake checklist")
        page.click("#chat-send-btn")
        page.wait_for_selector('.chat-turn .shim-card[data-ok="true"]')
        card = page.inner_text(".chat-turn")
        self.assertIn("PROV-FIXTURE-BOUNDARY v3 · score 0.5", card)
        self.assertIn("FIXTURE SYSTEM TEXT: keep crisis steps human_only.", card)

        fake.on("POST", HERMA, r"^/api/preview$", lambda p, b, h: (200, {}, {
            "persisted": False, "matches": [], "responded_directly": False, "direct_response_text": None,
            "augmented_payload": {"model": "fixture-model", "messages": [{"role": "user", "content": b["prompt"]}]}}))
        page.fill("#chat-input", "Something Herma has no provision for")
        page.click("#chat-send-btn")
        page.wait_for_function("document.querySelectorAll('.chat-turn').length === 2")
        second = page.locator(".chat-turn").nth(1).inner_text()
        self.assertIn("Herma matched nothing and returned the payload unchanged.", second)
        self.assertNotIn("FIXTURE SYSTEM TEXT", second)
        self.assert_no_simulation(page)

    # The worker lab names this browser and says what Tessera answered to the stale overwrite ----------------------

    def test_stale_overwrite_reports_tessera_answers(self):
        fake = FakeServices()
        page = self.open(fake)
        self.pill_state(page, "live")
        page.click("#tab-btn-worker")
        self.assertIn("Send a Stale Overwrite", page.inner_text("#worker-btn-4"))
        page.click("#worker-run-all-btn")
        page.wait_for_selector("#worker-conflict-banner:not([hidden])")
        banner = page.inner_text("#worker-conflict-banner")
        self.assertIn("Tessera refused the stale overwrite: HTTP 409 version_conflict", banner)
        self.assertIn("HTTP 409 stale_lease", banner)
        stale = fake.calls("POST", TESSERA, r"/v1/stores/demo\.artifacts/records/")[-1]["body"]
        self.assertEqual(1, stale["expected_version"])
        self.assertIn("This browser, as worker agora-studio-browser", page.inner_text("#worker-event-feed"))
        self.assert_no_simulation(page)


class StaticSource(unittest.TestCase):
    """(f) The page's code keeps no simulation path and names no worker that did not run."""

    def test_f_studio_js_has_no_simulation_or_invented_worker(self):
        source = STUDIO_JS.read_text(encoding="utf-8")
        for token in ("fallback", "simulated: true", "sim_", "Fallback", "muse-code-sandbox"):
            self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main()
