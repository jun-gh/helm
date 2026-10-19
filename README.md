# Helm — Multi-Agent Orchestration System

**Helm** is a cloud-native AI Agent Orchestration system designed for steering and coordinating multi-agent workflows with **minimal to zero cloud cost**.

---

## 1. Tech Stack & Architecture

| Layer | Technology | Cost / Scaling Profile |
| :--- | :--- | :--- |
| **Backend Runtime** | Python 3.11+, FastAPI, Pydantic v2, Uvicorn (`uv`) | Stateless async container |
| **Agent Orchestration** | LangGraph (Supervisor-Worker Multi-Node StateGraph) | Deterministic routing + LLM steering |
| **AI / LLM Layer** | Google Gemini API (`google-genai`, dynamic `GEMINI_MODEL`) | Free/Pay-as-you-go tier with fail-fast retries |
| **Tool Layer** | Model Context Protocol (`mcp`) | Extensible MCP tool client registry |
| **State & Memory** | PostgreSQL (Neon) / SQLite Checkpoint Store (`SQLStateStore`) | Persistent thread checkpoints across scale-to-zero sleep |
| **Relational DB** | SQLite (Local Dev) / Neon Serverless Postgres (Prod) | Scale-to-zero compute (`NullPool`) |
| **Frontend** | Angular 19+ Standalone SPA + Tailwind CSS | Hosted on Vercel (Hobby free tier) |
| **Cloud Compute** | Render.com Web Service (Docker runtime) | Free tier (750 hrs/month, scale-to-zero idle) |
| **Container / Builds**| Render Git Build & GitHub Container Registry (GHCR) | Continuous auto-deploy directly from Git |
| **IaC & Blueprints** | Render Blueprint (`render.yaml`) + GitHub Actions CI | Declarative infrastructure as code |

---

## 2. Multi-Worker Orchestration Topology

Helm leverages a **Supervisor-Worker** state machine built on LangGraph to coordinate domain-specialized workers with bound MCP tools:

<p align="center">
  <img src="helm_architecture.png" alt="Helm Multi-Worker Orchestration Topology" width="100%" />
</p>

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

## 3. Resilience, Fault Tolerance & Best-Practice Error Handling

To guarantee enterprise reliability and optimal user experience under strict Google Gemini free-tier rate limits (e.g. 20 requests/day per project), API demand spikes, or network drops:

1. **Maximum 3 Retries with Exponential Backoff (`execute_with_retry`)**:
   - Upstream LLM calls across the Supervisor Router, Researcher, and Coder execute with a strict retry limit of **3 attempts**.
   - Applies exponential backoff (`initial_delay=1.0s`, `backoff_factor=1.5`) for transient errors (`503 UNAVAILABLE` high demand, transient `429` rate limits, socket timeouts).
   - **Fail-Fast for Fatal Errors**: Non-retryable errors such as `401 UNAUTHENTICATED` (invalid/missing API key) or `400 INVALID_ARGUMENT` fail fast immediately on attempt 1 without wasting execution budget or time.
2. **Frontend Network & Gateway Resilience**:
   - The Angular `HelmApiService` implements RxJS `retry` with up to **3 attempts** for transient HTTP gateway dropouts (`502 Bad Gateway`, `503 Service Unavailable`, `504 Gateway Timeout`, or network connection drops) before falling back.
3. **Structured Diagnostics & Quota Classification (`categorize_gemini_error`)**:
   - Errors are classified into structured diagnostic records with specific status codes, root causes, human-readable titles, and actionable remediation steps (`QUOTA_EXCEEDED`, `SERVICE_UNAVAILABLE`, `AUTH_ERROR`, `TIMEOUT`, `UPSTREAM_ERROR`).
4. **Rich UI Error & Quota Diagnostics Card**:
   - Rather than freezing or displaying generic alerts, the dashboard renders a dedicated, color-coded **Resilient AI Execution & Quota Diagnostics** card.
   - Displays error category badges, worker context, attempt counts (`3/3 Retries Attempted`), actionable recommendations (e.g. switching models in `.env`), and collapsible raw telemetry for debugging.
5. **Circuit Breaker & Self-Healing Domain Intelligence**:
   - When an upstream quota or cluster spike is detected, subsequent worker nodes trip a circuit breaker to avoid hanging calls.
   - The system self-heals by substituting deterministic domain intelligence, ensuring the user always receives valid research findings and code artifacts without interruption.
6. **Dynamic Model Steering via `.env`**:
   - Easily switch models (e.g. `gemini-3.8-flash`, `gemini-3.1-flash-lite`, `gemini-2.5-flash`) by setting `GEMINI_MODEL` in your `.env` and restarting the backend server.
   - The active model is dynamically reflected across backend health endpoints, frontend telemetry cards, worker execution traces, and final mission artifacts.

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
├── .github/workflows/   # CI (Ruff, Pytest, Angular, Terraform validation)
├── backend/             # FastAPI + LangGraph + Gemini + MCP + Neon Postgres / SQLite
│   ├── app/
│   │   ├── api/endpoints/         # Health & Agent dispatch endpoints
│   │   ├── core/                  # Settings, database session, MCP client registry
│   │   ├── db/                    # SQLAlchemy models & serverless session manager
│   │   ├── memory/                # SQLStateStore (Postgres / SQLite checkpoints + memory fallback)
│   │   └── orchestration/         # LangGraph graph definition, state, & specialized worker nodes
│   │       ├── graph.py           # StateGraph builder and routing conditions
│   │       ├── state.py           # Typed AgentState with trace history & code artifacts
│   │       └── nodes/             # supervisor.py, researcher.py, coder.py
│   ├── Dockerfile                 # Portable multi-stage Docker build with uv
│   └── pyproject.toml             # Python dependencies and tool configs
├── frontend/            # Angular 19+ Standalone SPA + Tailwind CSS + Vercel config
│   ├── src/
│   │   ├── app/
│   │   │   ├── core/services/     # HelmApiService with typed responses and error handling
│   │   │   └── features/dashboard/# Steering dashboard, telemetry, presets & trace viewer
│   │   ├── environments/          # Environment configs (environment.prod.ts -> Render backend)
│   │   ├── styles.css             # Root CSS variables & base typography
│   │   └── index.html             # Entry HTML with canvas background
│   └── tailwind.config.js         # Helm design system tokens (canvas, teal, slate, coral)
├── infra/               # Optional / Reference Terraform modules (GCP / multi-cloud IaC)
├── render.yaml          # Render.com Infrastructure Blueprint (Free Web Service tier)
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

## 7. Cloud Deployment (Render.com + Vercel)

Helm is configured to run at **100% zero cloud cost** by pairing **Render.com** (Backend Web Service) with **Vercel** (Frontend SPA) and **Neon** (Serverless Postgres).

### 7.1 Backend Deployment on Render.com

#### Option A: Using the Blueprint (`render.yaml`)
1. In the [Render Dashboard](https://dashboard.render.com/), click **New +** > **Blueprint**.
2. Connect your GitHub repository.
3. Render automatically detects [`render.yaml`](file:///Users/martinabanes/Sites/ai-skill/helm/render.yaml) and provisions the `helm-backend` web service.
4. Set the secret environment variables in the prompt:
   - `DATABASE_URL`: `postgresql+asyncpg://...` (your Neon connection string)
   - `GEMINI_API_KEY`: Your Google Gemini API key

#### Option B: Manual Web Service Setup
1. In Render, select **New +** > **Web Service**.
2. Connect your repository and select your deployment branch (e.g. `main` or `prodDeploy`).
3. Set the following fields:
   - **Name**: `helm-backend`
   - **Language / Runtime**: `Docker`
   - **Region**: `Singapore (Southeast Asia)` (or region closest to your Neon database)
   - **Instance Type**: `Free` (512 MB RAM, 0.1 CPU, sleeps on idle)
   - **Docker Context**: `backend`
   - **Dockerfile Path**: `backend/Dockerfile`
4. Add the **Environment Variables**:
   ```ini
   APP_ENV=production
   GEMINI_MODEL=gemini-3.8-flash
   GEMINI_API_KEY=YOUR_GEMINI_API_KEY
   DATABASE_URL=postgresql+asyncpg://user:pass@ep-xyz.region.aws.neon.tech/neondb?ssl=require
   CORS_ORIGINS=http://localhost:4200,https://helm.vercel.app,https://*.vercel.app
   ```
5. Click **Create Web Service**. Your service URL will be available at:
   `https://<your-service-name>.onrender.com`

---

### 7.2 Frontend Deployment on Vercel

1. Update the production API URL in [`frontend/src/environments/environment.prod.ts`](file:///Users/martinabanes/Sites/ai-skill/helm/frontend/src/environments/environment.prod.ts):
   ```typescript
   export const environment = {
     production: true,
     apiBaseUrl: 'https://<your-service-name>.onrender.com/api/v1',
   };
   ```
2. Import the repository into [Vercel](https://vercel.com/):
   - **Framework Preset**: `Angular`
   - **Root Directory**: `frontend`
3. Click **Deploy**. Vercel will build the Angular SPA and host it on their global edge network.

## License

MIT
