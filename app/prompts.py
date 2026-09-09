from __future__ import annotations

from app.models import SourceFile, StaticSignal

SYSTEM_PROMPT = """
You are a precise senior code reviewer.
Analyze ONLY the provided file and repository context.
Every finding must be grounded in the supplied code.
Do not invent files, tests, architectures, or vulnerabilities that are not visible in the code.
If evidence is weak or non-existent, return empty arrays.
Return strict JSON only — no prose before or after the JSON.
""".strip()

ROLE_PROMPTS = {
    "security": """
You are a SECURITY expert.
Analyze ONLY the given code file for vulnerabilities such as injection risks, unsafe input handling,
authentication mistakes, insecure deserialization, secret exposure, or authorization bypasses.
Avoid generic secure-coding advice not grounded in this file.
Prefer empty arrays over weak or speculative claims.
""".strip(),
    "performance": """
You are a PERFORMANCE expert.
Analyze ONLY the given code file for concrete inefficiencies such as repeated heavy work in loops,
redundant parsing, avoidable synchronous I/O, N+1 behavior, unnecessary memory growth, unoptimized PyTorch/GPU tensor allocations, or blocking calls.
Do not report style issues.
Prefer empty arrays over vague optimization advice.
""".strip(),
    "maintainability": """
You are a MAINTAINABILITY and CODE QUALITY expert.
Analyze ONLY the given code file for concrete readability, structure, naming, complexity, or architecture
problems that are visible in the code.
Also look for logical bugs, incorrect error handling, PyTorch training loop pitfalls, and missing edge-case handling.
Do not invent missing modules or tests.
Prefer empty arrays over generic comments.
""".strip(),
}


def build_review_prompt(
    role: str,
    source_file: SourceFile,
    static_signals: list[StaticSignal],
    repo_name: str,
) -> str:
    signal_lines = [
        f"- {signal.file_path} {signal.line_hint}: {signal.message}"
        for signal in static_signals
        if signal.file_path == source_file.path
    ]
    signals_text = "\n".join(signal_lines) if signal_lines else "- none"

    notebook_note = ""
    if source_file.is_notebook or source_file.path.endswith(".ipynb"):
        notebook_note = """
NOTEBOOK SPECIAL INSTRUCTIONS:
- This file is a Jupyter Notebook (.ipynb). Executable code cells are demarcated by `# [Cell <N>: Code]`.
- In your findings, specify the exact cell number in "cell_number" (e.g. 2, 7) and "line_hint" (e.g. "Cell 2" or "Cell 2:L15").
- Quote the exact code snippet from that cell in "evidence".
"""

    return f"""
{ROLE_PROMPTS[role]}

Repository: {repo_name}
File path: {source_file.path}
Language: {source_file.language}
Static signals for this file:
{signals_text}
{notebook_note}

Return STRICT JSON with EXACTLY this shape (no text outside the JSON):
{{
  "summary": "one short paragraph tied to this file only",
  "strengths": ["..."],
  "bugs": [
    {{
      "title": "...",
      "severity": "critical|high|medium|low",
      "category": "security|correctness|performance|maintainability|testing|architecture",
      "line_hint": "L12 or Cell 3",
      "line_start": 12,
      "line_end": 15,
      "cell_number": null,
      "summary": "...",
      "recommendation": "...",
      "evidence": "short code-grounded reason quoting the exact code"
    }}
  ],
  "security": [],
  "performance": [],
  "readability": []
}}

Rules:
- Ground EVERY finding in the provided file content. Quote the relevant code in evidence.
- Do not mention files you cannot see.
- line_start and line_end must be actual integers if you can identify them; omit (null) if not.
- cell_number should be an integer (e.g. 1, 2, 3) if the issue is inside a notebook cell; otherwise null.
- If this is a mature or well-structured file, prefer design observations or return empty arrays.
- Do NOT return findings you are not confident about.

Code to analyze:
```{source_file.language}
{source_file.content}
```
""".strip()
