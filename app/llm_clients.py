from __future__ import annotations

import json
from typing import Any

import httpx

from app.models import ProviderResult, RepositorySnapshot, ReviewIssue, SourceFile, StageStatus
from app.prompts import SYSTEM_PROMPT, build_review_prompt


class ProviderError(Exception):
    """Raised when an LLM provider call fails for any reason."""

    def __init__(self, provider: str, message: str) -> None:
        self.provider = provider
        self.message = message
        super().__init__(f"{provider}: {message}")


class BaseReviewer:
    provider: str = ""

    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    def is_available(self) -> bool:
        return bool(self.api_key)

    async def review_file(
        self, role: str, source_file: SourceFile, snapshot: RepositorySnapshot
    ) -> ProviderResult:
        raise NotImplementedError


class OpenAIReviewer(BaseReviewer):
    provider = "openai"

    async def review_file(
        self, role: str, source_file: SourceFile, snapshot: RepositorySnapshot
    ) -> ProviderResult:
        if not self.is_available():
            raise ProviderError("openai", "API key not configured")

        prompt = build_review_prompt(role, source_file, snapshot.static_signals, snapshot.repo_name)
        payload = {
            "model": self.model,
            "input": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            async with httpx.AsyncClient(timeout=90) as client:
                response = await client.post(
                    "https://api.openai.com/v1/responses",
                    headers=headers,
                    json=payload,
                )
                if response.status_code == 401:
                    raise ProviderError("openai", "API authentication error (401). Check your OPENAI_API_KEY.")
                if response.status_code == 429:
                    raise ProviderError("openai", "Rate limit exceeded (429). Please wait and retry.")
                if response.status_code >= 400:
                    raise ProviderError("openai", f"API error {response.status_code}: {response.text[:300]}")
                data = response.json()
        except httpx.TimeoutException:
            raise ProviderError("openai", "Request timed out after 90 seconds.")
        except httpx.RequestError as exc:
            raise ProviderError("openai", f"Network error: {exc}")

        text = _extract_openai_text(data)
        if not text:
            raise ProviderError("openai", "Empty response received from API.")
        return _parse_provider_result("openai", role, source_file.path, text)


class AnthropicReviewer(BaseReviewer):
    provider = "anthropic"

    async def review_file(
        self, role: str, source_file: SourceFile, snapshot: RepositorySnapshot
    ) -> ProviderResult:
        if not self.is_available():
            raise ProviderError("anthropic", "API key not configured")

        prompt = build_review_prompt(role, source_file, snapshot.static_signals, snapshot.repo_name)
        payload = {
            "model": self.model,
            "system": SYSTEM_PROMPT,
            "max_tokens": 2048,
            "messages": [{"role": "user", "content": prompt}],
        }
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }
        try:
            async with httpx.AsyncClient(timeout=90) as client:
                response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers=headers,
                    json=payload,
                )
                if response.status_code == 401:
                    raise ProviderError("anthropic", "API authentication error (401). Check your ANTHROPIC_API_KEY.")
                if response.status_code == 429:
                    raise ProviderError("anthropic", "Rate limit exceeded (429). Please wait and retry.")
                if response.status_code >= 400:
                    raise ProviderError("anthropic", f"API error {response.status_code}: {response.text[:300]}")
                data = response.json()
        except httpx.TimeoutException:
            raise ProviderError("anthropic", "Request timed out after 90 seconds.")
        except httpx.RequestError as exc:
            raise ProviderError("anthropic", f"Network error: {exc}")

        text = "\n".join(block.get("text", "") for block in data.get("content", []))
        if not text.strip():
            raise ProviderError("anthropic", "Empty response received from API.")
        return _parse_provider_result("anthropic", role, source_file.path, text)


class GeminiReviewer(BaseReviewer):
    provider = "gemini"

    async def review_file(
        self, role: str, source_file: SourceFile, snapshot: RepositorySnapshot
    ) -> ProviderResult:
        if not self.is_available():
            raise ProviderError("gemini", "API key not configured")

        prompt = build_review_prompt(role, source_file, snapshot.static_signals, snapshot.repo_name)
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent?key={self.api_key}"
        )
        payload = {
            "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": [{"parts": [{"text": prompt}]}],
        }
        try:
            async with httpx.AsyncClient(timeout=90) as client:
                response = await client.post(url, json=payload)
                if response.status_code == 400:
                    raise ProviderError("gemini", f"Bad request (400): {response.text[:300]}")
                if response.status_code == 401 or response.status_code == 403:
                    raise ProviderError("gemini", f"API authentication error ({response.status_code}). Check your GEMINI_API_KEY.")
                if response.status_code == 429:
                    raise ProviderError("gemini", "Rate limit exceeded (429). Please wait and retry.")
                if response.status_code >= 400:
                    raise ProviderError("gemini", f"API error {response.status_code}: {response.text[:300]}")
                data = response.json()
        except httpx.TimeoutException:
            raise ProviderError("gemini", "Request timed out after 90 seconds.")
        except httpx.RequestError as exc:
            raise ProviderError("gemini", f"Network error: {exc}")

        try:
            text = data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as exc:
            raise ProviderError("gemini", f"Unexpected response structure: {exc}. Response: {str(data)[:300]}")
        if not text.strip():
            raise ProviderError("gemini", "Empty response received from API.")
        return _parse_provider_result("gemini", role, source_file.path, text)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _extract_openai_text(data: dict[str, Any]) -> str:
    output = data.get("output", [])
    for item in output:
        for content in item.get("content", []):
            if content.get("type") == "output_text":
                return content.get("text", "")
    return ""


def _parse_provider_result(provider: str, role: str, file_path: str, text: str) -> ProviderResult:
    parsed = _safe_json_loads(text)
    if parsed is None:
        # JSON parse failed — treat as provider error with partial data
        return ProviderResult(
            provider=provider,
            role=role,
            status=StageStatus.failed,
            error=f"Failed to parse JSON response. Raw excerpt: {text[:200]}",
        )

    concerns: list[ReviewIssue] = []
    for section in ("bugs", "security", "performance", "readability"):
        for concern in parsed.get(section, []):
            try:
                severity = concern.get("severity", "low")
                if severity not in ("critical", "high", "medium", "low"):
                    severity = "low"
                category = _normalize_category(concern.get("category"), role, section)
                line_start = concern.get("line_start") or concern.get("line_number")
                line_end = concern.get("line_end")
                line_hint_str = str(concern.get("line_hint", ""))

                raw_cell = concern.get("cell_number")
                cell_number: int | None = None
                if raw_cell is not None:
                    try:
                        cell_number = int(raw_cell)
                    except (ValueError, TypeError):
                        pass
                if cell_number is None and line_hint_str:
                    import re
                    match = re.search(r"\bCell\s*[:#]?\s*(\d+)\b", line_hint_str, re.IGNORECASE)
                    if match:
                        try:
                            cell_number = int(match.group(1))
                        except ValueError:
                            pass

                concerns.append(
                    ReviewIssue(
                        title=concern.get("title", "Unnamed issue"),
                        severity=severity,
                        category=category,
                        file_path=file_path,
                        line_hint=line_hint_str,
                        line_start=int(line_start) if line_start else None,
                        line_end=int(line_end) if line_end else None,
                        cell_number=cell_number,
                        summary=concern.get("summary", concern.get("description", "")),
                        recommendation=concern.get("recommendation", ""),
                        source_model=provider,
                        reviewer_role=role,
                        evidence=concern.get("evidence", ""),
                        detected_by=[provider],
                    )
                )
            except Exception:
                continue  # Skip malformed individual findings, don't fail entire file

    return ProviderResult(
        provider=provider,
        role=role,
        status=StageStatus.completed,
        summary=parsed.get("summary", ""),
        strengths=parsed.get("strengths", []),
        concerns=concerns,
    )


def _safe_json_loads(text: str) -> dict[str, Any] | None:
    stripped = text.strip()
    # Strip markdown code fences if present
    if stripped.startswith("```"):
        lines = stripped.split("\n")
        # Remove first and last fence lines
        inner = lines[1:] if lines[0].startswith("```") else lines
        if inner and inner[-1].strip() == "```":
            inner = inner[:-1]
        stripped = "\n".join(inner)
    try:
        return json.loads(stripped or "{}")
    except json.JSONDecodeError:
        # Try to find JSON object within the text
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start != -1 and end != -1:
            try:
                return json.loads(stripped[start : end + 1])
            except json.JSONDecodeError:
                pass
        return None


ROLE_CATEGORIES: dict[str, tuple[str, str]] = {
    "security": ("security", "correctness"),
    "performance": ("performance", "architecture"),
    "maintainability": ("maintainability", "architecture"),
}

_VALID_CATEGORIES = {"security", "correctness", "performance", "maintainability", "testing", "architecture"}


def _normalize_category(category: str | None, role: str, section: str) -> str:
    if category in _VALID_CATEGORIES:
        return category
    fallback = {
        "security": "security",
        "performance": "performance",
        "readability": "maintainability",
        "bugs": ROLE_CATEGORIES.get(role, ("correctness", "correctness"))[0],
    }
    return fallback.get(section, ROLE_CATEGORIES.get(role, ("correctness", "correctness"))[0])
