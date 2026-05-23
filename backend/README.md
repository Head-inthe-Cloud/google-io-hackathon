# ClosetAI FastAPI Backend

An AI-powered styling backend for online retailers. The store's product catalog is pre-loaded from a JSON file, and the API serves outfit recommendations, virtual try-on, and shopper session management.

---

## Technical Stack
- **Framework:** FastAPI + Uvicorn
- **AI Models:** Google Gemini 2.0 Flash (via `google-genai` SDK), Replicate (IDM-VTON for try-on)
- **Database:** PostgreSQL + pgvector (via SQLAlchemy)
- **Package Manager:** `uv`

---

## Setup

### 1. Prerequisites
- Python 3.13+
- `uv` package manager
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
```bash
cd backend
uv sync
uv run uvicorn main:app --reload --port 8000
```

On first startup the server auto-seeds the catalog from `gymshark_closet_inventory.json` at the project root.

### 4. API Docs
- Swagger: http://localhost:8000/docs
- Redoc: http://localhost:8000/redoc

---

## API Surface

### Catalog (read-only, served from DB)
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/catalog` | List items (filter: `gender`, `category`) |
| `GET` | `/api/catalog/{item_id}` | Single item detail |

### Shopper Sessions
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/sessions` | Create session (selfie, prefs, occasion) |
| `GET` | `/api/sessions/{session_token}` | Get session |
| `PATCH` | `/api/sessions/{session_token}` | Update preferences |

### Outfit Recommendation
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/sessions/{session_token}/recommend` | Generate outfit recommendations |

### Virtual Try-On
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/virtual-try-on` | Single try-on |
| `POST` | `/api/virtual-try-on/batch` | Batch try-on per recommendation |
| `GET` | `/api/virtual-try-on/status/{prediction_id}` | Poll status |

### Agent Pipeline Stubs
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/guardrail-check` | Validate try-on faithfulness (stub) |
| `POST` | `/api/rank-outfits` | Fashion Master ranking (stub) |

### Utility
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Health check + catalog stats |
