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


def without_number(inner: str) -> str:
    """A slide's markup without the footer's slide number, which no claim needs to back."""
    return re.sub(r'<span class="slide-no"[^>]*>\d+</span>', "", inner)


def numbers(value) -> list[int]:
    """Every whole number in a noun, however deeply it sits."""
    if type(value) is int:
        return [value]
    items = value.values() if isinstance(value, dict) else value if isinstance(value, list) else []
    return [found for item in items for found in numbers(item)]


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


def css_tokens(css: str, selector: str) -> dict[str, str]:
    """The custom properties a stylesheet declares in the first block that starts with this selector."""
    block = css[css.index(selector + " {"):]
    block = block[:block.index("}")]
    return dict(re.findall(r"(--[a-z0-9-]+):\s*(#[0-9A-Fa-f]{6})", block))


def resolved_tokens() -> dict[str, str]:
    """Agora's colour tokens with every var() reference resolved through tokens v3 (assets/tokens.css)."""
    found = {}
    for name in ("tokens.css", "site.css"):
        css = (build.SITE / "assets" / name).read_text(encoding="utf-8")
        block = css[css.index(":root {"):]
        block = block[:block.index("}")]
        found.update(re.findall(r"(--[a-z0-9-]+):\s*([^;]+);", block))
    def value(name: str, depth: int = 0) -> str:
        raw = found[name].strip()
        ref = re.fullmatch(r"var\((--[a-z0-9-]+)\)", raw)
        return value(ref.group(1), depth + 1) if ref and depth < 5 else raw
    return {k: value(k) for k in found if re.fullmatch(r"#[0-9A-Fa-f]{6}", value(k))}


def contrast(a: str, b: str) -> float:
    def luminance(colour: str) -> float:
        channels = [int(colour[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        r, g, b_ = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
        return 0.2126 * r + 0.7152 * g + 0.0722 * b_
    light, dark = sorted((luminance(a), luminance(b)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


def plain_words(value: str) -> list[str]:
    """Words, lowercased, without punctuation: how a transcript and its captions are compared."""
    value = value.lower().replace("…", " ").replace("’", "").replace("'", "").replace("\u2014", " ").replace("-", " ")
    return re.sub(r"[^a-z0-9% ]", "", value).split()


def caption_words(vtt: str) -> list[str]:
    """The words a WebVTT file's cues show."""
    cues = [block.split("\n") for block in vtt.strip().split("\n\n")]
    return plain_words(" ".join(line for cue in cues for n, line in enumerate(cue) if any("-->" in c for c in cue[:n])))


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
        roll = self.outputs[build.DECKS / "roll-your-own" / "index.html"]
        self.assertEqual(1, roll.count(f'<pre id="slide-brief" '))
        self.assertEqual(1, roll.count(f">{brief}</pre>"))
        self.assertEqual(build.read_brief() + "\n", (build.SITE / "agent-brief.txt").read_text(encoding="utf-8"))

    def test_every_page_opens_with_one_agent_banner_from_its_noun(self):
        # October 31 (AgentBanner, BannerSpec): one thin line above the header on every page, its words embedded
        # from the agent-banner noun for the shared <ta-agent-banner> element, with a plain line and an llms.txt
        # link for readers without scripts. The copied line is exactly the noun's.
        embedded = f'<script type="application/json">{build.banner_json(self.nouns)}</script>'
        self.assertEqual("Read https://agora.ta-amps.workers.dev/llms.txt and follow it.", self.nouns.banner["copy_text"])
        for path, content in self.outputs.items():
            if path.suffix != ".html":
                continue
            self.assertEqual(1, content.count("<ta-agent-banner "), path)
            self.assertEqual(1, content.count(embedded), path)
            self.assertEqual(1, content.count('assets/agent-banner.js" defer></script>'), path)
            body = content[content.index("<body"):]
            if "<!-- site:header -->" in body:
                # Above the header, and the skip link stays the first thing a keyboard reaches.
                self.assertLess(body.index("<ta-agent-banner "), body.index('class="site-header"'), path)
                self.assertLess(body.index('class="skip-link"'), body.index("<ta-agent-banner "), path)
        data = json.loads(build.banner_json(self.nouns))
        self.assertNotIn("about", data)
        for field in ("label", "lead_strong", "lead", "copy_text", "copy", "copied", "copy_failed", "more", "less",
                      "panel_title", "can", "rules", "links"):
            self.assertTrue(data[field], field)

    def test_page_text_comes_from_content_nouns(self):
        nouns = copy.copy(self.nouns)
        nouns.home = copy.deepcopy(self.nouns.home)
        nouns.home["start"]["heading"] = "A heading from data."
        nouns.home["uses"]["lead"] = "A lead from data."
        home_page = build.render_home(nouns)
        self.assertIn("A heading from data.", home_page)
        self.assertIn("A lead from data.", home_page)
        nouns.uses = copy.deepcopy(self.nouns.uses)
        nouns.uses["cards"][1]["title"] = "A use case from data"
        uses_page = build.render_use_cases(nouns)
        self.assertIn("A use case from data", uses_page)
        nouns.banner = dict(self.nouns.banner, lead="A banner from data.")
        self.assertIn("A banner from data.", build.header_block(build.SITE / "index.html", "", nouns))
        nouns.site = copy.deepcopy(self.nouns.site)
        nouns.site["header"]["eranos_label"] = "Eranos from data"
        self.assertIn("Eranos from data", build.header_block(build.SITE / "index.html", "", nouns))


    def test_use_cases_follow_the_board_with_the_featured_run_from_the_models_catalog(self):
        # Board UseCases (Nov 1): a filter, the featured Oct 31 test run read from the models catalog Task Object (no
        # number typed by hand), then six cards, each saying who it helps, what they ask, what they get and how it is
        # made, with a present-tense state. The home strip shows the same six.
        uses, featured = self.nouns.uses, self.nouns.catalog["featured_use_case"]
        main = build.main_of(self.outputs[build.SITE / "use-cases" / "index.html"])
        self.assertEqual(6, len(uses["cards"]))
        self.assertEqual(6, main.count('<li class="uc-card'))
        self.assertEqual(4, main.count('class="uc-filter-button"'))
        self.assertIn(build.text(featured["title"]), main)
        for rule in featured["rules"]:
            self.assertIn(build.text(rule), main)
        for step in featured["steps"]:
            if "seconds" in step:
                self.assertIn(build.minutes_seconds(step["seconds"]), main)
        self.assertEqual("3 min 27 s", build.minutes_seconds(207.27))
        self.assertEqual({"live", "tested", "example"}, {c["state"] for c in uses["cards"]})
        for card in uses["cards"]:
            self.assertEqual({"audience", "state", "title", "ask", "get", "how"}, set(card), card["title"])
        home = build.main_of(self.outputs[build.SITE / "index.html"])
        self.assertEqual(6, home.count('<li class="uc-card'))
        self.assertIn('href="models/"', home)
        for word in ("nanoMuse", "Muse Code"):
            self.assertNotIn(word, main)

    def test_the_home_page_is_start_here_the_decks_and_the_use_cases(self):
        # November 1 (the AgoraHome board, light only): Start here with the two public sites, Open Eranos and the
        # judges' tour in the first screen, then the decks and the use cases. The film is withdrawn until its
        # re-recorded cut lands, so there is no film slot. The start part's heading is the page's one h1.
        home = self.outputs[build.SITE / "index.html"]
        main = home[home.index('<main id="main">'):home.index("</main>")]
        self.assertEqual(3, main.count("<section"))
        self.assertNotIn("<video", main)
        self.assertNotIn('class="film', main)
        order = [main.index(marker) for marker in ('<section class="start', '<section class="deck-band"',
                                                    '<section class="home-uses"')]
        self.assertEqual(sorted(order), order)
        start = self.nouns.home["start"]
        self.assertEqual(1, main.count("<h1"))
        self.assertIn(f"<h1>{build.text(start['heading'])}</h1>", main)
        self.assertEqual(["Eranos", "Agora"], [card["name"] for card in start["cards"]])
        self.assertIn('href="https://eranos.ta-amps.workers.dev/"', main)
        self.assertIn('href="how-it-works/"', main)
        self.assertIn('<a class="button" href="https://eranos.ta-amps.workers.dev/">Open Eranos ↗</a>', main)
        self.assertIn('<a class="home-tour" href="?tour=judge">Take the 45-second tour →</a>', main)
        self.assertEqual(5, main.count('class="deck-card"'))
        # The same six use cases as /use-cases/ (board AgoraHome, Nov 1), each with its present-tense state.
        self.assertEqual(6, main.count('<li class="uc-card'))
        self.assertIn('href="use-cases/"', main)
        self.assertIn('href="models/"', main)
        self.assertNotIn('href="film/"', main)
        # The film's production page is linked only once its production trace is final.
        self.assertEqual(build.film_made_ready(start), start["film_made"]["href"] in main)

    def test_tasks_and_task_objects_are_glossed_in_plain_words_the_first_time(self):
        # Feedback, October 30: a viewer took the vocabulary for a model architecture. Owner, Nov 1: it is Tasks and Task
        # Objects. The overview and roll-your-own decks say in plain words what they are the first time they name them:
        # Tasks are the work, and Task Objects are everything a Task uses or makes. The overview says plainly that this
        # is how the work is organized, not a model architecture. The marketplace deck, written for nonprofits, says
        # what its first Task is: a queued piece of work.
        named = re.compile(r"\bTask Objects?\b")

        def glossed(shown: str, where: str) -> None:
            found = named.search(shown)
            self.assertIsNotNone(found, where)
            self.assertIn("everything a task uses or makes", shown[found.start():found.start() + 160].lower(), where)

        decks = {deck["id"]: deck for deck in self.nouns.decks}
        for deck_id in ("overview-and-architecture", "roll-your-own"):
            glossed(" ".join(build.plain_text(slide["inner"]) for slide in decks[deck_id]["slides"]), deck_id)
        overview = {slide["name"]: build.plain_text(slide["inner"]) for slide in decks["overview-and-architecture"]["slides"]}
        self.assertIn("NOT A MODEL ARCHITECTURE", overview["nouns-and-verbs"])
        self.assertIn("how the work is organized", overview["nouns-and-verbs"])
        market = " ".join(build.plain_text(slide["inner"]) for slide in decks["public-good-marketplace"]["slides"])
        first = re.search(r"\bTask\b", market)
        self.assertEqual(", a queued piece of work", market[first.end():first.end() + len(", a queued piece of work")])

    def test_the_memory_systems_slide_is_a_measured_scan_and_no_slide_is_an_illustration(self):
        # Review, October 31: the illustrated worked example is gone (the How it works page replays a real run), and the
        # memory-systems slide is the feed's real scan. Every number on it has a measured claim, and no current slide or
        # claim is marked illustration or planned.
        deck = next(deck for deck in self.nouns.decks if deck["id"] == "overview-and-architecture")
        order = [slide["name"] for slide in deck["slides"]]
        self.assertNotIn("worked-example", order)
        self.assertEqual(order.index("feeds") + 1, order.index("memory-systems"))
        slide = next(slide for slide in deck["slides"] if slide["name"] == "memory-systems")
        shown, notes = build.plain_text(without_number(slide["inner"])), build.plain_text(slide["notes"])
        mine = [claim for claim in deck["claims"]["claims"] if claim["slide"] == "memory-systems"]
        self.assertTrue(mine and all(claim["status"] == "measured" for claim in mine))
        listed = " ".join(claim["number"] for claim in mine)
        for part in (shown, notes):
            for number in re.findall(r"\d+(?:[.,]\d+)?", part):
                self.assertIn(number, listed, number)
        for current in self.nouns.decks:
            for claim in (current["claims"] or {"claims": []})["claims"]:
                self.assertNotIn(claim["status"], ("illustration", "planned"), (current["id"], claim["number"]))
            for each in current["slides"]:
                self.assertIsNone(re.search(r"(?i)\b(illustration|planned|coming next|not yet)\b", build.plain_text(each["inner"])),
                                  (current["id"], each["name"]))
        # Every claim status still has its own label style in the notes.
        css = (build.SITE / "assets" / "viewer.css").read_text(encoding="utf-8")
        for status in build.CLAIM_STATUSES:
            self.assertIn(f".claim-status.{status} {{", css, status)

    def test_meta_models_are_named_from_the_models_noun(self):
        # Owner, Nov 1: name the specific models, rendered from the models catalog Task Object (models.meta, a local copy).
        self.assertEqual("Muse Spark 1.3 and Muse Wonder 1.0", build.meta_models("{{model:muse-spark-1.3}} and {{model:muse-wonder-1.0}}", self.nouns.models))
        self.assertEqual("Muse Glimmer 30B, fine-tuned by ta-amps · MusicGen · Muse Spark 1.3",
                         build.meta_models("{{model:muse-glimmer-30b:tuned}} · {{model:facebook/musicgen-small}} · "
                                           "{{model:muse-spark-1.3-contributor}}", self.nouns.models))
        # Models used (board ModelsUsed): rendered from the catalog, only live or measured entries, Meta first; agent
        # apps are named there and nowhere else (v2 brief: zero nanoMuse outside /models/).
        page = self.outputs[build.SITE / "models" / "index.html"]
        catalog = self.nouns.catalog
        for group in ("meta_models", "film_models"):
            for m in catalog[group]:
                (self.assertIn if m["state"] in ("live", "measured") else self.assertNotIn)(f"<h3>{build.text(m['name'])}</h3>", page)
        self.assertEqual(6, page.count('class="mu-step"'))
        self.assertEqual(1, page.count('aria-pressed="true"'))
        self.assertIn('aria-live="polite"', page)
        for path, out in self.outputs.items():
            if path != build.SITE / "models" / "index.html" and path.suffix == ".html" and "source/slides" not in path.as_posix():
                self.assertNotIn("nanoMuse", build.main_of(out) if "<main" in out else out, path)
        with self.assertRaises(build.BuildError):
            build.meta_models("{{model:not-a-model}}", self.nouns.models)
        for page in build.SITE.rglob("*.html"):
            if "source" in page.relative_to(build.SITE).parts:
                continue  # a deck's slide sources write the tokens; the deck page they become renders them
            self.assertNotIn("{{model:", page.read_text(encoding="utf-8"), page)

    def test_the_film_made_page_exists_only_with_real_evidence_and_shows_no_hash(self):
        # Gated (board AgoraFilmMade): no page until the production agent writes phase-1 or final facts.
        nouns = copy.copy(self.nouns)
        nouns.film_made = None
        self.assertIsNone(build.render_film_made(nouns))
        nouns.film_made = {"status": "draft", "films": []}
        self.assertIsNone(build.render_film_made(nouns))
        nouns.film_made = {
            "status": "phase-1", "title": "How this film was made | Agora", "description": "d", "heading": "How this film was made",
            "lead": "Every step of making the film is a Task, and every step is recorded.",
            "films": [{"id": "3m", "cut": "3:00", "name": "The film", "state_label": "Phase 1 recorded",
                       "steps": [{"title": "Capture", "what": "Real Chrome records the live pages.", "who": "a dedicated worker run by ta-amps",
                                  "when": "Nov 1", "seconds": 130}],
                       "summary": "Every step is recorded.", "record": {"label": "Record ↗", "href": "../../evidence/"}}]}
        page = build.render_film_made(nouns)
        self.assertIn("2 min 10 s", page)
        self.assertIn('href="../../evidence/"', page)
        self.assertIsNone(re.search(r"\b[0-9a-f]{12,}\b", build.plain_text(build.main_of(page))))
        built = self.nouns.film_made is not None and self.nouns.film_made.get("status") in build.FILM_MADE_STATES
        self.assertEqual(built, build.SITE / "film" / "made" / "index.html" in self.outputs)
        # Whenever the page is built, its noun is served byte for byte beside it (the production agent reads it).
        self.assertEqual(built, build.SITE / "film" / "made" / "film-made.json" in self.outputs)
        if built:
            self.assertEqual((build.CONTENT / "film-made.json").read_text(encoding="utf-8"),
                             self.outputs[build.SITE / "film" / "made" / "film-made.json"])

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
                self.assertIn(html.escape(build.meta_models(claim["number"], self.nouns.models), quote=False), notes,
                              claim["number"])

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

    def test_moved_pages_point_to_places_that_exist(self):
        for item in self.nouns.moved["pages"]:
            path, _, anchor = item["to"].partition("#")
            target = build.SITE / path / "index.html"
            page = self.outputs.get(target) or target.read_text(encoding="utf-8")
            if anchor:
                self.assertIn(f'id="{anchor}"', page, item["to"])
        # The not-found page lists every moved page, and says the old addresses redirect (the worker reads the
        # same noun), so it never sends anyone to a page that is not there.
        not_found = self.outputs[build.SITE / "404.html"]
        for item in self.nouns.moved["pages"]:
            self.assertIn(f'href="/{html.escape(item["to"])}"', not_found)
        self.assertIn("301", not_found)

    def test_learning_is_a_tab_of_agora_built_from_its_noun(self):
        # A page of Agora, not a new surface. November 1 (v2 brief): the header reads How it works, Use cases, Models used, Decks,
        # Evidence (the film is withdrawn until its re-recorded cut lands), and Learning sits in the footer's second row.
        self.assertEqual(["How it works", "Use cases", "Models used", "Decks", "Evidence"],
                         [item["label"] for item in self.nouns.site["nav"]])
        page = self.outputs[build.SITE / "learning" / "index.html"]
        self.assertIn('<li><a href="../learning/">Learning</a></li>', page)
        main = build.main_of(page)
        # Every word the learning page shows, outside the shared header and footer, is a string of its noun, with its
        # {{model:...}} names rendered from the models catalog.
        written = {build.meta_models(found, self.nouns.models) for found in strings(self.nouns.learning)}
        for shown in shown_text(main):
            self.assertIn(shown, written)
        # The loop is an ordered list of its steps, in the noun's order.
        steps = [step["verb"] for step in self.nouns.learning["loop"]["steps"]]
        self.assertEqual(len(steps), main.count('<li class="loop-step">'))
        places = [main.index(f'<h3 class="loop-verb">{build.text(step)}</h3>') for step in steps]
        self.assertEqual(sorted(places), places)
        # Every measured result links to public evidence, and the build refuses one that doesn't.
        for item in self.nouns.learning["results"]["items"]:
            self.assertTrue(item["link"].startswith("https://github.com/ta-amps/"), item["model"])
            self.assertIn(f'href="{html.escape(build.repoint(item["link"], self.nouns.links))}"', main)
        nouns = copy.copy(self.nouns)
        nouns.learning = copy.deepcopy(self.nouns.learning)
        nouns.learning["results"]["items"][0]["link"] = "notes.md"
        with self.assertRaises(build.BuildError):
            build.render_learning(nouns)

    def test_the_learning_page_and_deck_give_the_same_numbers(self):
        deck = next(deck for deck in self.nouns.decks if deck["id"] == "continuous-learning")
        claims = deck["claims"]["claims"]
        for item in self.nouns.learning["results"]["items"]:
            about = [claim for claim in claims if item["model"] in claim["number"]]
            exact = [claim for claim in about if item["before"] in claim["number"] and item["after"] in claim["number"]]
            self.assertTrue(exact, item["model"])
            for claim in exact:
                self.assertEqual(("measured", item["link"]), (claim["status"], claim["link"]), item["model"])
            listed = " ".join(claim["number"] for claim in about)
            for number in re.findall(r"\d+(?:\.\d+)?", item["line"]):
                self.assertIn(number, listed, (item["model"], number))

    def test_the_library_is_a_page_of_agora_built_from_its_noun(self):
        library, explorer, ecosystem = self.nouns.library, self.nouns.explorer, self.nouns.ecosystem
        page = self.outputs[build.SITE / "library" / "index.html"]
        self.assertIn('<li><a href="../library/">Library</a></li>', page)
        main = build.main_of(page)
        # Every word the page shows is a string of its nouns. The rest is the measured part: numbers, the commit and
        # its date.
        sizes = {len(category["packs"]) for category in library["categories"]}
        measured = {f"{n:,}" for n in set(numbers(library)) | sizes | set(numbers(explorer)) | set(numbers(ecosystem))}
        measured |= {library["source"]["commit"][:7], build.human_date(library["source"]["committed_at"]), "·"}
        written = {build.meta_models(found, self.nouns.models)
                   for found in strings(library) + strings(explorer) + strings(ecosystem)}
        for shown in shown_text(main):
            self.assertIn(shown, written | measured)
        # One card per pack, inside its category's section and in its order, linking to its folder at the commit.
        packs = {pack["id"]: pack for pack in library["packs"]}
        self.assertEqual(len(packs), main.count('<li class="lib-card"'))
        for category in library["categories"]:
            section = main[main.index(f'<section class="lib-group" id="{category["id"]}"'):]
            section = section[:section.index("</section>")]
            self.assertEqual(len(category["packs"]), section.count('<li class="lib-card"'), category["id"])
            places = [section.index(f'<li class="lib-card" id="{pack_id}">') for pack_id in category["packs"]]
            self.assertEqual(sorted(places), places, category["id"])
            for pack_id in category["packs"]:
                self.assertIn(f'href="{html.escape(build.repoint(packs[pack_id]["url"], self.nouns.links))}"', section)
                self.assertIn(f"/tree/{library['source']['commit']}/packs/{pack_id}", packs[pack_id]["url"])
        # The totals shown are the noun's, and every code + tests badge but the legend's is a pack's that ships code.
        for key, value in library["totals"].items():
            self.assertIn(f'<span class="lib-stat-n">{value:,}</span>', main, key)
        self.assertEqual(library["totals"]["with_code"] + 1, main.count('<span class="lib-badge">'))
        # Every pack is a proposal, and the page says so at the top and on every card.
        self.assertEqual({"proposal_only"}, {pack["status"] for pack in packs.values()})
        self.assertIn(build.text(library["dateline"]), main)
        self.assertEqual(len(packs), main.count(f'<span class="lib-card-kind"><span>'
                                                f'{library["words"]["status"]["proposal_only"]}</span>'))
        # The filter: "All", then a link per category, and the page's one style rule marks each when it is on show.
        nav = main[main.index('<nav class="lib-filter"'):]
        nav = nav[:nav.index("</nav>")]
        self.assertEqual(["categories"] + [category["id"] for category in library["categories"]],
                         re.findall(r'href="#([a-z0-9-]+)"', nav))
        style = page[page.index("<style>"):page.index("</style>")]
        for category in library["categories"]:
            self.assertIn(f'.library:has(#{category["id"]}:target) .lib-filter a[href="#{category["id"]}"]', style)

    def test_library_explorer_harness_feeds_and_ecosystem_catalog(self):
        page = self.outputs[build.SITE / "library" / "index.html"]
        main = build.main_of(page)
        for anchor in ("explorer", "ecosystem-explorer"):
            self.assertIn(f'id="{anchor}"', main)
        # Owner, Nov 1 (v2 brief): agent apps appear only on /models/, so the library shows no harness panel, filter
        # or chips; the explorer's data keeps them.
        self.assertNotIn('id="harness-feeds"', main)
        self.assertNotIn("data-exp-harness", main)
        for harness in ("Harness Square", "Muse Code", "OpenCode", "Pi"):
            self.assertNotIn(f"<h3>{harness}</h3>", main)
        match = re.search(r'<script type="application/json" id="agora-explorer-data">(.*?)</script>', page)
        self.assertIsNotNone(match)
        payload = json.loads(match.group(1))
        self.assertEqual(self.nouns.explorer["counts"]["total"], len(payload["items"]))
        self.assertEqual(self.nouns.library["totals"]["packs"],
                         sum(1 for item in payload["items"] if item["kind"] == "pack"))
        # One entry of the source catalog is left out, and the page says so (Agora builder, Nov 1).
        self.assertEqual((706, 707), (len(payload["projects"]), self.nouns.ecosystem["source_metadata"]["source_project_count"]))
        self.assertIn("One entry of the source catalog is left out.", self.nouns.ecosystem["honesty_note"])
        bad_exp = copy.deepcopy(self.nouns.explorer)
        bad_exp["counts"]["total"] += 1
        with self.assertRaises(build.BuildError):
            build.check_explorer(bad_exp, self.nouns.ecosystem)
        bad_eco = copy.deepcopy(self.nouns.ecosystem)
        bad_eco["status"] = "certified"
        with self.assertRaises(build.BuildError):
            build.check_explorer(self.nouns.explorer, bad_eco)

    def test_the_overview_deck_and_the_library_page_agree_at_the_same_commit(self):
        # The overview deck's measured pack count and the library page are counted separately; when they name the
        # same library commit, they must give the same numbers.
        library = self.nouns.library
        deck = next(deck for deck in self.nouns.decks if deck["id"] == "overview-and-architecture")
        claim = next(claim for claim in deck["claims"]["claims"] if claim["slide"] == "seed-packs")
        commit = re.search(r"/blob/([0-9a-f]{40})/", claim["link"]).group(1)
        if commit == library["source"]["commit"]:
            totals = library["totals"]
            self.assertTrue(claim["number"].startswith(
                f'{totals["packs"]:,} seed packs in one library, with {totals["nouns"]:,} Task Objects, {totals["verbs"]:,} '
                f'Task templates and {totals["worked_examples"]:,} worked examples'), claim["number"])

    def test_library_categories_follow_what_the_packs_are(self):
        library = self.nouns.library
        home = {pack_id: category["id"] for category in library["categories"] for pack_id in category["packs"]}
        self.assertEqual(sorted(home), sorted(pack["id"] for pack in library["packs"]))
        # The nine agent kits pin a kit noun in the library, and they all sit with the nonprofit packs.
        kits = [pack["id"] for pack in library["packs"] if pack["kit"]]
        self.assertTrue(kits)
        for pack_id in kits:
            self.assertEqual("nonprofit-kits", home[pack_id], pack_id)
        # Hand-written words state no counts, which only the measured part holds.
        for text_ in [library["lead"], library["dateline"], library["description"]] + \
                     [category["intro"] for category in library["categories"]]:
            self.assertIsNone(re.search(r"\b\d+\s+(?:packs?|nouns?|verbs?)\b", text_), text_)

    def test_the_build_refuses_a_malformed_library_noun(self):
        base = self.nouns.library
        build.check_library(base)
        first, other = base["packs"][0]["id"], base["categories"][1]["packs"][0]

        def refused(change):
            noun = copy.deepcopy(base)
            change(noun)
            with self.assertRaises(build.BuildError):
                build.check_library(noun)

        refused(lambda n: n["totals"].update(nouns=n["totals"]["nouns"] + 1))
        refused(lambda n: n["packs"][0].update(verbs=n["packs"][0]["verbs"] + 1))
        refused(lambda n: n["categories"][0]["packs"].append(other))
        refused(lambda n: n["categories"][0]["packs"].pop())
        refused(lambda n: n["categories"][0]["packs"].append("no-such-pack"))
        refused(lambda n: n["packs"][0].update(url=n["packs"][0]["url"].replace(n["source"]["commit"], "main")))
        refused(lambda n: n["packs"][0].update(status="admitted"))
        refused(lambda n: n["packs"][0].update(purpose="A collection of nouns and verbs for everything"))
        refused(lambda n: n["packs"][0].update(code={"files": 3, "tests": 0, "workflow": ".github/workflows/x.yml"}))
        refused(lambda n: n["packs"][0].update(installed=True))
        refused(lambda n: n["packs"].append(copy.deepcopy(n["packs"][0])))
        refused(lambda n: n["source"].update(commit=n["source"]["commit"][:7]))
        refused(lambda n: n["source"].update(committed_at="2026-10-30"))
        refused(lambda n: n["source"].update(repository="https://github.com/someone/fork"))
        refused(lambda n: n["categories"][0].update(id=first))
        refused(lambda n: n["categories"][0].update(id="3d-and-video"))
        refused(lambda n: n["categories"][0].update(id="categories"))

    def test_every_number_in_the_learning_deck_has_a_claim_with_public_evidence(self):
        deck = next(deck for deck in self.nouns.decks if deck["id"] == "continuous-learning")
        claims = deck["claims"]["claims"]
        for claim in claims:
            self.assertTrue(claim["link"].startswith("https://github.com/ta-amps/"), claim["number"])
        # Model and GPU names, the loop's step labels and the date are names, not numbers to source.
        names = re.compile(r"\b(?:1|3|30)B\b|\bT4s?\b|October 30, 2026|(?<![\d.])0[1-8](?![\d.])", re.I)
        for slide in deck["slides"]:
            listed = " ".join(claim["number"] for claim in claims if claim["slide"] == slide["name"])
            for part in (build.plain_text(without_number(slide["inner"])), build.plain_text(slide["notes"])):
                for number in re.findall(r"\d+(?:[.,]\d+)?", names.sub(" ", part)):
                    self.assertIn(number, listed, (slide["name"], number))

    # Acceptance and accessibility fixes, October 30 ------------------------------------------------------------

    def test_deck_viewer_controls_and_help_come_from_the_site_noun(self):
        # The letter shortcuts have a visible switch (WCAG 2.1.4), and slides can be shown larger (WCAG 1.4.4).
        ui = self.nouns.site["deck"]
        self.assertIn("<kbd>N</kbd>", ui["help_html"])
        self.assertIn("focus", ui["help_html"])
        for deck in self.nouns.decks:
            main = build.main_of(self.outputs[deck["page"]])
            self.assertEqual(1, main.count(f'data-large-toggle aria-pressed="false" hidden>{build.text(ui["larger"])}</button>'),
                             deck["id"])
            self.assertEqual(1, main.count(f'<label class="deck-keys"><input type="checkbox" data-keys-toggle checked> '
                                           f'{build.text(ui["letter_keys"])}</label>'), deck["id"])
            self.assertIn(f'<p>{ui["help_html"]}</p>', main)

    def test_repository_links_go_to_agoras_mirror_only_when_it_mirrors_the_repository(self):
        # F31-014 (Oct 31) pointed every GitHub link at Agora's source mirror. Nov 1 (the lead): a repository is
        # mirrored only once its head is free of every banned word (source-links.json "mirrored", matched by the
        # deploy builder's repos.json); until then its links go to its GitHub page. Pages sites stay retired.
        links = self.nouns.links
        mirrored = set(links["mirrored"])
        self.assertLessEqual(mirrored, set(links["heads"]))
        source_links = 0
        for path, page in self.outputs.items():
            self.assertNotIn("ta-amps.github.io", page, path)
            for repo, dotgit in re.findall(r"github\.com/ta-amps/([A-Za-z0-9._-]+?)(\.git)?(?=[/\"'<\s?#]|$)", page):
                self.assertIn(repo, links["heads"], path)
                # A mirrored repository's clone address stays on GitHub while Agora serves no history for it.
                if not (dotgit and repo not in links.get("git_served", [])):
                    self.assertNotIn(repo, mirrored, path)
            for href in re.findall(r'\shref="(/source/[^"]*)"', page):
                self.assertRegex(href, r"^/source/(?:[a-z0-9-]+/(?:[0-9a-f]{12}/.*)?)?$", path)
                repo = href.split("/")[2]
                if repo:  # the /source/ index itself always exists: it lists every repository and where its files are
                    source_links += 1
                    self.assertIn(repo, mirrored, (path, href))
        if not mirrored:
            self.assertEqual(0, source_links)
        self.assertEqual(set(links["heads"]), {"ta-amps-hackathon", "eranos-public-marketplace-for-public-good-token-burn",
                                               "agora-public-overview-architecture-setup-and-contribution",
                                               "tessera-infrastructure-work-and-storage-engine",
                                               "herma-infrastructure-shim-for-intelligent-agents",
                                               "seed-packs-library-of-nouns-and-verbs"})
        for sha in list(links["heads"].values()) + list(links["pulls"].values()):
            self.assertRegex(sha, r"^[0-9a-f]{40}$")
        # Both states of the switch. Not mirrored: the GitHub address stays exactly as the noun wrote it.
        tessera = "https://github.com/ta-amps/tessera-infrastructure-work-and-storage-engine"
        off = dict(links, mirrored=[], git_served=[])
        for url in (f"{tessera}/blob/main/docs/x.md", f"git clone {tessera}.git\n", f"{tessera}/tree/some-branch/x"):
            self.assertEqual(url, build.repoint(url, off))
        # Mirrored: every link means the swept head (a branch name, a full commit or a pull request alike: Agora serves
        # no older tree), and an address without a home fails; a clone address goes to the git mirror, which git can
        # clone; the file view cannot be cloned.
        on = dict(links, mirrored=sorted(links["heads"]), git_served=sorted(links["heads"]))
        head12 = links["heads"]["tessera-infrastructure-work-and-storage-engine"][:12]
        for ref in ("main", "95e434eb820f2dbc3873cd443e4ba144acefc762"):
            self.assertEqual(f"/source/tessera-infrastructure-work-and-storage-engine/{head12}/docs/x.md",
                             build.repoint(f"{tessera}/blob/{ref}/docs/x.md", on))
        with self.assertRaises(build.BuildError):
            build.repoint(f"{tessera}/tree/some-branch/x", on)
        with self.assertRaises(build.BuildError):
            build.repoint("https://github.com/ta-amps/another-repo", on)
        self.assertEqual("git clone https://agora.ta-amps.workers.dev/git/tessera-infrastructure-work-and-storage-engine.git\n",
                         build.repoint(f"git clone {tessera}.git\n", on))
        # Agora's own repository has no published git mirror, so a clone address for it stops the build when mirrored.
        with self.assertRaises(build.BuildError):
            build.repoint("https://github.com/ta-amps/agora-public-overview-architecture-setup-and-contribution.git", on)
        for page in build.SITE.rglob("*.html"):
            if not page.relative_to(build.SITE).as_posix().startswith(("decks/2026-10-29/", "storyboards/")):
                self.assertNotRegex(page.read_text(encoding="utf-8"), r"git clone /", page)
        # The release files the frozen drafts link are served here, byte for byte as recorded.
        for version in self.nouns.manifest["versions"]:
            for download in version.get("downloads", []):
                if "url" in download:
                    local = build.SITE / build.repoint(download["url"], dict(links, mirrored=sorted(links["heads"]))).lstrip("/")
                    data = local.read_bytes()
                    self.assertEqual((download["sha256"], download["bytes"]), (build.sha256(data), len(data)), local)

    def test_the_film_page_is_built_only_from_a_cuts_lines_word_for_word(self):
        # The film page is a cut's text alternative. Owner, Nov 1: the October 31 cut named a model the owner no longer
        # shows, so its lines are gone and no film page is built until the re-recorded cut's captions fill them.
        film, home = self.nouns.film, self.nouns.home
        self.assertIn("transcript and scene descriptions", film["heading"].lower())
        self.assertIn("no separate audio-described cut", film["audio_description"])
        page_path = build.SITE / "film" / "index.html"
        if not film["lines"]:
            self.assertEqual([], film["acts"])
            self.assertNotIn(page_path, self.outputs)
            return
        page = self.outputs[page_path]
        self.assertIn(f"<h1>{build.text(film['heading'])}</h1>", page)
        self.assertIn(f'<p class="dateline">{build.text(film["audio_description"])}</p>', page)
        self.assertIn("transcript", home["videos"]["outline"]["label"].lower())
        self.assertIn(f'<a href="film/">{build.text(home["videos"]["outline"]["label"])}</a>',
                      self.outputs[build.SITE / "index.html"])
        # A transcript is the narration word for word: the film noun's lines are the full cut's captions.
        full = next(cut for cut in home["videos"]["cuts"] if cut["id"] == "full")
        captions = build.plain_words((build.SITE / full["captions"]).read_text(encoding="utf-8"))
        self.assertEqual(caption_words(captions), plain_words(" ".join(line["words"] for line in film["lines"])))

    def test_the_film_page_says_its_storyboard_is_the_draft_runs(self):
        # Hunt, October 30: the page said the storyboard was drawn from the production run, but the image is
        # the draft run's (its own header says "Draft preview", captures from 01:06 EDT).
        film = self.nouns.film
        self.assertNotIn("from the production run", film["lead"])
        if film.get("storyboard"):
            self.assertIn("draft run", film["lead"])
            self.assertIn("draft run", film["storyboard"]["caption"])

    def test_the_home_description_names_no_film_until_its_new_cut(self):
        description = self.nouns.home["description"]
        self.assertNotIn("draft video", description)
        self.assertNotIn("film", description)  # withdrawn until the re-recorded cut lands
        self.assertIn(f'<meta name="description" content="{build.attr(description)}">', self.outputs[build.SITE / "index.html"])

    def test_the_footer_privacy_line_comes_from_its_noun_and_matches_what_the_pages_load(self):
        privacy = self.nouns.site["footer"]["privacy"]
        for path, page in self.outputs.items():
            if path.suffix == ".html" and "<!-- site:footer -->" in page:
                self.assertEqual(1, page.count(f'<p class="footer-privacy">{build.text(privacy)}</p>'), path)
        # "The fonts come from this site": no current page loads anything from another host (self-hosted fonts, Nov 1).
        loads = re.compile(r'<(?:link|script|img|video|source|track|iframe)\b[^>]*?\s(?:href|src)="(https?://[^"/]+)', re.I)
        hosts = {host for path, page in self.outputs.items() if path.suffix == ".html" for host in loads.findall(page)}
        self.assertEqual(set(), hosts)
        self.assertNotIn("Google Fonts", privacy)
        # "No analytics, ads or cookies", and "display choices stay in this browser": the scripts set no cookie,
        # send nothing, and keep only these display choices in local storage.
        scripts = {path.name: path.read_text(encoding="utf-8") for path in (build.SITE / "assets").glob("*.js")}
        # The shared agent banner can read its noun from a src address, as Eranos does; on Agora the noun is
        # embedded in the page and no banner has a src, so that one fetch never runs here.
        banner_script = scripts.pop("agent-banner.js")
        # The judge tour can read its noun from a src address too; on Agora it is embedded and no tour has a src.
        tour_script = scripts.pop("judge-tour.js")
        self.assertEqual(1, len(re.findall(r"\bfetch\(", tour_script)))
        self.assertIsNone(re.search(r"\b(XMLHttpRequest|sendBeacon|WebSocket|localStorage)\b", tour_script))
        for path, page in self.outputs.items():
            if path.suffix == ".html":
                self.assertIsNone(re.search(r"<ta-judge-tour\b[^>]*\ssrc=", page), path)
        self.assertEqual(1, len(re.findall(r"\bfetch\(", banner_script)))
        self.assertIsNone(re.search(r"\b(XMLHttpRequest|sendBeacon|WebSocket)\b", banner_script))
        self.assertNotIn("cookie", banner_script.lower())
        self.assertNotIn("localStorage", banner_script)
        for path, page in self.outputs.items():
            if path.suffix == ".html":
                self.assertIsNone(re.search(r"<ta-agent-banner\b[^>]*\ssrc=", page), path)
        stored = set()
        for name, script in scripts.items():
            self.assertNotIn("cookie", script.lower(), name)
            self.assertIsNone(re.search(r"\b(fetch|XMLHttpRequest|sendBeacon|WebSocket)\b", script), name)
            stored |= set(re.findall(r'localStorage\.setItem\("([^"]+)"', script))
            stored |= set(re.findall(r'write\("([^"]+)"', script))
        # Light only: there is no stored mode any more; the deck viewer keeps its three display choices.
        self.assertEqual({"ta-amps-deck-notes", "ta-amps-deck-large", "ta-amps-deck-letter-keys"}, stored)
        self.assertIn("No analytics, ads or cookies", privacy)

    def test_slide_and_notes_text_colours_pass_contrast(self):
        css = (build.SITE / "assets" / "site.css").read_text(encoding="utf-8")
        # Light only (owner, Nov 1): one token set, Paper & Ink tokens v3 (assets/tokens.css) under Agora's names.
        for stylesheet in ("site.css", "tokens.css", "viewer.css"):
            text_ = (build.SITE / "assets" / stylesheet).read_text(encoding="utf-8")
            self.assertNotIn("prefers-color-scheme: dark", text_, stylesheet)
            self.assertNotIn('data-mode="dark"', text_, stylesheet)
        light = resolved_tokens()
        self.assertEqual("only light", re.search(r":root \{\s*color-scheme: ([\w ]+);", css).group(1))
        # Text and its paper pass AA: body, secondary and muted ink, both accents' text, and the notes headings.
        for fg, bg in (("--color-ink", "--color-paper"), ("--color-ink-2", "--color-paper"), ("--color-muted", "--color-paper"),
                       ("--color-noun-ink", "--color-paper"), ("--color-verb-ink", "--color-paper"),
                       ("--color-band-ink", "--color-band"), ("--color-code-ink", "--color-code"),
                       ("--color-button-ink", "--color-button")):
            self.assertGreaterEqual(contrast(light[fg], light[bg]), 4.5, (fg, bg))
        # The speaker-notes and slide-links headings sit on the stage: 4.38:1 before, so a darker grey on light.
        self.assertGreaterEqual(contrast(light["--color-muted-on-stage"], light["--color-stage"]), 4.5)
        viewer = (build.SITE / "assets" / "viewer.css").read_text(encoding="utf-8")
        for selector in (".slide-notes h2", ".slide-links h2"):
            self.assertIn(f"{selector} {{ font-family: var(--font-body); font-size: var(--text-small); font-weight: 600; "
                          "color: var(--color-muted-on-stage); }", viewer)
        # Slide text in rust uses the darker text rust (5.09:1 on the paper, 5.6:1 on cards); #B8541F stays a fill.
        self.assertLess(contrast("#B8541F", "#F5F2EA"), 4.5)
        self.assertGreaterEqual(contrast("#A84B1B", "#F5F2EA"), 4.5)
        for deck in self.nouns.decks:
            for slide in deck["slides"]:
                self.assertNotIn("color:#B8541F", slide["inner"], (deck["id"], slide["name"]))
        # The learning deck's dark panels keep labels in a grey that passes on #11161F (5.80:1).
        self.assertGreaterEqual(contrast("#8A92A2", "#11161F"), 4.5)

    def test_the_seed_pack_count_on_the_slide_matches_its_measured_claim(self):
        deck = next(deck for deck in self.nouns.decks if deck["id"] == "overview-and-architecture")
        slide = next(slide for slide in deck["slides"] if slide["name"] == "seed-packs")
        claim = next(claim for claim in deck["claims"]["claims"] if claim["slide"] == "seed-packs")
        packs = re.search(r"(\d+) packs live in one library", build.plain_text(slide["inner"])).group(1)
        self.assertTrue(claim["number"].startswith(f"{packs} seed packs in one library, with "), claim["number"])
        self.assertEqual("measured", claim["status"])
        # Measured at one commit of the library, and linked to that commit's README.
        commit = re.search(r"/blob/([0-9a-f]{40})/README\.md#seed-pack-library$", claim["link"]).group(1)
        self.assertNotIn(commit[:7], claim["source"])
        if commit == self.nouns.library["source"]["commit"]:
            self.assertIn(build.human_date(self.nouns.library["source"]["committed_at"]), claim["source"])


if __name__ == "__main__":
    unittest.main()
