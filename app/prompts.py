from __future__ import annotations

from app.models import SourceFile, StaticSignal

SYSTEM_PROMPT = """
You are a precise senior code reviewer.
Analyze only the provided file and repository context.
Every finding must be grounded in the supplied code.
Do not invent files, tests, architectures, or vulnerabilities.
If the evidence is weak, return empty arrays.
Return strict JSON only.
""".strip()

ROLE_PROMPTS = {
    "security": """
You are a SECURITY expert.
Analyze ONLY the given code file for vulnerabilities such as injection risks, unsafe input handling, auth mistakes, insecure deserialization, or secret exposure.
Avoid generic secure-coding advice.
Prefer empty arrays over weak claims.
""".strip(),
    "performance": """
You are a PERFORMANCE expert.
Analyze ONLY the given code file for concrete inefficiencies such as repeated heavy work in loops, redundant parsing, avoidable synchronous I/O, N+1 behavior, or unnecessary memory growth.
Do not report style issues.
Prefer empty arrays over vague optimization advice.
""".strip(),
    "maintainability": """
You are a MAINTAINABILITY expert.
Analyze ONLY the given code file for concrete readability, structure, naming, or complexity problems that are visible in the code.
Do not invent missing modules or tests.
Prefer empty arrays over generic comments.
""".strip(),
}


def build_review_prompt(role: str, source_file: SourceFile, static_signals: list[StaticSignal], repo_name: str) -> str:
    signal_lines = [
        f"- {signal.file_path} {signal.line_hint}: {signal.message}"
        for signal in static_signals
        if signal.file_path == source_file.path
    ]
    signals_text = "\n".join(signal_lines) if signal_lines else "- none"

    return f"""
{ROLE_PROMPTS[role]}

Repository: {repo_name}
File path: {source_file.path}
Language: {source_file.language}
Static signals for this file:
{signals_text}

Return STRICT JSON with this exact shape:
{{
  "summary": "one short paragraph tied to this file only",
  "strengths": ["..."],
  "bugs": [
    {{
      "title": "...",
      "severity": "critical|high|medium|low",
      "category": "security|correctness|performance|maintainability|testing|architecture",
      "line_hint": "L12 or function name",
      "summary": "...",
      "recommendation": "...",
      "evidence": "short code-grounded reason"
    }}
  ],
  "security": [],
  "performance": [],
  "readability": []
}}

Rules:
- Ground every finding in the provided file content.
- Do not mention files you cannot see.
- If this is a mature or well-structured file, prefer design observations or return empty arrays.
- Avoid fake critical issues for well-known production repositories.

Code to analyze:
```{source_file.language}
{source_file.content}
```
""".strip()
