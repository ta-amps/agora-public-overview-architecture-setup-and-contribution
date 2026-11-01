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
        nouns.uses["flagships"][1]["name"] = "A flagship from data"
        nouns.uses["fields"]["items"].append("A field from data")
        uses_page = build.render_use_cases(nouns)
        self.assertIn("A flagship from data", uses_page)
        self.assertIn("A field from data", uses_page)
        nouns.banner = dict(self.nouns.banner, lead="A banner from data.")
        self.assertIn("A banner from data.", build.header_block(build.SITE / "index.html", "", nouns))
        nouns.site = copy.deepcopy(self.nouns.site)
        nouns.site["header"]["eranos_label"] = "Eranos from data"
        self.assertIn("Eranos from data", build.header_block(build.SITE / "index.html", "", nouns))
        # Every word the use cases page shows, outside the shared header and footer, is a string of its noun, or the
        # title of a pack it names, which comes from the library noun.
        titles = {pack["id"]: pack["title"] for pack in self.nouns.library["packs"]}
        written = set(strings(self.nouns.uses)) | {titles[pack_id] for item in self.nouns.uses["flagships"]
                                                    for pack_id in item["packs"]}
        for shown in shown_text(build.main_of(self.outputs[build.SITE / "use-cases" / "index.html"])):
            self.assertIn(shown, written)

    def test_use_cases_are_ideas_without_status_or_evidence(self):
        uses = self.nouns.uses
        self.assertLessEqual(set(uses), {"about", "title", "description", "heading", "lead", "nouns_label", "verbs_label",
                                         "packs_label", "flagships", "fields"})
        # The owner's seven flagships, in the owner's order and words; Tokens for Good leads.
        self.assertEqual(["Tokens for Good", "Motion Graphics and Video Gen", "Feed Systems to Keep Your Agent Informed",
                          "Shimming Systems", "Code Reusability", "Continuous Learning",
                          "Long-Horizon Tasks via Atomic Steps and Decentralized Solutioning"],
                         [" ".join(filter(None, (item["name"], item.get("rest")))) for item in uses["flagships"]])
        self.assertTrue(uses["flagships"][0]["line"].startswith("Spare tokens for good."))
        page = self.outputs[build.SITE / "use-cases" / "index.html"]
        main = build.main_of(page)
        self.assertEqual(7, main.count('<li class="use-card'))
        self.assertEqual(1, main.count('<li class="use-card use-lead"'))
        self.assertLess(main.index("use-lead"), main.index(uses["flagships"][1]["name"]))
        for item in uses["flagships"]:
            # An idea is a name, a line or two, example nouns and verbs, the library packs that hold them and where to
            # read more: no status, badge or evidence.
            self.assertLessEqual(set(item), {"name", "rest", "line", "detail", "nouns", "verbs", "packs", "links", "home"},
                                 item["name"])
            self.assertTrue(3 <= len(item["nouns"]) <= 5 and 3 <= len(item["verbs"]) <= 5, item["name"])
            self.assertTrue(1 <= len(item["links"]) <= 3, item["name"])
            words = ([item["name"], item.get("rest", ""), item["line"], item.get("detail", "")] + item["nouns"] + item["verbs"]
                     + list((item.get("home") or {}).values()))
            self.assertIsNone(re.search(r"\d", " ".join(words)), item["name"])
            for link in item["links"]:
                href = link["href"] if link["href"].startswith("https://") else "../" + link["href"]
                self.assertIn(f'href="{html.escape(build.repoint(href, self.nouns.links))}"', main, item["name"])
        # Other fields are plain names, with no nouns or verbs of their own, and point to the roll-your-own deck.
        self.assertTrue(all(isinstance(field, str) for field in uses["fields"]["items"]))
        self.assertIn(f'href="../{uses["fields"]["link"]["href"]}"', main)
        for leftover in ("claim-status", 'class="badge', "use-tag"):
            self.assertNotIn(leftover, main)

    def test_the_home_page_is_the_film_start_here_the_decks_and_the_use_cases(self):
        # October 31 (the Agora-Home board): the film first, then Start here with the two public sites, the decks
        # and the use cases. The start part's heading is the page's one h1.
        home = self.outputs[build.SITE / "index.html"]
        main = home[home.index('<main id="main">'):home.index("</main>")]
        self.assertEqual(4, main.count("<section"))
        self.assertEqual(1, main.count("<video"))
        self.assertIn('kind="captions"', main)
        self.assertIn(" default>", main)
        self.assertLess(home.index("<ta-agent-banner "), home.index("<video"))
        order = [main.index(marker) for marker in ('<section class="film', '<section class="start"', '<section class="deck-band"',
                                                    '<section class="home-uses"')]
        self.assertEqual(sorted(order), order)
        start = self.nouns.home["start"]
        self.assertEqual(1, main.count("<h1"))
        self.assertIn(f"<h1>{build.text(start['heading'])}</h1>", main)
        self.assertEqual(["Eranos", "Agora"], [card["name"] for card in start["cards"]])
        self.assertIn('href="https://eranos.ta-amps.workers.dev/"', main)
        self.assertIn('href="how-it-works/"', main)
        self.assertEqual(5, main.count('class="deck-card"'))
        self.assertEqual(6, main.count('class="home-use"'))
        self.assertEqual(1, main.count('class="home-use-live"'))  # only Eranos is live, so only it says so
        # The film's production page is linked only once its production trace is final.
        self.assertEqual(build.film_made_ready(start), start["film_made"]["href"] in main)

    def test_nouns_and_verbs_are_glossed_in_plain_words_the_first_time(self):
        # Feedback, October 30: a viewer took nouns and verbs for a model architecture. The home page, the use cases
        # page and the overview and roll-your-own decks say in plain words what they are the first time they name
        # them: verbs are tasks, and nouns are everything a task uses or makes. The overview says plainly that this
        # is how the work is organized, not a model architecture. The marketplace deck, written for nonprofits,
        # glosses its first verb once, as a task.
        named = re.compile(r"\b(?:nouns?|verbs?)\b", re.I)

        def glossed(shown: str, where: str) -> None:
            found = named.search(shown)
            self.assertIsNotNone(found, where)
            self.assertIn("verbs are tasks", shown[found.start():found.start() + 160].lower(), where)

        for path in (build.SITE / "index.html", build.SITE / "use-cases" / "index.html"):
            glossed(build.plain_text(build.main_of(self.outputs[path])), path.relative_to(build.ROOT).as_posix())
        decks = {deck["id"]: deck for deck in self.nouns.decks}
        for deck_id in ("overview-and-architecture", "roll-your-own"):
            glossed(" ".join(build.plain_text(slide["inner"]) for slide in decks[deck_id]["slides"]), deck_id)
        overview = {slide["name"]: build.plain_text(slide["inner"]) for slide in decks["overview-and-architecture"]["slides"]}
        self.assertIn("NOT A MODEL ARCHITECTURE", overview["nouns-and-verbs"])
        self.assertIn("how the work is organized", overview["nouns-and-verbs"])
        market = " ".join(build.plain_text(slide["inner"]) for slide in decks["public-good-marketplace"]["slides"])
        self.assertEqual(1, market.count("(a task)"))
        first = re.search(r"\bverbs?\b", market)
        self.assertEqual(" (a task)", market[first.end():first.end() + len(" (a task)")])

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
        one = dict(videos["cuts"][0], id="one")
        videos["cuts"], videos["default"] = [one], "one"
        self.assertNotIn("data-film-cuts", build.render_home(nouns))
        other = dict(one, id="other", tab="Other cut", label="The other cut")
        other["src"] = "video/2026-10-29/animatic-60s-v1/eranos-animatic-60s-open-captions.mp4"
        videos["cuts"].insert(0, other)
        videos["default"] = "other"
        page = build.render_home(nouns)
        self.assertEqual(1, page.count("<video"))
        self.assertEqual(2, page.count('class="film-cut"'))
        self.assertIn(f'<source src="{other["src"]}"', page)
        self.assertIn('aria-pressed="true" data-cut="other"', page)
        self.assertIn('aria-pressed="false" data-cut="one"', page)
        self.assertIn('id="film-label">The other cut</span>', page)
        # Hunt, October 30: without JavaScript the buttons stay hidden, so every other cut is a plain link,
        # which site.js hides once the buttons work. Before, the short cut was unreachable without JavaScript.
        self.assertIn(f'<span data-no-script> · <a href="{one["src"]}">{one["tab"]}</a></span>', page)
        self.assertNotIn(f'<span data-no-script> · <a href="{other["src"]}">', page)
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
        # A page of Agora, not a new surface. October 31 (SiteHeader board): the header reads The film, How it works,
        # Use cases, Decks, Evidence, and Learning sits in the footer of every page.
        self.assertEqual(["The film", "How it works", "Use cases", "Decks", "Evidence"],
                         [item["label"] for item in self.nouns.site["nav"]])
        page = self.outputs[build.SITE / "learning" / "index.html"]
        self.assertIn('<li><a href="../learning/">Learning</a></li>', page)
        main = build.main_of(page)
        # Every word the learning page shows, outside the shared header and footer, is a string of its noun.
        written = set(strings(self.nouns.learning))
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
        written = set(strings(library)) | set(strings(explorer)) | set(strings(ecosystem))
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
        for anchor in ("explorer", "harness-feeds", "ecosystem-explorer"):
            self.assertIn(f'id="{anchor}"', main)
        for harness in ("Harness Square", "Muse Code", "OpenCode", "Pi"):
            self.assertIn(f"<h3>{harness}</h3>", main)
        for tier in ("Tier 0", "Tier 1", "Tier 2", "Tier 3"):
            self.assertIn(tier, main)
        match = re.search(r'<script type="application/json" id="agora-explorer-data">(.*?)</script>', page)
        self.assertIsNotNone(match)
        payload = json.loads(match.group(1))
        self.assertEqual(self.nouns.explorer["counts"]["total"], len(payload["items"]))
        self.assertEqual(self.nouns.library["totals"]["packs"],
                         sum(1 for item in payload["items"] if item["kind"] == "pack"))
        self.assertEqual(707, len(payload["projects"]))
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
                f'{totals["packs"]:,} seed packs in one library, with {totals["nouns"]:,} nouns, {totals["verbs"]:,} '
                f'verb templates and {totals["worked_examples"]:,} worked examples'), claim["number"])

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

    def test_every_use_case_names_library_packs_that_link_to_their_cards(self):
        packs = {pack["id"]: pack for pack in self.nouns.library["packs"]}
        main = build.main_of(self.outputs[build.SITE / "use-cases" / "index.html"])
        library_page = self.outputs[build.SITE / "library" / "index.html"]
        for item in self.nouns.uses["flagships"]:
            self.assertTrue(2 <= len(item["packs"]) <= 5, item["name"])
            for pack_id in item["packs"]:
                self.assertIn(f'<a href="../library/#{pack_id}">{build.text(packs[pack_id]["title"])}</a>', main)
                self.assertIn(f'<li class="lib-card" id="{pack_id}">', library_page)
        for wrong in (["no-such-pack", "video-qa"], ["video-qa"], ["video-qa", "video-qa"], sorted(packs)[:6]):
            nouns = copy.copy(self.nouns)
            nouns.uses = copy.deepcopy(self.nouns.uses)
            nouns.uses["flagships"][1]["packs"] = wrong
            with self.assertRaises(build.BuildError):
                build.render_use_cases(nouns)

    def test_every_number_in_the_learning_deck_has_a_claim_with_public_evidence(self):
        deck = next(deck for deck in self.nouns.decks if deck["id"] == "continuous-learning")
        claims = deck["claims"]["claims"]
        for claim in claims:
            self.assertTrue(claim["link"].startswith("https://github.com/ta-amps/"), claim["number"])
        # Model and GPU names, the loop's step labels and the date are names, not numbers to source.
        names = re.compile(r"Llama 3\.2 [13]B|\b(?:1|3|30)B\b|RTX 3060|\bT4s?\b|October 30, 2026|(?<![\d.])0[1-8](?![\d.])",
                           re.I)
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

    def test_no_page_links_the_retired_github_organization(self):
        # F31-014, October 31: github.com/ta-amps answers 404 since the account was suspended, and so do its Pages
        # sites. Every page links Agora's source mirror instead, at a pinned commit, and no page names a GitHub
        # address at all. The nouns keep the old addresses only as machine-readable provenance.
        checked = 0
        for path, page in self.outputs.items():
            self.assertNotIn("github.com/ta-amps", page, path)
            self.assertNotIn("ta-amps.github.io", page, path)
            for href in re.findall(r'\shref="(/source/[^"]*)"', page):
                checked += 1
                self.assertRegex(href, r"^/source/(?:[a-z0-9-]+/(?:[0-9a-f]{12}/.*)?)?$", path)
        self.assertGreaterEqual(checked, 100)
        links = self.nouns.links
        self.assertEqual(set(links["heads"]), {"ta-amps-hackathon", "eranos-public-marketplace-for-public-good-token-burn",
                                               "agora-public-overview-architecture-setup-and-contribution",
                                               "tessera-infrastructure-work-and-storage-engine",
                                               "herma-infrastructure-shim-for-intelligent-agents",
                                               "seed-packs-library-of-nouns-and-verbs"})
        for sha in list(links["heads"].values()) + list(links["pulls"].values()):
            self.assertRegex(sha, r"^[0-9a-f]{40}$")
        # A branch link means the pinned head, a full commit stays itself, and an address without a home fails.
        self.assertEqual("/source/tessera-infrastructure-work-and-storage-engine/95e434eb820f/docs/x.md",
                         build.repoint("https://github.com/ta-amps/tessera-infrastructure-work-and-storage-engine/blob/main/docs/x.md", links))
        with self.assertRaises(build.BuildError):
            build.repoint("https://github.com/ta-amps/tessera-infrastructure-work-and-storage-engine/tree/some-branch/x", links)
        with self.assertRaises(build.BuildError):
            build.repoint("https://github.com/ta-amps/another-repo", links)
        # A clone address goes to the git mirror, which git can clone; the file view cannot be cloned. Agora's own
        # repository has no published mirror, so a clone address for it stops the build.
        self.assertEqual("git clone https://agora.ta-amps.workers.dev/git/tessera-infrastructure-work-and-storage-engine.git\n",
                         build.repoint("git clone https://github.com/ta-amps/tessera-infrastructure-work-and-storage-engine.git\n", links))
        with self.assertRaises(build.BuildError):
            build.repoint("https://github.com/ta-amps/agora-public-overview-architecture-setup-and-contribution.git", links)
        for page in build.SITE.rglob("*.html"):
            if not page.relative_to(build.SITE).as_posix().startswith(("decks/2026-10-29/", "storyboards/")):
                self.assertNotRegex(page.read_text(encoding="utf-8"), r"git clone /", page)
        # The release files the frozen drafts link are served here, byte for byte as recorded.
        for version in self.nouns.manifest["versions"]:
            for download in version.get("downloads", []):
                if "url" in download:
                    local = build.SITE / build.repoint(download["url"], links).lstrip("/")
                    data = local.read_bytes()
                    self.assertEqual((download["sha256"], download["bytes"]), (build.sha256(data), len(data)), local)

    def test_the_film_page_is_its_transcript_and_says_there_is_no_described_cut(self):
        film, home = self.nouns.film, self.nouns.home
        page = self.outputs[build.SITE / "film" / "index.html"]
        self.assertIn("transcript and scene descriptions", film["heading"].lower())
        self.assertIn(f"<h1>{build.text(film['heading'])}</h1>", page)
        self.assertIn(f'<p class="dateline">{build.text(film["audio_description"])}</p>', page)
        self.assertIn("audio-described cut is not available yet", film["audio_description"])
        self.assertIn("transcript", home["videos"]["outline"]["label"].lower())
        self.assertIn(f'<a href="film/">{build.text(home["videos"]["outline"]["label"])}</a>',
                      self.outputs[build.SITE / "index.html"])
        # A transcript is the narration word for word: the film noun's lines are the full cut's captions, except that
        # the owner's October 31 rule puts plain words where the current cut's captions say "synthetic", until the
        # replacement cut lands.
        full = next(cut for cut in home["videos"]["cuts"] if cut["id"] == "full")
        captions = build.plain_words((build.SITE / full["captions"]).read_text(encoding="utf-8"))
        self.assertEqual(caption_words(captions), plain_words(" ".join(line["words"] for line in film["lines"])))

    def test_the_film_page_says_its_storyboard_is_the_draft_runs(self):
        # Hunt, October 30: the page said the storyboard was drawn from the production run, but the image is
        # the draft run's (its own header says "Draft preview", captures from 01:06 EDT).
        film = self.nouns.film
        self.assertNotIn("from the production run", film["lead"])
        self.assertIn("draft run", film["lead"])
        self.assertIn("draft run", film["storyboard"]["caption"])

    def test_the_home_description_names_the_film_not_a_draft_video(self):
        description = self.nouns.home["description"]
        self.assertNotIn("draft video", description)
        self.assertIn("three-minute film", description)
        self.assertIn(f'<meta name="description" content="{build.attr(description)}">', self.outputs[build.SITE / "index.html"])

    def test_the_footer_privacy_line_comes_from_its_noun_and_matches_what_the_pages_load(self):
        privacy = self.nouns.site["footer"]["privacy"]
        for path, page in self.outputs.items():
            if path.suffix == ".html" and "<!-- site:footer -->" in page:
                self.assertEqual(1, page.count(f'<p class="footer-privacy">{build.text(privacy)}</p>'), path)
        # "Fonts load from Google Fonts": the only outside hosts any current page loads anything from.
        loads = re.compile(r'<(?:link|script|img|video|source|track|iframe)\b[^>]*?\s(?:href|src)="(https?://[^"/]+)', re.I)
        hosts = {host for path, page in self.outputs.items() if path.suffix == ".html" for host in loads.findall(page)}
        self.assertEqual({"https://fonts.googleapis.com", "https://fonts.gstatic.com"}, hosts)
        self.assertIn("Google Fonts", privacy)
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
        self.assertEqual({"ta-amps-mode", "ta-amps-deck-notes", "ta-amps-deck-large", "ta-amps-deck-letter-keys"}, stored)
        self.assertIn("No analytics, ads or cookies", privacy)

    def test_slide_and_notes_text_colours_pass_contrast(self):
        css = (build.SITE / "assets" / "site.css").read_text(encoding="utf-8")
        light, dark = css_tokens(css, ":root"), css_tokens(css, '[data-mode="dark"]')
        self.assertEqual(dark, css_tokens(css[css.index("@media (prefers-color-scheme: dark)"):], "  :root:not([data-mode])"))
        # The speaker-notes and slide-links headings sit on the stage: 4.38:1 before, so a darker grey on light.
        for tokens in (light, dark):
            self.assertGreaterEqual(contrast(tokens["--color-muted-on-stage"], tokens["--color-stage"]), 4.5)
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
        # The learning deck's dark result panel: labels in a lighter grey (5.80:1 on #11161F, 3.06:1 before).
        small = next(s for d in self.nouns.decks for s in d["slides"] if s["name"] == "small-models")
        self.assertNotIn("color:#5E6472", small["inner"])
        self.assertEqual(4, small["inner"].count("color:#8A92A2"))
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
        self.assertIn(f"at commit {commit[:7]}", claim["source"])


if __name__ == "__main__":
    unittest.main()
