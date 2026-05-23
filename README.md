# ClosetAI — Agentic Personal Closet Stylist

ClosetAI is an advanced agentic styling assistant that recommends, refines, and generates outfit configurations from a store catalog based on personal style profiles, occasion context, and optional reference images.

The system supports two first-class retail catalogs:
1. **Gymshark** (Default): Sports, leisure, and active apparel (52 curated closet items, or 8,730 full catalog items).
2. **Everlane (Dataset 2)**: Chinos, bags, casual tees, outerwear, and modern daily-wear apparel (10,000 items).

---

## 🚀 How to Use Dataset 2 (Everlane)

ClosetAI is built to support dataset switching dynamically via the `DATASET` environment variable. To switch the entire backend, catalog database, and recommendation agent services to **Everlane (Dataset 2)**, simply set `DATASET=dataset2`.

### 1. Seeding and Querying the Catalog
When `DATASET=dataset2` is active, the backend's in-memory store automatically loads the compact Everlane catalog from `data/dataset2_products.json` (10,000 items) and seeds all items into memory, dynamically mapping:
- Product names and detailed descriptions.
- Hierarchical category structures (Tops, Bottoms, Outerwear, etc.).
- Metadata fields (brand, color, fit, gender, activity).
- Precomputed facet indexes and navigation trees (`data/dataset2_search_tree.json`).

### 2. Standalone Recommender Agent
Setting `DATASET=dataset2` instructs the standalone recommendation agent service to resolve all outfit recommendations, semantic matches, and styling branches from the Everlane dataset instead of Gymshark.

---

## 🛠️ Setup & Running

Make sure to configure your environment. Create a `.env` file in the `backend/` directory or at the root of the project:

```bash
# backend/.env
GEMINI_API_KEY="your-gemini-api-key-here"
```

### Running the Backend with Dataset 2

To start the FastAPI server seeded with **Everlane (Dataset 2)**:

```bash
cd backend
DATASET=dataset2 uv run uvicorn main:app --reload --port 8000
```

*(To run with the default Gymshark dataset, omit the `DATASET` variable or set `DATASET=gymshark`.)*

### Running the Standalone Recommender Agent

To start the standalone agent service configured with **Everlane (Dataset 2)**:

```bash
cd recommender-agent
DATASET=dataset2 uv run uvicorn app:app --reload --port 8001
```

### Running the Frontend

To start the React/Vite/Express application:

```bash
cd frontend
npm install
npm run dev
```

The frontend will start at [http://localhost:3000](http://localhost:3000). All API requests are proxied automatically to the backend running on port 8000.

### 🐳 Running with Docker & Docker Compose

ClosetAI supports fully containerized execution for both services. We've updated the Docker configuration and `docker-compose.yml` to automatically handle dataset switching.

#### 1. Set your environment variables:
Create a `.env` file at the root of the workspace:
```bash
GEMINI_API_KEY="your-gemini-api-key"
```

#### 2. Start the services with Dataset 2 (Everlane):
Simply run `docker-compose` with the `DATASET=dataset2` variable:
```bash
DATASET=dataset2 docker-compose up --build
```

This starts:
- **`closet-ai`** (Vite Frontend + FastAPI Backend) at [http://localhost:8000](http://localhost:8000)
- **`recommender-agent`** (Standalone Recommendation service) at [http://localhost:8001](http://localhost:8001)

Both containers are dynamically seeded with the 10,000-item Everlane catalog.

*(To start with Gymshark instead, simply run `docker-compose up --build`.)*

---

## 🧪 Testing the Agentic Pipeline with Dataset 2

You can run the full end-to-end integration test of the agentic pipeline (Customer Intake, Retrieval, Recommendation, Virtual Try-on, Guardrail checking, and Conversational refinement loops) using **Everlane (Dataset 2)** by running:

```bash
cd backend
DATASET=dataset2 uv run python ../tests/test_full_flow.py
```

All 10,000 items will be successfully seeded and used by the Image Describer, Matching, Guardrail, and Ranking agents, ensuring robust performance.
