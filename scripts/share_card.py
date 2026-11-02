#!/usr/bin/env python3
"""Draw Agora's share card, assets/share/agora-1200x630.png, the og:image on every page.

The card is light Paper & Ink (MUST-FOLLOW rule 13): paper ground, ink type, the tile mark, the name and the line
from site.json's share.card, in the site's own self-hosted fonts. It promises nothing the site does not hold (the
film is withdrawn, so the card names none). The words are the Task Object's; the alt text says the same words.
After drawing, media.json's row gets the new size and hash, so scripts/check.py keeps pinning the file.

Usage: python3 scripts/share_card.py   (needs the Playwright package and a Chromium it can start)
"""
from __future__ import annotations

import hashlib
import html
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
CARD = SITE / "assets" / "share" / "agora-1200x630.png"


def page(card: dict) -> str:
    mark = (SITE / "assets" / "mark.svg").read_text(encoding="utf-8")
    fonts = (SITE / "assets" / "fonts").as_uri()
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="color-scheme" content="only light">
<style>
@font-face {{ font-family: "Space Grotesk"; src: url("{fonts}/SpaceGrotesk-wght.woff2") format("woff2"); font-weight: 300 700; }}
@font-face {{ font-family: "IBM Plex Sans"; src: url("{fonts}/IBMPlexSans-wdth-wght.woff2") format("woff2"); font-weight: 100 700; }}
html, body {{ margin: 0; width: 1200px; height: 630px; background: #F5F2EA; color: #11161F; color-scheme: only light; }}
.card {{ box-sizing: border-box; width: 1200px; height: 630px; padding: 76px 88px 64px; display: grid;
  grid-template-rows: auto 1fr auto; border-bottom: 18px solid #EDE8DC; }}
.name {{ display: flex; align-items: center; gap: 22px; font: 600 54px/1 "Space Grotesk", sans-serif; letter-spacing: -0.01em; }}
.name svg {{ width: 64px; height: 64px; display: block; }}
.line {{ align-self: center; margin: 0; font: 600 112px/1.02 "Space Grotesk", sans-serif; letter-spacing: -0.03em; }}
.address {{ font: 500 30px/1 "IBM Plex Sans", sans-serif; color: #3B4252; }}
</style></head><body><div class="card">
<div class="name">{mark}<span>{html.escape(card["name"])}</span></div>
<p class="line">{html.escape(card["line"])}</p>
<div class="address">{html.escape(card["address"])}</div>
</div></body></html>"""


def main() -> int:
    from playwright.sync_api import sync_playwright

    site = json.loads((SITE / "content" / "site.json").read_text(encoding="utf-8"))
    card = site["share"]["card"]
    if site["share"]["alt"] != f'{card["name"]}. {card["line"]} {card["address"]}':
        print("site.json: the share card's alt text must say the card's words", file=sys.stderr)
        return 1
    with tempfile.TemporaryDirectory() as tmp:
        source = Path(tmp) / "card.html"
        source.write_text(page(card), encoding="utf-8")
        with sync_playwright() as p:
            browser = p.chromium.launch()
            view = browser.new_page(viewport={"width": 1200, "height": 630}, color_scheme="light")
            view.goto(source.as_uri(), wait_until="load")
            view.evaluate("document.fonts.ready")
            CARD.parent.mkdir(parents=True, exist_ok=True)
            CARD.write_bytes(view.screenshot(type="png", clip={"x": 0, "y": 0, "width": 1200, "height": 630}))
            browser.close()
    data = CARD.read_bytes()
    listing_path = SITE / "media.json"
    listing = json.loads(listing_path.read_text(encoding="utf-8"))
    row = next(i for i in listing["items"] if i["path"] == "assets/share/agora-1200x630.png")
    row["sha256"], row["bytes"] = hashlib.sha256(data).hexdigest(), len(data)
    listing_path.write_text(json.dumps(listing, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {CARD.relative_to(ROOT)} ({len(data):,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
