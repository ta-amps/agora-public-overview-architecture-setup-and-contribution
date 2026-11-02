#!/usr/bin/env python3
"""make light-check: MUST-FOLLOW rule 13, light only, checked in a real browser.

Every route is opened in Chromium twice, once with the system asking for light and once for dark, at 1280 x 800.
A route fails when:
  * its color-scheme meta is missing, repeated or anything but "only light", or the root's computed color-scheme is
    not "only light";
  * any stylesheet (shadow roots included), <link>, <style> or <source> carries a prefers-color-scheme: dark query;
  * any visible opaque element larger than 5% of the viewport is dark: relative luminance below 0.25 for its
    background or SVG fill (composited over the page's paper), or, for an image, video, canvas, SVG, frame or a
    background image, for the mean of its rendered pixels.
One brand colour is accepted by token, not by luminance: the Task chips' orange (--verb-text, #9C4416; the Agora
review of Nov 1). The exemption matches that token's resolved value exactly, so nothing else dark slips through.

Two ways to run it:
  python3 scripts/light_check.py                      every current page of the built site/ (check.current_pages),
                                                      served from a local address the check starts
  python3 scripts/light_check.py --base URL --crawl   a running copy (the bundle's local preview, or the live site):
                                                      every HTML page reachable from / plus the given --routes, and
                                                      the not-found page
It writes a JSON report (--report) and exits 1 when any route fails, or when the browser cannot start (fail closed).
"""
from __future__ import annotations

import argparse
import io
import json
import re
import sys
import threading
from functools import partial
from html.parser import HTMLParser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urldefrag, urljoin, urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
sys.path.insert(0, str(ROOT / "scripts"))

VIEWPORT = {"width": 1280, "height": 800}
SHARE = 0.05            # of the viewport's area
DARK = 0.25             # relative luminance (WCAG): below this, an opaque area is dark
EXEMPT_TOKENS = ("--verb-text",)  # the Task chips' brand orange, accepted by token (review, Nov 1)
MISSING = "/__light-check-not-found__/"
SKIP_SUFFIXES = (".pdf", ".zip", ".pptx", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".mp4", ".webm", ".vtt", ".srt",
                 ".json", ".txt", ".xml", ".css", ".js", ".woff2", ".ttf", ".bundle", ".tar.gz", ".gz", ".md", ".csv")

PROBE = r"""
({share, dark, exemptTokens}) => {
  const out = {metas: [], rootScheme: "", darkQueries: [], darkAreas: [], pictures: [], exempted: 0, large: 0};
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = 1;
  const ctx = canvas.getContext("2d", {willReadFrequently: true});
  const parse = (css) => {
    const m = /^rgba?\(\s*([\d.]+)[,\s]+([\d.]+)[,\s]+([\d.]+)(?:\s*[,/]\s*([\d.]+%?))?\s*\)$/i.exec(css || "");
    if (m) {
      let a = m[4] === undefined ? 1 : m[4].endsWith("%") ? parseFloat(m[4]) / 100 : parseFloat(m[4]);
      return [+m[1], +m[2], +m[3], a];
    }
    ctx.clearRect(0, 0, 1, 1);
    ctx.fillStyle = "rgba(0, 0, 0, 0)";
    ctx.fillStyle = css;
    ctx.fillRect(0, 0, 1, 1);
    const d = ctx.getImageData(0, 0, 1, 1).data;
    return [d[0], d[1], d[2], d[3] / 255];
  };
  const lin = (c) => { c /= 255; return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); };
  const lum = (rgb) => 0.2126 * lin(rgb[0]) + 0.7152 * lin(rgb[1]) + 0.0722 * lin(rgb[2]);
  const over = (top, under) => [0, 1, 2].map((i) => top[i] * top[3] + under[i] * (1 - top[3]));
  const name = (el) => {
    let s = el.tagName.toLowerCase();
    if (el.id) s += "#" + el.id;
    const cls = typeof el.className === "string" ? el.className.trim().split(/\s+/).filter(Boolean).slice(0, 3) : [];
    if (cls.length) s += "." + cls.join(".");
    const host = el.getRootNode && el.getRootNode().host;
    return host ? host.tagName.toLowerCase() + " >> " + s : s;
  };

  const all = [];
  const roots = [];
  const walk = (root) => {
    for (const el of root.querySelectorAll("*")) {
      all.push(el);
      if (el.shadowRoot) { roots.push(el.shadowRoot); walk(el.shadowRoot); }
    }
  };
  walk(document);

  out.metas = [...document.querySelectorAll("meta")]
    .filter((m) => (m.getAttribute("name") || "").toLowerCase() === "color-scheme")
    .map((m) => m.getAttribute("content"));
  out.rootScheme = getComputedStyle(document.documentElement).colorScheme;

  const DARKQ = /prefers-color-scheme\s*:\s*dark/i;
  const sheets = [...document.styleSheets, ...(document.adoptedStyleSheets || [])];
  for (const r of roots) sheets.push(...r.styleSheets, ...(r.adoptedStyleSheets || []));
  const scan = (rules, where) => {
    for (const rule of rules) {
      const media = (rule.media && rule.media.mediaText) || rule.conditionText || "";
      if (DARKQ.test(media)) out.darkQueries.push(where + ": @" + (rule.constructor.name || "rule") + " " + media);
      if (rule.styleSheet) { try { scan(rule.styleSheet.cssRules, where); } catch (e) { out.darkQueries.push("unreadable import in " + where); } }
      if (rule.cssRules) scan(rule.cssRules, where);
    }
  };
  for (const sheet of sheets) {
    const where = sheet.href || (sheet.ownerNode ? "inline <" + sheet.ownerNode.nodeName.toLowerCase() + ">" : "adopted sheet");
    if (sheet.media && DARKQ.test(sheet.media.mediaText)) out.darkQueries.push(where + " media=" + sheet.media.mediaText);
    let rules;
    try { rules = sheet.cssRules; } catch (e) { out.darkQueries.push("unreadable stylesheet " + where); continue; }
    scan(rules, where);
  }
  for (const el of all) {
    const media = el.getAttribute && el.getAttribute("media");
    if (media && DARKQ.test(media)) out.darkQueries.push("<" + el.tagName.toLowerCase() + " media=\"" + media + "\">");
  }

  const rootStyle = getComputedStyle(document.documentElement);
  const exempt = exemptTokens.map((t) => rootStyle.getPropertyValue(t).trim()).filter(Boolean).map(parse);
  const same = (a, b) => [0, 1, 2].every((i) => a[i] === b[i]) && b[3] >= 0.99;  // the token's exact colour
  const bodyBg = parse(getComputedStyle(document.body).backgroundColor);
  const htmlBg = parse(rootStyle.backgroundColor);
  const paper = bodyBg[3] > 0 ? over(bodyBg, htmlBg[3] > 0 ? htmlBg : [255, 255, 255, 1]) : (htmlBg[3] > 0 ? htmlBg : [255, 255, 255]);
  const limit = share * innerWidth * innerHeight;
  const docW = Math.max(document.documentElement.scrollWidth, innerWidth);
  const docH = Math.max(document.documentElement.scrollHeight, innerHeight);
  const PICTURES = new Set(["img", "video", "canvas", "svg", "picture", "iframe", "object", "embed"]);
  const SHAPES = new Set(["rect", "circle", "ellipse", "path", "polygon"]);
  for (const el of all) {
    const cs = getComputedStyle(el);
    if (cs.display === "none" || cs.visibility !== "visible" || parseFloat(cs.opacity) === 0) continue;
    const r = el.getBoundingClientRect();
    const x0 = Math.max(0, r.left + scrollX), y0 = Math.max(0, r.top + scrollY);
    const x1 = Math.min(docW, r.right + scrollX), y1 = Math.min(docH, r.bottom + scrollY);
    const w = x1 - x0, h = y1 - y0;
    if (w <= 0 || h <= 0 || w * h <= limit) continue;
    out.large += 1;
    const tag = el.tagName.toLowerCase();
    const bg = parse(cs.backgroundColor);
    if (bg[3] > 0.02) {
      const shown = over(bg, paper), l = lum(shown);
      if (l < dark) {
        if (exempt.some((e) => same(e, bg))) out.exempted += 1;
        else out.darkAreas.push({element: name(el), kind: "background", color: cs.backgroundColor, luminance: +l.toFixed(3), area: Math.round(w * h)});
      }
    }
    if (el instanceof SVGElement && SHAPES.has(tag) && cs.fill && cs.fill !== "none" && !cs.fill.startsWith("url(")) {
      const fill = parse(cs.fill);
      fill[3] *= parseFloat(cs.fillOpacity || "1");
      if (fill[3] > 0.02) {
        const l = lum(over(fill, paper));
        if (l < dark && !exempt.some((e) => same(e, fill)))
          out.darkAreas.push({element: name(el), kind: "svg fill", color: cs.fill, luminance: +l.toFixed(3), area: Math.round(w * h)});
      }
    }
    if (PICTURES.has(tag) || cs.backgroundImage !== "none")
      out.pictures.push({element: name(el), x: x0, y: y0, width: w, height: h});
  }
  return out;
}
"""


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.hrefs.append(href)


def crawl(base: str, seeds: list[str], limit: int) -> list[str]:
    """Every HTML page of the running copy reachable from / and the seeds, by its path."""
    origin = urlparse(base)
    queue, seen, pages = ["/"] + seeds, set(), []
    while queue and len(pages) < limit:
        path = queue.pop(0)
        if path in seen:
            continue
        seen.add(path)
        try:
            with urlopen(Request(urljoin(base, path), headers={"User-Agent": "agora-light-check"}), timeout=30) as answer:
                if "text/html" not in answer.headers.get("Content-Type", ""):
                    continue
                final = urlparse(answer.geturl())
                if (final.scheme, final.netloc) != (origin.scheme, origin.netloc):
                    continue
                body = answer.read().decode("utf-8", "replace")
                path = final.path + (("?" + final.query) if final.query else "")
        except HTTPError:
            continue
        if path in pages:
            continue
        pages.append(path)
        parser = Links()
        parser.feed(body)
        for href in parser.hrefs:
            target = urlparse(urldefrag(urljoin(urljoin(base, path), href))[0])
            if (target.scheme, target.netloc) != (origin.scheme, origin.netloc):
                continue
            if target.path.lower().endswith(SKIP_SUFFIXES) or target.path in seen:
                continue
            queue.append(target.path + (("?" + target.query) if target.query else ""))
    return pages


def picture_luminance(png: bytes) -> float:
    from PIL import Image

    image = Image.open(io.BytesIO(png)).convert("RGB")
    image.thumbnail((48, 48))
    table = [((c / 255) / 12.92 if c / 255 <= 0.04045 else (((c / 255) + 0.055) / 1.055) ** 2.4) for c in range(256)]
    data = image.tobytes()
    count = len(data) // 3
    return sum(0.2126 * table[data[i]] + 0.7152 * table[data[i + 1]] + 0.0722 * table[data[i + 2]]
               for i in range(0, count * 3, 3)) / count


def judge(page, probe: dict) -> list[str]:
    problems = []
    if probe["metas"] != ["only light"]:
        problems.append(f"color-scheme meta must be one, 'only light': {probe['metas']}")
    if set(probe["rootScheme"].split()) != {"only", "light"}:
        problems.append(f"the root's computed color-scheme is {probe['rootScheme']!r}, not 'only light'")
    problems += [f"dark media query: {q}" for q in probe["darkQueries"]]
    problems += [f"dark {a['kind']} on {a['element']}: {a['color']}, luminance {a['luminance']}, {a['area']:,} px²"
                 for a in probe["darkAreas"]]
    for pic in probe["pictures"][:40]:
        clip = {k: pic[k] for k in ("x", "y", "width", "height")}
        try:
            png = page.screenshot(clip=clip, full_page=True, animations="disabled", timeout=30000)
        except Exception as error:  # noqa: BLE001 - a picture we cannot see is reported, not skipped
            problems.append(f"could not render {pic['element']}: {error}")
            continue
        level = picture_luminance(png)
        if level < DARK:
            problems.append(f"dark picture {pic['element']}: mean luminance {level:.3f}, "
                            f"{round(pic['width'] * pic['height']):,} px²")
    return problems


class Quiet(SimpleHTTPRequestHandler):
    """The built site, served without a log line per request; a browser that drops a font request is not news."""

    def log_message(self, *args):
        pass

    def copyfile(self, source, outputfile):
        try:
            super().copyfile(source, outputfile)
        except (BrokenPipeError, ConnectionResetError):
            pass


def serve(directory: Path):
    handler = partial(Quiet, directory=str(directory))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", help="a running copy to check, such as http://127.0.0.1:8942 (default: serve site/)")
    ap.add_argument("--crawl", action="store_true", help="with --base: check every page reachable from /")
    ap.add_argument("--routes", nargs="*", default=[], help="paths to check as well, such as /source/")
    ap.add_argument("--limit", type=int, default=2000, help="most pages a crawl visits")
    ap.add_argument("--report", default=str(ROOT / "light-check.json"), help="where the JSON report goes")
    args = ap.parse_args(argv)
    server = None
    if args.base:
        base = args.base.rstrip("/")
        routes = crawl(base, args.routes, args.limit) if args.crawl else (args.routes or ["/"])
        print(f"light-check: {len(routes)} pages found at {base}", flush=True)
    else:
        import check

        server, base = serve(SITE)
        root = SITE.resolve()
        routes = []
        for page in check.current_pages(SITE):
            rel = page.relative_to(root).as_posix()
            routes.append("/" + (rel[: -len("index.html")] if rel.endswith("index.html") else rel))
        routes = sorted(set(routes) - {"/404.html"})
    routes.append(MISSING)  # the not-found page, as a visitor with a wrong link sees it
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("light-check: the Playwright package is missing, so nothing was checked (fail closed)", file=sys.stderr)
        return 1
    results, failed = [], 0
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            for scheme in ("light", "dark"):
                context = browser.new_context(viewport=VIEWPORT, color_scheme=scheme, reduced_motion="reduce")
                page = context.new_page()
                for route in routes:
                    try:
                        answer = page.goto(base + route, wait_until="load", timeout=60000)
                        status = answer.status if answer else None
                        if route == MISSING and server is not None:
                            # The plain local server has no not-found page; open the built one directly.
                            answer = page.goto(base + "/404.html", wait_until="load", timeout=60000)
                            status = 404
                        page.evaluate("document.fonts.ready")
                        probe = page.evaluate(PROBE, {"share": SHARE, "dark": DARK, "exemptTokens": list(EXEMPT_TOKENS)})
                        problems = judge(page, probe)
                    except Exception as error:  # noqa: BLE001 - a page that does not load fails the check
                        status, probe, problems = None, {"exempted": 0, "large": 0}, [f"could not check: {error}"]
                    failed += bool(problems)
                    results.append({"route": route, "scheme": scheme, "status": status, "problems": problems,
                                    "large_elements": probe.get("large", 0), "brand_exempted": probe.get("exempted", 0)})
                    if problems:
                        print(f"FAIL {scheme:5} {route}", *problems, sep="\n    ", flush=True)
                    done = len(results)
                    if done % 100 == 0:
                        print(f"light-check: {done} of {2 * len(routes)} checked, {failed} failed so far", flush=True)
                context.close()
            browser.close()
    except Exception as error:  # noqa: BLE001 - no browser means no check: fail closed
        print(f"light-check: the browser did not run ({error}); nothing was checked (fail closed)", file=sys.stderr)
        return 1
    finally:
        if server is not None:
            server.shutdown()
    report = {"rule": "MUST-FOLLOW rule 13, light only", "base": base if args.base else "site/ (built)",
              "viewport": VIEWPORT, "share_of_viewport": SHARE, "dark_below_luminance": DARK,
              "exempt_tokens": list(EXEMPT_TOKENS), "routes": len(routes), "checked": len(results),
              "failed": failed, "results": results}
    Path(args.report).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"light-check: {len(routes)} routes x 2 colour schemes, {failed} failed (report: {args.report})")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
