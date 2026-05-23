# Recommendation Agent Service

Standalone FastAPI service for agentic product-set recommendations.

This service is separate from the main `backend/` app. It reads the shared product catalog JSON, exposes recommendation endpoints, and runs the LLM-directed recommendation pipeline in `recommender_agent/`.

## Service Boundary

- Own FastAPI app: `recommender-agent/app.py`
- Own Docker image: `recommender-agent/Dockerfile`
- Own dependencies: `recommender-agent/pyproject.toml`
- Shared read-only catalog mount: `../data/gymshark_products.json`
- No imports from the main `backend/` service

## Run With Docker Compose

From the repo root:

```bash
export GEMINI_API_KEY="your_gemini_api_key"
docker compose up --build recommender-agent
```

The service listens on:

```text
http://localhost:8001
```

By default, all recommendation-agent LLM stages use `gemini-3.5-flash` through the Gemini API. Override with `RECOMMENDER_MODEL` only when testing another model.

Useful endpoints:

```text
GET  /health
GET  /api/facets
GET  /api/sample-output
POST /api/recommend
POST /api/recommend/stream
```

## Recommend Request

```bash
curl -X POST http://localhost:8001/api/recommend \
  -H "Content-Type: application/json" \
  -d @recommender-agent/examples/request.json
```

To watch search progress as it happens, use the streaming endpoint:

```bash
curl -N -X POST http://localhost:8001/api/recommend/stream \
  -H "Content-Type: application/json" \
  -d @recommender-agent/examples/request.json
```

The stream uses Server-Sent Events. It emits named events such as `context_compiler.started`, `branch_retrieval.completed`, `set_builder.started`, `critic.completed`, and a final `result` event containing the recommendation payload.

Request body:

```json
{
  "query": "Find me a black or grey lifting set that is breathable and works with my reference image.",
  "preference_stack": "The shopper prefers minimal, understated gymwear with clean silhouettes.",
  "images": [],
  "target_sets": 5,
  "include_debug": false
}
```

## Public Output

The response is a product-set recommendation payload:

```json
{
  "output_format_version": "agentic_product_set_recommender.v1",
  "recommendation_type": "product_sets",
  "product_sets": []
}
```

See `examples/sample_output.json` for a concrete sample response with real catalog products.

## Local CLI

The service package still includes a CLI for debugging the agent pipeline directly:

```bash
cd recommender-agent
python3 -m venv .venv
. .venv/bin/activate
pip install -e .

python3 -m recommender_agent.cli \
  --catalog ../data/gymshark_products.json \
  --preference-stack-file examples/preference_stack.txt \
  --query "Find me a black or grey lifting set that is breathable and works with my reference image." \
  --target-sets 5 \
  --output output/product_sets.json
```

Use `--include-debug` to include compiled context and search trace.

## Architecture

This is not a hardcoded recommender. Product selection is performed by LLM agents:

```text
Context Compiler Agent
-> Search Expansion Agent
-> Stylist Set Builder Agent
-> Critic Agent
```

The local Python code only loads the product catalog, exposes catalog facets, executes LLM-authored search branches, maps candidate IDs back to real products, and validates final product sets.

See `ARCHITECTURE_DECISION_FRAMEWORK.md` for the detailed design.
