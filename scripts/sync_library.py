"""Write the library catalog noun, site/content/library.json, from a clean checkout of the seed-pack library.

The noun has two parts.
  * The measured part is written here, from the checkout at one pinned commit: the commit, its date, the Tessera
    commit the library's validation receipt names, every pack's id, title, one-line purpose, version, status,
    noun, verb and worked-example counts, whether it is an agent kit, its code with the CI workflow that tests it,
    and its link at that commit, and the totals.
  * The authored part is kept exactly as written: the page's words, the categories, their intros and which category
    holds each pack. The library's manifests carry no category, so the categories are the noun's own explicit
    mapping. A pack the categories don't place, or a placed pack the library doesn't have, stops the sync.

Where each measured field comes from, in the checkout:
  * id, title, version, status and the code folder: packs/<pack>/manifest.json;
  * the one-line purpose: the title of the pack's own descriptor noun (role "pack") in packs/<pack>/nouns.json,
    without its opening "A collection of nouns and verbs for ";
  * nouns and verbs: the records of nouns.json and the tasks of verbs.json, which must match the manifest and
    packs/VALIDATION.json, the library's receipt of its offline check with Tessera's own models, byte digests
    included;
  * worked examples: the nouns that carry a fixture_kind, which the library's checks recompute;
  * agent kit: the descriptor pins a kit noun;
  * code and tests: the manifest pins a code folder, the folder has test files, and a workflow in .github/workflows
    runs on that pack's path.

It reads only those files, plus `git rev-parse`, `git status`, `git remote` and `git show` on the checkout to pin
the commit. It imports and runs none of the library's code and touches no network. The site build renders the
committed noun and never runs this script, so the build stays offline and reproducible.

Usage:
  python3 scripts/sync_library.py --library PATH               rewrite the noun from the checkout at the pinned commit
  python3 scripts/sync_library.py --library PATH --check       fail when the noun differs from what the checkout gives
  python3 scripts/sync_library.py --library PATH --commit SHA  move the pin to SHA; the checkout must be at SHA
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NOUN = ROOT / "site" / "content" / "library.json"
REPOSITORY = "https://github.com/ta-amps/seed-packs-library-of-nouns-and-verbs"
PACK_PHRASE = "A collection of nouns and verbs for "
RECEIPT_FORMAT = "ta-amps.seed-pack-validation.v1"
SHA = re.compile(r"[0-9a-f]{40}\Z")

_SPEC = importlib.util.spec_from_file_location("build_site", Path(__file__).resolve().parent / "build_site.py")
build_site = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(build_site)


class SyncError(Exception):
    pass


def fail(message: str) -> None:
    raise SyncError(message)


def git(library: Path, *args: str) -> str:
    try:
        result = subprocess.run(["git", "-C", str(library), *args], capture_output=True, text=True, check=False)
    except FileNotFoundError:
        fail("git is needed to pin the library's commit")
    if result.returncode != 0:
        fail(f"git {' '.join(args)} failed in {library}: {result.stderr.strip()}")
    return result.stdout.strip()


def repository_url(remote: str) -> str:
    """A GitHub remote as its https address, whether it was cloned over https or ssh."""
    remote = remote.strip()
    remote = re.sub(r"^git@github\.com:", "https://github.com/", remote)
    remote = re.sub(r"^ssh://git@github\.com/", "https://github.com/", remote)
    return re.sub(r"\.git$", "", remote.rstrip("/"))


def pinned_checkout(library: Path, pin: str) -> tuple[str, str]:
    """The checkout's commit and its date, once it is shown to be the library, clean and at the pinned commit."""
    if not (library / "packs").is_dir():
        fail(f"{library} is not a checkout of the seed-pack library: it has no packs folder")
    head = git(library, "rev-parse", "HEAD")
    if SHA.fullmatch(head) is None:
        fail(f"unexpected commit id {head!r}")
    if len(pin) < 7 or not head.startswith(pin):
        fail(f"the checkout is at {head[:7]}, not the pinned commit {pin[:7]}; check it out, or pass --commit to move the pin")
    if git(library, "status", "--porcelain", "--untracked-files=all"):
        fail("the checkout has local changes or untracked files; the catalog must match the commit exactly")
    origin = repository_url(git(library, "remote", "get-url", "origin"))
    if origin != REPOSITORY:
        fail(f"the checkout's origin is {origin}, not {REPOSITORY}")
    return head, git(library, "show", "-s", "--format=%cI", "HEAD")


def read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        fail(f"missing {path}")
    except json.JSONDecodeError as error:
        fail(f"{path} is not JSON: {error}")
    if not isinstance(data, dict):
        fail(f"{path} is not a JSON object")
    return data


def read_receipt(library: Path) -> dict:
    receipt = read_json(library / "packs" / "VALIDATION.json")
    if receipt.get("format") != RECEIPT_FORMAT:
        fail("packs/VALIDATION.json is not the library's validation receipt")
    if receipt.get("errors"):
        fail("the library's validation receipt records errors")
    commit = receipt.get("tessera", {}).get("commit", "")
    if SHA.fullmatch(commit) is None:
        fail("the validation receipt names no Tessera commit")
    return receipt


def read_workflows(library: Path) -> dict[str, str]:
    folder = library / ".github" / "workflows"
    files = sorted([*folder.glob("*.yml"), *folder.glob("*.yaml")]) if folder.is_dir() else []
    return {path.relative_to(library).as_posix(): path.read_text(encoding="utf-8") for path in files}


def measure_pack(library: Path, pack_id: str, commit: str, receipt: dict, workflows: dict[str, str]) -> dict:
    """One pack's catalog entry, from its own files and the library's receipt."""
    folder = library / "packs" / pack_id
    manifest = read_json(folder / "manifest.json")
    if manifest.get("pack_id") != pack_id:
        fail(f"packs/{pack_id}/manifest.json names the pack {manifest.get('pack_id')!r}")
    raw_nouns, raw_verbs = (folder / "nouns.json").read_bytes(), (folder / "verbs.json").read_bytes()
    records, tasks = json.loads(raw_nouns)["records"], json.loads(raw_verbs)["tasks"]
    if (len(records), len(tasks)) != (len(manifest["nouns"]), len(manifest["verbs"])):
        fail(f"{pack_id}: nouns.json and verbs.json differ from the manifest's counts")
    checked = receipt["packs"].get(pack_id)
    if checked is None:
        fail(f"{pack_id}: the validation receipt does not cover this pack")
    if (checked["records"], checked["tasks"]) != (len(records), len(tasks)) or \
            checked["nouns_sha256"] != hashlib.sha256(raw_nouns).hexdigest() or \
            checked["verbs_sha256"] != hashlib.sha256(raw_verbs).hexdigest():
        fail(f"{pack_id}: the nouns or verbs changed after the library's validation receipt")
    descriptors = [record["value"] for record in records if record["value"].get("role") == "pack"]
    if len(descriptors) != 1:
        fail(f"{pack_id}: expected one descriptor noun with role 'pack', found {len(descriptors)}")
    descriptor = descriptors[0]
    if not descriptor.get("title", "").startswith(PACK_PHRASE) or len(descriptor["title"]) == len(PACK_PHRASE):
        fail(f"{pack_id}: the descriptor noun's title does not start with {PACK_PHRASE!r}")
    purpose = descriptor["title"][len(PACK_PHRASE):]
    code = None
    if "code" in manifest:
        code_folder = folder / "code"
        tests = [path for path in code_folder.rglob("test*.py") if "tests" in path.relative_to(code_folder).parts]
        if not tests:
            fail(f"{pack_id}: the manifest pins a code folder, but it holds no tests")
        covering = sorted(name for name, text in workflows.items() if f"packs/{pack_id}/**" in text)
        if not covering:
            fail(f"{pack_id}: no workflow in .github/workflows runs on this pack's path")
        code = {"files": manifest["code"]["files"], "tests": len(tests), "workflow": covering[0]}
    return {
        "id": pack_id,
        "title": manifest["title"],
        "purpose": purpose[:1].upper() + purpose[1:],
        "version": manifest["version"],
        "status": manifest["status"],
        "nouns": len(records),
        "verbs": len(tasks),
        "worked_examples": sum(1 for record in records if record["value"].get("fixture_kind") is not None),
        "kit": "kit" in descriptor,
        "code": code,
        "url": f"{REPOSITORY}/tree/{commit}/packs/{pack_id}",
    }


def sync(library: Path, noun: dict, pin: str | None = None) -> dict:
    """The noun with its measured part rewritten from the checkout; the authored part stays as it is."""
    library = library.resolve()
    pin = pin or noun["source"]["commit"]
    commit, committed_at = pinned_checkout(library, pin)
    receipt = read_receipt(library)
    workflows = read_workflows(library)
    present = sorted(path.parent.name for path in (library / "packs").glob("*/manifest.json"))
    if set(present) != set(receipt["packs"]):
        fail("the validation receipt and the packs folder list different packs")
    packs = [measure_pack(library, pack_id, commit, receipt, workflows) for pack_id in present]
    placed = [pack_id for category in noun["categories"] for pack_id in category["packs"]]
    missing, unknown = sorted(set(present) - set(placed)), sorted(set(placed) - set(present))
    if missing:
        fail("no category holds " + ", ".join(missing) + "; add each to one category in the noun")
    if unknown:
        fail("the categories name packs the library does not have: " + ", ".join(unknown))
    out = copy.deepcopy(noun)
    out["source"] = {**noun["source"], "commit": commit, "committed_at": committed_at,
                     "tessera_commit": receipt["tessera"]["commit"]}
    out["totals"] = {
        "packs": len(packs),
        "nouns": sum(pack["nouns"] for pack in packs),
        "verbs": sum(pack["verbs"] for pack in packs),
        "worked_examples": sum(pack["worked_examples"] for pack in packs),
        "with_code": sum(1 for pack in packs if pack["code"]),
    }
    out["packs"] = packs
    try:
        build_site.check_library(out)
    except build_site.BuildError as error:
        fail(f"the site build would refuse this noun: {error}")
    return out


def encode(value, level: int = 0, key: str = "") -> str:
    """JSON with two-space indents, lists of plain values on one line, and each pack on a line of its own."""
    pad, end = "  " * (level + 1), "  " * level
    if isinstance(value, dict):
        if not value:
            return "{}"
        items = [f"{pad}{json.dumps(k)}: {encode(v, level + 1, k)}" for k, v in value.items()]
        return "{\n" + ",\n".join(items) + "\n" + end + "}"
    if isinstance(value, list):
        if not value:
            return "[]"
        if all(not isinstance(item, (dict, list)) for item in value):
            return json.dumps(value, ensure_ascii=False)
        if key == "packs":
            return "[\n" + ",\n".join(pad + json.dumps(item, ensure_ascii=False) for item in value) + "\n" + end + "]"
        return "[\n" + ",\n".join(pad + encode(item, level + 1) for item in value) + "\n" + end + "]"
    return json.dumps(value, ensure_ascii=False)


def noun_text(noun: dict) -> str:
    return encode(noun) + "\n"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--library", required=True, type=Path, help="a clean checkout of the seed-pack library")
    parser.add_argument("--commit", help="move the pin to this commit (the checkout must be at it)")
    parser.add_argument("--check", action="store_true", help="report a stale noun without writing")
    args = parser.parse_args(argv)
    current = NOUN.read_text(encoding="utf-8")
    try:
        text = noun_text(sync(args.library, json.loads(current), args.commit))
    except SyncError as error:
        print(f"sync_library: {error}", file=sys.stderr)
        return 2
    if args.check:
        if text != current:
            print("sync_library: site/content/library.json differs from the checkout; run without --check",
                  file=sys.stderr)
            return 1
        print("sync_library: the noun matches the checkout")
        return 0
    if text != current:
        NOUN.write_text(text, encoding="utf-8")
        print("wrote site/content/library.json")
    else:
        print("sync_library: the noun already matches the checkout")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
