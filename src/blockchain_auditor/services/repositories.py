from __future__ import annotations

import os
import re
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlparse

from ..provenance import safe_project_path


GITHUB_REPOSITORY = re.compile(r"^/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:\.git)?$")


class RepositoryService:
    """Materializes approved repository sources for workers."""
    def normalize(self, value: str) -> str:
        value = value.strip()
        if not value: raise ValueError("A project path or GitHub repository URL is required")
        if not value.startswith(("http://", "https://")): return str(safe_project_path(value))
        parsed = urlparse(value)
        if parsed.scheme != "https" or parsed.hostname != "github.com":
            raise ValueError("Remote audits support public HTTPS GitHub repository URLs only")
        if parsed.username or parsed.password: raise ValueError("Credentials must not be embedded in repository URLs")
        if parsed.port or parsed.query or parsed.fragment or not GITHUB_REPOSITORY.fullmatch(parsed.path):
            raise ValueError("GitHub URL must have the form https://github.com/owner/repository")
        return f"https://github.com{parsed.path}"

    def resolve(self, source: dict) -> Path:
        source_type = source.get("type", "local")
        if source_type != "local": raise ValueError("Remote repositories must be materialized by an audit worker")
        return safe_project_path(str(source.get("path", "")))

    @contextmanager
    def materialize(self, value: str):
        normalized = self.normalize(value)
        if not normalized.startswith("https://"):
            yield Path(normalized), None
            return
        with tempfile.TemporaryDirectory(prefix="blockchain-auditor-github-") as temporary:
            target = Path(temporary) / "repository"
            environment = {**os.environ, "GIT_TERMINAL_PROMPT": "0", "GIT_LFS_SKIP_SMUDGE": "1"}
            command = ["git", "-c", "core.hooksPath=/dev/null", "clone", "--depth", "1", "--single-branch", "--no-tags", "--no-recurse-submodules", normalized, str(target)]
            try:
                result = subprocess.run(command, capture_output=True, text=True, timeout=120, env=environment, check=False)
            except FileNotFoundError as exc: raise ValueError("Git is required to audit a GitHub repository URL") from exc
            except subprocess.TimeoutExpired as exc: raise ValueError("GitHub repository clone exceeded the 120 second limit") from exc
            if result.returncode:
                detail = (result.stderr or result.stdout or "clone failed").strip().splitlines()[-1][:300]
                raise ValueError(f"GitHub repository could not be cloned: {detail}")
            files = 0; total = 0
            for path in target.rglob("*"):
                if path.is_symlink(): raise ValueError("GitHub repositories containing symbolic links are not accepted for audit")
                if not path.is_file() or ".git" in path.parts: continue
                files += 1; total += path.stat().st_size
                if files > 50_000 or total > 250 * 1024 * 1024:
                    raise ValueError("GitHub repository exceeds the 50,000 file or 250 MiB audit limit")
            yield safe_project_path(str(target)), normalized
