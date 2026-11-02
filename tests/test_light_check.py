"""The light check (scripts/light_check.py, make light-check) catches each kind of dark UI that MUST-FOLLOW rule 13
bans, accepts the one brand colour by its token only, and passes a light page. Fixture pages, in a real browser."""
from __future__ import annotations

import base64
import os
import sys
import tempfile
import threading
import unittest
import zlib
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import light_check  # noqa: E402

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # the CI runner has no browser; make light-check itself fails closed without one
    sync_playwright = None

TOKENS = ":root { color-scheme: only light; --paper: #F5F2EA; --text: #11161F; --task-text: #9C4416; } " \
         "body { margin: 0; background: var(--paper); color: var(--text); font: 16px sans-serif; }"


def png(width: int, height: int, rgb: tuple[int, int, int]) -> bytes:
    """A plain one-colour PNG, for the dark picture case."""
    row = b"\x00" + bytes(rgb) * width
    raw = zlib.compress(row * height)
    chunk = lambda kind, data: (struct.pack(">I", len(data)) + kind + data
                                + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", raw) + chunk(b"IEND", b""))


def page(body: str, meta: str = '<meta name="color-scheme" content="only light">', style: str = "") -> str:
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8">{meta}<title>t</title>'
            f"<style>{TOKENS} {style}</style></head><body>{body}</body></html>")


PAGES = {
    "light": page('<main><h1>Light</h1><p>Paper and ink.</p><button style="background:#11161F;color:#fff">Go</button></main>'),
    "scheme": page("<p>x</p>", meta='<meta name="color-scheme" content="light dark">'),
    "no-meta": page("<p>x</p>", meta=""),
    "query": page("<p>x</p>", style="@media (prefers-color-scheme: dark) { body { background: #0b0f16; } }"),
    "panel": page('<section style="background:#1b2230;color:#fff;height:300px">An ink panel</section>'),
    "band": page('<footer style="background:rgba(17,22,31,0.92);height:120px;color:#fff">An ink footer</footer>'),
    "picture": page('<img src="dark.png" width="800" height="400" alt="">'),
    "band": page('<div style="background:#11161F;height:36px;color:#fff">An ink band, 36 px tall</div><p>Paper below.</p>'),
    "thin-ok": page('<div style="background:#11161F;height:6px"></div><a href="#" style="display:block;background:#11161F;color:#fff;height:40px">A full-width ink link</a>'),
    "brand": page('<div style="background:var(--task-text);height:300px;color:#fff">The Task orange, by its token</div>'),
    "near-brand": page('<div style="background:#9C4417;height:300px;color:#fff">Almost the Task orange</div>'),
    "shadow": page('<x-banner></x-banner><script>customElements.define("x-banner", class extends HTMLElement {'
                   'constructor() { super(); this.attachShadow({mode: "open"}).innerHTML = '
                   '"<style>@media (prefers-color-scheme: dark) { div { color: white } }</style><div>b</div>"; } });</script>'),
}


@unittest.skipIf(sync_playwright is None, "needs the Playwright package")
class LightCheck(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        folder = Path(cls.tmp.name)
        for name, html in PAGES.items():
            (folder / f"{name}.html").write_text(html, encoding="utf-8")
        (folder / "dark.png").write_bytes(png(80, 40, (20, 24, 32)))
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), partial(light_check.Quiet, directory=str(folder)))
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        cls.server.shutdown()
        cls.tmp.cleanup()

    def problems(self, name: str, scheme: str = "dark") -> list[str]:
        ctx = self.browser.new_context(viewport=light_check.VIEWPORT, color_scheme=scheme)
        self.addCleanup(ctx.close)
        view = ctx.new_page()
        view.goto(f"{self.base}/{name}.html", wait_until="load")
        probe = view.evaluate(light_check.PROBE, {"share": light_check.SHARE, "dark": light_check.DARK,
                                                  "exemptTokens": list(light_check.EXEMPT_TOKENS)})
        return light_check.judge(view, probe)

    def test_a_light_page_passes_under_both_schemes_with_a_small_ink_button(self):
        self.assertEqual([], self.problems("light", "light"))
        self.assertEqual([], self.problems("light", "dark"))

    def test_each_banned_kind_fails(self):
        expected = {
            "scheme": "color-scheme meta must be one, 'only light'",
            "no-meta": "color-scheme meta must be one, 'only light'",
            "query": "dark media query",
            "panel": "dark background on section",
            "band": "dark background on footer",
            "picture": "dark picture img",
            "near-brand": "dark background on div",
            "band": "dark band on div",
            "shadow": "dark media query",
        }
        for name, words in expected.items():
            with self.subTest(name):
                found = self.problems(name)
                self.assertTrue(any(words in line for line in found), found)

    def test_a_hairline_and_a_link_are_not_bands(self):
        self.assertEqual([], self.problems("thin-ok"))

    def test_only_the_brand_token_is_exempt(self):
        self.assertEqual([], self.problems("brand"))
        self.assertTrue(self.problems("near-brand"))


if __name__ == "__main__":
    unittest.main()
