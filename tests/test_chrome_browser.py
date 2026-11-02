"""The agent banner, the header and the library in a real browser (October 31, 2026 boards and findings).

Like test_viewer_browser, these need Playwright's Chromium, serve site/ on 127.0.0.1 and abort every other
request, so they make no network calls. Without Playwright they are skipped.
"""
from __future__ import annotations

import unittest

try:
    from test_viewer_browser import LocalSite, sync_playwright
except ImportError:  # run as tests.test_chrome_browser from the repository root
    from tests.test_viewer_browser import LocalSite, sync_playwright

LINE = "Read https://agora.eranosforgood.org/llms.txt and follow it."


@unittest.skipIf(sync_playwright is None, "needs the Playwright package")
class Chrome(LocalSite):
    def open(self, path="", grant_clipboard=False, **context):
        ctx = self.browser.new_context(**context)
        self.addCleanup(ctx.close)
        if grant_clipboard:
            ctx.grant_permissions(["clipboard-read", "clipboard-write"], origin=self.base.rstrip("/"))
        page = ctx.new_page()
        page.route("**/*", lambda route: route.continue_() if route.request.url.startswith(self.base) else route.abort())
        page.goto(self.base + path)
        page.wait_for_selector("ta-agent-banner[data-ready]")
        return page

    def test_the_banner_is_one_thin_line_above_the_header_on_desktop_and_phone(self):
        for viewport, height in (({"width": 1280, "height": 720}, 37), ({"width": 390, "height": 844}, 41)):
            page = self.open(viewport=viewport)
            box = page.locator("ta-agent-banner").bounding_box()
            header = page.locator(".site-header").bounding_box()
            self.assertEqual(0, box["y"], viewport)
            self.assertLessEqual(box["height"], height, viewport)  # 36 px, or 40 px under 720 px, plus its rule
            self.assertLessEqual(box["y"] + box["height"], header["y"] + 0.5, viewport)
            self.assertFalse(page.evaluate("document.documentElement.scrollWidth > innerWidth"), viewport)
        # It scrolls away with the page: never sticky or fixed.
        self.assertEqual("relative", page.evaluate("getComputedStyle(document.querySelector('ta-agent-banner')).position"))

    def test_the_banner_shows_a_focus_ring_and_its_hairline(self):
        # Review B3 (Nov 1): the banner's theme variables are literal colours, so its shadow CSS gets a real --focus.
        # After the skip link, the next two tab stops are the banner's buttons, and each draws a 3 px blue ring.
        page = self.open("")
        for expected in ("copy", "toggle"):
            page.keyboard.press("Tab")
            if page.evaluate("document.activeElement && document.activeElement.classList.contains('skip-link')"):
                page.keyboard.press("Tab")
            ring = page.evaluate("""() => { const host = document.activeElement;
              const el = host && host.shadowRoot ? host.shadowRoot.activeElement : host;
              const cs = getComputedStyle(el);
              return {cls: el.className, style: cs.outlineStyle, width: cs.outlineWidth, color: cs.outlineColor}; }""")
            self.assertIn(expected, ring["cls"])
            self.assertEqual(("solid", "3px", "rgb(42, 93, 176)"), (ring["style"], ring["width"], ring["color"]), ring)
        line = page.evaluate("getComputedStyle(document.querySelector('ta-agent-banner')).borderBottom")
        self.assertEqual("1px solid rgb(226, 220, 207)", line)

    def test_the_banner_names_its_toggle_and_keeps_only_web_links(self):
        # Review N3: on a phone the toggle shows only its glyph, so it carries its name from the first paint.
        page = self.open(viewport={"width": 390, "height": 844})
        self.assertEqual("How", page.locator("ta-agent-banner .toggle").get_attribute("aria-label"))
        # Review N2: a noun fetched from another site cannot run script through a link.
        hrefs = page.evaluate("""() => {
            const b = document.querySelector("ta-agent-banner");
            return [b.href("javascript:alert(1)"), b.href("data:text/html,x"), b.href("/llms.txt"),
                    b.href("https://eranosforgood.org/connect")];
        }""")
        self.assertEqual(["#", "#"], hrefs[:2])
        self.assertTrue(hrefs[2].endswith("/llms.txt"), hrefs[2])
        self.assertEqual("https://eranosforgood.org/connect", hrefs[3])

    def test_copy_puts_exactly_the_line_on_the_clipboard_and_says_so(self):
        page = self.open(grant_clipboard=True, viewport={"width": 1280, "height": 720})
        page.click("ta-agent-banner button.copy")
        page.wait_for_function("document.querySelector('ta-agent-banner').shadowRoot.querySelector('[role=status]').textContent.length > 0")
        self.assertEqual(LINE, page.evaluate("navigator.clipboard.readText()"))
        self.assertIn("Copied", page.locator("ta-agent-banner button.copy").inner_text())

    def test_a_failed_copy_says_so_opens_the_panel_and_selects_the_line(self):
        page = self.open(viewport={"width": 1280, "height": 720})
        page.evaluate("Object.defineProperty(navigator, 'clipboard', {value: {writeText: () => Promise.reject(new Error('blocked'))}})")
        page.click("ta-agent-banner button.copy")
        page.wait_for_function("document.querySelector('ta-agent-banner').dataset.open === 'true'")
        self.assertIn("Select the line to copy", page.locator("ta-agent-banner button.copy").inner_text())
        self.assertNotIn("Copied", page.locator("ta-agent-banner button.copy").inner_text())
        self.assertEqual(LINE, page.evaluate("String(document.getSelection())"))

    def test_how_opens_a_panel_that_pushes_the_page_down_and_escape_closes_it(self):
        page = self.open(viewport={"width": 1280, "height": 720})
        toggle = page.locator("ta-agent-banner button.toggle")
        before = page.locator(".site-header").bounding_box()["y"]
        self.assertEqual("false", toggle.get_attribute("aria-expanded"))
        toggle.click()
        self.assertEqual("true", toggle.get_attribute("aria-expanded"))
        self.assertGreater(page.locator(".site-header").bounding_box()["y"], before + 100)  # pushed down, no overlay
        panel = page.locator("ta-agent-banner .panel")
        self.assertIn(LINE, panel.inner_text())
        self.assertIn("What it can do here", panel.inner_text())
        page.keyboard.press("Escape")
        self.assertEqual("false", toggle.get_attribute("aria-expanded"))
        self.assertTrue(page.evaluate("document.querySelector('ta-agent-banner').shadowRoot.querySelector('.panel').hidden"))

    def test_without_scripts_the_line_still_points_at_llms_txt(self):
        ctx = self.browser.new_context(java_script_enabled=False)
        self.addCleanup(ctx.close)
        page = ctx.new_page()
        page.route("**/*", lambda route: route.continue_() if route.request.url.startswith(self.base) else route.abort())
        page.goto(self.base)
        self.assertTrue(page.locator("ta-agent-banner .agent-fallback a[href='llms.txt']").is_visible())

    def test_eranos_is_in_the_first_screen_on_desktop_and_phone(self):
        # F31-004: someone landing on Agora finds Eranos at once.
        for viewport in ({"width": 1280, "height": 560}, {"width": 390, "height": 844}):
            page = self.open(viewport=viewport)
            link = page.locator(".eranos-link")
            self.assertTrue(link.is_visible(), viewport)
            self.assertLess(link.bounding_box()["y"] + link.bounding_box()["height"], viewport["height"], viewport)
            self.assertEqual("https://eranosforgood.org/", link.get_attribute("href"))

    def test_the_phone_menu_opens_and_closes_the_links(self):
        page = self.open(viewport={"width": 390, "height": 844})
        nav = page.locator("#site-nav")
        self.assertFalse(nav.is_visible())
        page.click("[data-menu-toggle]")
        self.assertTrue(nav.is_visible())
        self.assertEqual("true", page.get_attribute("[data-menu-toggle]", "aria-expanded"))
        page.click("[data-menu-toggle]")
        self.assertFalse(nav.is_visible())

    def test_the_judge_tour_shows_only_when_asked_and_closes(self):
        # The JudgeTour board: ?tour=judge opens a strip under the header; Agora is step 1, and the next link goes to
        # Eranos's nonprofit journey with the tour still on. Close hides it and drops the parameter.
        page = self.open(viewport={"width": 1280, "height": 720})
        self.assertTrue(page.evaluate("document.querySelector('ta-judge-tour').hidden"))
        page.goto(self.base + "?tour=judge", wait_until="domcontentloaded")
        page.wait_for_selector("ta-judge-tour[data-active=\"true\"]", state="attached")
        tour = page.locator("ta-judge-tour")
        self.assertEqual("1", tour.get_attribute("data-step"))
        self.assertIn("45-second tour", page.locator("ta-judge-tour nav").inner_text())
        self.assertEqual("https://eranosforgood.org/nonprofits?tour=judge", page.locator("ta-judge-tour a").get_attribute("href"))
        self.assertEqual("step", page.locator("ta-judge-tour li").first.get_attribute("aria-current"))
        header = page.locator(".site-header").bounding_box()
        self.assertGreaterEqual(tour.bounding_box()["y"], header["y"] + header["height"] - 1)  # under the header
        # The Studio is the live-queue step, and its next link goes back to Agora with the tour still on.
        page.goto(self.base + "studio/?tour=judge", wait_until="domcontentloaded")
        page.wait_for_selector("ta-judge-tour[data-active=\"true\"]", state="attached")
        self.assertEqual("5", page.locator("ta-judge-tour").get_attribute("data-step"))
        self.assertEqual("https://agora.eranosforgood.org/?tour=judge", page.locator("ta-judge-tour a").get_attribute("href"))
        page.click("ta-judge-tour button")
        self.assertTrue(page.evaluate("document.querySelector('ta-judge-tour').hidden"))
        self.assertNotIn("tour=judge", page.url)

    def test_the_library_is_short_enough_to_paint_at_device_scale_one_and_a_half(self):
        # F31-005: Chrome stopped painting the 15,000 px library partway down at device scale 1.5. Each category
        # now shows one row and a See all link, and the explorer pages twelve results at a time.
        page = self.open("library/", viewport={"width": 1280, "height": 560}, device_scale_factor=1.5)
        page.wait_for_timeout(300)
        height = page.evaluate("document.documentElement.scrollHeight")
        self.assertLess(height * 1.5, 16384)
        groups = page.locator(".lib-group")
        for i in range(groups.count()):
            visible = groups.nth(i).locator(".lib-cards > li:visible").count()
            self.assertLessEqual(visible, 3)
        # The See all link is the category filter: it shows every pack in its category.
        first = page.locator(".lib-group").first
        total = first.locator(".lib-cards > li").count()
        first.locator(".lib-see-all").click()
        self.assertEqual(total, first.locator(".lib-cards > li:visible").count())


if __name__ == "__main__":
    unittest.main()
