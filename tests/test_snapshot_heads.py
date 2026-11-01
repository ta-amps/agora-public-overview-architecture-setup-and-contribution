"""The served source snapshots name no retired model (owner, Nov 1: never the older open model family, anywhere).

Agora serves every repository it mirrors as files under /source/ and as git under /git/, regenerated at deploy time from
each repository's swept head (site/content/source-links.json names the heads). This test reads those heads, file names
and contents, case-insensitively, for the retired family's name:
  * Agora's own head: every file git tracks in this checkout, which is the snapshot the next deploy serves;
  * every other repository in source-links.json, when a clone of it is on this machine: set AGORA_SNAPSHOT_REPOS to a
    folder that holds one clone or bare mirror per repository, named as the repository (or <name>.git). Without
    one, that repository is skipped and the test says so. Old history is out of scope: only the head is read.

Ownership, for now (the wording-sweep branch, November 1): it fails only for files that branch owns (MINE). Every other
hit is printed as a known list for its owner; the Agora builder tightens this after merging by making OWNED_ONLY False.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME = re.compile(r"l[l]ama", re.I)  # spelled as a pattern, so that this file never says it
OWNED_ONLY = True
MINE = (
    "site/content/contribute.json", "site/content/decks-page.json", "site/content/ecosystem-catalog.json",
    "site/content/evidence.json", "site/content/explorer.json", "site/content/film.json", "site/content/learning.json",
    "site/content/library.json", "site/content/moved.json", "site/decks/overview-and-architecture/",
    "site/decks/public-good-marketplace/", "site/decks/roll-your-own/", "site/decks/server-workers/",
    "site/decks/continuous-learning/", "site/decks/index.html", "site/decks.json", "site/learning/", "site/library/",
    "site/evidence/index.html", "site/contribute/", "site/studio/studio.js", "site/agent-brief.txt",
    "scripts/build_site.py", "scripts/sync_explorer.py", "scripts/sync_ecosystem.py", "tests/test_build_site.py",
    "tests/test_forbidden_words.py", "tests/test_plain_words.py", "tests/test_snapshot_heads.py",
)
GIT = ["git", "-c", "core.quotePath=false"]


def git(args: list[str], cwd: Path) -> str:
    return subprocess.run(GIT + args, cwd=cwd, check=True, capture_output=True, text=True).stdout


def hits_at(repo: Path, ref: str | None) -> dict[str, int]:
    """Every file at one head whose path or contents name the family, with how many times."""
    out: dict[str, int] = {}
    if ref is None:
        names = [n for n in git(["ls-files", "-z"], repo).split("\0") if n]
        for name in names:
            path = repo / name
            count = len(NAME.findall(name))
            if path.is_file():
                data = path.read_bytes()
                if b"\0" not in data[:8192]:
                    count += len(NAME.findall(data.decode("utf-8", errors="replace")))
            if count:
                out[name] = count
        return out
    names = [n for n in git(["ls-tree", "-r", "-z", "--name-only", ref], repo).split("\0") if n]
    for name in names:
        if NAME.search(name):
            out[name] = len(NAME.findall(name))
    grep = subprocess.run(GIT + ["grep", "-I", "-i", "-c", "-e", "l[l]ama", ref, "--"], cwd=repo, capture_output=True,
                          text=True)
    for line in grep.stdout.splitlines():
        _, _, rest = line.partition(":")
        name, _, n = rest.rpartition(":")
        out[name] = out.get(name, 0) + int(n)
    return out


def mine(name: str) -> bool:
    return any(name == path or (path.endswith("/") and name.startswith(path)) for path in MINE)


class SnapshotHeads(unittest.TestCase):
    def test_agoras_own_head_names_no_retired_model_in_files_this_branch_owns(self):
        found = hits_at(ROOT, None)
        known = {name: n for name, n in found.items() if not mine(name)}
        if known:
            areas: dict[str, int] = {}
            for name in known:
                area = "/".join(name.split("/")[:2]) if name.count("/") > 1 else name
                areas[area] = areas.get(area, 0) + 1
            print(f"\nKnown in Agora's head, {len(known)} files other owners hold (clear or unserve them before deploy):")
            for area, n in sorted(areas.items()):
                print(f"  {area}: {n} file{'s' if n != 1 else ''}")
        self.assertEqual({}, {name: n for name, n in found.items() if mine(name)} if OWNED_ONLY else found)

    def test_the_other_mirrored_heads_when_a_clone_is_here(self):
        links = json.loads((ROOT / "site" / "content" / "source-links.json").read_text(encoding="utf-8"))
        base = os.environ.get("AGORA_SNAPSHOT_REPOS")
        for repo, head in sorted(links["heads"].items()):
            if repo.startswith("agora-"):
                continue  # Agora's own head is the test above
            clone = next((Path(base) / n for n in (repo, repo + ".git") if base and (Path(base) / n).exists()), None)
            if clone is None:
                print(f"\n{repo}: no clone here (set AGORA_SNAPSHOT_REPOS), skipped")
                continue
            with self.subTest(repo=repo):
                found = hits_at(clone, head)
                self.assertEqual({}, found, f"{repo} at {head[:12]} names the retired family in these files")

    def test_the_pattern_finds_the_name(self):
        self.assertTrue(NAME.search("L" + "lama 3.2"))
        self.assertTrue(NAME.search("O" + "l" + "lama"))
        self.assertIsNone(NAME.search("Muse Glimmer 30B"))


if __name__ == "__main__":
    unittest.main()
