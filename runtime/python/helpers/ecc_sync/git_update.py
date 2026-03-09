from __future__ import annotations

from pathlib import Path
import subprocess


def _run_git(vendor_root: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(vendor_root), *args],
        capture_output=True,
        text=True,
    )


def _git_sha(vendor_root: Path) -> str:
    proc = _run_git(vendor_root, ["rev-parse", "--short", "HEAD"])
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "git rev-parse failed")
    return proc.stdout.strip()


def get_repo_info(vendor_root: Path) -> dict:
    info: dict = {
        "path": str(vendor_root),
        "exists": vendor_root.exists(),
        "is_git": False,
        "remote_url": "",
        "branch": "",
        "current_sha": "",
        "dirty": False,
    }
    if not vendor_root.exists():
        return info

    check = _run_git(vendor_root, ["rev-parse", "--is-inside-work-tree"])
    if check.returncode != 0 or check.stdout.strip() != "true":
        return info

    info["is_git"] = True
    remote = _run_git(vendor_root, ["remote", "get-url", "origin"])
    if remote.returncode == 0:
        info["remote_url"] = remote.stdout.strip()

    branch = _run_git(vendor_root, ["rev-parse", "--abbrev-ref", "HEAD"])
    if branch.returncode == 0:
        info["branch"] = branch.stdout.strip()

    sha = _run_git(vendor_root, ["rev-parse", "--short", "HEAD"])
    if sha.returncode == 0:
        info["current_sha"] = sha.stdout.strip()

    dirty = _run_git(vendor_root, ["status", "--porcelain"])
    if dirty.returncode == 0:
        info["dirty"] = bool(dirty.stdout.strip())

    return info


def update_to_latest(vendor_root: Path) -> dict:
    before_sha = _git_sha(vendor_root)

    fetch = _run_git(vendor_root, ["fetch"])
    if fetch.returncode != 0:
        return {"success": False, "error": fetch.stderr.strip() or fetch.stdout.strip(), "before_sha": before_sha}

    pull = _run_git(vendor_root, ["pull", "--ff-only"])
    if pull.returncode != 0:
        return {"success": False, "error": pull.stderr.strip() or pull.stdout.strip(), "before_sha": before_sha}

    after_sha = _git_sha(vendor_root)
    return {"success": True, "before_sha": before_sha, "after_sha": after_sha, "changed": before_sha != after_sha}
