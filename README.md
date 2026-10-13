# Helm — Multi-Agent Orchestration System

**Helm** is a cloud-native AI Agent Orchestration system designed for steering and coordinating multi-agent workflows with **minimal to zero cloud cost**.

---

## 1. Tech Stack & Architecture

| Layer | Technology | Cost / Scaling Profile |
| :--- | :--- | :--- |
| **Backend Runtime** | Python 3.11+, FastAPI, Pydantic v2, Uvicorn (`uv`) | Stateless async container |
| **Agent Orchestration** | LangGraph (Supervisor + Worker StateGraph) | Deterministic + LLM routing |
| **AI / LLM Layer** | Google Gemini API (`langchain-google-genai`) | Gemini 2.5 Flash free/low-cost tier |
| **Tool Layer** | Model Context Protocol (`mcp`) | Extensible MCP client registry |
| **State & Memory** | Google Cloud Firestore (Native Mode) | 1 GiB + 50k reads/day free + local fallback |
| **Relational DB** | SQLite (Local Dev) / Neon Serverless Postgres (Prod) | Scale-to-zero compute (`NullPool`) |
| **Frontend** | Angular 19+ Standalone SPA + Tailwind CSS | Hosted on Vercel (Hobby free tier) |
| **Cloud Compute** | Google Cloud Run v2 | `min_instance_count = 0` (Scale-to-Zero) |
| **Container Registry** | Google Artifact Registry (GAR) + GHCR mirror | Auto-cleanup policy (keeps last 5 images) |
| **IaC & CI/CD** | Terraform / OpenTofu + GitHub Actions (OIDC) | Keyless Workload Identity Federation |

---

## 2. Repository Structure

```text
helm/
├── .github/workflows/   # CI (Ruff, Pytest, Angular, Terraform) & CD (OIDC -> GAR/GHCR -> Cloud Run)
├── backend/             # FastAPI + LangGraph + Gemini + MCP + SQLAlchemy + Firestore
├── frontend/            # Angular 19+ Standalone SPA + Tailwind CSS + Vercel config
├── infra/               # Terraform / OpenTofu modules for GCP Cloud Run, Firestore, GAR, OIDC
└── README.md
```

---

## 3. Quick Start (Local Development)

### 3.1 Backend Setup (`backend/`)

1. Navigate to `backend/` and create your local `.env`:
   ```bash
   cd backend
   cp .env.example .env
   ```
2. Install dependencies and run tests using `uv`:
   ```bash
   uv sync --all-groups
   uv run pytest
   ```
3. Start the FastAPI + Uvicorn development server:
   ```bash
   uv run uvicorn app.main:app --reload --port 8000
   ```
   - Interactive OpenAPI docs: `http://localhost:8000/docs`
   - Health check: `http://localhost:8000/api/v1/health`

### 3.2 Frontend Setup (`frontend/`)

1. Install dependencies and start the Angular development server:
   ```bash
   cd frontend
   npm install
   npm start
   ```
2. Open `http://localhost:4200` to dispatch missions to the Helm Supervisor agent and inspect live LangGraph execution traces.

---

## 4. Infrastructure & Cloud Deployment (`infra/`)

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
3. Populate the Secret Manager values for Neon Serverless Postgres and Gemini:
   ```bash
   echo -n "postgresql+asyncpg://user:pass@ep-host.neon.tech/helm?ssl=require" | \
     gcloud secrets versions add helm-database-url --data-file=-

   echo -n "YOUR_GEMINI_API_KEY" | \
     gcloud secrets versions add helm-gemini-api-key --data-file=-
   ```
4. Configure the Terraform outputs (`workload_identity_provider` and `deployer_service_account_email`) as GitHub Actions secrets (`GCP_WORKLOAD_IDENTITY_PROVIDER`, `GCP_DEPLOYER_SERVICE_ACCOUNT`) and repository variable (`GCP_PROJECT_ID`) for automated OIDC deployments on push to `main`.
