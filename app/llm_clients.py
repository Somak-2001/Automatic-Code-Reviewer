from __future__ import annotations

import json
from typing import Any

import httpx

from app.models import ModelReview, RepositorySnapshot, ReviewIssue, SourceFile
from app.prompts import SYSTEM_PROMPT, build_review_prompt

ROLE_CATEGORIES = {
    "security": ("security", "correctness"),
    "performance": ("performance", "architecture"),
    "maintainability": ("maintainability", "architecture"),
}


class BaseReviewer:
    provider = "mock"

    def __init__(self, api_key: str = "") -> None:
        self.api_key = api_key

    def is_available(self) -> bool:
        return bool(self.api_key)

    async def review_file(self, role: str, source_file: SourceFile, snapshot: RepositorySnapshot) -> ModelReview:
        raise NotImplementedError


class MockReviewer(BaseReviewer):
    provider = "mock"

    async def review_file(self, role: str, source_file: SourceFile, snapshot: RepositorySnapshot) -> ModelReview:
        summary = {
            "security": (
                f"Security review for {source_file.path}: no obvious high-confidence vulnerability is visible "
                "in the sampled code without runtime context."
            ),
            "performance": (
                f"Performance review for {source_file.path}: the file appears structurally reasonable, "
                "so only code-local trade-offs should be surfaced."
            ),
            "maintainability": (
                f"Maintainability review for {source_file.path}: feedback should stay close to naming, "
                "branching, and file structure visible in this file."
            ),
        }[role]
        strengths = {
            "security": ["The file can be reviewed with direct code grounding instead of repo-level guesses."],
            "performance": ["The logic appears scoped enough for file-level performance reasoning."],
            "maintainability": ["The review flow can attribute findings to a specific file and line hint."],
        }[role]
        concerns = _mock_concerns_for_role(role, source_file)
        return ModelReview(
            provider="mock",
            role=role,
            summary=summary,
            strengths=strengths,
            concerns=concerns,
            raw_excerpt="Generated in grounded mock mode.",
        )


class OpenAIReviewer(BaseReviewer):
    provider = "openai"
    model = "gpt-4.1-mini"

    async def review_file(self, role: str, source_file: SourceFile, snapshot: RepositorySnapshot) -> ModelReview:
        prompt = build_review_prompt(role, source_file, snapshot.static_signals, snapshot.repo_name)
        payload = {
            "model": self.model,
            "input": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                "https://api.openai.com/v1/responses",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
        text = _extract_openai_text(data)
        return _parse_model_review("openai", role, source_file.path, text)


class AnthropicReviewer(BaseReviewer):
    provider = "anthropic"
    model = "claude-3-5-sonnet-latest"

    async def review_file(self, role: str, source_file: SourceFile, snapshot: RepositorySnapshot) -> ModelReview:
        prompt = build_review_prompt(role, source_file, snapshot.static_signals, snapshot.repo_name)
        payload = {
            "model": self.model,
            "system": SYSTEM_PROMPT,
            "max_tokens": 1800,
            "messages": [{"role": "user", "content": prompt}],
        }
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
        text = "\n".join(block.get("text", "") for block in data.get("content", []))
        return _parse_model_review("anthropic", role, source_file.path, text)


class GeminiReviewer(BaseReviewer):
    provider = "gemini"
    model = "gemini-1.5-pro"

    async def review_file(self, role: str, source_file: SourceFile, snapshot: RepositorySnapshot) -> ModelReview:
        prompt = build_review_prompt(role, source_file, snapshot.static_signals, snapshot.repo_name)
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent?key={self.api_key}"
        )
        payload = {
            "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": [{"parts": [{"text": prompt}]}],
        }
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        return _parse_model_review("gemini", role, source_file.path, text)


def _extract_openai_text(data: dict[str, Any]) -> str:
    output = data.get("output", [])
    for item in output:
        for content in item.get("content", []):
            if content.get("type") == "output_text":
                return content.get("text", "")
    return ""


def _parse_model_review(provider: str, role: str, file_path: str, text: str) -> ModelReview:
    parsed = _safe_json_loads(text)
    concerns: list[ReviewIssue] = []
    for section in ("bugs", "security", "performance", "readability"):
        for concern in parsed.get(section, []):
            concerns.append(
                ReviewIssue(
                    title=concern["title"],
                    severity=concern["severity"],
                    category=_normalize_category(concern.get("category"), role, section),
                    file_path=file_path,
                    line_hint=concern.get("line_hint", ""),
                    summary=concern["summary"],
                    recommendation=concern["recommendation"],
                    source_model=provider,
                    reviewer_role=role,
                    evidence=concern.get("evidence", ""),
                )
            )
    return ModelReview(
        provider=provider,
        role=role,
        summary=parsed.get("summary", ""),
        strengths=parsed.get("strengths", []),
        concerns=concerns,
        raw_excerpt=text[:500],
    )


def _safe_json_loads(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        stripped = stripped.replace("json\n", "", 1)
    return json.loads(stripped or "{}")


def _normalize_category(category: str | None, role: str, section: str) -> str:
    valid_categories = {"security", "correctness", "performance", "maintainability", "testing", "architecture"}
    if category in valid_categories:
        return category
    fallback = {
        "security": "security",
        "performance": "performance",
        "readability": "maintainability",
        "bugs": ROLE_CATEGORIES[role][0],
    }
    return fallback.get(section, ROLE_CATEGORIES[role][0])


def _mock_concerns_for_role(role: str, source_file: SourceFile) -> list[ReviewIssue]:
    content = source_file.content
    concerns: list[ReviewIssue] = []

    if role == "security" and any(marker in content for marker in ("eval(", "exec(", "innerHTML =")):
        concerns.append(
            ReviewIssue(
                title="Dynamic code or HTML execution path deserves verification",
                severity="medium",
                category="security",
                file_path=source_file.path,
                line_hint="local dynamic execution usage",
                summary="This file appears to use a dynamic execution or HTML sink, which can become unsafe if it receives untrusted input.",
                recommendation="Confirm the input source and add validation or safer APIs where user-controlled data can reach the sink.",
                source_model="mock",
                reviewer_role=role,
                evidence="Detected a dynamic execution or DOM sink marker in the file.",
            )
        )

    if role == "performance" and ("for " in content or ".map(" in content or ".filter(" in content):
        concerns.append(
            ReviewIssue(
                title="Iteration-heavy paths should be checked for repeated work",
                severity="low",
                category="performance",
                file_path=source_file.path,
                line_hint="loop-heavy section",
                summary="The file contains iteration constructs that may hide repeated parsing, lookup, or allocation work in hot paths.",
                recommendation="Inspect whether expensive work inside loops can be hoisted, cached, or short-circuited.",
                source_model="mock",
                reviewer_role=role,
                evidence="Detected loop or collection traversal constructs in the file.",
            )
        )

    if role == "maintainability" and len(content.splitlines()) > 220:
        concerns.append(
            ReviewIssue(
                title="Large file may be harder to review and evolve safely",
                severity="low",
                category="maintainability",
                file_path=source_file.path,
                line_hint="file scope",
                summary="This file is long enough that responsibilities may be blending together, which raises review and change risk.",
                recommendation="Consider extracting distinct responsibilities or helper units if the file keeps growing.",
                source_model="mock",
                reviewer_role=role,
                evidence="The sampled file length is comparatively large.",
            )
        )

    return concerns
