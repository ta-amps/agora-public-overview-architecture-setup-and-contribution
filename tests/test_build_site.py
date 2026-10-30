import copy
import html
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("build_site", ROOT / "scripts/build_site.py")
build = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(build)


def slide(folder: Path, name: str, body: str) -> None:
    (folder / "slides").mkdir(parents=True, exist_ok=True)
    (folder / "slides" / f"{name}.html").write_text(f'<section id="{name}" style="color:#111">{body}</section>')


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
        nouns.uses["ideas"].append({"name": "An idea from data", "line": "One line.", "nouns": ["A noun"], "verbs": ["A verb"]})
        self.assertIn("An idea from data", build.render_use_cases(nouns))
        nouns.site = copy.deepcopy(self.nouns.site)
        nouns.site["banner"]["lead"] = "A banner from data."
        self.assertIn("A banner from data.", build.header_block(build.SITE / "index.html", "", nouns))

    def test_use_cases_are_ideas_without_status_or_evidence(self):
        uses = self.nouns.uses
        self.assertEqual("Public-good marketplace", uses["flagship"]["name"])
        for idea in uses["ideas"]:
            self.assertLessEqual(set(idea), {"name", "line", "nouns", "verbs", "public"}, idea["name"])
        page = self.outputs[build.SITE / "use-cases" / "index.html"]
        self.assertNotIn("claim-status", page)
        self.assertIn(uses["yours"]["link"]["href"], page)

    def test_the_home_page_is_the_video_one_sentence_and_the_decks(self):
        home = self.outputs[build.SITE / "index.html"]
        main = home[home.index('<main id="main">'):home.index("</main>")]
        self.assertEqual(3, main.count("<section"))
        self.assertEqual(1, main.count("<video"))
        self.assertIn('kind="captions"', main)
        self.assertIn(" default>", main)
        self.assertEqual(3, main.count('class="deck-card"'))
        self.assertLess(home.index('class="agent-banner"'), home.index("<video"))

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
