import copy
import hashlib
import importlib.util
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("check", ROOT / "scripts/check.py")
check = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(check)


class PublicationChecks(unittest.TestCase):
    def test_current_documents(self):
        self.assertTrue(check.check(ROOT)["offline_only"])

    def test_rejects_duplicate_and_nonfinite_json(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "input.json"
            for value in ('{"x":1,"x":2}', '{"x":NaN}', '[]'):
                file.write_text(value)
                with self.assertRaises(ValueError):
                    check.load(file)

    def test_rejects_false_green_and_wrong_repository_evidence(self):
        data = check.load(ROOT / "status.json")
        evidence = check.load(ROOT / data["evidence_path"])
        for field, value in (("conclusion", "failure"), ("url", "https://example.invalid/run/1")):
            invalid = copy.deepcopy(data)
            invalid["repositories"][0]["checks"][0][field] = value
            with self.assertRaises(ValueError):
                check.snapshot(invalid, evidence)

    def test_rejects_mutable_revision_and_inconsistent_counts(self):
        data = check.load(ROOT / "status.json")
        evidence = check.load(ROOT / data["evidence_path"])
        for revision in ("main", "abc123"):
            invalid = copy.deepcopy(data)
            invalid["repositories"][0]["main_revision"] = revision
            with self.assertRaises(ValueError):
                check.snapshot(invalid, evidence)
        data["summary"]["merged_pull_requests"] += 1
        with self.assertRaises(ValueError):
            check.snapshot(data, evidence)

    def test_blocks_broken_and_escaping_links(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            file = root / "guide.md"
            for link in ("missing.md", "../outside.md", "%2e%2e/outside.md"):
                file.write_text("[reference](" + link + ")")
                with self.assertRaises(ValueError):
                    check.local_links(file, root)

    def test_blocks_common_credentials_without_real_secrets(self):
        for prefix in ("ghp_", "tan_", "tsk_", "hmk_"):
            with self.assertRaises(ValueError):
                check.public_text(prefix + "z" * 40)
        with self.assertRaises(ValueError):
            check.public_text("https://" + "user:password@" + "example.invalid")

    def test_architecture_rejects_competing_work_authority_and_hidden_fallback(self):
        baseline = check.load(ROOT / "architecture.json")
        names = {r["name"] for r in check.load(ROOT / "status.json")["repositories"]}
        invalid = copy.deepcopy(baseline)
        invalid["implicit_server_fallback"] = True
        with self.assertRaisesRegex(ValueError, "reasoning belongs in workers"):
            check.architecture(invalid, names, ROOT)
        invalid = copy.deepcopy(baseline)
        next(r for r in invalid["repositories"] if r["name"] == "kinema")["role"] = "fabric"
        with self.assertRaisesRegex(ValueError, "must not own"):
            check.architecture(invalid, names, ROOT)

    def test_architecture_rejects_incomplete_inventory_and_management_inference(self):
        baseline = check.load(ROOT / "architecture.json")
        names = {r["name"] for r in check.load(ROOT / "status.json")["repositories"]}
        invalid = copy.deepcopy(baseline)
        invalid["repositories"].pop()
        with self.assertRaisesRegex(ValueError, "classify every"):
            check.architecture(invalid, names, ROOT)
        invalid = copy.deepcopy(baseline)
        next(e for e in invalid["server_exceptions"] if e["id"] == "management")["reasoning"] = True
        with self.assertRaisesRegex(ValueError, "blanket inference"):
            check.architecture(invalid, names, ROOT)
        for field in ("payer", "model", "destination"):
            invalid = copy.deepcopy(baseline)
            next(e for e in invalid["server_exceptions"] if e["id"] == "explicit_inference")["required_record"].remove(field)
            with self.assertRaisesRegex(ValueError, "record authority"):
                check.architecture(invalid, names, ROOT)

    def test_architecture_rejects_extra_primitives_and_pack_authority(self):
        baseline = check.load(ROOT / "architecture.json")
        names = {r["name"] for r in check.load(ROOT / "status.json")["repositories"]}
        for field, value in (("core_entities", ["noun", "verb", "project"]),
                             ("project_is_primitive", True),
                             ("seed_pack_contents", ["noun", "verb", "autonomous_service"])):
            invalid = copy.deepcopy(baseline)
            invalid[field] = value
            with self.assertRaises(ValueError):
                check.architecture(invalid, names, ROOT)


PUBLISHED = {"v1": "f82b276b2fde16f993c958845de56026a4a2ef50a655d616a93b7f8c377803e4",
             "v2": "5ebb6fefbd04ed37907d27ab2b07974d1b0e785eadd1bf9550daf05231a5ac02"}


def page(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("<!doctype html><html><body>" + body + "</body></html>")


class SiteChecks(unittest.TestCase):
    def test_published_deck_versions_never_change(self):
        decks = check.load(ROOT / "site/decks.json")
        for version in decks["versions"][:2]:
            self.assertEqual(PUBLISHED[version["version"]], version["html_sha256"])
            data = (ROOT / "site" / version["path"] / "index.html").read_bytes()
            self.assertEqual(PUBLISHED[version["version"]], hashlib.sha256(data).hexdigest())

    def test_site_links_must_resolve_inside_the_site(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            site = root / "site"
            page(site / "index.html", '<a href="docs/">Docs</a><a href="/agora/docs/#top">Top</a><p id="here"></p>')
            page(site / "docs/index.html", '<h1 id="top">Docs</h1><a href="../#here">Back</a>')
            pages = check.site_pages(site)
            for path in pages:
                check.site_links(path, site, pages, root)
            for body in ('<a href="missing/">x</a>', '<a href="../outside.html">x</a>', '<a href="#nowhere">x</a>',
                         '<a href="docs/#nowhere">x</a>', '<a href="/elsewhere/">x</a>'):
                page(site / "bad.html", body)
                pages = check.site_pages(site)
                with self.assertRaises(ValueError):
                    check.site_links(site / "bad.html", site, pages, root)

    def test_issue_form_links_need_their_form(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            site = root / "site"
            link = '<a href="https://github.com/ta-amps/agora/issues/new?template=feedback.yml">Feedback</a>'
            page(site / "index.html", link)
            pages = check.site_pages(site)
            with self.assertRaises(ValueError):
                check.site_links(site / "index.html", site, pages, root)
            (root / ".github/ISSUE_TEMPLATE").mkdir(parents=True)
            (root / ".github/ISSUE_TEMPLATE/feedback.yml").write_text("name: Feedback\n")
            check.site_links(site / "index.html", site, pages, root)

    def test_site_downloads_are_hash_checked(self):
        with tempfile.TemporaryDirectory() as directory:
            site = Path(directory)
            data = b"%PDF-1.7 synthetic"
            (site / "deck.pdf").write_bytes(data)
            entry = {"format": "pdf", "path": "deck.pdf", "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
            self.assertEqual("deck.pdf", check.deck_download(entry, site))
            for field, value in (("sha256", "0" * 64), ("bytes", 1), ("path", "../deck.pdf"), ("path", "other.pdf")):
                with self.assertRaises(ValueError):
                    check.deck_download(dict(entry, **{field: value}), site)
            with self.assertRaises(ValueError):
                check.deck_download({"format": "pdf", "url": "https://example.invalid/deck.pdf", "sha256": "0" * 64}, site)

    def test_undeclared_binary_files_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            shutil.copytree(ROOT, root, ignore=shutil.ignore_patterns(".git", "__pycache__", ".venv"))
            self.assertTrue(check.check(root)["offline_only"])
            (root / "site/extra.pdf").write_bytes(b"%PDF-1.7 not declared")
            with self.assertRaisesRegex(ValueError, "undeclared binary"):
                check.check(root)

    def test_retired_pack_names_are_blocked_on_public_pages(self):
        saved = check.RETIRED_NAME_HASHES
        try:
            check.RETIRED_NAME_HASHES = {hashlib.sha256(b"oldname").hexdigest()}
            self.assertTrue(check.retired_names("<p>The Oldname pack</p>"))
            self.assertFalse(check.retired_names('<li data-provenance="https://example.invalid/oldname">A pack</li>'))
            self.assertFalse(check.retired_names("<p>A collection of nouns and verbs</p>"))
        finally:
            check.RETIRED_NAME_HASHES = saved


if __name__ == "__main__":
    unittest.main()
