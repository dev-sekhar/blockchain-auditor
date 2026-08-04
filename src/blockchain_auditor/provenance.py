from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

from .models import SourceIdentity


IGNORED_PARTS = {".git", ".audit-reports", "node_modules", ".venv", "venv", "target", "build", "dist"}


def _git(project: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(project), *args], capture_output=True, text=True, timeout=5, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def tree_hash(project: Path) -> str:
    digest = hashlib.sha256()
    files = sorted(
        p for p in project.rglob("*")
        if p.is_file() and not any(part in IGNORED_PARTS for part in p.relative_to(project).parts)
    )
    for path in files:
        relative = path.relative_to(project).as_posix().encode()
        digest.update(len(relative).to_bytes(4, "big"))
        digest.update(relative)
        try:
            with path.open("rb") as stream:
                while chunk := stream.read(1024 * 1024):
                    digest.update(chunk)
        except (OSError, PermissionError):
            digest.update(b"<unreadable>")
    return digest.hexdigest()


def identify_source(project: Path) -> SourceIdentity:
    commit = _git(project, "rev-parse", "HEAD")
    branch = _git(project, "branch", "--show-current") if commit else None
    status = _git(project, "status", "--porcelain") if commit else None
    return SourceIdentity(
        path=str(project),
        project_name=project.name,
        tree_hash=tree_hash(project),
        git_commit=commit,
        git_branch=branch,
        git_dirty=bool(status) if commit else None,
    )


def safe_project_path(value: str) -> Path:
    project = Path(value).expanduser().resolve()
    if not project.exists():
        raise ValueError(f"Project path does not exist: {project}")
    if not project.is_dir():
        raise ValueError(f"Project path is not a directory: {project}")
    if project == Path(project.anchor):
        raise ValueError("Refusing to audit a filesystem root")
    if not os.access(project, os.R_OK):
        raise ValueError(f"Project path is not readable: {project}")
    return project
