import copy
import hashlib
import importlib.util
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("sync_library", ROOT / "scripts/sync_library.py")
sync = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sync)

NOUN = ROOT / "site/content/library.json"


def write(path: Path, data) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = data if isinstance(data, str) else json.dumps(data)
    path.write_text(text, encoding="utf-8")
    return text


def git(folder: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(folder), "-c", "user.name=test", "-c", "user.email=test@example.invalid",
                             "-c", "commit.gpgsign=false", *args], check=True, capture_output=True, text=True)
    return result.stdout.strip()


def pack(root: Path, pack_id: str, title: str, purpose: str, nouns: int, verbs: int, *, fixtures: int = 0,
         kit: bool = False, code: bool = False) -> dict:
    """A synthetic pack folder shaped like the library's, and its line in the validation receipt."""
    folder = root / "packs" / pack_id
    descriptor = {"role": "pack", "title": sync.PACK_PHRASE + purpose}
    if kit:
        descriptor["kit"] = {"store": f"seedpack.{pack_id}", "key": f"{pack_id}.kit", "version": 1, "value_sha256": "0" * 64}
    records = [{"value": descriptor}] + [{"value": {"role": "item", **({"fixture_kind": "check"} if n < fixtures else {})}}
                                         for n in range(nouns - 1)]
    tasks = [{"brief": {"template_id": f"{pack_id}.verb-{n}"}} for n in range(verbs)]
    raw_nouns = write(folder / "nouns.json", {"records": records})
    raw_verbs = write(folder / "verbs.json", {"tasks": tasks})
    manifest = {"pack_id": pack_id, "title": title, "version": "0.1.0", "status": "proposal_only",
                "nouns": [{"key": str(n)} for n in range(nouns)], "verbs": [{"template_id": str(n)} for n in range(verbs)]}
    if code:
        manifest["code"] = {"path": f"packs/{pack_id}/code", "files": 2, "sha256": "0" * 64}
        write(folder / "code" / "tool.py", "VALUE = 1\n")
        write(folder / "code" / "tests" / "test_tool.py", "def test_value():\n    assert True\n")
    write(folder / "manifest.json", manifest)
    return {"records": nouns, "tasks": verbs, "nouns_sha256": hashlib.sha256(raw_nouns.encode()).hexdigest(),
            "verbs_sha256": hashlib.sha256(raw_verbs.encode()).hexdigest()}


@unittest.skipUnless(shutil.which("git"), "the sync pins a git commit")
class SyncLibrary(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "library"
        receipt = {"format": sync.RECEIPT_FORMAT, "errors": [], "tessera": {"commit": "5" * 40}, "packs": {
            "kit-pantry": pack(self.root, "kit-pantry", "Pantry kit", "a pantry's agent kit", 5, 3, kit=True),
            "video-checks": pack(self.root, "video-checks", "Video checks", "checking an encoded video", 7, 4,
                                 fixtures=2, code=True),
        }}
        write(self.root / "packs" / "VALIDATION.json", receipt)
        write(self.root / ".github" / "workflows" / "video-checks.yml",
              'on:\n  pull_request:\n    paths:\n      - "packs/video-checks/**"\n')
        git(self.root, "init", "-q")
        self.commit = self.save("packs")
        git(self.root, "remote", "add", "origin", sync.REPOSITORY + ".git")
        self.noun = copy.deepcopy(json.loads(NOUN.read_text(encoding="utf-8")))
        self.noun["source"]["commit"] = self.commit
        self.noun["categories"] = [
            {"id": "kits", "name": "Kits", "short": "Kits", "intro": "Agent kits.", "packs": ["kit-pantry"]},
            {"id": "media", "name": "Media", "short": "Media", "intro": "Video.", "packs": ["video-checks"]},
        ]

    def save(self, message: str) -> str:
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", message)
        return git(self.root, "rev-parse", "HEAD")

    def test_measures_every_pack_from_its_own_files(self):
        out = sync.sync(self.root, self.noun)
        self.assertEqual({"packs": 2, "nouns": 12, "verbs": 7, "worked_examples": 2, "with_code": 1}, out["totals"])
        kit, video = out["packs"]
        self.assertEqual(("kit-pantry", "Pantry kit", "A pantry's agent kit", 5, 3, 0, True, None),
                         (kit["id"], kit["title"], kit["purpose"], kit["nouns"], kit["verbs"], kit["worked_examples"],
                          kit["kit"], kit["code"]))
        self.assertEqual({"files": 2, "tests": 1, "workflow": ".github/workflows/video-checks.yml"}, video["code"])
        self.assertEqual(f"{sync.REPOSITORY}/tree/{self.commit}/packs/video-checks", video["url"])
        self.assertEqual((self.commit, "5" * 40), (out["source"]["commit"], out["source"]["tessera_commit"]))
        # The authored part comes back exactly as it went in.
        for key in ("words", "categories", "heading", "lead", "dateline", "about"):
            self.assertEqual(self.noun[key], out[key], key)

    def test_the_pin_must_match_the_checkout(self):
        self.noun["source"]["commit"] = "0" * 40
        with self.assertRaisesRegex(sync.SyncError, "not the pinned commit"):
            sync.sync(self.root, self.noun)
        self.assertEqual(self.commit, sync.sync(self.root, self.noun, self.commit[:7])["source"]["commit"])

    def test_the_checkout_must_be_clean_and_the_library_itself(self):
        write(self.root / "packs" / "notes.txt", "not committed")
        with self.assertRaisesRegex(sync.SyncError, "local changes"):
            sync.sync(self.root, self.noun)
        (self.root / "packs" / "notes.txt").unlink()
        git(self.root, "remote", "set-url", "origin", "https://github.com/someone/fork.git")
        with self.assertRaisesRegex(sync.SyncError, "origin"):
            sync.sync(self.root, self.noun)
        git(self.root, "remote", "set-url", "origin", "git@github.com:ta-amps/seed-packs-library-of-nouns-and-verbs.git")
        self.assertEqual(2, sync.sync(self.root, self.noun)["totals"]["packs"])

    def test_payloads_must_be_the_ones_the_receipt_validated(self):
        records = json.loads((self.root / "packs/kit-pantry/nouns.json").read_text())["records"]
        records[1]["value"]["role"] = "changed"
        write(self.root / "packs/kit-pantry/nouns.json", {"records": records})
        self.noun["source"]["commit"] = self.save("change a noun after validation")
        with self.assertRaisesRegex(sync.SyncError, "after the library's validation receipt"):
            sync.sync(self.root, self.noun)

    def test_every_pack_sits_in_a_category_and_every_entry_is_a_pack(self):
        noun = copy.deepcopy(self.noun)
        noun["categories"][1]["packs"] = []
        with self.assertRaisesRegex(sync.SyncError, "no category holds video-checks"):
            sync.sync(self.root, noun)
        noun = copy.deepcopy(self.noun)
        noun["categories"][1]["packs"].append("retired-pack")
        with self.assertRaisesRegex(sync.SyncError, "does not have: retired-pack"):
            sync.sync(self.root, noun)

    def test_code_counts_only_with_tests_and_a_workflow(self):
        (self.root / ".github/workflows/video-checks.yml").unlink()
        self.noun["source"]["commit"] = self.save("drop the workflow")
        with self.assertRaisesRegex(sync.SyncError, "no workflow"):
            sync.sync(self.root, self.noun)
        write(self.root / ".github/workflows/video-checks.yml", 'on:\n  push:\n    paths: ["packs/video-checks/**"]\n')
        shutil.rmtree(self.root / "packs/video-checks/code/tests")
        self.noun["source"]["commit"] = self.save("drop the tests")
        with self.assertRaisesRegex(sync.SyncError, "holds no tests"):
            sync.sync(self.root, self.noun)

    def test_remotes_read_the_same_over_https_and_ssh(self):
        for remote in (sync.REPOSITORY, sync.REPOSITORY + ".git", sync.REPOSITORY + "/",
                       "git@github.com:ta-amps/seed-packs-library-of-nouns-and-verbs.git",
                       "ssh://git@github.com/ta-amps/seed-packs-library-of-nouns-and-verbs.git"):
            self.assertEqual(sync.REPOSITORY, sync.repository_url(remote), remote)


class CommittedNoun(unittest.TestCase):
    def test_the_committed_noun_is_in_the_format_the_sync_writes(self):
        text = NOUN.read_text(encoding="utf-8")
        self.assertEqual(text, sync.noun_text(json.loads(text)))

    def test_the_committed_noun_is_pinned_to_one_full_commit(self):
        noun = json.loads(NOUN.read_text(encoding="utf-8"))
        commit = noun["source"]["commit"]
        self.assertRegex(commit, r"\A[0-9a-f]{40}\Z")
        self.assertTrue(all(pack["url"].startswith(f"{sync.REPOSITORY}/tree/{commit}/packs/") for pack in noun["packs"]))


if __name__ == "__main__":
    unittest.main()
