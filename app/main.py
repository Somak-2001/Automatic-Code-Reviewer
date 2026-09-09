from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from git import GitCommandError, InvalidGitRepositoryError

from app.config import get_settings
from app.models import (
    ReviewIssue,
    ReviewJobStatus,
    ReviewReport,
    ReviewRequest,
    ReviewStartResponse,
    StageStatus,
)
from app.repo_loader import build_snapshot, cleanup_repository, clone_repository
from app.report_writer import write_report
from app.review_orchestrator import run_multi_model_review
from app.static_analyzer import enrich_with_static_analysis

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(title="Automatic Code Reviewer", version="2.0.0")

settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Accept"],
)

# ---------------------------------------------------------------------------
# In-memory job store (no database required)
# ---------------------------------------------------------------------------

_jobs: dict[str, ReviewJobStatus] = {}
_jobs_lock = asyncio.Lock()


async def _get_job(review_id: str) -> ReviewJobStatus:
    async with _jobs_lock:
        job = _jobs.get(review_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Review '{review_id}' not found.")
    return job


async def _update_job(review_id: str, **kwargs: Any) -> None:
    async with _jobs_lock:
        if review_id in _jobs:
            job = _jobs[review_id]
            for key, value in kwargs.items():
                setattr(job, key, value)


async def _update_stage(review_id: str, stage: str, status: StageStatus) -> None:
    async with _jobs_lock:
        if review_id in _jobs:
            _jobs[review_id].stages[stage] = status
            # Recalculate progress
            stages = _jobs[review_id].stages
            weights = {
                "repository": 15,
                "static_analysis": 10,
                "openai": 20,
                "anthropic": 20,
                "gemini": 20,
                "aggregation": 10,
                "report": 5,
            }
            done_weight = sum(
                w for k, w in weights.items()
                if stages.get(k) in (StageStatus.completed, StageStatus.failed, StageStatus.skipped)
            )
            _jobs[review_id].progress = int(done_weight / sum(weights.values()) * 100)


# ---------------------------------------------------------------------------
# Background review task
# ---------------------------------------------------------------------------

async def _run_review(review_id: str, repository_url: str) -> None:
    settings = get_settings()
    local_path = None

    try:
        await _update_job(review_id, status=StageStatus.running, started_at=datetime.now(timezone.utc))

        # ---- Stage: Repository clone ----
        await _update_stage(review_id, "repository", StageStatus.running)
        try:
            local_path = clone_repository(repository_url, None, settings)
        except GitCommandError as exc:
            msg = str(exc)
            if "not found" in msg.lower() or "repository" in msg.lower():
                raise ValueError(f"Repository could not be cloned. It may be private or the URL is incorrect: {repository_url}")
            raise ValueError(f"Git clone failed: {msg[:400]}")
        except Exception as exc:
            raise ValueError(f"Repository clone failed: {exc}")

        from git import Repo as GitRepo
        try:
            repo = GitRepo(local_path)
            active_branch = repo.active_branch.name
        except Exception:
            active_branch = settings.default_branch

        snapshot = build_snapshot(repository_url, local_path, active_branch, settings)
        if not snapshot.source_files:
            raise ValueError(
                f"No analyzable source files found in repository '{snapshot.repo_name}'. "
                "The repository may be empty, use unsupported languages, or all files may be in excluded directories."
            )
        await _update_stage(review_id, "repository", StageStatus.completed)

        # ---- Stage: Static analysis ----
        await _update_stage(review_id, "static_analysis", StageStatus.running)
        snapshot = enrich_with_static_analysis(snapshot)
        await _update_stage(review_id, "static_analysis", StageStatus.completed)

        # ---- Mark unconfigured providers as skipped up front ----
        available = settings.available_providers()
        for provider in ("openai", "anthropic", "gemini"):
            if provider not in available:
                await _update_stage(review_id, provider, StageStatus.skipped)

        if not available:
            raise ValueError(
                "No LLM providers are configured. "
                "Set at least one of OPENAI_API_KEY, ANTHROPIC_API_KEY, or GEMINI_API_KEY in your .env file."
            )

        # ---- Stage: LLM reviews (orchestrator manages stage callbacks) ----
        async def stage_cb(stage: str, status: StageStatus) -> None:
            await _update_stage(review_id, stage, status)

        report = await run_multi_model_review(snapshot, settings, stage_cb)

        # ---- Stage: Write report ----
        await _update_stage(review_id, "report", StageStatus.running)
        write_report(review_id, report, settings.reports_dir)
        await _update_stage(review_id, "report", StageStatus.completed)

        await _update_job(
            review_id,
            status=StageStatus.completed,
            progress=100,
            report=report,
            completed_at=datetime.now(timezone.utc),
        )

    except Exception as exc:
        error_message = str(exc)
        await _update_job(
            review_id,
            status=StageStatus.failed,
            error=error_message,
            completed_at=datetime.now(timezone.utc),
        )
    finally:
        if local_path is not None:
            cleanup_repository(local_path)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": "2.0.0"}


@app.get("/api/config")
async def api_config() -> dict[str, Any]:
    """Return non-sensitive configuration visible to the frontend."""
    s = get_settings()
    return {
        "providers_configured": s.available_providers(),
        "models": {
            "openai": s.openai_model if s.openai_api_key else None,
            "anthropic": s.anthropic_model if s.anthropic_api_key else None,
            "gemini": s.gemini_model if s.gemini_api_key else None,
        },
        "limits": {
            "max_files": s.max_files,
            "max_file_bytes": s.max_file_bytes,
        },
    }


@app.post("/api/reviews", response_model=ReviewStartResponse, status_code=202)
async def start_review(request: ReviewRequest, background_tasks: BackgroundTasks) -> ReviewStartResponse:
    """Start an async review job. Returns a review_id to poll for status."""
    # Basic URL validation
    url = request.repository_url.strip()
    if not url:
        raise HTTPException(status_code=422, detail="repository_url is required.")
    if not (url.startswith("https://github.com/") or url.startswith("http://github.com/")):
        raise HTTPException(
            status_code=422,
            detail="Only public GitHub URLs (https://github.com/...) are supported.",
        )

    settings = get_settings()
    if not settings.available_providers():
        raise HTTPException(
            status_code=503,
            detail=(
                "No LLM providers are configured on the server. "
                "The server administrator must set at least one of: "
                "OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY."
            ),
        )

    review_id = uuid.uuid4().hex[:12]
    job = ReviewJobStatus(
        review_id=review_id,
        repository_url=url,
        status=StageStatus.pending,
    )
    async with _jobs_lock:
        _jobs[review_id] = job

    background_tasks.add_task(_run_review, review_id, url)

    return ReviewStartResponse(review_id=review_id, status=StageStatus.pending)


@app.get("/api/reviews/{review_id}")
async def get_review_status(review_id: str) -> dict[str, Any]:
    """Poll for review job status and stage breakdown."""
    job = await _get_job(review_id)
    return {
        "review_id": job.review_id,
        "status": job.status.value,
        "progress": job.progress,
        "error": job.error,
        "stages": {k: v.value for k, v in job.stages.items()},
        "repository_url": job.repository_url,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    }


@app.get("/api/reviews/{review_id}/report")
async def get_review_report(review_id: str) -> dict[str, Any]:
    """Return the full structured report. Only available when status=completed."""
    job = await _get_job(review_id)

    if job.status == StageStatus.failed:
        raise HTTPException(
            status_code=422,
            detail={"error": "Review failed.", "message": job.error},
        )
    if job.status != StageStatus.completed or job.report is None:
        raise HTTPException(
            status_code=409,
            detail=f"Report not ready yet. Current status: {job.status.value}",
        )

    report = job.report
    return {
        "review_id": review_id,
        "report": {
            "generated_at": report.generated_at.isoformat(),
            "repo_name": report.repo_name,
            "repo_url": report.repo_url,
            "branch": report.branch,
            "executive_summary": report.executive_summary,
            "risk_score": report.risk_score,
            "providers_attempted": report.providers_attempted,
            "providers_succeeded": report.providers_succeeded,
            "providers_failed": report.providers_failed,
            "top_issues": [_serialize_issue(i) for i in report.top_issues],
            "consensus": [
                {"headline": c.headline, "details": c.details}
                for c in report.consensus
            ],
            "provider_results": [
                {
                    "provider": r.provider,
                    "role": r.role,
                    "status": r.status.value,
                    "summary": r.summary,
                    "strengths": r.strengths,
                    "error": r.error,
                    "issues_count": len(r.concerns),
                }
                for r in report.provider_results
            ],
            "static_signals": [
                {
                    "kind": s.kind,
                    "file_path": s.file_path,
                    "message": s.message,
                    "severity": s.severity,
                    "line_hint": s.line_hint,
                }
                for s in report.static_signals
            ],
            "next_steps": report.next_steps,
        },
    }


def _serialize_issue(issue: ReviewIssue) -> dict[str, Any]:
    return {
        "title": issue.title,
        "severity": issue.severity,
        "category": issue.category,
        "file_path": issue.file_path,
        "line_hint": issue.line_hint,
        "line_start": issue.line_start,
        "line_end": issue.line_end,
        "cell_number": issue.cell_number,
        "summary": issue.summary,
        "recommendation": issue.recommendation,
        "source_model": issue.source_model,
        "reviewer_role": issue.reviewer_role,
        "confidence": issue.confidence,
        "evidence": issue.evidence,
        "detected_by": issue.detected_by,
    }


# ---------------------------------------------------------------------------
# Legacy endpoints (kept for compatibility, redirect to new API)
# ---------------------------------------------------------------------------

@app.get("/")
async def root() -> dict[str, str]:
    return {
        "message": "Automatic Code Reviewer API v2.0",
        "docs": "/docs",
        "health": "/health",
        "start_review": "POST /api/reviews",
    }
