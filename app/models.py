from __future__ import annotations

from datetime import datetime, timezone
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
ProviderName = Literal["openai", "anthropic", "gemini", "mock"]


class ReviewRequest(BaseModel):
    repo_url: HttpUrl
    branch: str | None = None
    use_mock_fallback: bool = True


class ReviewIssue(BaseModel):
    title: str
    severity: Severity
    category: Category
    file_path: str
    line_hint: str = ""
    summary: str
    recommendation: str
    source_model: ProviderName
    reviewer_role: str = ""
    confidence: float = 0.0
    evidence: str = ""


class ModelReview(BaseModel):
    provider: ProviderName
    role: str
    summary: str
    strengths: list[str] = Field(default_factory=list)
    concerns: list[ReviewIssue] = Field(default_factory=list)
    raw_excerpt: str = ""


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
    model_reviews: list[ModelReview]
    static_signals: list[StaticSignal]
    next_steps: list[str]


class ReviewResponse(BaseModel):
    report_id: str
    report: ReviewReport
    markdown_path: str
    json_path: str
