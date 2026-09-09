from __future__ import annotations

import shutil
import uuid
from enum import Enum
from pathlib import Path

from git import Repo

from app.config import Settings
from app.models import RepositorySnapshot, SourceFile
from app.notebook_parser import extract_notebook_code


class FileCategory(str, Enum):
    SOURCE_CODE = "source_code"
    NOTEBOOK = "notebook"
    CONFIG_INFRA = "config_infra"
    DOCUMENTATION = "documentation"
    BINARY_MEDIA = "binary_media"
    GENERATED_BUILD = "generated_build"
    IGNORED = "ignored"


# ---------------------------------------------------------------------------
# File classification sets
# ---------------------------------------------------------------------------

SOURCE_EXTENSIONS: dict[str, str] = {
    # Python
    ".py": "python",
    ".pyw": "python",
    # JavaScript / TypeScript
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    # C / C++
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".hpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".c++": "cpp",
    ".h++": "cpp",
    ".hh": "cpp",
    # Java & JVM
    ".java": "java",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".scala": "scala",
    ".groovy": "groovy",
    # Go / Rust
    ".go": "go",
    ".rs": "rust",
    # C# / .NET
    ".cs": "csharp",
    ".fs": "fsharp",
    # Web / Scripting
    ".php": "php",
    ".rb": "ruby",
    ".swift": "swift",
    ".sh": "bash",
    ".bash": "bash",
    ".zsh": "bash",
    # Data / Scientific
    ".sql": "sql",
    ".r": "r",
    ".dart": "dart",
    ".lua": "lua",
    ".pl": "perl",
}

CONFIG_EXTENSIONS: dict[str, str] = {
    ".yml": "yaml",
    ".yaml": "yaml",
    ".json": "json",
    ".toml": "toml",
    ".xml": "xml",
    ".ini": "ini",
    ".cfg": "ini",
}

DOC_EXTENSIONS = {".md", ".rst", ".txt", ".adoc"}

BINARY_MEDIA_EXTENSIONS = {
    # Video & Audio
    ".avi", ".mp4", ".mov", ".mkv", ".flv", ".wmv", ".webm",
    ".mp3", ".wav", ".ogg", ".flac", ".aac",
    # Images
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".bmp", ".tiff",
    # Archives & Compressed
    ".zip", ".tar", ".gz", ".tgz", ".bz2", ".xz", ".rar", ".7z",
    # Compiled / Binaries
    ".exe", ".dll", ".so", ".dylib", ".bin", ".iso", ".o", ".a",
    ".class", ".pyc", ".pyo", ".whl",
    # ML Models / Weights / Datasets
    ".pt", ".pth", ".onnx", ".h5", ".hdf5", ".safetensors",
    ".pkl", ".pickle", ".parquet", ".feather", ".arrow", ".weights", ".ckpt",
    # Documents
    ".pdf", ".docx", ".xlsx", ".pptx", ".doc",
}

GENERATED_OR_LOCK_FILES = {
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "poetry.lock",
    "pipfile.lock",
    "cargo.lock",
    "composer.lock",
}

IGNORE_DIRS = {
    ".git",
    "node_modules",
    "dist",
    "build",
    "__pycache__",
    ".next",
    ".nuxt",
    ".venv",
    "venv",
    "env",
    "coverage",
    ".pytest_cache",
    ".mypy_cache",
    "target",
    "out",
    "bin",
    "obj",
}

PRIORITY_DIRS = ("src", "lib", "app", "server", "api", "core", "models", "modules")


def classify_file(path: Path, root_path: Path | None = None) -> FileCategory:
    """Classify a repository file into its functional category."""
    name_lower = path.name.lower()
    suffix_lower = path.suffix.lower()

    if root_path is not None:
        try:
            rel_dir_parts = path.relative_to(root_path).parts[:-1]
        except ValueError:
            rel_dir_parts = path.parts[:-1]
    else:
        rel_dir_parts = path.parts[:-1]

    if any(part.lower() in IGNORE_DIRS for part in rel_dir_parts):
        return FileCategory.IGNORED

    if name_lower in GENERATED_OR_LOCK_FILES or name_lower.endswith(
        (".min.js", ".min.css", ".bundle.js", ".map", ".snap", ".lock")
    ):
        return FileCategory.GENERATED_BUILD

    if suffix_lower in BINARY_MEDIA_EXTENSIONS:
        return FileCategory.BINARY_MEDIA

    if suffix_lower == ".ipynb":
        return FileCategory.NOTEBOOK

    if suffix_lower in SOURCE_EXTENSIONS:
        return FileCategory.SOURCE_CODE

    if suffix_lower in CONFIG_EXTENSIONS or name_lower in {"dockerfile", "makefile", "containerfile"}:
        return FileCategory.CONFIG_INFRA

    if suffix_lower in DOC_EXTENSIONS:
        return FileCategory.DOCUMENTATION

    return FileCategory.IGNORED


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
    analyzable_candidates: list[tuple[Path, FileCategory]] = []

    for path in local_path.rglob("*"):
        if not path.is_file():
            continue
        category = classify_file(path, root_path=local_path)
        # We analyze notebooks, source code, and key config/infra files
        if category in {
            FileCategory.NOTEBOOK,
            FileCategory.SOURCE_CODE,
            FileCategory.CONFIG_INFRA,
        }:
            analyzable_candidates.append((path, category))

    # Sort candidates by architectural priority
    prioritized = sorted(
        analyzable_candidates,
        key=lambda item: _priority_key(item[0], item[1], root_path=local_path),
    )

    source_files: list[SourceFile] = []

    for path, category in prioritized[: settings.max_files]:
        relative_path = path.relative_to(local_path).as_posix()

        if category == FileCategory.NOTEBOOK:
            # Safely parse notebook JSON and extract pure code cells
            extracted_code, lang, code_cells, total_cells = extract_notebook_code(
                path, max_bytes=settings.max_file_bytes
            )
            source_file = SourceFile(
                path=relative_path,
                content=extracted_code,
                language=lang,
                bytes=len(extracted_code.encode("utf-8")),
                is_notebook=True,
                total_cells=total_cells,
            )
        else:
            raw_content = path.read_text(encoding="utf-8", errors="ignore")[: settings.max_file_bytes]
            source_file = SourceFile(
                path=relative_path,
                content=raw_content,
                language=_detect_language(path),
                bytes=path.stat().st_size,
                is_notebook=False,
                total_cells=0,
            )

        selected_files.append(relative_path)
        source_files.append(source_file)
        preview = "\n".join(source_file.content.splitlines()[:30])
        file_summaries.append(
            {
                "path": relative_path,
                "preview": preview,
                "bytes": str(source_file.bytes),
                "language": source_file.language,
                "is_notebook": str(source_file.is_notebook),
            }
        )

    repo_name = repo_url.rstrip("/").split("/")[-1].removesuffix(".git") or local_path.name

    return RepositorySnapshot(
        repo_name=repo_name,
        repo_url=repo_url,
        branch=branch,
        local_path=str(local_path),
        total_files=len(analyzable_candidates),
        selected_files=selected_files,
        file_summaries=file_summaries,
        source_files=source_files,
    )


def _priority_key(
    path: Path, category: FileCategory, root_path: Path | None = None
) -> tuple[int, int, int, str]:
    """
    Sort files so that:
    1. Executable source code and Jupyter notebooks come first.
    2. Files in priority directories (src, lib, app, etc.) or root source files come first.
    3. Config files come next.
    4. Size and alphabetical order tie-break predictably.
    """
    if root_path is not None:
        try:
            relative_parts = [part.lower() for part in path.relative_to(root_path).parts]
        except ValueError:
            relative_parts = [part.lower() for part in path.parts]
    else:
        relative_parts = [part.lower() for part in path.parts]

    in_priority_dir = any(part in PRIORITY_DIRS for part in relative_parts)
    is_root_source = len(relative_parts) <= 1  # e.g. "Section1.ipynb"

    category_rank = {
        FileCategory.NOTEBOOK: 0,
        FileCategory.SOURCE_CODE: 0,
        FileCategory.CONFIG_INFRA: 1,
        FileCategory.DOCUMENTATION: 2,
    }.get(category, 3)

    location_rank = 0 if (in_priority_dir or is_root_source) else 1
    size = path.stat().st_size if path.exists() else 0

    return (
        category_rank,
        location_rank,
        -size,
        path.name.lower(),
    )


def _detect_language(path: Path) -> str:
    name_lower = path.name.lower()
    suffix_lower = path.suffix.lower()
    if name_lower in {"dockerfile", "containerfile"}:
        return "dockerfile"
    if name_lower == "makefile":
        return "makefile"
    if suffix_lower in SOURCE_EXTENSIONS:
        return SOURCE_EXTENSIONS[suffix_lower]
    if suffix_lower in CONFIG_EXTENSIONS:
        return CONFIG_EXTENSIONS[suffix_lower]
    return "text"
