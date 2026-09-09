# CodeReview AI

**CodeReview AI** is a production-grade, multi-LLM automated code review system. Given a public GitHub repository URL, the platform clones the repository, classifies source assets, strips heavy binary/media files, extracts pure executable code from source files and Jupyter Notebooks (`.ipynb`), runs static analysis, and dispatches files to specialized AI models. It aggregates findings into a unified, consensus-ranked report featuring line/cell citations, grounded code evidence, severity scoring, and actionable remediation steps—presented through a dark-mode React interface.

---

## Features

- **Public GitHub Ingestion**: Shallow-clones public repositories on demand with automatic branch detection and temporary workspace isolation.
- **First-Class Jupyter Notebook Support**: Safely parses `.ipynb` JSON, extracts executable code cells while discarding bulky outputs, charts, and base64 payloads, and preserves cell numbering for pinpoint reviews.
- **Intelligent File Classification**: Distinguishes source code, notebooks, configuration, and documentation from binary assets, media files, and build artifacts.
- **Multi-LLM Architecture**: Pluggable reviewer architecture supporting Google Gemini, OpenAI, and Anthropic with role-based review assignments (Security, Maintainability, Performance).
- **Consensus & Confidence Scoring**: Deduplicates overlapping findings across models; computes confidence ratings based on provider agreement and flags single-model vs multi-model issues.
- **Transparent Execution**: Zero mock data or fabricated results—unconfigured providers are explicitly reported as `skipped`, failed calls are isolated, and completed reviews reflect real LLM output.
- **Integrated Static Analysis**: Detects hardcoded secrets (AWS keys, GitHub tokens, Stripe keys, JWTs) and `TODO`/`FIXME` maintenance notes with precise file and cell-level line hints.
- **Asynchronous Job Polling**: Non-blocking review pipeline with real-time stage progress tracking (`repository` → `static_analysis` → `llm_providers` → `aggregation` → `report`).
- **Developer-Centric UI**: Polished React + Tailwind dashboard with risk gauges, severity breakdowns, filterable findings, cell/line location badges, and multi-provider consensus views.

---

## Architecture

```
                      ┌────────────────────────────────────────┐
                      │          React Frontend (Vite)         │
                      │   (URL Form, Job Polling, Dashboard)   │
                      └───────────────────┬────────────────────┘
                                          │ HTTP REST / Polling
                                          ▼
                      ┌────────────────────────────────────────┐
                      │            FastAPI Backend             │
                      │ (Job Store, Async Task Worker, CORS)   │
                      └───────────────────┬────────────────────┘
                                          │
                                          ▼
                      ┌────────────────────────────────────────┐
                      │       GitHub Repository Analyzer       │
                      │  (GitPython Clone, File Classification)│
                      └───────────────────┬────────────────────┘
                                          │
                    ┌─────────────────────┴─────────────────────┐
                    ▼                                           ▼
       ┌─────────────────────────┐                 ┌─────────────────────────┐
       │   Static Code Analyzer  │                 │ Jupyter Notebook Parser │
       │ (Regex Secrets & TODOs) │                 │(JSON Stripping, Cells)  │
       └────────────┬────────────┘                 └────────────┬────────────┘
                    └─────────────────────┬─────────────────────┘
                                          │ Analyzable Source Files
                                          ▼
                      ┌────────────────────────────────────────┐
                      │              LLM Reviewers             │
                      │   OpenAI       Anthropic      Gemini   │
                      │ (Security)  (Maintainability)(Performance)
                      └───────────────────┬────────────────────┘
                                          │ Provider Results
                                          ▼
                      ┌────────────────────────────────────────┐
                      │       Aggregation & Consensus          │
                      │(Deduplication, Confidence, Risk Score) │
                      └───────────────────┬────────────────────┘
                                          │
                                          ▼
                      ┌────────────────────────────────────────┐
                      │         Structured Review Report       │
                      │    (Stored in JSON/MD & React State)   │
                      └────────────────────────────────────────┘
```

---

## Supported Repository Content

The analyzer classifies every file in the repository before processing:

### 1. Source Code Files
- **Python**: `.py`, `.pyw`
- **JavaScript / TypeScript**: `.js`, `.jsx`, `.ts`, `.tsx`, `.mjs`, `.cjs`
- **C / C++**: `.c`, `.h`, `.cpp`, `.hpp`, `.cc`, `.cxx`, `.c++`, `.hh`
- **Java & JVM**: `.java`, `.kt`, `.kts`, `.scala`, `.groovy`
- **Systems & Modern**: `.go`, `.rs`, `.swift`, `.cs`, `.fs`
- **Scripting & Web**: `.php`, `.rb`, `.sh`, `.bash`, `.zsh`, `.lua`, `.pl`, `.dart`
- **Data**: `.sql`, `.r`

### 2. Jupyter Notebooks (`.ipynb`)
- Parses raw notebook JSON using `app/notebook_parser.py`.
- Strips out binary image outputs, execution counters, and matplotlib display bundles.
- Extracts executable code cells in sequential order, demarcated with clear boundary headers:
  ```python
  # ==========================================
  # [Cell 3: Code]
  # ==========================================
  ```
- Incorporates brief markdown context as commented headers without breaking code syntax.
- Maps line numbers back to specific notebook cells so findings report e.g. `Cell 7` instead of arbitrary line offsets.

### 3. Configuration & Infrastructure
- Supported: `.yml`, `.yaml`, `.json`, `.toml`, `.xml`, `.ini`, `.cfg`, `Dockerfile`, `Makefile`.

### 4. Automatically Ignored Files
- **Binary & Media**: `.avi`, `.mp4`, `.mov`, `.mkv`, `.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`, `.pdf`, `.mp3`, `.wav`, `.zip`, `.tar`, `.gz`.
- **Model Weights & Checkpoints**: `.pt`, `.pth`, `.onnx`, `.h5`, `.hdf5`, `.safetensors`, `.pkl`, `.ckpt`.
- **Generated & Build Artifacts**: `package-lock.json`, `yarn.lock`, `poetry.lock`, `.min.js`, `.min.css`, `.bundle.js`, `.map`.
- **Excluded Directories**: `.git`, `node_modules`, `dist`, `build`, `__pycache__`, `.venv`, `coverage`.

---

## AI Providers

The system architecture defines specialized roles for three LLM families:

| Provider | Assigned Role | Default Model | Config Variable | Implementation Status |
| :--- | :--- | :--- | :--- | :--- |
| **Google Gemini** | Performance Optimization | `gemini-3.5-flash` | `GEMINI_API_KEY` | **Verified & Live** (Tested on real repos) |
| **OpenAI** | Security Vulnerabilities | `gpt-4.1-mini` | `OPENAI_API_KEY` | **Implemented** (Uses `/v1/responses` endpoint) |
| **Anthropic** | Maintainability & Quality | `claude-haiku-4-5-20251001` | `ANTHROPIC_API_KEY` | **Implemented** (Uses `/v1/messages` endpoint) |

> **Provider Policy**: If an API key is missing, the provider is marked as `skipped` with a clear explanation (`"API key not configured."`). Unconfigured providers are **never** simulated with mock data. Reviews proceed successfully if at least one provider is configured.

---

## Review Pipeline

1. **Submission**: User submits a public GitHub repository URL via the React UI (`POST /api/reviews`).
2. **Cloning**: The backend shallow-clones (`depth=1`) the repository into an isolated workspace (`.tmp/<uuid>`).
3. **Classification & Sampling**: Files are categorized. Source code and notebooks are prioritized. Up to `MAX_FILES` (default: 30) are selected, capped at `MAX_FILE_BYTES` (default: 20 KB) of pure code per file.
4. **Notebook Extraction**: `.ipynb` files are parsed, code cells are extracted, and boundary metadata is injected.
5. **Static Analysis**: Regex patterns scan for credentials (AWS, GitHub, Stripe, JWTs) and `TODO`/`FIXME` tags.
6. **LLM Dispatch**: Active providers review selected files in parallel. Prompts require strict JSON output grounded in the supplied code.
7. **Consensus & Scoring**:
   - Findings are deduplicated across models based on file path, category, and normalized title.
   - The highest-severity representation is retained.
   - `detected_by` records which providers flagged each issue.
   - `confidence` is calculated as `agreeing_providers / total_active_providers`.
   - A composite **Risk Score (0–100)** is computed from finding severities and static signals.
8. **Storage & Delivery**: Results are saved to `reports/<id>.json` and `reports/<id>.md`. The frontend polls status and displays the finalized report.
9. **Cleanup**: Temporary cloned repository directories are purged upon job completion or failure.

---

## Finding Format

Every review finding generated by the platform contains:

```json
{
  "title": "Extremely slow video decoding via frequent frame-seeking (CAP_PROP_POS_FRAMES)",
  "severity": "high",
  "category": "performance",
  "file_path": "Section1_CNN_LSTM.ipynb",
  "cell_number": 7,
  "line_hint": "Cell 7",
  "line_start": 12,
  "line_end": 23,
  "summary": "Seeking to random positions in compressed video streams is slow because the decoder must seek to keyframes...",
  "recommendation": "Read sequentially using cap.grab() to skip intermediate frames without resetting decoder state.",
  "evidence": "cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))\nret, f = cap.read()",
  "confidence": 1.0,
  "source_model": "gemini",
  "reviewer_role": "performance",
  "detected_by": ["gemini"]
}
```

---

## Web Interface

The React frontend provides five distinct views for review analysis:

- **Overview Tab**:
  - Radial **Risk Score Gauge** (0–100) with color-coded severity levels.
  - **Findings by Severity** horizontal distribution bar chart.
  - High-level metric cards (Total findings, Static signals, Providers completed).
  - Executive summary and ordered **Recommended Next Steps**.
- **Findings Tab**:
  - Interactive search bar across finding titles, paths, and explanations.
  - Filter pills for severity (`critical`, `high`, `medium`, `low`) and category (`security`, `performance`, etc.).
  - Clickable finding cards showing title, file path, notebook cell tags, and confidence percentages.
  - **Finding Detail View**: Displays exact code evidence quotes, remediation instructions, and provider consensus status.
- **Providers Tab**:
  - Individual status cards for Gemini, OpenAI, and Anthropic.
  - Reports provider status (`completed`, `skipped`, or `failed`).
  - Summarizes provider-specific observations and identified strengths.
- **Consensus Tab**:
  - Highlights multi-model agreements and single-provider observations.
  - Summarizes coverage statistics and positive engineering signals.
- **Static Signals Tab**:
  - Displays regex-detected secrets and maintenance flags with exact file locations and cell markers.

---

## Tech Stack

### Frontend
- **Framework**: React 18
- **Language**: TypeScript
- **Bundler & Dev Server**: Vite 5
- **Styling**: Tailwind CSS
- **Routing**: React Router DOM v6

### Backend
- **Framework**: FastAPI (async HTTP)
- **ASGI Server**: Uvicorn
- **Language**: Python 3.12+
- **Data Validation & Settings**: Pydantic v2 & Pydantic-Settings
- **HTTP Client**: HTTPX (async requests for LLM APIs)
- **Git Integration**: GitPython (shallow repository clones)

---

## Project Structure

```
.
├── app/                        # FastAPI Backend
│   ├── main.py                 # REST endpoints, in-memory job store, background tasks
│   ├── config.py               # Pydantic settings loading from .env
│   ├── models.py               # Pydantic schemas (ReviewIssue, Report, JobStatus)
│   ├── prompts.py              # Role-specific system prompts & JSON output schemas
│   ├── llm_clients.py          # OpenAI, Anthropic, and Gemini API clients
│   ├── review_orchestrator.py  # Multi-model dispatch, consensus, and risk scoring
│   ├── repo_loader.py          # Git cloning, file classification, and priority sampling
│   ├── notebook_parser.py      # Jupyter Notebook (.ipynb) code extraction engine
│   ├── static_analyzer.py      # Pattern-based secret & TODO detection
│   └── report_writer.py        # Markdown and JSON report generator
├── frontend/                   # React Frontend
│   ├── src/
│   │   ├── components/
│   │   │   ├── review/         # RepoInputForm, ReviewProgress, ReviewReport, FindingsList
│   │   │   └── ui/             # Badge, Card, Spinner, CodeViewer
│   │   ├── hooks/
│   │   │   └── useReviewJob.ts # Polling hook (auto-polls GET /api/reviews/{id} every 2s)
│   │   ├── pages/              # HomePage, ReviewPage
│   │   ├── services/api.ts     # Frontend fetch client for backend endpoints
│   │   └── types/api.ts        # TypeScript interfaces matching backend models
│   ├── package.json
│   ├── vite.config.ts          # Configured with proxy to http://127.0.0.1:8000
│   └── tailwind.config.js
├── reports/                    # Generated JSON and Markdown review reports
├── requirements.txt            # Python dependencies
├── .env.example                # Template for environment configuration
└── README.md
```

---

## Setup

### Prerequisites
- **Python 3.10+** (tested on Python 3.12)
- **Node.js 18+** & **npm** (tested with Node v24)
- **Git** CLI installed

### 1. Backend Setup

```bash
# In the project root
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Frontend Setup

```bash
cd frontend
npm install
cd ..
```

---

## Environment Variables

Create your `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` and configure at least one API key:

```ini
# LLM Provider API Keys (Configure at least one)
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GEMINI_API_KEY=

# Configurable Model Identifiers (Optional overrides)
OPENAI_MODEL=gpt-4.1-mini
ANTHROPIC_MODEL=claude-haiku-4-5-20251001
GEMINI_MODEL=gemini-3.5-flash

# Ingestion Limits
DEFAULT_BRANCH=main
MAX_FILES=30
MAX_FILE_BYTES=20000

# CORS & Staging Paths
FRONTEND_ORIGIN=http://localhost:5173
REPORTS_DIR=reports
TEMP_DIR=.tmp
```

> ⚠️ **SECURITY NOTICE**: **NEVER** commit your `.env` file or API keys to Git. The `.gitignore` file is pre-configured to ignore `.env`, `.tmp`, and `frontend/node_modules`.

---

## Running a Review

### 1. Start the Backend
```bash
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```
Backend API will be available at `http://127.0.0.1:8000`.

### 2. Start the Frontend (Second Terminal)
```bash
cd frontend
npm run dev
```
Frontend UI will be available at `http://localhost:5173`.

### 3. Execute a Review
1. Navigate to **`http://localhost:5173`** in your browser.
2. Verify that your configured providers show a green checkmark under provider status.
3. Paste a public GitHub URL (e.g. `https://github.com/Somak-2001/deepvision-suite.git`).
4. Click **Analyze Repository**.
5. Watch the live progress stages update as the repo is cloned, analyzed, and reviewed.
6. Inspect the generated report across the Overview, Findings, Providers, and Consensus tabs.

---

## Verified Example: `deepvision-suite`

The pipeline was verified end-to-end against [`https://github.com/Somak-2001/deepvision-suite.git`](https://github.com/Somak-2001/deepvision-suite.git):

```
Repository Structure:
├── Section1_CNN_LSTM.ipynb   (1.7 MB - Video Action Recognition)
├── Section2_ViT.ipynb        (545 KB - Vision Transformer on CIFAR-10)
├── Section3_Tracking.ipynb   (2.7 MB - Multi-Object Tracking System)
├── README.md                 (18 KB - Documentation)
├── train_output.avi          (980 KB - Video Media)
└── test_output.avi           (1.1 MB - Video Media)
```

### Reviewer Execution:
- **Filtering**: `train_output.avi` and `test_output.avi` were detected as `binary_media` and ignored.
- **Extraction**: `app/notebook_parser.py` stripped binary output charts and extracted pure PyTorch/Python code cells.
- **Sampling**: Analyzed all 3 notebooks (509, 513, and 435 lines of pure code).
- **Findings Produced**:
  - `Section1_CNN_LSTM.ipynb` (Cell 7): High-severity video decode seek bottleneck (`cap.set(cv2.CAP_PROP_POS_FRAMES)`).
  - `Section1_CNN_LSTM.ipynb` (Cell 8): Medium-severity redundant activation memory tracking for frozen ResNet backbone.
  - `Section2_ViT.ipynb` (Cell 10): Medium-severity single-sample sequential GPU inference loop.
  - `Section3_Tracking.ipynb` (Cell 9): Medium-severity quadratic list copying of trajectories in video loop.
  - `Section2_ViT.ipynb` (Cell 4): Low-severity manual attention calculation instead of PyTorch SDPA FlashAttention.

---

## API Endpoints

The FastAPI backend exposes the following REST endpoints:

| Method | Endpoint | Description | Request / Response Payload |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | Server health check | Returns `{"status": "ok", "version": "2.0.0"}` |
| `GET` | `/api/config` | Discovers available providers & limits | Returns configured providers and model names (no keys exposed) |
| `POST` | `/api/reviews` | Starts an asynchronous review job | Request: `{"repository_url": "https://github.com/..."}`<br>Response: `{"review_id": "abc123", "status": "pending"}` (HTTP 202) |
| `GET` | `/api/reviews/{id}` | Polls status and per-stage progress | Returns current status (`running`, `completed`, `failed`), progress percentage (0–100), and stage breakdown |
| `GET` | `/api/reviews/{id}/report` | Fetches the full structured review report | Returns full JSON report when job status is `completed` (HTTP 409 if still in progress) |
| `GET` | `/` | API entry metadata | Returns link to docs (`/docs`) and API status |

---

## Error Handling

- **Invalid or Private URLs**: Returns HTTP 422 if URL is malformed or non-GitHub. If `git clone` fails (e.g. private repo or nonexistent target), the job stage fails with a clean descriptive error.
- **No Analyzable Files**: If a repository contains only unsupported formats or ignored media files, the review halts gracefully with an explanatory message.
- **No Configured Providers**: Returns HTTP 503 if zero API keys are set in `.env`.
- **Individual Provider Failures**: If an individual provider encounters authentication errors (HTTP 401) or rate limits (HTTP 429), that provider is marked as `failed` in the report with its error string, while other successful providers complete normally.
- **Zero Mock Fallbacks**: Missing or failing providers are never substituted with fake results.

---

## Security

- **Backend-Only Secrets**: API keys are loaded via server-side environment variables and are never transmitted to the frontend browser client.
- **Safe Repository Cleaning**: Cloned repositories are kept inside `.tmp/<uuid>` and deleted in a `finally` block when the review completes or aborts.
- **Input Sanitization**: Repositories are cloned shallowly with depth 1. File sizes are capped before reading into memory to prevent memory exhaustion attacks.
- **Binary Exclusion**: Video, image, and compiled binaries are filtered by file classification before any text processing occurs.

---

## Limitations

- **In-Memory Job Store**: Review jobs are tracked in-memory using an `asyncio.Lock`-protected dictionary. Restarting the backend server clears active jobs (persisted reports remain available on disk in `reports/`).
- **No Review History**: Intentionally designed without a persistent database for simplicity; each review session is accessed via its unique `review_id`.
- **Public Repositories Only**: Private repositories requiring SSH keys or GitHub OAuth tokens are currently not supported.
- **Context Window Limits**: Repositories exceeding `MAX_FILES` (default: 30) or files exceeding `MAX_FILE_BYTES` (default: 20 KB) are sampled and truncated.
- **Single-Provider Fallback**: When only one provider key is configured, findings originate from that single provider, meaning cross-model consensus agreement is unavailable.

---

## Future Improvements

- [ ] **Persistent Database**: Add SQLite/PostgreSQL storage for review history and searchable past reports.
- [ ] **GitHub PR Bot**: Integrate GitHub Apps/Webhooks to automatically comment findings on pull requests.
- [ ] **Incremental Diff Reviews**: Analyze only changed files in a PR or commit range rather than sampling the whole repository.
- [ ] **Additional Linters**: Integrate AST-based static tools (Ruff, ESLint, Semgrep) to supplement regex checks.
- [ ] **Distributed Worker Queue**: Add Celery or Redis for horizontal worker scaling under heavy concurrent review workloads.

---

## Hackathon Demo Flow

1. **Start Services**: Run backend on port 8000 and frontend on port 5173.
2. **Show Status**: Open the UI to demonstrate provider discovery (`/api/config` detecting active keys).
3. **Submit Real Repository**: Enter `https://github.com/Somak-2001/deepvision-suite.git` (or any public Python/JS repository).
4. **Live Stage Progress**: Watch non-simulated stage updates (Clone → Static Analysis → Model Review → Aggregation → Report).
5. **Inspect Real Findings**: Walk through identified issues citing exact notebook cells (e.g. `Cell 7: Video seek bottleneck`), code quotes, and actionable recommendations.
6. **Show Transparency**: Highlight how media files (`.avi`) were automatically ignored and unconfigured models were skipped without fake mock reviews.

---

## Development & Testing

### TypeScript Type Checking
```bash
cd frontend
npx tsc --noEmit
```

### Frontend Production Build
```bash
cd frontend
npm run build
```

### Backend Imports & Diagnostics
```bash
source .venv/bin/activate
python3 -c "from app.main import app; from app.repo_loader import build_snapshot; print('Backend OK')"
```

---

## Project Status

| Area | Status | Notes |
| :--- | :--- | :--- |
| **FastAPI Backend & Async Jobs** | ✅ Verified | Tested with real background execution & polling |
| **Jupyter Notebook (.ipynb) Support** | ✅ Verified | Tested on PyTorch notebooks in `deepvision-suite` |
| **File Classification & Media Filtering**| ✅ Verified | Successfully ignores `.avi` while parsing code |
| **Static Secret & TODO Analyzer** | ✅ Verified | Scans code & notebook cells for security signals |
| **Google Gemini Reviewer** | ✅ Verified | Tested live with real API calls using `gemini-3.5-flash` |
| **OpenAI & Anthropic Clients** | 🟡 Implemented | Code complete; skipped when keys are unconfigured |
| **Multi-Provider Consensus Scoring** | 🟡 Implemented | Algorithm ready; requires >=2 configured API keys |
| **React + Tailwind Frontend** | ✅ Verified | Built and tested with live backend proxying |
| **Database & PR Integration** | ⚪ Future Work | Intentionally excluded from initial hackathon scope |
