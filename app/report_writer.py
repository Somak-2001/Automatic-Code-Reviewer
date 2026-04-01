from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from app.models import ReviewIssue, ReviewReport


def write_report(report_id: str, report: ReviewReport, output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"{report_id}.json"
    markdown_path = output_dir / f"{report_id}.md"

    json_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    markdown_path.write_text(_to_markdown(report), encoding="utf-8")
    return markdown_path, json_path


def _to_markdown(report: ReviewReport) -> str:
    lines = [
        f"# Multi-Agent Code Review Report: {report.repo_name}",
        "",
        f"- Repository: {report.repo_url}",
        f"- Branch: {report.branch}",
        f"- Generated At: {report.generated_at.isoformat()}",
        f"- Risk Score: {report.risk_score}/100",
        "",
        "## Executive Summary",
        report.executive_summary,
        "",
        "## Top Issues",
    ]

    if not report.top_issues:
        lines.append("- No high-confidence file-level issues were identified.")
    else:
        for issue in report.top_issues[:5]:
            lines.extend(
                [
                    f"- [{issue.severity}] {issue.file_path} {issue.line_hint or ''}".strip(),
                    f"  {issue.title} (confidence {issue.confidence:.2f})",
                    f"  {issue.summary}",
                ]
            )

    lines.extend(["", "## Findings By File"])
    grouped = _group_issues_by_file(report.top_issues)
    if not grouped:
        lines.append("- No file-specific findings survived deduplication.")
    else:
        for file_path, issues in grouped.items():
            lines.append(f"### {file_path}")
            for issue in issues:
                lines.append(
                    f"- [{issue.severity}/{issue.category}] {issue.title} at {issue.line_hint or 'N/A'} "
                    f"(confidence {issue.confidence:.2f})"
                )
                lines.append(f"  Summary: {issue.summary}")
                lines.append(f"  Recommendation: {issue.recommendation}")
                if issue.evidence:
                    lines.append(f"  Evidence: {issue.evidence}")
            lines.append("")

    lines.append("## Static Signals")
    if not report.static_signals:
        lines.append("- No static-analysis signals were detected.")
    else:
        for signal in report.static_signals:
            line_suffix = f" {signal.line_hint}" if signal.line_hint else ""
            lines.append(f"- [{signal.severity}] {signal.file_path}{line_suffix}: {signal.message}")

    lines.extend(["", "## Reviewer Perspectives"])
    for review in report.model_reviews:
        if not review.summary and not review.concerns:
            continue
        lines.append(f"### {review.role.title()} Reviewer ({review.provider})")
        if review.summary:
            lines.append(review.summary)
        for concern in review.concerns[:2]:
            lines.append(f"- {concern.file_path}: {concern.title}")
        lines.append("")

    lines.append("## Recommended Next Steps")
    for step in report.next_steps:
        lines.append(f"- {step}")

    return "\n".join(lines).strip() + "\n"


def _group_issues_by_file(issues: list[ReviewIssue]) -> dict[str, list[ReviewIssue]]:
    grouped: dict[str, list[ReviewIssue]] = defaultdict(list)
    for issue in issues:
        grouped[issue.file_path].append(issue)
    return dict(grouped)
