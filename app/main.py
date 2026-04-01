from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from git import Repo

from app.config import get_settings
from app.models import ReviewRequest, ReviewResponse
from app.repo_loader import build_snapshot, cleanup_repository, clone_repository
from app.report_writer import write_report
from app.review_orchestrator import run_multi_model_review
from app.static_analyzer import enrich_with_static_analysis

app = FastAPI(title="Automatic Code Reviewer", version="1.0.0")


@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    html_path = Path(__file__).parent / "templates" / "index.html"
    return html_path.read_text(encoding="utf-8")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/review", response_model=ReviewResponse)
async def review_repository(request: ReviewRequest) -> ReviewResponse:
    settings = get_settings()
    local_path = None
    branch = request.branch or settings.default_branch

    try:
        local_path = clone_repository(str(request.repo_url), request.branch, settings)
        repo = Repo(local_path)
        active_branch = request.branch or repo.active_branch.name
        snapshot = build_snapshot(str(request.repo_url), local_path, active_branch, settings)
        snapshot = enrich_with_static_analysis(snapshot)
        report = await run_multi_model_review(snapshot, settings, request.use_mock_fallback)
        report_id = uuid.uuid4().hex[:10]
        markdown_path, json_path = write_report(report_id, report, settings.reports_dir)
        return ReviewResponse(
            report_id=report_id,
            report=report,
            markdown_path=str(markdown_path),
            json_path=str(json_path),
        )
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        if local_path is not None:
            cleanup_repository(local_path)
