from __future__ import annotations

import re

from app.models import RepositorySnapshot, SourceFile, StaticSignal

SECRET_PATTERNS = (
    (
        "aws-access-key",
        re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
        "Potential AWS access key detected.",
        "high",
    ),
    (
        "github-token",
        re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
        "Potential GitHub token detected.",
        "high",
    ),
    (
        "stripe-live-key",
        re.compile(r"\bsk_live_[0-9A-Za-z]{16,}\b"),
        "Potential Stripe live secret detected.",
        "high",
    ),
    (
        "jwt-or-api-token",
        re.compile(
            r"(?i)\b(?:api[_-]?key|secret|token|password)\b\s*[:=]\s*['\"][A-Za-z0-9_\-\/+=]{12,}['\"]"
        ),
        "Potential hardcoded credential assignment detected.",
        "medium",
    ),
)

TODO_PATTERN = re.compile(r"\b(TODO|FIXME)\b")
COMMENT_PREFIXES = ("#", "//", "*", "/*", "*/", "<!--")
CODE_EXTENSIONS = {".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".go", ".rs", ".rb", ".php", ".kt", ".swift"}


def enrich_with_static_analysis(snapshot: RepositorySnapshot) -> RepositorySnapshot:
    signals: list[StaticSignal] = []

    for source_file in snapshot.source_files:
        signals.extend(_find_secret_signals(source_file))
        signals.extend(_find_todo_signals(source_file))

    snapshot.static_signals = _dedupe_signals(signals)
    return snapshot


def _find_secret_signals(source_file: SourceFile) -> list[StaticSignal]:
    signals: list[StaticSignal] = []
    for line_number, line in enumerate(source_file.content.splitlines(), start=1):
        code_line = _strip_line_comments(line, source_file.language).strip()
        if not code_line:
            continue

        for kind, pattern, message, severity in SECRET_PATTERNS:
            if pattern.search(code_line):
                signals.append(
                    StaticSignal(
                        kind=kind,
                        file_path=source_file.path,
                        line_hint=f"L{line_number}",
                        message=message,
                        severity=severity,
                    )
                )
    return signals


def _find_todo_signals(source_file: SourceFile) -> list[StaticSignal]:
    if not _supports_code_comments(source_file):
        return []

    signals: list[StaticSignal] = []
    for line_number, line in enumerate(source_file.content.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or not stripped.startswith(COMMENT_PREFIXES):
            continue
        if TODO_PATTERN.search(stripped):
            signals.append(
                StaticSignal(
                    kind="maintenance-note",
                    file_path=source_file.path,
                    line_hint=f"L{line_number}",
                    message="TODO/FIXME found in code comment.",
                    severity="low",
                )
            )
    return signals


def _supports_code_comments(source_file: SourceFile) -> bool:
    suffix = ""
    if "." in source_file.path:
        suffix = "." + source_file.path.rsplit(".", 1)[-1].lower()
    return suffix in CODE_EXTENSIONS


def _strip_line_comments(line: str, language: str) -> str:
    stripped = line.strip()
    if stripped.startswith(COMMENT_PREFIXES):
        return ""

    if language == "python":
        return line.split("#", 1)[0]

    for marker in ("//", "/*"):
        if marker in line:
            return line.split(marker, 1)[0]
    return line


def _dedupe_signals(signals: list[StaticSignal]) -> list[StaticSignal]:
    deduped: dict[tuple[str, str, str], StaticSignal] = {}
    for signal in signals:
        key = (signal.kind, signal.file_path, signal.line_hint)
        deduped.setdefault(key, signal)
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    return sorted(
        deduped.values(),
        key=lambda signal: (
            severity_order[signal.severity],
            signal.file_path,
            signal.line_hint,
        ),
    )
