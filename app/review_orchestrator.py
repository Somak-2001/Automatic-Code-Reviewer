from __future__ import annotations

import asyncio
from collections import Counter, defaultdict
from typing import Awaitable, Callable

from app.config import Settings
from app.llm_clients import AnthropicReviewer, GeminiReviewer, OpenAIReviewer, ProviderError
from app.models import (
    ConsensusSection,
    ProviderResult,
    RepositorySnapshot,
    ReviewIssue,
    ReviewReport,
    StageStatus,
)

# Each reviewer is assigned a distinct role so they bring different perspectives.
PROVIDER_ROLES: dict[str, str] = {
    "openai": "security",
    "anthropic": "maintainability",
    "gemini": "performance",
}

# Type alias for the stage-update callback
StageCallback = Callable[[str, StageStatus], Awaitable[None]]


async def run_multi_model_review(
    snapshot: RepositorySnapshot,
    settings: Settings,
    stage_callback: StageCallback,
) -> ReviewReport:
    """
    Run a real multi-LLM review of the given repository snapshot.

    Raises ValueError if no providers are configured.
    Never substitutes mock data for missing/failed providers.
    """
    # Build only the reviewers for configured providers
    reviewers: dict[str, tuple[object, str]] = {}  # provider → (reviewer, role)

    if settings.openai_api_key:
        reviewers["openai"] = (
            OpenAIReviewer(settings.openai_api_key, settings.openai_model),
            PROVIDER_ROLES["openai"],
        )
    if settings.anthropic_api_key:
        reviewers["anthropic"] = (
            AnthropicReviewer(settings.anthropic_api_key, settings.anthropic_model),
            PROVIDER_ROLES["anthropic"],
        )
    if settings.gemini_api_key:
        reviewers["gemini"] = (
            GeminiReviewer(settings.gemini_api_key, settings.gemini_model),
            PROVIDER_ROLES["gemini"],
        )

    if not reviewers:
        raise ValueError(
            "No LLM providers configured. "
            "Set at least one of OPENAI_API_KEY, ANTHROPIC_API_KEY, or GEMINI_API_KEY."
        )

    providers_attempted = list(reviewers.keys())

    # For each provider, review all selected source files sequentially per provider
    # (parallelise across providers, sequential within each provider to keep token usage sane)
    async def run_one_provider(
        provider_name: str,
        reviewer: object,
        role: str,
    ) -> ProviderResult:
        await stage_callback(provider_name, StageStatus.running)

        file_results: list[ProviderResult] = []
        last_error: str = ""

        for source_file in snapshot.source_files:
            try:
                result = await reviewer.review_file(role, source_file, snapshot)  # type: ignore[union-attr]
                file_results.append(result)
            except ProviderError as exc:
                last_error = exc.message
                # Propagate immediately — a provider auth error won't fix itself
                if "authentication" in exc.message.lower() or "api key" in exc.message.lower():
                    await stage_callback(provider_name, StageStatus.failed)
                    return ProviderResult(
                        provider=provider_name,
                        role=role,
                        status=StageStatus.failed,
                        error=exc.message,
                    )
                # For non-fatal errors (rate limit, timeout on single file), record but continue
                # We create a partial result for this file
            except Exception as exc:
                last_error = str(exc)
                # Non-ProviderError unexpected exception — treat entire provider as failed
                await stage_callback(provider_name, StageStatus.failed)
                return ProviderResult(
                    provider=provider_name,
                    role=role,
                    status=StageStatus.failed,
                    error=f"Unexpected error: {last_error}",
                )

        if not file_results:
            # All files failed for this provider
            await stage_callback(provider_name, StageStatus.failed)
            return ProviderResult(
                provider=provider_name,
                role=role,
                status=StageStatus.failed,
                error=last_error or "No files could be reviewed.",
            )

        # Merge results from all files for this provider into one ProviderResult
        merged = _merge_file_results(provider_name, role, file_results)
        await stage_callback(provider_name, StageStatus.completed)
        return merged

    # Run all providers concurrently
    provider_tasks = {
        name: asyncio.create_task(run_one_provider(name, reviewer, role))
        for name, (reviewer, role) in reviewers.items()
    }

    provider_results_map: dict[str, ProviderResult] = {}
    for name, task in provider_tasks.items():
        try:
            provider_results_map[name] = await task
        except Exception as exc:
            # Safety net
            provider_results_map[name] = ProviderResult(
                provider=name,
                role=PROVIDER_ROLES.get(name, "general"),
                status=StageStatus.failed,
                error=str(exc),
            )
            await stage_callback(name, StageStatus.failed)

    # Mark any provider that wasn't attempted as skipped
    all_provider_names = ["openai", "anthropic", "gemini"]
    provider_results_list: list[ProviderResult] = list(provider_results_map.values())
    for name in all_provider_names:
        if name not in provider_results_map:
            provider_results_list.append(
                ProviderResult(
                    provider=name,
                    role=PROVIDER_ROLES.get(name, "general"),
                    status=StageStatus.skipped,
                    error="API key not configured.",
                )
            )

    providers_succeeded = [
        r.provider for r in provider_results_list if r.status == StageStatus.completed
    ]
    providers_failed = [
        r.provider for r in provider_results_list if r.status == StageStatus.failed
    ]

    if not providers_succeeded:
        # All real providers failed
        errors = "; ".join(
            f"{r.provider}: {r.error}"
            for r in provider_results_list
            if r.status == StageStatus.failed
        )
        raise ValueError(f"All LLM providers failed. Details: {errors}")

    # Aggregate and deduplicate issues across all successful providers
    all_concerns = [
        issue
        for result in provider_results_list
        if result.status == StageStatus.completed
        for issue in result.concerns
    ]

    await stage_callback("aggregation", StageStatus.running)
    issues = _merge_issues(all_concerns, total_providers=len(providers_succeeded))
    risk_score = _compute_risk_score(issues, snapshot)
    await stage_callback("aggregation", StageStatus.completed)

    return ReviewReport(
        repo_name=snapshot.repo_name,
        repo_url=snapshot.repo_url,
        branch=snapshot.branch,
        executive_summary=_build_executive_summary(
            provider_results_list, issues, snapshot, providers_succeeded, providers_failed
        ),
        risk_score=risk_score,
        top_issues=issues[:15],
        consensus=_build_consensus(provider_results_list, issues, snapshot),
        provider_results=provider_results_list,
        static_signals=snapshot.static_signals,
        next_steps=_build_next_steps(issues, snapshot),
        providers_attempted=providers_attempted,
        providers_succeeded=providers_succeeded,
        providers_failed=providers_failed,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _merge_file_results(provider: str, role: str, results: list[ProviderResult]) -> ProviderResult:
    """Merge per-file ProviderResults for one provider into a single result."""
    all_concerns = [c for r in results for c in r.concerns]
    all_strengths = list({s for r in results for s in r.strengths})
    summaries = [r.summary for r in results if r.summary]
    combined_summary = " ".join(summaries[:3])  # cap to avoid very long summaries

    return ProviderResult(
        provider=provider,
        role=role,
        status=StageStatus.completed,
        summary=combined_summary,
        strengths=all_strengths[:8],
        concerns=all_concerns,
    )


def _issue_key(issue: ReviewIssue) -> tuple[str, str, str]:
    """Canonical deduplication key for an issue."""
    normalized_title = " ".join(issue.title.lower().split())
    return (issue.file_path.lower(), issue.category.lower(), normalized_title)


def _merge_issues(all_concerns: list[ReviewIssue], total_providers: int) -> list[ReviewIssue]:
    """Deduplicate, merge, and score issues from all providers."""
    grouped: dict[tuple[str, str, str], list[ReviewIssue]] = defaultdict(list)
    for issue in all_concerns:
        grouped[_issue_key(issue)].append(issue)

    merged: list[ReviewIssue] = []
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}

    for group in grouped.values():
        # Pick the highest-severity version as the canonical one
        best_issue = sorted(group, key=lambda i: severity_order[i.severity])[0]
        # Collect all unique providers that detected this issue
        detected_by = list({i.source_model for i in group})
        confidence = round(len(detected_by) / max(total_providers, 1), 2)

        merged.append(
            best_issue.model_copy(
                update={
                    "confidence": confidence,
                    "detected_by": detected_by,
                    "evidence": best_issue.evidence or _pick_best_evidence(group),
                }
            )
        )

    return sorted(
        merged,
        key=lambda i: (
            severity_order[i.severity],
            -i.confidence,
            i.file_path,
            i.title.lower(),
        ),
    )


def _pick_best_evidence(issues: list[ReviewIssue]) -> str:
    for issue in issues:
        if issue.evidence:
            return issue.evidence
    return ""


def _compute_risk_score(issues: list[ReviewIssue], snapshot: RepositorySnapshot) -> int:
    score = 10
    score += sum(
        {"critical": 24, "high": 16, "medium": 8, "low": 3}[issue.severity]
        * max(issue.confidence, 0.34)
        for issue in issues[:10]
    )
    score += sum(
        {"critical": 15, "high": 10, "medium": 6, "low": 2}[signal.severity]
        for signal in snapshot.static_signals[:8]
    )
    return min(int(round(score)), 100)


def _build_executive_summary(
    provider_results: list[ProviderResult],
    issues: list[ReviewIssue],
    snapshot: RepositorySnapshot,
    providers_succeeded: list[str],
    providers_failed: list[str],
) -> str:
    provider_summary = f"{len(providers_succeeded)} of {len(providers_succeeded) + len(providers_failed)} providers completed"
    if providers_failed:
        provider_summary += f" ({', '.join(providers_failed)} failed)"

    if not issues:
        return (
            f"Reviewed {len(snapshot.source_files)} files from {snapshot.repo_name} using "
            f"{provider_summary}. No high-confidence issues were found in the sampled code."
        )

    categories = Counter(issue.category for issue in issues[:5])
    top_themes = ", ".join(cat for cat, _ in categories.most_common(3))
    return (
        f"Reviewed {len(snapshot.source_files)} files from {snapshot.repo_name} using "
        f"{provider_summary}. "
        f"Top themes: {top_themes}. "
        f"Found {len(issues)} issues with {len(snapshot.static_signals)} static signals."
    )


def _build_consensus(
    provider_results: list[ProviderResult],
    issues: list[ReviewIssue],
    snapshot: RepositorySnapshot,
) -> list[ConsensusSection]:
    by_file = Counter(issue.file_path for issue in issues)
    strengths = Counter(
        s
        for r in provider_results
        if r.status == StageStatus.completed
        for s in r.strengths
    )
    high_consensus = [i for i in issues if len(i.detected_by) >= 2]
    single_model = [i for i in issues if len(i.detected_by) == 1]

    return [
        ConsensusSection(
            headline="Multi-Provider Agreement",
            details=[
                f"{issue.file_path}: {issue.title} "
                f"(detected by {', '.join(issue.detected_by)}, confidence {issue.confidence:.0%})"
                for issue in high_consensus[:5]
            ]
            or ["No issues were detected by multiple providers."],
        ),
        ConsensusSection(
            headline="Single-Provider Findings",
            details=[
                f"{issue.file_path}: {issue.title} "
                f"(detected by {issue.detected_by[0] if issue.detected_by else 'unknown'} only)"
                for issue in single_model[:5]
            ]
            or ["No single-provider-only findings."],
        ),
        ConsensusSection(
            headline="Coverage",
            details=[
                f"Files with most findings: {', '.join(p for p, _ in by_file.most_common(3)) or 'none'}",
                f"Sampled {len(snapshot.source_files)} of {snapshot.total_files} eligible files.",
            ]
            + [
                f"{result.provider} ({result.role}): {'completed' if result.status == StageStatus.completed else result.error}"
                for result in provider_results
            ],
        ),
        ConsensusSection(
            headline="Positive Signals",
            details=[f"{s}: noted {c} time(s)" for s, c in strengths.most_common(4)]
            or ["No explicit strengths returned."],
        ),
    ]


def _build_next_steps(issues: list[ReviewIssue], snapshot: RepositorySnapshot) -> list[str]:
    if not issues:
        return [
            "No high-confidence findings were surfaced. Consider expanding file coverage.",
            "Add automated linting and type checking to the repository CI pipeline.",
            "Review the static analysis signals manually for any missed context.",
        ]

    steps = [
        f"Address '{issues[0].title}' in {issues[0].file_path} — highest priority finding.",
    ]
    critical_files = list({i.file_path for i in issues if i.severity in ("critical", "high")})[:3]
    if critical_files:
        steps.append(f"Focus security/quality review on: {', '.join(critical_files)}")
    steps.append("Re-run review after fixes to verify resolution and updated confidence scores.")
    return steps
