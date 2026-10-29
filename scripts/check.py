"""Offline consistency and publication checks for the dated Agora snapshot."""
from __future__ import annotations

import datetime as dt
import json
import re
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
    data = json.loads(path.read_text(), object_pairs_hook=unique_pairs, parse_constant=nonfinite)
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
        prefix = "https://github.com/ta-amps/" + repo["name"]
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


def public_text(text: str) -> None:
    for name, pattern in SENSITIVE.items():
        require(pattern.search(text) is None, "possible private material: " + name)


def local_links(path: Path, root: Path) -> None:
    for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", path.read_text()):
        target = target.strip("<>")
        parsed = urlsplit(target)
        if parsed.scheme or parsed.netloc or not parsed.path:
            continue
        local = (path.parent / unquote(parsed.path)).resolve()
        require(local.is_relative_to(root.resolve()) and local.is_file(),
                "broken or escaping local link in " + path.name + ": " + target)


def check(root: Path = ROOT) -> dict:
    data = load(root / "status.json")
    evidence = load(root / data["evidence_path"])
    snapshot(data, evidence)
    files = [p for p in root.rglob("*") if p.is_file() and not SKIP.intersection(p.relative_to(root).parts)]
    for path in files:
        text = path.read_text()
        public_text(text)
        if path.suffix == ".json":
            load(path)
        if path.suffix == ".md" or path.name == "llms.txt":
            local_links(path, root)
    report = (root / "docs/status.md").read_text()
    for repo in data["repositories"]:
        require(repo["main_revision"] in report, "status page missing exact revision")
        for run in repo["checks"]:
            require(run["url"] in report, "status page missing CI link")
    return {"files_checked": len(files), "repositories": len(data["repositories"]),
            "offline_only": True, "live_checks_performed": False}


if __name__ == "__main__":
    print(json.dumps(check(), sort_keys=True))
