import copy
import html
import importlib.util
import json
import re
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("build_site", ROOT / "scripts/build_site.py")
build = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(build)


def slide(folder: Path, name: str, body: str) -> None:
    (folder / "slides").mkdir(parents=True, exist_ok=True)
    (folder / "slides" / f"{name}.html").write_text(f'<section id="{name}" style="color:#111">{body}</section>')


def strings(value) -> list[str]:
    """Every string in a noun, however deeply it sits."""
    if isinstance(value, str):
        return [value]
    items = value.values() if isinstance(value, dict) else value if isinstance(value, list) else []
    return [found for item in items for found in strings(item)]


class ShownText(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.shown: list[str] = []

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.shown.append(data.strip())


def shown_text(fragment: str) -> list[str]:
    """The text a page shows, piece by piece, without its markup."""
    parser = ShownText()
    parser.feed(fragment)
    parser.close()
    return parser.shown


class Builder(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nouns = build.Nouns()
        cls.outputs = build.outputs_for(cls.nouns)

    def test_the_general_slide_loader_reads_the_frozen_v4_source_as_v4_was_built(self):
        source = ROOT / "site/decks/2026-10-29/v4/source"
        frozen = (ROOT / "site/decks/2026-10-29/v4/index.html").read_text()
        order = json.loads((source / "deck.json").read_text())["order"]
        for name in order:
            loaded = build.load_slide(source, name)
            self.assertIn(f'<div class="slide-canvas" style="{html.escape(loaded["style"])}">\n{loaded["inner"]}\n</div>',
                          frozen, name)
            self.assertIn(f'<p>{loaded["notes"]}</p>', frozen, name)

    def test_frozen_pages_are_never_written(self):
        self.assertEqual(6, len(self.nouns.frozen))
        self.assertFalse(set(self.outputs) & self.nouns.frozen)

    def test_the_starting_brief_has_one_source(self):
        brief = build.text(build.read_brief())
        banner = f'aria-labelledby="agent-brief-title">{brief}</pre>'
        for path, content in self.outputs.items():
            self.assertEqual(1, content.count(banner), path)
        roll = self.outputs[build.DECKS / "roll-your-own" / "index.html"]
        self.assertEqual(1, roll.count(f'<pre id="slide-brief" '))
        self.assertEqual(2, roll.count(f">{brief}</pre>"))

    def test_page_text_comes_from_content_nouns(self):
        nouns = copy.copy(self.nouns)
        nouns.home = dict(self.nouns.home, statement={"lead": "Everything is nouns and verbs:", "rest": "A new line."})
        self.assertIn("A new line.", build.render_home(nouns))
        nouns.uses = copy.deepcopy(self.nouns.uses)
        nouns.uses["flagships"][1]["name"] = "A flagship from data"
        nouns.uses["fields"]["items"].append("A field from data")
        uses_page = build.render_use_cases(nouns)
        self.assertIn("A flagship from data", uses_page)
        self.assertIn("A field from data", uses_page)
        nouns.site = copy.deepcopy(self.nouns.site)
        nouns.site["banner"]["lead"] = "A banner from data."
        self.assertIn("A banner from data.", build.header_block(build.SITE / "index.html", "", nouns))
        # Every word the use cases page shows, outside the shared header and footer, is a string of its noun.
        written = set(strings(self.nouns.uses))
        for shown in shown_text(build.main_of(self.outputs[build.SITE / "use-cases" / "index.html"])):
            self.assertIn(shown, written)

    def test_use_cases_are_ideas_without_status_or_evidence(self):
        uses = self.nouns.uses
        self.assertLessEqual(set(uses), {"about", "title", "description", "heading", "lead", "nouns_label", "verbs_label",
                                         "flagships", "fields"})
        # The owner's seven flagships, in the owner's order and words; Tokens for Good leads.
        self.assertEqual(["Tokens for Good", "Motion Graphics and Video Gen", "Feed Systems to Keep Your Agent Informed",
                          "Shimming Systems", "Code Reusability", "Continuous Learning",
                          "Long-Horizon Tasks via Atomic Steps and Decentralized Solutioning"],
                         [" ".join(filter(None, (item["name"], item.get("rest")))) for item in uses["flagships"]])
        self.assertTrue(uses["flagships"][0]["line"].startswith("Spare tokens for good."))
        page = self.outputs[build.SITE / "use-cases" / "index.html"]
        main = build.main_of(page)
        self.assertEqual(7, main.count('<li class="use-card'))
        self.assertEqual(1, main.count('<li class="use-card use-lead">'))
        self.assertLess(main.index("use-lead"), main.index(uses["flagships"][1]["name"]))
        for item in uses["flagships"]:
            # An idea is a name, a line or two, example nouns and verbs and where to read more: no status, badge or evidence.
            self.assertLessEqual(set(item), {"name", "rest", "line", "detail", "nouns", "verbs", "links"}, item["name"])
            self.assertTrue(3 <= len(item["nouns"]) <= 5 and 3 <= len(item["verbs"]) <= 5, item["name"])
            self.assertTrue(1 <= len(item["links"]) <= 2, item["name"])
            words = [item["name"], item.get("rest", ""), item["line"], item.get("detail", "")] + item["nouns"] + item["verbs"]
            self.assertIsNone(re.search(r"\d", " ".join(words)), item["name"])
            for link in item["links"]:
                href = link["href"] if link["href"].startswith("https://") else "../" + link["href"]
                self.assertIn(f'href="{html.escape(href)}"', main, item["name"])
        # Other fields are plain names, with no nouns or verbs of their own, and point to the roll-your-own deck.
        self.assertTrue(all(isinstance(field, str) for field in uses["fields"]["items"]))
        self.assertIn(f'href="../{uses["fields"]["link"]["href"]}"', main)
        for leftover in ("claim-status", 'class="badge', "use-tag"):
            self.assertNotIn(leftover, main)

    def test_the_home_page_is_the_video_one_sentence_and_the_decks(self):
        home = self.outputs[build.SITE / "index.html"]
        main = home[home.index('<main id="main">'):home.index("</main>")]
        self.assertEqual(3, main.count("<section"))
        self.assertEqual(1, main.count("<video"))
        self.assertIn('kind="captions"', main)
        self.assertIn(" default>", main)
        self.assertEqual(4, main.count('class="deck-card"'))
        self.assertLess(home.index('class="agent-banner"'), home.index("<video"))

    def test_nonprofits_never_choose_a_kind_of_request(self):
        # A nonprofit types what it needs; the request's first step sorts it into a kit, public work or both.
        asking = re.compile(r"request(s|ing)? (a|an) (verb|agent kit|kit)\b|verb requests?\b|an agent kit or a verb", re.I)
        pages = {path: page for path, page in self.outputs.items() if isinstance(page, str)}
        self.assertIn(build.SITE / "decks" / "public-good-marketplace" / "index.html", pages)
        for path, page in pages.items():
            self.assertIsNone(asking.search(page), path)

    def test_deck_pages_are_only_slides_with_sources_in_the_notes(self):
        for deck in self.nouns.decks:
            page = self.outputs[deck["page"]]
            main = page[page.index('<main id="main"'):page.index("</main>")]
            for leftover in ('id="claim-review"', "deck-intro", "deck-more", "print-colophon", "print-claims"):
                self.assertNotIn(leftover, main, deck["id"])
            for claim in (deck["claims"] or {"claims": []})["claims"]:
                start = main.index(f'data-name="{claim["slide"]}"')
                notes = main[main.index('class="slide-notes"', start):main.index("</section>", start)]
                self.assertIn(html.escape(claim["number"], quote=False), notes, claim["number"])

    def test_the_film_offers_a_selector_only_when_it_has_more_than_one_cut(self):
        nouns = copy.copy(self.nouns)
        nouns.home = copy.deepcopy(self.nouns.home)
        videos = nouns.home["videos"]
        self.assertNotIn("data-film-cuts", build.render_home(nouns))
        full = dict(videos["cuts"][0], id="full", tab="Full · 3 min", label="The full cut")
        full["src"] = "video/2026-10-29/animatic-60s-v1/eranos-animatic-60s-open-captions.mp4"
        videos["cuts"].insert(0, full)
        videos["default"] = "full"
        page = build.render_home(nouns)
        self.assertEqual(1, page.count("<video"))
        self.assertEqual(2, page.count('class="film-cut"'))
        self.assertIn(f'<source src="{full["src"]}"', page)
        self.assertIn('aria-pressed="true" data-cut="full"', page)
        self.assertIn('aria-pressed="false" data-cut="short"', page)
        self.assertIn('id="film-label">The full cut</span>', page)
        videos["default"] = "missing"
        with self.assertRaises(build.BuildError):
            build.render_home(nouns)

    def test_slide_elements_become_html(self):
        endpoints = self.nouns.site["endpoints"]
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            slide(folder, "a", '<h2>Title</h2><x-brief style="white-space:pre-wrap"></x-brief><x-endpoints style="font-size:20px">'
                               '</x-endpoints><x-shape kind="arrow-down" style="width:20px;height:40px;background:#888">'
                               '</x-shape><aside>Notes</aside>')
            loaded = build.load_slide(folder, "a", brief="Use <b> & go", endpoints=endpoints)
            self.assertIn('<pre id="slide-brief" style="white-space:pre-wrap">Use &lt;b&gt; &amp; go</pre>', loaded["inner"])
            self.assertEqual("slide-brief", loaded["copy"])
            self.assertIn(endpoints["rows"][0]["mcp"], loaded["inner"])
            self.assertIn((endpoints["rows"][0]["llms"], endpoints["rows"][0]["llms"]), loaded["links"])
            self.assertEqual("Title", loaded["title"])
            self.assertEqual("Notes", loaded["notes"])
            for body in ('<h2>T</h2><x-unknown></x-unknown><aside>N</aside>', '<h2>T</h2>',
                         '<h2>T</h2><x-brief style=""></x-brief><x-brief style=""></x-brief><aside>N</aside>'):
                slide(folder, "b", body)
                with self.assertRaises(build.BuildError):
                    build.load_slide(folder, "b", brief="text", endpoints=endpoints)

    def test_slide_links_use_names_that_moved_pages_can_point_to(self):
        for item in self.nouns.moved["pages"]:
            path, _, anchor = item["to"].partition("#")
            if anchor:
                self.assertIn(f'class="slide-frame" id="{anchor}"', self.outputs[build.SITE / path / "index.html"])


if __name__ == "__main__":
    unittest.main()
