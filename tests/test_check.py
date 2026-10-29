import copy
import importlib.util
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


if __name__ == "__main__":
    unittest.main()
