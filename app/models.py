from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


Severity = Literal["critical", "high", "medium", "low"]
Category = Literal[
    "security",
    "correctness",
    "performance",
    "maintainability",
    "testing",
    "architecture",
]
ProviderName = Literal["openai", "anthropic", "gemini"]


class StageStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    skipped = "skipped"


class ReviewRequest(BaseModel):
    repository_url: str


class ReviewIssue(BaseModel):
    title: str
    severity: Severity
    category: Category
    file_path: str
    line_hint: str = ""
    line_start: int | None = None
    line_end: int | None = None
    cell_number: int | None = None
    summary: str
    recommendation: str
    source_model: ProviderName
    reviewer_role: str = ""
    confidence: float = 0.0
    evidence: str = ""
    detected_by: list[ProviderName] = Field(default_factory=list)


class ProviderResult(BaseModel):
    provider: ProviderName
    role: str
    status: StageStatus
    summary: str = ""
    strengths: list[str] = Field(default_factory=list)
    concerns: list[ReviewIssue] = Field(default_factory=list)
    error: str = ""


class StaticSignal(BaseModel):
    kind: str
    file_path: str
    message: str
    severity: Severity
    line_hint: str = ""


class SourceFile(BaseModel):
    path: str
    content: str
    language: str
    bytes: int
    is_notebook: bool = False
    total_cells: int = 0


class RepositorySnapshot(BaseModel):
    repo_name: str
    repo_url: str
    branch: str
    local_path: str
    total_files: int
    selected_files: list[str]
    file_summaries: list[dict[str, str]]
    source_files: list[SourceFile] = Field(default_factory=list)
    static_signals: list[StaticSignal] = Field(default_factory=list)


class ConsensusSection(BaseModel):
    headline: str
    details: list[str]


class ReviewReport(BaseModel):
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    repo_name: str
    repo_url: str
    branch: str
    executive_summary: str
    risk_score: int
    top_issues: list[ReviewIssue]
    consensus: list[ConsensusSection]
    provider_results: list[ProviderResult]
    static_signals: list[StaticSignal]
    next_steps: list[str]
    providers_attempted: list[ProviderName] = Field(default_factory=list)
    providers_succeeded: list[ProviderName] = Field(default_factory=list)
    providers_failed: list[ProviderName] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Job tracking models (in-memory, no DB)
# ---------------------------------------------------------------------------

class ReviewJobStatus(BaseModel):
    review_id: str
    status: StageStatus = StageStatus.pending
    progress: int = 0  # 0-100
    error: str = ""
    stages: dict[str, StageStatus] = Field(
        default_factory=lambda: {
            "repository": StageStatus.pending,
            "static_analysis": StageStatus.pending,
            "openai": StageStatus.pending,
            "anthropic": StageStatus.pending,
            "gemini": StageStatus.pending,
            "aggregation": StageStatus.pending,
            "report": StageStatus.pending,
        }
    )
    report: ReviewReport | None = None
    repository_url: str = ""
    started_at: datetime | None = None
    completed_at: datetime | None = None


class ReviewStartResponse(BaseModel):
    review_id: str
    status: StageStatus
