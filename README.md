# Automatic Code Reviewer

An intelligent multi-LLM code review system that accepts a GitHub repository URL, analyzes the repository, gathers feedback from multiple model perspectives, and produces a structured review report with actionable engineering recommendations.

## Quick start

### Run the Streamlit dashboard

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py
```

Open `http://localhost:8501`

If that URL does not work, try `http://127.0.0.1:8501`.

### Run the FastAPI backend

```bash
source .venv/bin/activate
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`

## Why this stands out

- Uses multiple LLM families instead of relying on a single model opinion.
- Assigns each model a specialized reviewer role: security, architecture, and testing/performance.
- Adds lightweight static analysis signals to ground the final report.
- Merges all findings into a single executive summary, risk score, issue list, and next-step plan.
- Includes a mock fallback mode so the project is always demoable during a hackathon.

## System architecture

1. Repository ingestion
   - Clones a GitHub repository into a temporary workspace.
   - Samples high-signal source and config files while skipping heavy folders like `node_modules` and `dist`.

2. Static analysis
   - Looks for risky strings such as secrets, dangerous APIs, and missing tests.
   - Produces supporting evidence that can be shown alongside LLM findings.

3. Multi-model review
   - `OpenAI` reviewer acts as a security-focused senior engineer.
   - `Anthropic` reviewer acts as an architecture and maintainability reviewer.
   - `Gemini` reviewer acts as a testing and performance reviewer.
   - All reviewers are asked to return structured JSON for predictable downstream parsing.

4. Consensus engine
   - Deduplicates overlapping issues.
   - Prioritizes findings by severity.
   - Computes a repository risk score.
   - Produces shared-risk and positive-signal sections.

5. Report generation
   - Exposes a simple web interface and API endpoint.
   - Saves both Markdown and JSON reports in `reports/`.

## Tech stack

- FastAPI for the backend API
- Streamlit for the analytics dashboard UI
- Plotly for interactive charts and gauges
- Pandas for report shaping and dashboard tables
- GitPython for cloning repositories
- HTTPX for external LLM API calls
- Pydantic for strongly typed request/response models

## Project structure

```text
.
|-- app
|   |-- config.py
|   |-- llm_clients.py
|   |-- main.py
|   |-- models.py
|   |-- prompts.py
|   |-- repo_loader.py
|   |-- report_writer.py
|   |-- review_orchestrator.py
|   |-- static_analyzer.py
|   `-- templates
|       `-- index.html
|-- streamlit_app.py
|-- requirements.txt
|-- .env.example
`-- README.md
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
```

## Run the apps

### Streamlit dashboard

```bash
source .venv/bin/activate
python -m streamlit run streamlit_app.py
```

Open `http://localhost:8501`

If `localhost:8501` does not work, try `http://127.0.0.1:8501`.

Use `python -m streamlit` instead of `streamlit` directly to avoid PATH issues such as `command not found`.

### FastAPI backend

```bash
source .venv/bin/activate
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`

### Running both together

Use two terminals:

1. Start the backend with `uvicorn app.main:app --reload`
2. Start the dashboard with `python -m streamlit run streamlit_app.py`

URLs:

- Streamlit dashboard: `http://localhost:8501`
- FastAPI backend: `http://127.0.0.1:8000`

## Environment variables

- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `GEMINI_API_KEY`
- `DEFAULT_BRANCH`
- `MAX_FILES`
- `MAX_FILE_BYTES`
- `REPORTS_DIR`
- `TEMP_DIR`

If API keys are not provided, the system can still run in mock mode for demo purposes. The Streamlit dashboard currently uses mock data for presentation, so it is safe to demo without live model credentials.

## API usage

### `POST /review`

Request:

```json
{
  "repo_url": "https://github.com/owner/repo",
  "branch": "main",
  "use_mock_fallback": true
}
```

Response:

```json
{
  "report_id": "7aa21d4562",
  "report": {
    "repo_name": "repo",
    "repo_url": "https://github.com/owner/repo",
    "branch": "main",
    "executive_summary": "Multi-model review found...",
    "risk_score": 76
  },
  "markdown_path": "reports/7aa21d4562.md",
  "json_path": "reports/7aa21d4562.json"
}
```

## Dashboard features

- Wide SaaS-style dashboard layout
- Sidebar navigation for `Dashboard`, `Reports`, `Integrations`, and `Settings`
- GitHub repository and branch input controls
- Multi-model selection across `GPT-4`, `Claude`, `Gemini`, and `Llama`
- Review progress indicator with staged status updates
- Stats cards for repository health, issue totals, and risk score
- Plotly charts for issue breakdown by model and issue-type distribution
- Tabbed reporting views for summary, file-level issues, performance, security, and consensus
- Right-side highlight panels for top risks and reviewer agreement

## Demo pitch

“Traditional automated code review tools either rely on static rules or one model opinion. Our system combines multiple LLM families with specialized reviewer roles and then synthesizes them into a single, structured engineering report. This reduces blind spots, improves confidence, and produces feedback that is far more actionable for real developer workflows.”

## Suggested live demo flow

1. Start the Streamlit dashboard.
2. Optionally start the FastAPI backend in a second terminal.
3. Paste a public GitHub repository URL into the dashboard input.
4. Run the review and walk through the stats cards, charts, and report tabs.
5. Show the generated JSON response and the saved Markdown report in `reports/` if the backend is connected.
6. Highlight the mock fallback and mock dashboard data as reliable demo-safe modes.

## Future improvements

- Add PR-diff review instead of full repository sampling.
- Add embeddings or graph-based file selection for better context packing.
- Add confidence scoring and reviewer disagreement analysis.
- Support inline code annotations and GitHub pull request comments.
- Add benchmark datasets to evaluate review quality against human reviewers.
