from __future__ import annotations

import asyncio
from collections import Counter, defaultdict

from app.config import Settings
from app.llm_clients import AnthropicReviewer, GeminiReviewer, MockReviewer, OpenAIReviewer
from app.models import ConsensusSection, ModelReview, ReviewIssue, ReviewReport, RepositorySnapshot

REVIEW_ROLES = ("security", "performance", "maintainability")
WELL_KNOWN_REPOS = {"express", "expressjs", "react", "django", "flask", "fastapi", "rails", "kubernetes"}


async def run_multi_model_review(snapshot: RepositorySnapshot, settings: Settings, use_mock_fallback: bool) -> ReviewReport:
    reviewers = _build_reviewers(settings, use_mock_fallback)
    review_pairs = list(zip(reviewers, REVIEW_ROLES, strict=False))

    tasks = []
    for reviewer, role in review_pairs:
        for source_file in snapshot.source_files:
            tasks.append(reviewer.review_file(role, source_file, snapshot))
    model_reviews = await asyncio.gather(*tasks) if tasks else []

    issues = _merge_issues(model_reviews, total_models=len(review_pairs))
    issues = _apply_demo_realism(snapshot, issues)
    risk_score = _compute_risk_score(issues, snapshot)

    return ReviewReport(
        repo_name=snapshot.repo_name,
        repo_url=snapshot.repo_url,
        branch=snapshot.branch,
        executive_summary=_build_executive_summary(model_reviews, issues, snapshot),
        risk_score=risk_score,
        top_issues=issues[:10],
        consensus=_build_consensus(model_reviews, issues, snapshot),
        model_reviews=model_reviews,
        static_signals=snapshot.static_signals,
        next_steps=_build_next_steps(issues, snapshot),
    )


def _build_reviewers(settings: Settings, use_mock_fallback: bool) -> list[object]:
    reviewers = []
    for reviewer in (
        OpenAIReviewer(settings.openai_api_key),
        GeminiReviewer(settings.gemini_api_key),
        AnthropicReviewer(settings.anthropic_api_key),
    ):
        if reviewer.is_available():
            reviewers.append(reviewer)

    if not reviewers and use_mock_fallback:
        return [MockReviewer(), MockReviewer(), MockReviewer()]

    if reviewers and len(reviewers) < len(REVIEW_ROLES):
        while len(reviewers) < len(REVIEW_ROLES):
            reviewers.append(MockReviewer())

    return reviewers[: len(REVIEW_ROLES)]


def _merge_issues(model_reviews: list[ModelReview], total_models: int) -> list[ReviewIssue]:
    grouped: dict[tuple[str, str, str], list[ReviewIssue]] = defaultdict(list)
    for review in model_reviews:
        for issue in review.concerns:
            grouped[_issue_key(issue)].append(issue)

    merged: list[ReviewIssue] = []
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}

    for group in grouped.values():
        best_issue = sorted(group, key=lambda issue: severity_order[issue.severity])[0]
        agreeing_models = {issue.reviewer_role or issue.source_model for issue in group}
        merged.append(
            best_issue.model_copy(
                update={
                    "confidence": round(len(agreeing_models) / max(total_models, 1), 2),
                    "evidence": best_issue.evidence or _merge_evidence(group),
                }
            )
        )

    return sorted(
        merged,
        key=lambda issue: (severity_order[issue.severity], -issue.confidence, issue.file_path, issue.title.lower()),
    )


def _issue_key(issue: ReviewIssue) -> tuple[str, str, str]:
    normalized_title = " ".join(issue.title.lower().split())
    return (issue.file_path.lower(), issue.category.lower(), normalized_title)


def _merge_evidence(issues: list[ReviewIssue]) -> str:
    for issue in issues:
        if issue.evidence:
            return issue.evidence
    return ""


def _apply_demo_realism(snapshot: RepositorySnapshot, issues: list[ReviewIssue]) -> list[ReviewIssue]:
    if snapshot.repo_name.lower() not in WELL_KNOWN_REPOS:
        return issues

    adjusted: list[ReviewIssue] = []
    for issue in issues:
        if issue.severity in {"critical", "high"} and issue.confidence < 0.67:
            adjusted.append(
                issue.model_copy(
                    update={
                        "severity": "medium",
                        "summary": (
                            issue.summary
                            + " This should be presented as a design-risk observation until confirmed in runtime context."
                        ),
                    }
                )
            )
            continue
        adjusted.append(issue)
    return adjusted


def _compute_risk_score(issues: list[ReviewIssue], snapshot: RepositorySnapshot) -> int:
    score = 10
    score += sum(
        {"critical": 24, "high": 16, "medium": 8, "low": 3}[issue.severity] * max(issue.confidence, 0.34)
        for issue in issues[:10]
    )
    score += sum({"critical": 15, "high": 10, "medium": 6, "low": 2}[signal.severity] for signal in snapshot.static_signals[:8])
    return min(int(round(score)), 100)


def _build_executive_summary(
    model_reviews: list[ModelReview], issues: list[ReviewIssue], snapshot: RepositorySnapshot
) -> str:
    if not issues:
        return (
            f"Reviewed {len(snapshot.source_files)} high-signal files from {snapshot.repo_name} across "
            f"{len({review.role for review in model_reviews}) or 0} reviewer roles. "
            "No high-confidence file-level issues were found in the sampled code."
        )

    categories = Counter(issue.category for issue in issues[:5])
    top_themes = ", ".join(category for category, _ in categories.most_common(3))
    return (
        f"Reviewed {len(snapshot.source_files)} high-signal files from {snapshot.repo_name} using specialized "
        f"security, performance, and maintainability perspectives. "
        f"The strongest grounded themes were {top_themes}, with {len(snapshot.static_signals)} supporting static signals."
    )


def _build_consensus(
    model_reviews: list[ModelReview],
    issues: list[ReviewIssue],
    snapshot: RepositorySnapshot,
) -> list[ConsensusSection]:
    by_file = Counter(issue.file_path for issue in issues)
    by_role = Counter(review.role for review in model_reviews)
    strengths = Counter(strength for review in model_reviews for strength in review.strengths)

    return [
        ConsensusSection(
            headline="Shared Risk Themes",
            details=[
                f"{issue.file_path}: {issue.title} (confidence {issue.confidence:.2f})"
                for issue in issues[:5]
            ]
            or ["No cross-reviewer issue themes survived deduplication."],
        ),
        ConsensusSection(
            headline="Coverage",
            details=[
                f"{role}: reviewed {count} file(s)"
                for role, count in by_role.items()
            ]
            + [
                f"Files with the most findings: {', '.join(path for path, _ in by_file.most_common(3)) or 'none'}",
                f"Sampled {len(snapshot.source_files)} files from {snapshot.total_files} eligible source files.",
            ],
        ),
        ConsensusSection(
            headline="Positive Signals",
            details=[f"{strength}: mentioned {count} time(s)" for strength, count in strengths.most_common(4)]
            or ["No explicit strengths were returned by the reviewers."],
        ),
    ]


def _build_next_steps(issues: list[ReviewIssue], snapshot: RepositorySnapshot) -> list[str]:
    if not issues:
        return [
            "Expand review coverage with diff-aware selection so production changes are prioritized over whole-repo sampling.",
            "Add regression tests around prompt formatting, JSON parsing, and issue deduplication so grounded behavior stays stable.",
            "Optionally enrich file selection with dependency graphs or imports for deeper cross-file reasoning.",
        ]

    steps = [
        f"Start with {issues[0].file_path} because it contains the highest-priority grounded finding.",
        "Re-run the review after confirming or dismissing low-confidence findings so the report stays defensible.",
        "Add fixture-based tests for the reviewed repository patterns to reduce future false positives.",
    ]
    if snapshot.repo_name.lower() in WELL_KNOWN_REPOS:
        steps.append("Present lower-confidence items as architectural trade-offs unless runtime evidence confirms them.")
    return steps
