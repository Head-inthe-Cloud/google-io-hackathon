import json
import os
import queue
import threading
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, model_validator

from recommender_agent.agent import recommend_product_sets
from recommender_agent.catalog import Catalog
from recommender_agent.llm import GeminiJSONClient, LLMConfigurationError


SERVICE_ROOT = Path(__file__).resolve().parent
DEFAULT_CATALOG_PATH = SERVICE_ROOT.parent / "data" / "gymshark_products.json"
DEFAULT_MODEL = "gemini-3.5-flash"


app = FastAPI(
    title="Recommendation Agent",
    description="Standalone product-set recommendation agent service.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ImageInput(BaseModel):
    url: Optional[str] = None
    path: Optional[str] = None
    mime_type: Optional[str] = None

    @model_validator(mode="after")
    def require_image_source(self):
        if not self.url and not self.path:
            raise ValueError("Either url or path is required.")
        return self


class RecommendationRequest(BaseModel):
    query: str = Field(..., min_length=1)
    preference_stack: str = ""
    images: List[ImageInput] = Field(default_factory=list)
    target_sets: int = Field(default=5, ge=1, le=10)
    max_depth: int = Field(default=2, ge=0, le=5)
    max_branches_per_layer: int = Field(default=12, ge=1, le=40)
    candidates_per_branch: int = Field(default=24, ge=1, le=100)
    top_text_candidates: int = Field(default=20, ge=1, le=100)
    include_debug: bool = False
    model: Optional[str] = None


def _catalog_path() -> Path:
    return Path(os.getenv("CATALOG_PATH", str(DEFAULT_CATALOG_PATH))).expanduser()


def _model_name(request_model: Optional[str] = None) -> str:
    return request_model or os.getenv("RECOMMENDER_MODEL") or DEFAULT_MODEL


@lru_cache(maxsize=4)
def _load_catalog(path: str) -> Catalog:
    return Catalog.load(path)


def _get_catalog() -> Catalog:
    path = _catalog_path()
    if not path.exists():
        raise FileNotFoundError(f"Catalog file not found at {path}")
    return _load_catalog(str(path))


@app.get("/")
def root() -> Dict[str, str]:
    return {
        "service": "recommendation-agent",
        "health": "/health",
        "docs": "/docs",
    }


@app.get("/health")
def health() -> Dict[str, Any]:
    catalog_path = _catalog_path()
    try:
        catalog = _get_catalog()
        status = "ok"
        catalog_items = len(catalog.products)
        error = None
    except Exception as exc:
        status = "degraded"
        catalog_items = 0
        error = str(exc)

    return {
        "status": status,
        "service": "recommendation-agent",
        "catalog_path": str(catalog_path),
        "catalog_items": catalog_items,
        "model": _model_name(),
        "gemini_configured": bool(os.getenv("GEMINI_API_KEY")),
        "error": error,
    }


@app.get("/api/facets")
def facets() -> Dict[str, Any]:
    try:
        catalog = _get_catalog()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {
        "catalog_items": len(catalog.products),
        "facets": catalog.facet_summary(),
    }


@app.get("/api/sample-output")
def sample_output() -> Dict[str, Any]:
    with open(SERVICE_ROOT / "examples" / "sample_output.json", encoding="utf-8") as file:
        return json.load(file)


@app.get("/api/example-request")
def example_request() -> Dict[str, Any]:
    with open(SERVICE_ROOT / "examples" / "request.json", encoding="utf-8") as file:
        return json.load(file)


@app.post("/api/recommend")
def recommend(request: RecommendationRequest) -> Dict[str, Any]:
    try:
        catalog = _get_catalog()
        llm_client = GeminiJSONClient(model=_model_name(request.model))
        return recommend_product_sets(
            catalog,
            llm_client,
            request.query,
            request.preference_stack,
            images=[
                image.model_dump(exclude_none=True)
                for image in request.images
            ],
            target_sets=request.target_sets,
            max_depth=request.max_depth,
            max_branches_per_layer=request.max_branches_per_layer,
            candidates_per_branch=request.candidates_per_branch,
            top_text_candidates=request.top_text_candidates,
            include_debug=request.include_debug,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except LLMConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Recommendation generation failed: {exc}",
        ) from exc


def _run_recommendation(request: RecommendationRequest, progress_callback):
    catalog = _get_catalog()
    llm_client = GeminiJSONClient(model=_model_name(request.model))
    return recommend_product_sets(
        catalog,
        llm_client,
        request.query,
        request.preference_stack,
        images=[
            image.model_dump(exclude_none=True)
            for image in request.images
        ],
        target_sets=request.target_sets,
        max_depth=request.max_depth,
        max_branches_per_layer=request.max_branches_per_layer,
        candidates_per_branch=request.candidates_per_branch,
        top_text_candidates=request.top_text_candidates,
        include_debug=request.include_debug,
        progress_callback=progress_callback,
    )


def _sse_message(event_type: str, payload: Dict[str, Any]) -> str:
    return "\n".join(
        [
            f"event: {event_type}",
            f"data: {json.dumps(payload, ensure_ascii=False)}",
            "",
            "",
        ]
    )


@app.post("/api/recommend/stream")
def recommend_stream(request: RecommendationRequest) -> StreamingResponse:
    events = queue.Queue()
    done = object()

    def progress_callback(payload):
        events.put(payload)

    def worker():
        try:
            result = _run_recommendation(request, progress_callback)
            events.put({"type": "result", "result": result})
        except Exception as exc:
            events.put({"type": "error", "message": str(exc)})
        finally:
            events.put(done)

    def stream():
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        while True:
            event = events.get()
            if event is done:
                break
            event_type = event.get("type", "progress")
            yield _sse_message(event_type, event)

    return StreamingResponse(stream(), media_type="text/event-stream")
