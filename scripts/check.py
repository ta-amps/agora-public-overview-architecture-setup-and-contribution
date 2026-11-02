"""Offline consistency and publication checks for the dated Agora snapshot."""
from __future__ import annotations

import datetime as dt
import hashlib
import html
import json
import re
import zipfile
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
SHA = re.compile(r"[0-9a-f]{40}\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
SKIP = {".git", ".venv", "__pycache__"}
SENSITIVE = {
    "GitHub token": re.compile(r"(?:gh[pousr]_|github_pat_)[A-Za-z0-9_]{20,}"),
    "service token": re.compile(r"(?:tsk|tan|hmk)_[A-Za-z0-9_-]{24,}"),
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "local home path": re.compile(r"/(?:home|Users)/[A-Za-z0-9_.-]+/"),
    "credential URL": re.compile(r"https?://[^/\s]+:[^/\s]+@"),
}
BINARY_SUFFIXES = {".pdf", ".pptx", ".mp4", ".png", ".ttf", ".woff2", ".zip"}
MEDIA_MAGIC = {
    ".mp4": lambda b: b[4:8] == b"ftyp",
    ".png": lambda b: b.startswith(b"\x89PNG\r\n\x1a\n"),
    ".ttf": lambda b: b[:4] in {b"\x00\x01\x00\x00", b"OTTO", b"true"},
    ".woff2": lambda b: b[:4] == b"wOF2",
}
RELEASE_PREFIX = "https://github.com/ta-amps/agora-public-overview-architecture-setup-and-contribution/releases/download/"
PAGES_PREFIX = "/"
# Paths the deploy bundle adds next to the site: the source mirror, its file views and the git mirrors. The bundle
# builder writes them from committed refs and fails on any link into them that does not resolve.
DEPLOY_PATHS = ("source", "git")
RETIRED_HOSTS = re.compile(r"github\.com/ta-amps|ta-amps\.github\.io")
HTML_REF = re.compile(r'\s(?:href|src)="([^"]*)"')
HTML_ID = re.compile(r'\sid="([^"]+)"')
PROVENANCE = re.compile(r'\sdata-provenance="[^"]*"')
ISSUE_FORM = re.compile(r"https://github\.com/ta-amps/agora-public-overview-architecture-setup-and-contribution/issues/new\?template=([A-Za-z0-9._-]+)")
# Retired pack names (owner rule: packs carry no names). Stored as hashes, so the names never appear here.
RETIRED_NAME_HASHES = {
    "9410a442dd664c9234966c5ecc0ff595431749474bc67b7e2ce5ccaaed7793ec",
    "4322a6b237d4d0f47990bad6edf90913cd88d2a1a6a9698a756b73e4dfd69329",
    "d488476689bd8ff0424956c989ae7508815f2821f9524dfd3ea5aea931911978",
}
# Owner rule, October 29: exactly two public surfaces, and Tessera and Herma are the infrastructure.
# Everything else, agent kits included, is nouns and verbs in seed packs.
PUBLIC_SURFACES = ["eranos", "agora"]
INFRASTRUCTURE = ["tessera", "herma"]
# GitHub names of the repositories renamed on October 30, 2026. Snapshot records keep the code names they
# were observed under, while their links use these names. Removed repositories keep their recorded links.
GITHUB_NAMES = {
    "agora": "agora-public-overview-architecture-setup-and-contribution",
    "eranos": "eranos-public-marketplace-for-public-good-token-burn",
    "herma": "herma-infrastructure-shim-for-intelligent-agents",
    "pack-contributions": "seed-packs-library-of-nouns-and-verbs",
    "tessera": "tessera-infrastructure-work-and-storage-engine",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def unique_pairs(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate JSON key: " + key)
        result[key] = value
    return result


def nonfinite(value: str) -> None:
    raise ValueError("non-finite JSON number: " + value)


def load(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_pairs, parse_constant=nonfinite)
    require(isinstance(data, dict), "JSON document must be an object")
    return data


def snapshot(data: dict, evidence: dict) -> None:
    require(type(data.get("schema_version")) is int and data["schema_version"] == 1,
            "unsupported snapshot schema")
    observed = dt.datetime.fromisoformat(data["observed_at"])
    require(observed.tzinfo is not None, "snapshot needs a timezone")
    require(data["guide"]["kind"] == "documentation", "guide must remain documentation")
    repos = data["repositories"]
    names = [r["name"] for r in repos]
    require(len(names) == len(set(names)) and bool(names), "duplicate or missing repositories")
    require(len(repos) == data["summary"]["ecosystem_repositories"], "repository count mismatch")
    require(data["summary"]["open_pull_requests"] == sum(r["open_pull_requests"] for r in repos),
            "open PR count mismatch")
    for repo in repos:
        prefix = "https://github.com/ta-amps/" + GITHUB_NAMES.get(repo["name"], repo["name"])
        require(repo["url"] == prefix and SHA.fullmatch(repo["main_revision"]) is not None,
                "invalid repository URL or immutable revision")
        require(type(repo["open_pull_requests"]) is int and repo["open_pull_requests"] >= 0,
                "invalid open PR count")
        require(bool(repo["checks"]), "repository needs CI evidence")
        for check in repo["checks"]:
            require(check["url"].startswith(prefix + "/actions/runs/") and
                    check["url"].rsplit("/", 1)[-1].isdigit(), "CI evidence must belong to repository")
            require(check["status"] in {"completed", "in_progress", "queued"}, "unknown CI status")
            if data["summary"]["all_main_checks_passed"]:
                require(check["status"] == "completed" and check["conclusion"] == "success",
                        "green summary contradicts CI evidence")
    surfaces = data["surfaces"]
    require(len(surfaces) == data["summary"]["hosted_surfaces"], "surface count mismatch")
    require(len({s["name"] for s in surfaces}) == len(surfaces), "duplicate surface")
    for surface in surfaces:
        require(surface["source_repository"] is None or surface["source_repository"] in names,
                "unknown surface source")
        require(surface["url"] == "https://" + surface["name"] + ".ta-amps.workers.dev",
                "unexpected surface URL")
        require(bool(surface["modules"]), "surface needs module evidence")
        for module in surface["modules"]:
            require(SHA256.fullmatch(module["sha256"]) is not None, "invalid executable digest")
        if data["summary"]["all_bundles_match_tested_builds"]:
            require(surface["matches_tested_build"] is True, "parity summary contradicts evidence")
    require(evidence["observed_at"] == data["observed_at"], "snapshot/evidence dates differ")
    require(data["summary"]["merged_pull_requests"] == len(evidence["merged_pull_requests"]),
            "merge count mismatch")
    require(len(set(evidence["merged_pull_requests"])) == len(evidence["merged_pull_requests"]),
            "duplicate merge evidence")
    for trial in evidence["native_execution_history"]["runs"]:
        require(SHA256.fullmatch(trial["run_fingerprint"]) is not None, "invalid native fingerprint")
    require(bool(data["limitations"]), "snapshot needs its evidence limits")
    for capability in data["capabilities"]:
        require(capability["state"] in {"implemented", "implemented_with_limits", "proposed", "incomplete"},
                "unknown capability state")


def architecture(data: dict, repo_names: set[str], root: Path) -> None:
    require(data.get("schema_version") == 1 and data.get("kind") == "documentation_inventory",
            "architecture must remain a documentation inventory")
    require(data.get("authority") == "tessera", "work authority must remain Tessera")
    require(data.get("core_entities") == ["noun", "verb"] and
            data.get("supporting_boundaries") == ["surface", "infrastructure"],
            "only nouns and verbs with surfaces and supporting infrastructure")
    require(data.get("public_surfaces") == PUBLIC_SURFACES and data.get("infrastructure") == INFRASTRUCTURE,
            "exactly two public surfaces, Eranos and Agora; Tessera and Herma are the infrastructure")
    require(data.get("seed_pack_contents") == ["noun", "verb"] and
            data.get("project_is_primitive") is False,
            "seed packs bundle nouns and verbs; projects are not primitives")
    require(data.get("ordinary_reasoning") == "authorized_workers" and
            data.get("implicit_server_fallback") is False, "ordinary reasoning belongs in workers")
    require((root / data["policy"]).is_file(), "architecture needs its checkpoint")
    repos = data["repositories"]
    require({r["name"] for r in repos} == repo_names and len(repos) == len(repo_names),
            "architecture must classify every product repository once")
    roles = {"fabric", "adapter", "surface", "seed_pack", "authoring_kit"}
    for repo in repos:
        require(set(repo) == {"name", "role", "nouns", "verbs", "checks"},
                "unexpected repository authority or architecture field")
        require(repo["role"] in roles, "unknown architecture role")
        require((repo["role"] == "fabric") == (repo["name"] == "tessera"),
                "domain packs must not own the work lifecycle")
        require((repo["role"] == "surface") == (repo["name"] in PUBLIC_SURFACES),
                "only Eranos and Agora are surfaces, and a pack is never a surface")
        require((repo["role"] in {"fabric", "adapter"}) == (repo["name"] in INFRASTRUCTURE),
                "only Tessera and Herma are infrastructure")
        if retired_names(repo["name"]):
            require(repo["role"] == "seed_pack", "a repository under a retired pack name must be a seed pack")
        for field in ("nouns", "verbs", "checks"):
            require(isinstance(repo[field], list) and bool(repo[field]) and
                    all(isinstance(v, str) and bool(v.strip()) for v in repo[field]),
                    "repository needs noun, verb and check references")
    exceptions = data["server_exceptions"]
    require(len(exceptions) == 4 and {e["id"] for e in exceptions} ==
            {"infrastructure", "management", "model_transport", "explicit_inference"},
            "server exception classes must be explicit")
    fields = {"purpose", "principal", "data_scope", "provider", "model", "destination", "payer", "allowance",
              "deadline", "retry_policy", "outcome"}
    for exception in exceptions:
        require(bool(exception["owner"]) and bool(exception["boundary"]),
                "server exceptions need an owner and boundary")
        require((root / exception["evidence"]).is_file(), "exception reference missing")
        require(exception["reasoning"] is (exception["id"] == "explicit_inference"),
                "infrastructure and management are not blanket inference exemptions")
        if exception["reasoning"]:
            require(set(exception["required_record"]) == fields,
                    "server inference must record authority, scope, allowance and outcome")
    require(bool(data.get("enforcement_scope")), "architecture needs its enforcement limits")


def public_text(text: str) -> None:
    for name, pattern in SENSITIVE.items():
        require(pattern.search(text) is None, "possible private material: " + name)


def local_links(path: Path, root: Path) -> None:
    for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
        target = target.strip("<>")
        parsed = urlsplit(target)
        if parsed.scheme or parsed.netloc or not parsed.path:
            continue
        local = (path.parent / unquote(parsed.path)).resolve()
        require(local.is_relative_to(root.resolve()) and local.is_file(),
                "broken or escaping local link in " + path.name + ": " + target)


def retired_names(text: str) -> bool:
    text = PROVENANCE.sub(" ", text.lower())
    return any(hashlib.sha256(word.encode()).hexdigest() in RETIRED_NAME_HASHES
               for word in set(re.findall(r"[a-z0-9]+", text)))


def deck_download(download: dict, site: Path) -> str | None:
    """Validate one deck download; return its site-relative path when it is a file in the site."""
    require(SHA256.fullmatch(download["sha256"]) is not None, "deck downloads need a content hash")
    if "path" not in download:
        # The release is gone with the GitHub organization; its files are served from site/downloads/<tag>/.
        require(download["url"].startswith(RELEASE_PREFIX),
                "deck downloads need a public release URL and content hash")
        file = (site / "downloads" / download["url"][len(RELEASE_PREFIX):]).resolve()
    else:
        file = (site / download["path"]).resolve()
    require(file.is_relative_to(site.resolve()) and file.is_file(), "deck download missing from the static site")
    data = file.read_bytes()
    require(hashlib.sha256(data).hexdigest() == download["sha256"] and len(data) == download["bytes"],
            "deck download changed without updating its recorded hash")
    if file.suffix == ".pdf":
        require(data.startswith(b"%PDF-"), "deck PDF is not a PDF")
    if file.suffix == ".pptx":
        require(zipfile.is_zipfile(file), "deck PowerPoint is not a valid package")
        with zipfile.ZipFile(file) as package:
            require("ppt/presentation.xml" in package.namelist(), "deck PowerPoint has no presentation part")
    return file.relative_to(site.resolve()).as_posix()


def media_item(item: dict, site: Path) -> str:
    """A declared draft video or image: inside the site, hash-pinned and of the type its name says."""
    require(isinstance(item.get("path"), str) and SHA256.fullmatch(str(item.get("sha256", ""))) is not None,
            "media items need a path and a content hash")
    file = (site / item["path"]).resolve()
    require(file.is_relative_to(site.resolve()) and file.is_file(), "media item missing from the static site")
    data = file.read_bytes()
    require(hashlib.sha256(data).hexdigest() == item["sha256"] and len(data) == item.get("bytes"),
            "media item changed without updating its recorded hash")
    require(file.suffix in MEDIA_MAGIC and MEDIA_MAGIC[file.suffix](data), "media item is not the type its name says")
    return file.relative_to(site.resolve()).as_posix()


def site_pages(site: Path) -> dict[Path, set[str]]:
    pages = {}
    for page in sorted(site.rglob("*.html")):
        pages[page.resolve()] = set(HTML_ID.findall(page.read_text(encoding="utf-8")))
    return pages


def site_links(page: Path, site: Path, pages: dict[Path, set[str]], root: Path,
               moved: frozenset[Path] = frozenset()) -> None:
    """Every local link and anchor must resolve inside the site. A frozen page passes in the pages that moved
    after it was published, so its links to them are allowed; nothing else is."""
    text = page.read_text(encoding="utf-8")
    where = page.relative_to(site).as_posix()
    for raw in HTML_REF.findall(text):
        target = html.unescape(raw)
        for form in ISSUE_FORM.findall(target):
            require((root / ".github/ISSUE_TEMPLATE" / form).is_file(), "missing issue form in " + where + ": " + form)
        parsed = urlsplit(target)
        if parsed.scheme or parsed.netloc:
            continue
        path = unquote(parsed.path)
        if not path:
            require(not parsed.fragment or parsed.fragment in pages[page.resolve()],
                    "missing anchor in " + where + ": " + target)
            continue
        if path.startswith(PAGES_PREFIX):
            local = site / path[len(PAGES_PREFIX):]
        else:
            require(not path.startswith("/"), "site link outside the Pages path in " + where + ": " + target)
            local = page.parent / path
        local = local.resolve()
        if local.is_relative_to(site.resolve()) and local.relative_to(site.resolve()).parts[:1] in {(p,) for p in DEPLOY_PATHS}:
            continue  # checked by the bundle builder, which writes these paths
        if path.endswith("/") or local.is_dir():
            local = local / "index.html"
        if local in moved and not local.is_file():
            continue
        require(local.is_relative_to(site.resolve()) and local.is_file(),
                "broken or escaping site link in " + where + ": " + target)
        if parsed.fragment and local in pages:
            require(parsed.fragment in pages[local], "missing anchor in " + where + ": " + target)


def current_deck(deck: dict, site: Path, frozen: set[Path]) -> set[str]:
    """A current deck: built from its source, never a frozen version, with its slides counted and its PDF declared.
    Returns the site paths of its downloads."""
    page = (site / deck["path"] / "index.html").resolve()
    require(page.is_relative_to(site.resolve()) and page.is_file(), "deck path must remain within the static site")
    require(page not in frozen, "a current deck is never a frozen version")
    require((site / deck["source"] / "deck.json").is_file(), "a current deck needs its source")
    require(page.read_text(encoding="utf-8").count('aria-roledescription="slide"') == deck["slides"], "deck slide count mismatch")
    require(deck.get("unbranded") is True, "current decks name no retired pack")
    require(bool(deck["downloads"]), "a current deck needs its PDF")
    return {local for local in (deck_download(d, site) for d in deck["downloads"]) if local}


def frozen_drafts(listing: dict, site: Path) -> set[Path]:
    """Drafts pinned by hash in site/content/earlier-drafts.json: their bytes must never change."""
    frozen = set()
    for group in listing["groups"]:
        for item in group["items"]:
            if "html_sha256" not in item:
                continue
            page = (site / item["href"] / "index.html").resolve()
            require(page.is_relative_to(site.resolve()) and page.is_file(), "frozen draft missing: " + item["href"])
            require(SHA256.fullmatch(item["html_sha256"]) is not None and
                    hashlib.sha256(page.read_bytes()).hexdigest() == item["html_sha256"],
                    "frozen draft changed without updating its recorded hash: " + item["href"])
            frozen.add(page)
    return frozen


def moved_pages(listing: dict, site: Path, pages: dict[Path, set[str]]) -> frozenset[Path]:
    """Pages removed on purpose. Each must really be gone and point to a page and anchor that exist."""
    moved = set()
    for item in listing["pages"]:
        old = (site / item["from"] / "index.html").resolve()
        require(old.is_relative_to(site.resolve()) and not old.exists(),
                "a moved page must be gone from the site: " + item["from"])
        target = urlsplit(item["to"])
        new = (site / target.path / "index.html").resolve() if target.path.endswith("/") else (site / target.path).resolve()
        require(new in pages, "a moved page must point to a page in the site: " + item["to"])
        require(not target.fragment or target.fragment in pages[new], "missing anchor for a moved page: " + item["to"])
        moved.add(old)
    return frozenset(moved)


# Rule 13, light only (owner, Nov 1; Gemini's LightThemeOnlyGate in 2bb3c7e, widened to every current file): no dark
# palette, no dark media query, no dark colour scheme and no stored dark mode in any current page, style or script.
DARK_RULE = re.compile(r"prefers-color-scheme\s*:\s*dark|color-scheme\s*:[^;\"'}>]*\bdark\b|"
                       r"name=[\"']color-scheme[\"'][^>]*content=[\"'][^\"']*\bdark\b|"
                       r"data-mode\s*=\s*[\"']?dark|\[data-mode=[\"']?dark", re.I)
LIGHT_META = '<meta name="color-scheme" content="only light">'


def current_pages(site: Path) -> list[Path]:
    """The pages a visitor can reach today: every page of the site but the frozen drafts (decks.json's versions and
    the hash-pinned drafts in content/earlier-drafts.json, with their folders) and the deck sources. The light check
    (scripts/light_check.py) renders exactly these."""
    root = site.resolve()
    frozen = {(root / v["path"] / "index.html").resolve() for v in load(root / "decks.json")["versions"]}
    drafts = root / "content/earlier-drafts.json"
    if drafts.exists():
        frozen |= frozen_drafts(load(drafts), root)
    return [page for page in site_pages(root) if page not in frozen and "source" not in page.relative_to(root).parts
            and not any(f.parent in page.parents for f in frozen)]


def light_only(site: Path, pages: dict, frozen: set[Path]) -> None:
    """Every current page pins only light in its one color-scheme meta, and no current page, stylesheet or script
    carries a dark rule. Frozen drafts keep their bytes (the bundle does not serve them); deck sources are not pages."""
    root = site.resolve()

    def current(path: Path) -> bool:
        path = path.resolve()
        return (path not in frozen and "source" not in path.relative_to(root).parts
                and not any(f.parent in path.parents for f in frozen))

    for page in pages:
        if not current(page):
            continue
        body = page.read_text(encoding="utf-8")
        name = page.resolve().relative_to(root).as_posix()
        require(DARK_RULE.search(body) is None, "light only: a dark rule in " + name)
        require(body.count('name="color-scheme"') == 1 and LIGHT_META in body,
                "light only: the page must pin one color-scheme meta, only light: " + name)
    for path in sorted(root.rglob("*")):
        if path.suffix in (".css", ".js") and path.is_file() and current(path):
            require(DARK_RULE.search(path.read_text(encoding="utf-8")) is None,
                    "light only: a dark rule in " + path.relative_to(root).as_posix())
    for sheet in ("assets/tokens.css", "assets/site.css"):
        require("color-scheme: only light;" in (root / sheet).read_text(encoding="utf-8"),
                f"light only: {sheet} must declare color-scheme: only light;")


def check(root: Path = ROOT) -> dict:
    data = load(root / "status.json")
    evidence = load(root / data["evidence_path"])
    snapshot(data, evidence)
    architecture(load(root / "architecture.json"), {r["name"] for r in data["repositories"]}, root)
    manifest = root / "site/decks.json"
    declared: set[str] = set()
    historical: set[str] = set()
    frozen: set[Path] = set()
    if manifest.exists():
        decks = load(manifest)
        require(decks["kind"] == "versioned_draft_presentations" and
                decks["publication_does_not_certify_claims"] is True,
                "presentations must retain draft status")
        versions = decks["versions"]
        require(len({v["version"] for v in versions}) == len(versions), "duplicate deck version")
        for version in versions:
            page = (manifest.parent / version["path"] / "index.html").resolve()
            require(page.is_relative_to(manifest.parent.resolve()) and page.is_file(),
                    "deck path must remain within the static site")
            require(hashlib.sha256(page.read_bytes()).hexdigest() == version["html_sha256"],
                    "versioned deck changed without updating its recorded hash")
            require(page.read_text(encoding="utf-8").count('aria-roledescription="slide"') == version["slides"] ==
                    version["core_slides"] + version["appendix_slides"], "deck slide count mismatch")
            if version.get("unbranded") is not True:
                historical.add(page.relative_to(manifest.parent.resolve()).as_posix())
            frozen.add(page)
            for download in version["downloads"]:
                local = deck_download(download, manifest.parent)
                if local:
                    declared.add(local)
        current = decks.get("decks", [])
        require(len({d["id"] for d in current}) == len(current), "duplicate deck")
        for deck in current:
            declared |= current_deck(deck, manifest.parent, frozen)
    media = root / "site/media.json"
    if media.exists():
        listing = load(media)
        require(listing["kind"] == "draft_media" and listing["publication_does_not_certify_claims"] is True,
                "media must retain draft status")
        for item in listing["items"]:
            declared.add(media_item(item, media.parent))
    links = root / "site/content/source-links.json"
    if links.exists():
        for item in load(links).get("release_files", []):
            file = (root / "site" / item["path"]).resolve()
            require(file.is_relative_to((root / "site").resolve()) and file.is_file(), "release file missing: " + item["path"])
            blob = file.read_bytes()
            require(hashlib.sha256(blob).hexdigest() == item["sha256"] and len(blob) == item["bytes"],
                    "release file changed without updating its recorded hash: " + item["path"])
            declared.add(item["path"])
    files = [p for p in root.rglob("*") if p.is_file() and not SKIP.intersection(p.relative_to(root).parts)]
    site = root / "site"
    for path in files:
        if path.suffix.lower() in BINARY_SUFFIXES:
            rel = path.relative_to(site).as_posix() if path.is_relative_to(site) else path.as_posix()
            require(rel in declared, "undeclared binary file: " + path.relative_to(root).as_posix())
            public_text(path.read_bytes().decode("latin-1"))
            continue
        text = path.read_text(encoding="utf-8")
        public_text(text)
        if path.is_relative_to(site) and path.relative_to(site).as_posix() not in historical:
            require(not retired_names(text), "retired pack name on the public site: " + path.relative_to(root).as_posix())
        if path.suffix == ".json":
            load(path)
        if path.suffix == ".md" or path.name == "llms.txt":
            local_links(path, root)
    if site.is_dir():
        pages = site_pages(site)
        drafts = site / "content/earlier-drafts.json"
        if drafts.exists():
            frozen |= frozen_drafts(load(drafts), site)
        source_links = load(site / "content/source-links.json")
        unmirrored = set(source_links["heads"]) - set(source_links.get("mirrored", []))
        git_served = set(source_links.get("git_served", []))
        moved_list = site / "content/moved.json"
        moved = moved_pages(load(moved_list), site, pages) if moved_list.exists() else frozenset()
        for page in pages:
            site_links(page, site, pages, root, moved if page in frozen else frozenset())
            rel = page.relative_to(site.resolve() if page.is_absolute() else site).parts
            if page not in frozen and "source" not in rel and not any(f.parent in page.parents for f in frozen):
                # F31-014: the GitHub organization and its Pages sites answer 404; pages link the source mirror.
                # Deck sources keep the old addresses as provenance; the build repoints them in the pages.
                body = page.read_text(encoding="utf-8")
                for found in RETIRED_HOSTS.finditer(body):
                    # Nov 1: a repository Agora does not mirror links its GitHub page; a mirrored one never does.
                    tail = body[found.end():found.end() + 120]
                    repo = re.match(r"/([A-Za-z0-9._-]+?)(?:\.git)?(?=[/\"'<\s?#]|$)", tail)
                    clone = repo is not None and tail[len(repo.group(0)):].startswith("") and \
                        tail.startswith(f"/{repo.group(1)}.git")
                    require(found.group(0) == "github.com/ta-amps" and repo is not None
                            and (repo.group(1) in unmirrored or (clone and repo.group(1) not in git_served)),
                            "a page links GitHub for a mirrored repository, or a retired Pages site: "
                            + page.relative_to(site).as_posix())
        if (site / "llms.txt").exists():
            for found in RETIRED_HOSTS.finditer((site / "llms.txt").read_text(encoding="utf-8")):
                require(found.group(0) == "github.com/ta-amps", "llms.txt links a retired Pages site")
        light_only(site, pages, frozen)
    report = (root / "docs/status.md").read_text(encoding="utf-8")
    for repo in data["repositories"]:
        require(repo["main_revision"] in report, "status page missing exact revision")
        for run in repo["checks"]:
            require(run["url"] in report, "status page missing CI link")
    return {"files_checked": len(files), "repositories": len(data["repositories"]),
            "offline_only": True, "live_checks_performed": False}


if __name__ == "__main__":
    print(json.dumps(check(), sort_keys=True))
