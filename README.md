# Helm — Multi-Agent Orchestration System

**Helm** is a cloud-native AI Agent Orchestration system designed for steering and coordinating multi-agent workflows with **minimal to zero cloud cost**.

---

## 1. Tech Stack & Architecture

| Layer | Technology | Cost / Scaling Profile |
| :--- | :--- | :--- |
| **Backend Runtime** | Python 3.11+, FastAPI, Pydantic v2, Uvicorn (`uv`) | Stateless async container |
| **Agent Orchestration** | LangGraph (Supervisor-Worker Multi-Node StateGraph) | Deterministic routing + LLM steering |
| **AI / LLM Layer** | Google Gemini API (`google-genai`, `gemini-3.8-flash`) | Free/Pay-as-you-go tier with fail-fast retries |
| **Tool Layer** | Model Context Protocol (`mcp`) | Extensible MCP tool client registry |
| **State & Memory** | Google Cloud Firestore (Native Mode) | 1 GiB + 50k reads/day free + local fallback |
| **Relational DB** | SQLite (Local Dev) / Neon Serverless Postgres (Prod) | Scale-to-zero compute (`NullPool`) |
| **Frontend** | Angular 19+ Standalone SPA + Tailwind CSS | Hosted on Vercel (Hobby free tier) |
| **Cloud Compute** | Google Cloud Run v2 | `min_instance_count = 0` (Scale-to-Zero) |
| **Container Registry** | Google Artifact Registry (GAR) + GHCR mirror | Auto-cleanup policy (keeps last 5 images) |
| **IaC & CI/CD** | Terraform / OpenTofu + GitHub Actions (OIDC) | Keyless Workload Identity Federation |

---

## 2. Multi-Worker Orchestration Topology

Helm leverages a **Supervisor-Worker** state machine built on LangGraph to coordinate domain-specialized workers with bound MCP tools:

```
                  ┌──────────────────────┐
                  │      Supervisor      │ ◄─── Evaluates objective & routing
                  └──────────┬───────────┘
                             │
            ┌────────────────┴────────────────┐
            ▼                                 ▼
   ┌─────────────────┐               ┌─────────────────┐
   │Researcher Worker│               │  Coder Worker   │
   │  (Domain Notes) │               │(AST Validations)│
   └────────┬────────┘               └────────┬────────┘
            │                                 │
            └────────────────┬────────────────┘
                             ▼
                  ┌──────────────────────┐
                  │ Gemini Synthesizer   │ ───► Final executive mission synthesis
                  └──────────────────────┘
```

### Worker Roles & Capabilities
1. **Supervisor Router (`supervisor.py`)**:
   - Analyzes mission objectives using Gemini structured output and determines the next worker (`researcher`, `coder`, or `synthesizer`).
   - Hardened with a multi-strategy JSON extractor (`extract_next_agent_decision`) supporting standard double-quoted JSON, Python single-quoted dictionary formats (`{'next_agent': '...'}`), and markdown code blocks.
2. **Researcher Specialist (`researcher.py`)**:
   - Synthesizes architectural analyses, protocol comparisons, and security considerations into structured research notes.
   - Bound to MCP tool clients for live external information retrieval.
3. **Coder Specialist (`coder.py`)**:
   - Generates executable Python code scaffolds and implementation artifacts.
   - Runs automated Python AST parsing (`ast.parse`) as an integrated quality gate to verify syntax before publishing artifacts to state.
4. **Mission Synthesizer**:
   - Consolidates findings from all active workers (`completed_workers`) into an executive report with action items and execution traces.

---

## 3. Resilience, Quota Recovery & Fail-Fast Architecture

To guarantee high reliability and avoid UI freezes under strict Google Gemini free-tier rate limits (e.g. 20 requests/day per project) and API demand spikes:

1. **Fail-Fast Retry Configuration (`max_retries=1`)**:
   - Gemini API clients (`google.genai.Client`) are explicitly initialized with `HttpOptions(max_retries=1)`.
   - Prevents long blocking loops when Google returns `429 RESOURCE_EXHAUSTED` (e.g., `retryDelay: 75789s`) or `503 UNAVAILABLE` demand spikes.
2. **Transparent Error Surfacing**:
   - Upstream API exceptions and quota notices are captured in `AgentRunResponse.errors` and rendered immediately in the Angular UI as clear warning banners instead of leaving the user stuck on loading states.
3. **Graceful Domain Intelligence Fallback**:
   - If an external LLM call is throttled or unauthenticated, Helm's supervisor and worker nodes fall back to local deterministic domain intelligence.
   - The orchestration run completes successfully, active workers are recorded, and full trace telemetry is preserved.
4. **Google AI Studio Key Support**:
   - Supports Google AI Studio service account-bound authorization keys (keys prefixed with `AQ.`).
   - Targets the current `gemini-3.8-flash` model via `.env` configuration.

---

## 4. Design System & Frontend Architecture

The frontend is built using **Angular 19 Standalone Components** and **Signals** (`signal`, `inject`), styled with a 4-color design system prioritized left-to-right by visual dominance:

| Priority | Hex Code | Role | Usage |
| :--- | :--- | :--- | :--- |
| **1. Leftmost** | `#F5F5F5` | **Canvas** | Page background, header container backdrop, input surfaces, trace rows |
| **2. Second** | `#76ABAE` | **Structure** | Card borders (`#76ABAE`/35), Researcher findings panel, secondary badges |
| **3. Third** | `#303841` | **Typography** | High-contrast typography, headings, labels, and dark code block backgrounds |
| **4. Rightmost**| `#FF5722` | **Actions** | Primary CTA buttons (`Launch Orchestration Run`), brand logo mark, alert banners |

---

## 5. Repository Structure

```text
helm/
├── .github/workflows/   # CI (Ruff, Pytest, Angular, Terraform) & CD (OIDC -> GAR/GHCR -> Cloud Run)
├── backend/             # FastAPI + LangGraph + Gemini + MCP + SQLAlchemy + Firestore
│   ├── app/
│   │   ├── api/endpoints/         # Health & Agent dispatch endpoints
│   │   ├── core/                  # Settings, database session, MCP client registry
│   │   └── orchestration/         # LangGraph graph definition, state, & specialized worker nodes
│   │       ├── graph.py           # StateGraph builder and routing conditions
│   │       ├── state.py           # Typed AgentState with trace history & code artifacts
│   │       └── nodes/             # supervisor.py, researcher.py, coder.py
├── frontend/            # Angular 19+ Standalone SPA + Tailwind CSS + Vercel config
│   ├── src/
│   │   ├── app/
│   │   │   ├── core/services/     # HelmApiService with typed responses and error handling
│   │   │   └── features/dashboard/# Steering dashboard, telemetry, presets & trace viewer
│   │   ├── styles.css             # Root CSS variables & base typography
│   │   └── index.html             # Entry HTML with canvas background
│   └── tailwind.config.js         # Helm design system tokens (canvas, teal, slate, coral)
├── infra/               # Terraform / OpenTofu modules for GCP Cloud Run, Firestore, GAR, OIDC
└── README.md
```

---

## 6. Quick Start (Local Development)

### 6.1 Backend Setup (`backend/`)

1. Navigate to `backend/` and create your local `.env`:
   ```bash
   cd backend
   cp .env.example .env
   ```
2. Configure your Gemini API key and model in `backend/.env`:
   ```dotenv
   GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
   GEMINI_MODEL="gemini-3.8-flash"
   ```
3. Install dependencies and run test suite using `uv`:
   ```bash
   uv sync --all-groups
   uv run pytest
   ```
4. Start the FastAPI + Uvicorn development server:
   ```bash
   uv run uvicorn app.main:app --reload --port 8000
   ```
   - Interactive OpenAPI docs: `http://localhost:8000/docs`
   - Health check: `http://localhost:8000/api/v1/health`

### 6.2 Frontend Setup (`frontend/`)

1. Install dependencies and start the Angular development server:
   ```bash
   cd frontend
   npm install
   npm start
   ```
2. Open `http://localhost:4200` to dispatch missions, select presets, and inspect multi-worker traces.

---

## 7. Infrastructure & Cloud Deployment (`infra/`)

1. Configure your GCP variables:
   ```bash
   cd infra
   cp terraform.tfvars.example terraform.tfvars
   ```
2. Initialize and apply Terraform / OpenTofu:
   ```bash
   terraform init
   terraform plan
   terraform apply
   ```
3. Populate Secret Manager values for Neon Postgres and Gemini:
   ```bash
   echo -n "postgresql+asyncpg://user:pass@ep-host.neon.tech/helm?ssl=require" | \
     gcloud secrets versions add helm-database-url --data-file=-

   echo -n "YOUR_GEMINI_API_KEY" | \
     gcloud secrets versions add helm-gemini-api-key --data-file=-
   ```
4. Configure Terraform outputs (`workload_identity_provider` and `deployer_service_account_email`) as GitHub Actions secrets for automated keyless CI/CD.
