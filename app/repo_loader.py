from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from git import Repo

from app.config import Settings
from app.models import RepositorySnapshot, SourceFile

TEXT_EXTENSIONS = {
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".java",
    ".go",
    ".rs",
    ".cpp",
    ".c",
    ".cs",
    ".rb",
    ".php",
    ".swift",
    ".kt",
    ".yml",
    ".yaml",
    ".json",
    ".toml",
}

IGNORE_DIRS = {
    ".git",
    "node_modules",
    "dist",
    "build",
    "__pycache__",
    ".next",
    ".venv",
    "coverage",
    "test",
    "tests",
    "__tests__",
    "examples",
    "example",
    "docs",
}

PRIORITY_DIRS = ("src", "lib", "app", "server", "api", "core")

LANGUAGE_BY_EXTENSION = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
    ".go": "go",
    ".rs": "rust",
    ".cpp": "cpp",
    ".c": "c",
    ".cs": "csharp",
    ".rb": "ruby",
    ".php": "php",
    ".swift": "swift",
    ".kt": "kotlin",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".json": "json",
    ".toml": "toml",
}


def clone_repository(repo_url: str, branch: str | None, settings: Settings) -> Path:
    repo_id = uuid.uuid4().hex[:8]
    target_dir = settings.temp_dir / repo_id
    Repo.clone_from(repo_url, target_dir, branch=branch, depth=1)
    return target_dir


def cleanup_repository(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path, ignore_errors=True)


def build_snapshot(
    repo_url: str,
    local_path: Path,
    branch: str,
    settings: Settings,
) -> RepositorySnapshot:
    file_summaries: list[dict[str, str]] = []
    selected_files: list[str] = []
    all_files: list[Path] = []
    source_files: list[SourceFile] = []

    for path in local_path.rglob("*"):
        if not path.is_file():
            continue
        if any(part in IGNORE_DIRS for part in path.parts):
            continue
        if _is_ignored_file(path):
            continue
        if path.suffix.lower() not in TEXT_EXTENSIONS and path.name not in {"Dockerfile", "Makefile"}:
            continue
        all_files.append(path)

    prioritized = sorted(all_files, key=_priority_key)

    for path in prioritized[: settings.max_files]:
        relative_path = path.relative_to(local_path).as_posix()
        content = path.read_text(encoding="utf-8", errors="ignore")[: settings.max_file_bytes]
        preview = "\n".join(content.splitlines()[:40])
        source_file = SourceFile(
            path=relative_path,
            content=content,
            language=_detect_language(path),
            bytes=path.stat().st_size,
        )
        selected_files.append(relative_path)
        source_files.append(source_file)
        file_summaries.append(
            {
                "path": relative_path,
                "preview": preview,
                "bytes": str(source_file.bytes),
                "language": source_file.language,
            }
        )

    repo_name = repo_url.rstrip("/").split("/")[-1].removesuffix(".git") or local_path.name

    return RepositorySnapshot(
        repo_name=repo_name,
        repo_url=repo_url,
        branch=branch,
        local_path=str(local_path),
        total_files=len(all_files),
        selected_files=selected_files,
        file_summaries=file_summaries,
        source_files=source_files,
    )


def _is_ignored_file(path: Path) -> bool:
    name = path.name.lower()
    return name.endswith((".min.js", ".bundle.js", ".snap", ".lock"))


def _priority_key(path: Path) -> tuple[int, int, int, str]:
    relative_parts = [part.lower() for part in path.parts]
    directory_score = min(
        (index for index, part in enumerate(relative_parts) if part in PRIORITY_DIRS),
        default=len(PRIORITY_DIRS) + 1,
    )
    size = path.stat().st_size
    return (
        0 if directory_score <= len(PRIORITY_DIRS) else 1,
        directory_score,
        -size,
        path.name.lower(),
    )


def _detect_language(path: Path) -> str:
    if path.name in {"Dockerfile", "Makefile"}:
        return path.name.lower()
    return LANGUAGE_BY_EXTENSION.get(path.suffix.lower(), "text")
