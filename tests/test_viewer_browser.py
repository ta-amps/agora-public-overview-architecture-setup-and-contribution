"""The deck viewer in a real browser: letter shortcuts, browser zoom, larger slides and contrast.

These tests need the Playwright package and its Chromium. Without them they are skipped, as in this
repository's CI, which installs nothing beyond the standard library. Run them locally with
`python -m unittest tests.test_viewer_browser -v` from a Python that has Playwright. They serve site/ on
127.0.0.1 and abort every other request, so they make no network calls; the pages fall back to system fonts.
"""
from __future__ import annotations

import json
import threading
import unittest
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

SITE = Path(__file__).resolve().parents[1] / "site"
DECK = "decks/overview-and-architecture/"

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover - depends on the environment
    sync_playwright = None

STATE = """() => ({
  notes: document.querySelector('.deck').classList.contains('show-notes'),
  outline: document.getElementById('deck-outline').classList.contains('is-open'),
  current: document.querySelector('[data-current]').textContent,
  scale: parseFloat(getComputedStyle(document.querySelector('[data-stage]')).getPropertyValue('--slide-scale')),
  pageWide: document.documentElement.scrollWidth > innerWidth,
  stageWide: document.querySelector('[data-stage]').scrollWidth > document.querySelector('[data-stage]').clientWidth + 1,
  scrollLeft: document.querySelector('[data-stage]').scrollLeft,
})"""


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *args) -> None:
        pass

    def handle(self) -> None:
        try:
            super().handle()
        except (BrokenPipeError, ConnectionResetError):
            pass  # the browser stopped reading a video it does not play


class LocalSite(unittest.TestCase):
    """site/ on 127.0.0.1 and one Chromium, shared by a test class; every other request is aborted."""

    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Quiet, directory=str(SITE)))
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}/"
        cls.playwright = sync_playwright().start()
        try:
            cls.browser = cls.playwright.chromium.launch()
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


@unittest.skipIf(sync_playwright is None, "needs the Playwright package")
class Viewer(LocalSite):
    def open(self, path=DECK, **context):
        ctx = self.browser.new_context(**context)
        self.addCleanup(ctx.close)
        page = ctx.new_page()
        page.route("**/*", lambda route: route.continue_() if route.request.url.startswith(self.base) else route.abort())
        page.goto(self.base + path)
        page.wait_for_function("document.querySelector('[data-help]') && !document.querySelector('[data-help]').hidden")
        return page

    def state(self, page):
        return page.evaluate(STATE)

    # WCAG 2.1.4: N and O act only with focus on the deck, and can be turned off ------------------------------

    def test_letter_keys_wait_for_focus_on_the_deck(self):
        page = self.open(viewport={"width": 1440, "height": 900})
        page.evaluate("document.activeElement && document.activeElement.blur()")
        page.keyboard.press("n")
        page.keyboard.press("o")
        self.assertEqual((False, False), (self.state(page)["notes"], self.state(page)["outline"]))
        # The arrow keys are not letter keys: they still change slides from anywhere on the page.
        page.keyboard.press("ArrowRight")
        self.assertEqual("2", self.state(page)["current"])
        # Keys typed in the agent banner stay with it.
        page.focus(".agent-banner [data-copy]")
        page.keyboard.press("n")
        self.assertFalse(self.state(page)["notes"])
        # With the slide focused, or a deck button, they work.
        page.focus(".slide.is-current")
        page.keyboard.press("n")
        self.assertTrue(self.state(page)["notes"])
        page.keyboard.press("ArrowRight")
        self.assertEqual("3", self.state(page)["current"])
        page.focus("[data-notes-toggle]")
        page.keyboard.press("o")
        self.assertTrue(self.state(page)["outline"])
        page.keyboard.press("Escape")
        self.assertFalse(self.state(page)["outline"])

    def test_the_letter_shortcuts_switch_turns_them_off_and_is_remembered(self):
        page = self.open(viewport={"width": 1440, "height": 900})
        switch = page.get_by_label("Letter shortcuts")
        self.assertTrue(switch.is_visible())
        self.assertTrue(switch.is_checked())
        switch.uncheck()
        page.focus(".slide.is-current")
        page.keyboard.press("n")
        page.keyboard.press("o")
        self.assertEqual((False, False), (self.state(page)["notes"], self.state(page)["outline"]))
        page.keyboard.press("ArrowRight")
        self.assertEqual("2", self.state(page)["current"])
        page.reload()
        page.wait_for_function("!document.querySelector('[data-help]').hidden")
        self.assertFalse(page.get_by_label("Letter shortcuts").is_checked())
        page.focus(".slide.is-current")
        page.keyboard.press("n")
        self.assertFalse(self.state(page)["notes"])
        page.get_by_label("Letter shortcuts").check()
        page.focus(".slide.is-current")
        page.keyboard.press("n")
        self.assertTrue(self.state(page)["notes"])

    # WCAG 1.4.4: browser zoom enlarges slide text -----------------------------------------------------------

    def zoom_ratio(self, width, height, large=False):
        """Device pixels of 24 px slide text at 200% zoom over 100%, in the same window. Zoom halves the window in
        CSS pixels and doubles the device pixel ratio, which is how the acceptance pass measured it."""
        shown = []
        for zoom in (1, 2):
            page = self.open(viewport={"width": width // zoom, "height": height // zoom}, device_scale_factor=zoom)
            if large:
                page.click("[data-large-toggle]")
            state = self.state(page)
            self.assertFalse(state["pageWide"], (width, zoom))
            shown.append(24 * state["scale"] * zoom)
        return shown[1] / shown[0]

    def test_zoom_to_200_percent_doubles_slide_text_on_laptop_windows(self):
        # 1.43 and 1.80 before: the viewer refitted each slide to the smaller window.
        self.assertGreaterEqual(self.zoom_ratio(1440, 900), 1.95)
        self.assertGreaterEqual(self.zoom_ratio(1280, 720), 1.95)
        # A large window shows more than half size at 100%, so zoom adds less there; it still enlarges.
        self.assertGreaterEqual(self.zoom_ratio(1920, 1080), 1.6)

    def test_larger_slides_show_full_size_and_zoom_in_step(self):
        self.assertAlmostEqual(2.0, self.zoom_ratio(1920, 1080, large=True), places=3)
        page = self.open(viewport={"width": 1440, "height": 900})
        button = page.get_by_role("button", name="Larger slides")
        button.click()
        self.assertEqual("true", button.get_attribute("aria-pressed"))
        self.assertEqual(1, self.state(page)["scale"])
        page.reload()
        page.wait_for_function("!document.querySelector('[data-help]').hidden")
        self.assertEqual(1, self.state(page)["scale"])
        page.get_by_role("button", name="Larger slides").click()
        self.assertLess(self.state(page)["scale"], 1)

    def test_a_slide_wider_than_the_window_scrolls_inside_its_stage(self):
        # 200% zoom on a 1440 by 900 window: the slide keeps half size and scrolls sideways; the page does not.
        page = self.open(viewport={"width": 720, "height": 450}, device_scale_factor=2)
        state = self.state(page)
        self.assertTrue(state["stageWide"])
        self.assertFalse(state["pageWide"])
        # The arrow keys scroll the slide first, then change slides, which starts at its left edge.
        page.keyboard.press("ArrowRight")
        state = self.state(page)
        self.assertEqual("1", state["current"])
        self.assertGreater(state["scrollLeft"], 0)
        presses = 0
        while self.state(page)["current"] == "1" and presses < 5:
            page.keyboard.press("ArrowRight")
            presses += 1
        state = self.state(page)
        self.assertEqual("2", state["current"])
        self.assertEqual(0, state["scrollLeft"])
        # At a slide's left edge, the left arrow goes back a slide; Page Down always moves on.
        page.keyboard.press("ArrowLeft")
        self.assertEqual("1", self.state(page)["current"])
        page.keyboard.press("PageDown")
        page.keyboard.press("PageDown")
        self.assertEqual("3", self.state(page)["current"])
        # At 320 CSS pixels, the 400% zoom of a 1280 window, the page still never scrolls sideways.
        page = self.open(viewport={"width": 320, "height": 640}, device_scale_factor=4)
        self.assertFalse(self.state(page)["pageWide"])

    def test_phones_and_narrow_windows_still_fit_the_slide(self):
        phone = self.open(viewport={"width": 390, "height": 844}, device_scale_factor=3, is_mobile=True, has_touch=True)
        state = self.state(phone)
        self.assertLessEqual(state["scale"], 390 / 1920)
        self.assertFalse(state["stageWide"])
        self.assertTrue(state["notes"])
        narrow = self.open(viewport={"width": 960, "height": 900})
        self.assertFalse(self.state(narrow)["stageWide"])

    # WCAG 1.4.3: the notes heading on the stage ----------------------------------------------------------------

    def test_the_speaker_notes_heading_passes_contrast_in_both_themes(self):
        for scheme, minimum in (("light", 4.5), ("dark", 4.5)):
            page = self.open(viewport={"width": 390, "height": 844}, color_scheme=scheme, is_mobile=True, has_touch=True)
            ratio = page.evaluate("""() => {
              const rgb = c => c.match(/\\d+(\\.\\d+)?/g).slice(0, 3).map(Number);
              const lum = c => { const [r, g, b] = rgb(c).map(v => v / 255).map(v => v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4);
                return 0.2126 * r + 0.7152 * g + 0.0722 * b; };
              const heading = document.querySelector('.slide.is-current .slide-notes h2');
              const fg = lum(getComputedStyle(heading).color);
              const bg = lum(getComputedStyle(document.querySelector('[data-stage]')).backgroundColor);
              return (Math.max(fg, bg) + 0.05) / (Math.min(fg, bg) + 0.05);
            }""")
            self.assertGreaterEqual(ratio, minimum, scheme)

    # Hunt, October 30: fragments that name no slide ----------------------------------------------------------

    def errors_on(self, page):
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        return errors

    def test_a_broken_percent_escape_in_the_fragment_opens_the_first_slide(self):
        # Before: "URI malformed" stopped the viewer, and no slide was on show at all.
        for fragment in ("#%E0%A4%A", "#%"):
            with self.subTest(fragment=fragment):
                page = self.open(DECK + fragment, viewport={"width": 1440, "height": 900})
                self.assertEqual(1, page.locator("[data-stage] .slide.is-current").count())
                self.assertEqual("1", self.state(page)["current"])
                errors = self.errors_on(page)
                page.keyboard.press("ArrowRight")
                page.evaluate("location.hash = '#%E0%A4'")
                page.wait_for_timeout(100)
                self.assertEqual("2", self.state(page)["current"])
                self.assertEqual([], errors)

    def test_the_skip_link_keeps_the_slide_on_show(self):
        # Before: the skip link's #main sent every deck back to slide 1.
        page = self.open(DECK + "#slide-6", viewport={"width": 1440, "height": 900})
        self.assertEqual("6", self.state(page)["current"])
        page.focus(".skip-link")
        page.keyboard.press("Enter")
        page.wait_for_timeout(100)
        self.assertEqual("#main", page.evaluate("location.hash"))
        self.assertEqual("6", self.state(page)["current"])
        # A fragment that names a slide still moves to it, wherever the deck's order puts that slide.
        order = json.loads((SITE / DECK / "source" / "deck.json").read_text(encoding="utf-8"))["order"]
        page.evaluate("location.hash = '#map'")
        page.wait_for_timeout(100)
        self.assertEqual(str(order.index("map") + 1), self.state(page)["current"])


@unittest.skipIf(sync_playwright is None, "needs the Playwright package")
class SitePages(LocalSite):
    """The home page's light and dark switch and film cuts (site.js), in the same local browser."""

    def open(self, path="", **context):
        ctx = self.browser.new_context(**context)
        self.addCleanup(ctx.close)
        page = ctx.new_page()
        page.route("**/*", lambda route: route.continue_() if route.request.url.startswith(self.base) else route.abort())
        page.goto(self.base + path)
        page.wait_for_function("!document.querySelector('[data-mode-toggle]').hidden")
        return page

    def mode(self, page):
        return page.evaluate("""() => ({mode: document.documentElement.dataset.mode || null,
          stored: localStorage.getItem('ta-amps-mode'), pressed: document.querySelector('[data-mode-toggle]').getAttribute('aria-pressed'),
          background: getComputedStyle(document.body).backgroundColor})""")

    def test_a_choice_that_matches_the_system_follows_the_system_again(self):
        page = self.open(color_scheme="light")
        light = self.mode(page)["background"]
        page.click("[data-mode-toggle]")
        chosen = self.mode(page)
        self.assertEqual(("dark", "dark", "true"), (chosen["mode"], chosen["stored"], chosen["pressed"]))
        page.click("[data-mode-toggle]")
        back = self.mode(page)
        # Before: "light" was stored for good, so the page could never follow the system again.
        self.assertEqual((None, None, "false", light), (back["mode"], back["stored"], back["pressed"], back["background"]))
        page.emulate_media(color_scheme="dark")
        # The media query's change event arrives a moment later; the button then reads dark.
        page.wait_for_function("document.querySelector('[data-mode-toggle]').getAttribute('aria-pressed') === 'true'", timeout=3000)
        self.assertNotEqual(light, self.mode(page)["background"])
        page.reload()
        page.wait_for_function("!document.querySelector('[data-mode-toggle]').hidden")
        self.assertEqual(None, self.mode(page)["stored"])

    def cut(self, page):
        return page.evaluate("""() => ({pressed: document.querySelector('[data-cut][aria-pressed=true]').getAttribute('data-cut'),
          src: document.querySelector('.film-video source').getAttribute('src'), search: location.search,
          captions: Array.from(document.querySelector('.film-video').textTracks).filter(t => t.kind === 'captions').map(t => t.mode)})""")

    def test_a_cut_can_be_linked_and_keeps_the_caption_choice(self):
        page = self.open("?cut=short", viewport={"width": 1280, "height": 800})
        state = self.cut(page)
        self.assertEqual(("short", "video/2026-10-30/short-v2/eranos-60s.mp4", "?cut=short", ["showing"]),
                         (state["pressed"], state["src"], state["search"], state["captions"]))
        # The viewer turns captions off; switching cuts keeps them off. Before: they came back on.
        page.evaluate("Array.from(document.querySelector('.film-video').textTracks).forEach(t => { t.mode = 'hidden'; })")
        page.click("[data-cut=full]")
        state = self.cut(page)
        self.assertEqual(("full", "", ["hidden"]), (state["pressed"], state["search"], state["captions"]))
        page.click("[data-cut=short]")
        self.assertEqual("?cut=short", self.cut(page)["search"])
        # An unknown cut opens the default one.
        page = self.open("?cut=nope", viewport={"width": 1280, "height": 800})
        self.assertEqual(("full", ["showing"]), (self.cut(page)["pressed"], self.cut(page)["captions"]))


if __name__ == "__main__":
    unittest.main()
