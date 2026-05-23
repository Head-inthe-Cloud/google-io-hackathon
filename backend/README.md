# ClosetAI FastAPI Backend

An AI-powered styling backend for online retailers. The store's product catalog is pre-loaded from a JSON file, and the API serves outfit recommendations, virtual try-on, and shopper session management.

---

## Technical Stack
- **Framework:** FastAPI + Uvicorn
- **AI Models:** Google Gemini 2.0 Flash (via `google-genai` SDK), Replicate (IDM-VTON for try-on)
- **Database:** PostgreSQL + pgvector (via SQLAlchemy)
- **Package Manager:** Conda (`environment.yml`)

---

## Setup

### 1. Prerequisites
- [Conda](https://docs.conda.io/) (Miniconda or Anaconda)
- PostgreSQL with the `pgvector` extension

### 2. Environment Variables
```bash
cp .env.example .env
```

Required keys:
- `DATABASE_URL` — e.g. `postgresql://user:pass@localhost:5432/closet_db`
- `GEMINI_API_KEY` — from Google AI Studio
- `REPLICATE_API_TOKEN` — from Replicate (for virtual try-on)

### 3. Install & Run

For **local agent/model testing**, use the existing `ai2` conda env:

```bash
conda activate ai2
pip install google-genai python-dotenv   # if not already installed

cd backend
python scripts/test_tryon_guardrail.py --dry-run --all
python scripts/test_tryon_guardrail.py --scenario rec_m_gym_001
```

For the **full FastAPI server** (Postgres, Replicate, etc.), install all deps from [`environment.yml`](../environment.yml) or `pip install` the packages listed in [`pyproject.toml`](pyproject.toml).

```bash
conda activate ai2
cd backend
uvicorn main:app --reload --port 8000
```

On first startup the server auto-seeds the catalog from `gymshark_closet_inventory.json` at the project root.

### 4. API Docs
- Swagger: http://localhost:8000/docs
- Redoc: http://localhost:8000/redoc

---

## Architecture — Frontend ↔ Backend Integration

The frontend (React/Vite + Express) connects to this backend through an API proxy:

```
┌────────────────────┐         ┌─────────────────────────────────────┐
│  Frontend (Vite)   │         │  Backend (FastAPI)                  │
│  :3000             │         │  :8000                              │
│                    │         │                                     │
│  React UI ────────────/api/*─────►  Catalog (PostgreSQL)           │
│                    │  proxy   │  Gemini AI (recommendations)       │
│  Express server    │         │  Replicate (virtual try-on)        │
│  (dev proxy)       │         │  S3 (image uploads)                │
└────────────────────┘         └─────────────────────────────────────┘
```

### How it works:
1. **Vite dev proxy** (`vite.config.ts`) forwards `/api/*` → `http://localhost:8000`
2. **Express server** (`server.ts`) also proxies `/api/*` for production builds
3. **Frontend API layer** (`src/api.ts`) provides typed functions for all backend calls
4. **Catalog** is seeded from `gymshark_closet_inventory.json` into PostgreSQL on startup
5. **Frontend loads catalog** from `/api/catalog` on mount, with pagination & filtering

### Running both together:
```bash
# Terminal 1: Backend
cd backend && uv run uvicorn main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend && npm run dev
```

Then open http://localhost:3000 — all API calls are automatically proxied to the backend.

---

## API Surface

### Catalog (read-only, served from DB)
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/catalog` | List items (filter: `gender`, `category`, `search`, `color`, `activity`, `collection`; paginate: `limit`, `offset`) |
| `GET` | `/api/catalog/categories` | Category counts |
| `GET` | `/api/catalog/{item_id}` | Single item detail |

### Frontend-Compatible Endpoints
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/analyze-item` | Gemini vision: analyze clothing image (base64) |
| `POST` | `/api/recommend` | AI outfit recommendations (closet + preferences + prompt) |
| `POST` | `/api/generate-try-on` | Gemini image generation: synthetic try-on |
| `POST` | `/api/upload-url` | S3 presigned URL for image upload |

### Shopper Sessions
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/sessions` | Create session (selfie, prefs, occasion) |
| `GET` | `/api/sessions/{session_token}` | Get session |
| `PATCH` | `/api/sessions/{session_token}` | Update preferences |

### Session-Based Outfit Recommendation
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/sessions/{session_token}/recommend` | Generate outfit recommendations (with vector search) |

### Virtual Try-On (Replicate)
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/virtual-try-on` | Single try-on |
| `POST` | `/api/virtual-try-on/batch` | Batch try-on per recommendation |
| `GET` | `/api/virtual-try-on/status/{prediction_id}` | Poll status |

### Agent Pipeline Stubs
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/guardrail-check` | Validate try-on faithfulness (Gemini 3.5 Flash) |
| `POST` | `/api/rank-outfits` | Fashion Master ranking (stub) |

### Health
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Health check + catalog stats |
| `GET` | `/api/health` | Same (alias for frontend) |
