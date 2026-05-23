# ClosetAI FastAPI Backend

This is the FastAPI-based orchestration backend for ClosetAI. It handles:
- **Pre-signed S3 URL generation** for secure frontend-to-S3 uploads.
- **AI Background Removal/Cropping** via SAM-2 / Rembg on Replicate.
- **Image Metadata Extraction** (category, color, season, style) using Google Gemini 1.5.
- **Semantic Style Embeddings** via Google Gemini Text Embedding.
- **Vector Similarity Search** using PostgreSQL & `pgvector` to match the best wardrobe items for styling prompts.
- **Personalized Outfit Design** using Gemini 1.5 acting as a stylist.
- **Virtual Try-On** orchestration using IDM-VTON on Replicate.

---

## Technical Stack
- **Framework:** FastAPI, Uvicorn
- **AI Models:** Google Gemini 1.5 Flash (via `google-genai` SDK for vision analysis & outfit generation), Google `text-embedding-004` (for vector embeddings), Replicate (`yisol/idm-vton` and `cjwbby/rembg`).
- **Database:** PostgreSQL with `pgvector` (via SQLAlchemy)
- **Object Storage:** AWS S3 (pre-signed upload URLs)
- **Package Manager:** `uv`

---

## Setup & Running Local Development

### 1. Prerequisites
Make sure you have:
- Python 3.10+ (or Python 3.13)
- `uv` package manager installed (`pip install uv` or standard installer)
- A running PostgreSQL database with the `pgvector` extension installed.

### 2. Configure Environment Variables
Copy `.env.example` to `.env` and fill in your keys:
```bash
cp .env.example .env
```

Ensure you set:
- `DATABASE_URL` (e.g., `postgresql://username:password@localhost:5432/closet_db`)
- `GEMINI_API_KEY` (Get yours from Google AI Studio)
- `REPLICATE_API_TOKEN` (Get yours from Replicate)
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_BUCKET_NAME` (For S3)

*Note: If AWS keys are omitted, the backend will automatically fallback to local file uploads (`/api/mock-upload`) and serve uploads out of the local `./static` folder.*

### 3. Install Dependencies
Run this in the `backend` folder to sync dependencies:
```bash
uv sync
```

### 4. Start the Server
Run the FastAPI development server:
```bash
uv run uvicorn backend.main:app --reload
```
Alternatively, if you run inside the `backend` folder:
```bash
uv run uvicorn main:app --reload
```

---

## API Documentation
Once the server is running, you can access:
- **Interactive Swagger Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Alternative Redoc Docs:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## Main Endpoints Summary

- `GET /api/upload-url?filename=test.jpg` - Generates direct AWS S3 PUT URL (falls back to local mock upload if AWS is not configured).
- `POST /api/process-item` - Background crop + Gemini analysis + vector embedding + SQL storage.
- `POST /api/generate-outfit` - Vector search + Gemini stylist composition.
- `POST /api/virtual-try-on` - IDM-VTON try-on trigger.
- `GET /api/try-on/status/{prediction_id}` - Poll try-on status on Replicate.
- `GET /api/closet?user_id=123` - View all items in a user's closet.
