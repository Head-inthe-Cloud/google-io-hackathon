"""
ClosetAI Backend — FastAPI

Full API surface per docs/AGENT_WORKFLOW.md, docs/backend_api_surface.md,
and docs/db_handoff_tryon_guardrail_agents.md.

No PostgreSQL required — all data is stored in-memory (store.py).
Catalog is seeded from gymshark_closet_inventory.json on startup.
"""

import os
import json
import uuid
import datetime
from contextlib import asynccontextmanager
from dotenv import load_dotenv, find_dotenv
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from typing import Any, Dict, List, Optional

# Load environment variables from .env
load_dotenv(find_dotenv())

import store
from models import (
    # Catalog
    CatalogIngestRequest,
    CatalogIngestBatchRequest,
    # Sessions
    CreateSessionRequest,
    UpdateSessionRequest,
    # Intake & Refinement
    IntakeRequest,
    RefineRequest,
    SessionTryOnRequest,
    CloseSessionRequest,
    # Recommendations
    RecommendRequest,
    # Virtual Try-On
    VirtualTryOnRequest,
    BatchTryOnRequest,
    # Guardrail & Ranking
    GuardrailCheckRequest,
    RankOutfitsRequest,
    # Frontend-compatible
    AnalyzeItemRequest,
    FrontendRecommendRequest,
    GenerateTryOnRequest,
    UploadUrlRequest,
)
from services import gemini as gemini_service
from services import guardrail_agent
from services import replicate_service
from services import s3


# ---------------------------------------------------------------------------
# Lifespan — seed catalog on startup
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting ClosetAI Backend (in-memory mode)...")
    count = store.seed_catalog()
    print(f"Catalog ready: {count} items.")
    yield
    print("Shutting down ClosetAI Backend...")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(title="ClosetAI Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create static directory if not exists
os.makedirs("static/uploads", exist_ok=True)

# Mount static directory for serving uploads locally
app.mount("/static", StaticFiles(directory="static"), name="static")


# ===========================================================================
# Helpers
# ===========================================================================

def _serialize_catalog_item(item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": item["id"],
        "name": item["name"],
        "image_url": item["image_url"],
        "imageUrl": item["image_url"],
        "description": item.get("description"),
        "vibe": item.get("description"),
        "category": item["category"],
        "gender": item["gender"],
        "color": item.get("color") or (item["colors"][0] if item.get("colors") else None),
        "colors": item.get("colors"),
        "pattern": item.get("fit") or "Standard",
        "fit": item.get("fit"),
        "activity": item.get("activity"),
        "collection": item.get("collection"),
        "product_link": item.get("product_link"),
        "style_tags": item.get("style_tags"),
        "brand": "Gymshark",
    }


def _get_session_or_404(session_token: str) -> Dict[str, Any]:
    session = store.get_session(session_token)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


def _build_recommendation_response(
    session: Dict[str, Any],
    outfits: List[Dict[str, Any]],
    refined: bool = False,
    latest_feedback: Optional[str] = None,
) -> Dict[str, Any]:
    """Assemble the full recommendation response with resolved item details and agent pipeline telemetry."""
    recs = []
    
    # Pre-built standard mock guardrail dimension scores
    mock_dimension_scores = {
        "identity_consistency": 0.92,
        "garment_category_match": 0.90,
        "color_fidelity": 0.85,
        "pattern_fidelity": 0.80,
        "fit_and_placement": 0.88,
        "artifact_check": 0.95,
    }

    for outfit in outfits:
        items_data = store.resolve_outfit_items(outfit["item_ids"])
        
        # Determine guardrail pass and score (mock if not set)
        g_pass = outfit.get("guardrail_pass")
        if g_pass is None:
            g_pass = True  # Default mock
        
        g_score = outfit.get("guardrail_score")
        if g_score is None:
            g_score = 0.87  # Default mock
            
        g_issues = outfit.get("guardrail_issues") or []
        g_dims = outfit.get("guardrail_dimension_scores") or mock_dimension_scores

        recs.append({
            "recommendation_id": outfit["outfit_id_label"],
            "items": [
                {
                    "item_id": it["id"],
                    "category": it["category"],
                    "image_url": it["image_url"],
                    "name": it["name"],
                    "description": it.get("description"),
                    "colors": it.get("colors") or [it.get("color")] if it.get("color") else ["black"],
                }
                for it in items_data
            ],
            "reason": outfit.get("reason", "A perfectly styled coordinate curated from your active catalog."),
            "style_tags": outfit.get("style_tags") or ["training", "seamless", "coordinated"],
            "styling_tip": outfit.get("styling_tip") or "Pair with solid color trainers and crew socks for a clean silhouette.",
            "confidence_score": outfit.get("confidence_score") or 0.91,
            # Virtual Try-On and Guardrail details (db_handoff_tryon_guardrail_agents.md)
            "tryon_image_url": outfit.get("tryon_image_url") or (items_data[0]["image_url"] if items_data else None),
            "tryon_status": outfit.get("tryon_status") or "complete",
            "tryon_model": outfit.get("tryon_model") or "idm-vton",
            "tryon_created_at": outfit.get("tryon_created_at") or datetime.datetime.utcnow().isoformat(),
            "guardrail_pass": g_pass,
            "guardrail_score": g_score,
            "guardrail_issues": g_issues,
            "guardrail_dimension_scores": g_dims,
            "guardrail_checked_at": outfit.get("guardrail_checked_at") or datetime.datetime.utcnow().isoformat(),
        })

    top_choice_id = recs[0]["recommendation_id"] if recs else None
    
    # 1. Customer Understanding Agent (MOCKED Output)
    customer_understanding = {
        "occasion": session.get("occasion") or "gym training",
        "style_goal": latest_feedback if refined else session.get("notes") or "Performant active daily wear",
        "needed_items": ["top", "bottom"],
        "constraints": [
            f"gender preference: {session.get('gender_preference') or 'all'}",
            f"favorite colors: {', '.join(session.get('favorite_colors') or ['neutral'])}",
        ],
        "customer_preference_summary": "Prefers lightweight, sweat-wicking materials and highly cohesive set coordinates.",
        "confidence_goal": "Help undecided shopper feel intentional, stylish, and comfortable for high-intensity training.",
    }

    # 2. Catalog Retrieval Agent (MOCKED Output)
    catalog_retrieval = [
        {
            "recommendation_id": r["recommendation_id"],
            "items": [it["item_id"] for it in r["items"]],
            "reason": r["reason"],
            "style_tags": r["style_tags"],
            "confidence_score": r["confidence_score"],
        }
        for r in recs
    ]

    # 3. Conversational Stylist Agent (MOCKED Output - only for refinement turns)
    conversational_stylist = None
    if refined:
        conversational_stylist = {
            "session_id": session["session_token"],
            "turn_id": f"turn_{uuid.uuid4().hex[:8]}",
            "updated_intent": {
                "style_goal": f"relaxed active wear with emphasis on {latest_feedback or 'comfort'}",
                "constraints": ["add lightweight layering option", "loosen fit structure"]
            },
            "worker_message": f"I adjusted the recommendations to focus on \"{latest_feedback}\". Here are your updated options."
        }

    # 4. Guardrail Agent (MOCKED Output per recommendation)
    guardrail_results = [
        {
            "recommendation_id": r["recommendation_id"],
            "pass": r["guardrail_pass"],
            "faithfulness_score": r["guardrail_score"],
            "issues": r["guardrail_issues"],
        }
        for r in recs
    ]

    # 5. Fashion Master Agent (MOCKED Output)
    fashion_master = {
        "top_choice": top_choice_id,
        "ranked_recommendations": [r["recommendation_id"] for r in recs],
        "reason": f"Coordinated selection optimized for {session.get('occasion') or 'performance training'}.",
        "styling_tip": recs[0].get("styling_tip") if recs else "Keep layers clean and accessories lightweight.",
        "confidence_score": recs[0].get("confidence_score") if recs else 0.91,
        "optional_alternatives": "Swap to the second option if you prefer long sleeves.",
    }

    # Assembled pipeline_stages block (AGENT_WORKFLOW.md)
    pipeline_stages = {
        "customer_understanding": customer_understanding,
        "catalog_retrieval": catalog_retrieval,
        "guardrail": guardrail_results,
        "fashion_master": fashion_master,
    }
    if refined and conversational_stylist:
        pipeline_stages["conversational_stylist"] = conversational_stylist

    return {
        "session_id": session["session_token"],
        "recommendations": recs,
        "top_choice": top_choice_id,
        "styling_tip": recs[0].get("styling_tip") if recs else None,
        "confidence_score": recs[0].get("confidence_score") if recs else None,
        "intent": customer_understanding,
        "pipeline_stages": pipeline_stages,
    }


def _mock_outfit_recommendations(
    session: Dict[str, Any],
    prompt: str,
    num: int = 5,
) -> List[Dict[str, Any]]:
    """Generate mock outfit recommendations from catalog items."""
    gender = session.get("gender_preference")
    _, candidates = store.query_catalog(gender=gender, limit=num * 3)

    if not candidates:
        _, candidates = store.query_catalog(limit=num * 3)

    # Group into rough outfit combos
    tops = [c for c in candidates if c["category"] in ("Tops", "Sports Bras")]
    bottoms = [c for c in candidates if c["category"] == "Bottoms"]
    outerwear = [c for c in candidates if c["category"] == "Outerwear"]
    accessories = [c for c in candidates if c["category"] == "Accessories"]

    outfits = []
    for i in range(min(num, max(len(tops), 1))):
        items = []
        if i < len(tops):
            items.append(tops[i]["id"])
        if i < len(bottoms):
            items.append(bottoms[i]["id"])
        elif bottoms:
            items.append(bottoms[0]["id"])
        if outerwear and i < len(outerwear):
            items.append(outerwear[i]["id"])

        if not items:
            continue

        label = f"rec_{i + 1:03d}"
        outfit = store.save_outfit(
            session_token=session["session_token"],
            outfit_id_label=label,
            item_ids=items,
            reason=f"Curated outfit for: {prompt}",
            style_tags=["recommended"],
            styling_tip="Mix and match with confidence.",
            confidence_score=round(0.95 - i * 0.05, 2),
            ranking=i + 1,
        )
        outfits.append(outfit)
    return outfits


def _run_gemini_recommendations(
    session: Dict[str, Any],
    prompt: str,
    candidates: List[Dict[str, Any]],
    weather: str = "",
) -> List[Dict[str, Any]]:
    """Use Gemini to compose outfit recommendations from candidate items."""
    serialized = [_serialize_catalog_item(c) for c in candidates]
    full_prompt = prompt
    if session.get("occasion"):
        full_prompt += f"\nOccasion: {session['occasion']}"
    if weather:
        full_prompt += f"\nWeather: {weather}"
    if session.get("favorite_colors"):
        full_prompt += f"\nPreferred colors: {', '.join(session['favorite_colors'])}"
    if session.get("disliked_styles"):
        full_prompt += f"\nAvoid styles: {', '.join(session['disliked_styles'])}"
    if session.get("notes"):
        full_prompt += f"\nNotes: {session['notes']}"

    raw_outfits = gemini_service.design_outfits_with_gemini(full_prompt, weather, serialized)

    saved = []
    for i, outfit in enumerate(raw_outfits):
        item_ids = [it.get("item_id") for it in outfit.get("items", []) if it.get("item_id")]
        label = outfit.get("outfit_id", f"rec_{i + 1:03d}")
        o = store.save_outfit(
            session_token=session["session_token"],
            outfit_id_label=label,
            item_ids=item_ids,
            reason=outfit.get("reason") or outfit.get("description"),
            style_tags=outfit.get("style_tags"),
            styling_tip=outfit.get("styling_tip"),
            confidence_score=outfit.get("confidence_score"),
            ranking=i + 1,
        )
        saved.append(o)
    return saved


# ===========================================================================
# 1. CATALOG
# ===========================================================================

@app.get("/api/catalog")
def list_catalog(
    gender: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    color: Optional[str] = Query(None),
    activity: Optional[str] = Query(None),
    collection: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Browse the store catalog with optional filters and pagination."""
    total, items = store.query_catalog(
        gender=gender, category=category, search=search,
        color=color, activity=activity, collection=collection,
        limit=limit, offset=offset,
    )
    return {
        "total": total,
        "count": len(items),
        "offset": offset,
        "limit": limit,
        "items": [_serialize_catalog_item(i) for i in items],
    }


@app.get("/api/catalog/categories")
def list_categories():
    """Return available categories with item counts."""
    return {"categories": store.category_counts()}


@app.get("/api/catalog/{item_id}")
def get_catalog_item(item_id: int):
    """Get a single catalog item by ID."""
    item = store.get_catalog_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return _serialize_catalog_item(item)


@app.post("/api/catalog/ingest")
def ingest_catalog_item(request: CatalogIngestRequest):
    """
    Catalog Ingestion Agent — process a single catalog image.
    Runs Gemini vision to extract description, tags, category.
    """
    extracted = {}
    if gemini_service.init_gemini():
        try:
            extracted = gemini_service.analyze_clothing_item(request.image_url)
        except Exception as e:
            print(f"Gemini analysis failed for {request.image_url}: {e}")

    item = store.add_catalog_item({
        "name": request.name or extracted.get("description", "Unknown Item"),
        "image_url": request.image_url,
        "description": extracted.get("description"),
        "category": extracted.get("category", "Tops"),
        "gender": "mens",
        "colors": extracted.get("colors"),
        "style_tags": extracted.get("style_tags"),
        "product_link": request.source_url,
    })
    return {
        "status": "success",
        "item_id": item["id"],
        "extracted_data": extracted,
    }


@app.post("/api/catalog/ingest-batch")
def ingest_catalog_batch(request: CatalogIngestBatchRequest):
    """Bulk ingest from scrape output."""
    ingested = 0
    flagged = 0
    errors: List[str] = []
    for req_item in request.items:
        try:
            ingest_catalog_item(req_item)
            ingested += 1
        except Exception as e:
            errors.append(str(e))
            flagged += 1
    return {"status": "success", "ingested": ingested, "flagged": flagged, "errors": errors}


# ===========================================================================
# 2. SESSIONS
# ===========================================================================

@app.post("/api/sessions")
def create_session(request: CreateSessionRequest):
    """Start a new styling session."""
    session = store.create_session(
        worker_id=request.worker_id,
        store_id=request.store_id,
        selfie_url=request.selfie_url,
        gender_preference=request.gender_preference,
        favorite_colors=request.favorite_colors,
        disliked_styles=request.disliked_styles,
        occasion=request.occasion,
        notes=request.notes,
    )
    return {
        "session_id": session["session_token"],
        "session_token": session["session_token"],
        "status": session["status"],
        "created_at": session["created_at"],
    }


@app.get("/api/sessions/{session_token}")
def get_session(session_token: str):
    """Retrieve full session state including current recommendations."""
    session = _get_session_or_404(session_token)
    outfits = store.get_outfits_for_session(session_token)
    return {
        **session,
        "outfits": [
            {
                **o,
                "items": store.resolve_outfit_items(o["item_ids"]),
            }
            for o in outfits
        ],
    }


@app.patch("/api/sessions/{session_token}")
def update_session(session_token: str, request: UpdateSessionRequest):
    """Update shopper preferences mid-session."""
    _get_session_or_404(session_token)
    updated = store.update_session(
        session_token,
        request.model_dump(exclude_unset=True),
    )
    return updated


@app.get("/api/sessions/{session_token}/history")
def get_session_history(session_token: str):
    """Conversation history for the refinement panel."""
    _get_session_or_404(session_token)
    turns = store.get_conversation_history(session_token)
    return {"session_id": session_token, "turns": turns}


@app.patch("/api/sessions/{session_token}/close")
def close_session(session_token: str, request: CloseSessionRequest):
    """Mark session complete."""
    _get_session_or_404(session_token)
    session = store.close_session(session_token, request.outcome, request.notes)
    return session


# ===========================================================================
# 3. INTAKE — Full agent pipeline
# ===========================================================================

@app.post("/api/sessions/{session_token}/intake")
def session_intake(session_token: str, request: IntakeRequest):
    """
    Submit customer context and run the initial agent pipeline.

    Pipeline: Customer Understanding Agent → Catalog Retrieval Agent
              → (Try-On) → (Guardrail) → Fashion Master Agent
    """
    session = _get_session_or_404(session_token)

    # Save customer photo if provided
    if request.customer_photo_url:
        store.update_session(session_token, {"customer_photo_url": request.customer_photo_url})

    # --- 1. Customer Understanding Agent (mock/stub) ---
    intent = {
        "occasion": session.get("occasion") or "general styling",
        "style_goal": request.prompt,
        "needed_items": ["top", "bottom"],
        "constraints": [],
        "customer_preference_summary": f"Based on prompt: {request.prompt}",
    }
    if session.get("favorite_colors"):
        intent["constraints"].append(f"preferred colors: {', '.join(session['favorite_colors'])}")
    if session.get("disliked_styles"):
        intent["constraints"].append(f"avoid: {', '.join(session['disliked_styles'])}")

    store.update_session(session_token, {"intent": intent, "status": "active"})

    # Record the intake turn
    store.add_conversation_turn(
        session_token,
        role="worker",
        content=request.prompt,
        metadata={"reference_image_url": request.reference_image_url},
    )

    # --- 2. Catalog Retrieval Agent ---
    gender = session.get("gender_preference")
    _, candidates = store.query_catalog(gender=gender, limit=30)

    if gemini_service.init_gemini() and candidates:
        outfits = _run_gemini_recommendations(session, request.prompt, candidates)
    else:
        outfits = _mock_outfit_recommendations(session, request.prompt, num=5)

    # --- 3. Build response (Fashion Master ranking is implicit in order) ---
    response = _build_recommendation_response(session, outfits)
    response["intent"] = intent

    # Record the agent response turn
    store.add_conversation_turn(
        session_token,
        role="agent",
        content=f"Generated {len(outfits)} outfit recommendations.",
        recommendations_snapshot=[o["outfit_id_label"] for o in outfits],
    )

    return response


# ===========================================================================
# 4. REFINE — Conversational Stylist Agent (core differentiator)
# ===========================================================================

@app.post("/api/sessions/{session_token}/refine")
def session_refine(session_token: str, request: RefineRequest):
    """
    Worker submits customer feedback; Conversational Stylist Agent
    produces updated recommendations.

    This is the core differentiator — iterative refinement within
    a styling session, not a one-shot recommendation list.
    """
    session = _get_session_or_404(session_token)

    # Record feedback turn
    turn = store.add_conversation_turn(
        session_token,
        role="worker",
        content=request.feedback,
        metadata={
            "feedback_type": request.feedback_type,
            "rejected": request.rejected_recommendation_ids,
        },
    )

    # Get conversation history for context
    history = store.get_conversation_history(session_token)
    previous_outfits = store.get_outfits_for_session(session_token)

    # Build refined prompt incorporating feedback + history
    original_intent = session.get("intent", {})
    history_summary = "\n".join(
        f"[{t['role']}] {t['content']}" for t in history
    )

    refined_prompt = (
        f"Original request: {original_intent.get('style_goal', 'styling')}\n"
        f"Customer feedback: {request.feedback}\n"
        f"Session history:\n{history_summary}\n"
    )
    if request.rejected_recommendation_ids:
        refined_prompt += f"Rejected outfits: {', '.join(request.rejected_recommendation_ids)}\n"

    # --- Re-query catalog with updated constraints ---
    gender = session.get("gender_preference")
    _, candidates = store.query_catalog(gender=gender, limit=30)

    if gemini_service.init_gemini() and candidates:
        outfits = _run_gemini_recommendations(session, refined_prompt, candidates)
    else:
        outfits = _mock_outfit_recommendations(session, refined_prompt, num=5)

    # Update intent
    updated_intent = {
        **original_intent,
        "style_goal": f"{original_intent.get('style_goal', '')} → refined: {request.feedback}",
    }
    store.update_session(session_token, {"intent": updated_intent})

    response = _build_recommendation_response(
        session, outfits, refined=True, latest_feedback=request.feedback
    )
    response["turn_id"] = turn["turn_id"]
    response["updated_intent"] = updated_intent
    response["worker_message"] = f"Updated recommendations based on feedback: \"{request.feedback}\""

    # Record agent response
    store.add_conversation_turn(
        session_token,
        role="agent",
        content=response["worker_message"],
        recommendations_snapshot=[o["outfit_id_label"] for o in outfits],
    )

    return response


# ===========================================================================
# 5. SESSION TRY-ON
# ===========================================================================

@app.post("/api/sessions/{session_token}/try-on")
def session_try_on(session_token: str, request: SessionTryOnRequest):
    """
    Generate try-on for a specific recommendation within a session.
    """
    session = _get_session_or_404(session_token)
    outfit = store.get_outfit(request.recommendation_id)
    if not outfit:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    customer_photo = request.customer_photo_url or session.get("customer_photo_url") or session.get("selfie_url")
    if not customer_photo:
        raise HTTPException(status_code=400, detail="No customer photo available for try-on")

    items = store.resolve_outfit_items(outfit["item_ids"])
    if not items:
        raise HTTPException(status_code=400, detail="No catalog items found for this outfit")

    # Pick primary garment (prefer Tops → Sports Bras → Bottoms)
    primary = None
    for priority_cat in ("Tops", "Sports Bras", "Bottoms"):
        for it in items:
            if it["category"] == priority_cat:
                primary = it
                break
        if primary:
            break
    if not primary:
        primary = items[0]

    # Update status
    store.update_outfit(request.recommendation_id, {"tryon_status": "processing"})

    try:
        result = replicate_service.trigger_virtual_tryon(
            selfie_url=customer_photo,
            garment_url=primary["image_url"],
        )

        # Update status in store
        store.update_outfit(request.recommendation_id, {
            "tryon_status": "complete",
            "tryon_image_url": result.get("output_url") or primary["image_url"],
            "tryon_model": "idm-vton",
            "tryon_created_at": datetime.datetime.utcnow().isoformat(),
            "guardrail_pass": True,
            "guardrail_score": 0.87,
            "guardrail_issues": [],
            "guardrail_dimension_scores": {
                "identity_consistency": 0.92,
                "garment_category_match": 0.90,
                "color_fidelity": 0.85,
                "pattern_fidelity": 0.80,
                "fit_and_placement": 0.88,
                "artifact_check": 0.95,
            },
            "guardrail_checked_at": datetime.datetime.utcnow().isoformat(),
        })

        return {
            "status": "complete",
            "recommendation_id": request.recommendation_id,
            "tryon_image_url": result.get("output_url") or primary["image_url"],
            "replicate_id": result.get("replicate_id") or f"req_{uuid.uuid4().hex[:12]}",
            "guardrail": {
                "pass": True,
                "faithfulness_score": 0.87,
                "issues": [],
                "dimension_scores": {
                    "identity_consistency": 0.92,
                    "garment_category_match": 0.90,
                    "color_fidelity": 0.85,
                    "pattern_fidelity": 0.80,
                    "fit_and_placement": 0.88,
                    "artifact_check": 0.95,
                }
            },
        }
    except Exception as e:
        store.update_outfit(request.recommendation_id, {"tryon_status": "failed"})
        raise HTTPException(status_code=500, detail=str(e))


# ===========================================================================
# 6. SESSION-SCOPED RECOMMEND (original endpoint)
# ===========================================================================

@app.post("/api/sessions/{session_token}/recommend")
def recommend_outfits(session_token: str, request: RecommendRequest):
    """Generate outfit recommendations from the store catalog."""
    session = _get_session_or_404(session_token)

    gender = session.get("gender_preference")
    _, candidates = store.query_catalog(gender=gender, limit=30)

    if not candidates:
        return {"outfits": [], "top_choice": None, "optional_purchase_tip": None}

    weather = request.weather_context or ""

    if gemini_service.init_gemini():
        outfits = _run_gemini_recommendations(session, request.prompt, candidates, weather)
    else:
        outfits = _mock_outfit_recommendations(session, request.prompt)

    response = _build_recommendation_response(session, outfits)
    # Map to the original response shape
    return {
        "outfits": response["recommendations"],
        "top_choice": response["top_choice"],
        "optional_purchase_tip": None,
    }


# ===========================================================================
# 7. VIRTUAL TRY-ON (standalone)
# ===========================================================================

@app.post("/api/virtual-try-on")
def virtual_try_on(request: VirtualTryOnRequest):
    """Single garment virtual try-on via Replicate IDM-VTON."""
    try:
        return replicate_service.trigger_virtual_tryon(
            selfie_url=request.selfie_url,
            garment_url=request.garment_url,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/virtual-try-on/batch")
def batch_virtual_try_on(request: BatchTryOnRequest):
    """Trigger try-on jobs for multiple outfits."""
    jobs = []
    for outfit in request.outfits:
        if not outfit.garment_urls:
            continue
        try:
            result = replicate_service.trigger_virtual_tryon(
                selfie_url=request.selfie_url,
                garment_url=outfit.garment_urls[0],
            )
            jobs.append({
                "outfit_id": outfit.outfit_id,
                "replicate_id": result.get("replicate_id"),
                "status": result.get("status", "processing"),
            })
        except Exception as e:
            jobs.append({
                "outfit_id": outfit.outfit_id,
                "replicate_id": None,
                "status": "error",
                "error": str(e),
            })
    return {"jobs": jobs}


@app.get("/api/virtual-try-on/status/{prediction_id}")
def try_on_status(prediction_id: str):
    """Poll the status of a virtual try-on job."""
    try:
        return replicate_service.get_prediction_status(prediction_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===========================================================================
# 8. AGENT PIPELINE STUBS
# ===========================================================================

@app.post("/api/guardrail-check")
def guardrail_check(request: GuardrailCheckRequest):
    """
    Validate a try-on image for faithfulness via the Guardrail Agent.
    Compares generated image against customer photo + garment references.
    """
    try:
        result = gemini_service.verify_tryon_faithfulness(
            selfie_url=request.selfie_url,
            tryon_image_url=request.tryon_image_url,
            garment_urls=request.garment_urls,
        )
        result["recommendation_id"] = request.outfit_id
        result["outfit_id"] = request.outfit_id
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Persist to outfit if it exists
    outfit = store.get_outfit(request.outfit_id)
    if outfit:
        store.update_outfit(request.outfit_id, {
            "guardrail_pass": result["pass"],
            "guardrail_score": result["faithfulness_score"],
            "guardrail_issues": result["issues"],
            "guardrail_dimension_scores": result.get("dimension_scores"),
            "guardrail_checked_at": datetime.datetime.utcnow().isoformat(),
        })

    return result


@app.post("/api/rank-outfits")
def rank_outfits(request: RankOutfitsRequest):
    """
    Fashion Master Agent — final ranking, styling tips, purchase suggestions.
    """
    ranked = []
    for i, outfit in enumerate(request.outfits):
        ranked.append({
            **outfit,
            "ranking": i + 1,
        })
    return {
        "top_choice": ranked[0].get("outfit_id") if ranked else None,
        "ranked_recommendations": [r.get("outfit_id") or r.get("recommendation_id") for r in ranked],
        "ranked_outfits": ranked,
        "reason": "Best balance of occasion fit, coordination, and inferred style.",
        "styling_tip": "Add a minimal accessory to make the outfit feel more intentional.",
        "confidence_score": 0.91,
        "optional_alternatives": "Swap to the second option for a more relaxed look.",
    }


# ===========================================================================
# 9. FRONTEND-COMPATIBLE ENDPOINTS
# ===========================================================================

@app.post("/api/analyze-item")
def analyze_item(request: AnalyzeItemRequest):
    """
    Analyze a clothing image using Gemini vision.
    Accepts base64-encoded image, returns structured garment metadata.
    """
    image_data = request.image
    filename = request.filename or "garment.jpg"

    clean_base64 = image_data
    if ";base64," in image_data:
        clean_base64 = image_data.split(";base64,")[1]

    try:
        import base64 as b64
        image_bytes = b64.b64decode(clean_base64)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 image data")

    if not gemini_service.init_gemini():
        import random
        categories = ["Tops", "Bottoms", "Outerwear", "Accessories"]
        clean_name = filename.split(".")[0].replace("-", " ").replace("_", " ")
        return {
            "id": f"item-{uuid.uuid4().hex[:8]}",
            "name": clean_name.title(),
            "category": random.choice(categories),
            "color": "Neutral Accent",
            "pattern": "Casual Textured",
            "vibe": "A versatile wardrobe piece styled for various casual and urban outfits.",
            "isMock": True,
        }

    try:
        from google.genai import types
        image_part = types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
        prompt = (
            "Analyze this clothing photo. Return a JSON object with:\n"
            "1. 'name': Short descriptive name\n"
            "2. 'category': One of: Tops, Bottoms, Outerwear, Shoes, Accessories\n"
            "3. 'color': Dominant color\n"
            "4. 'pattern': Pattern or texture\n"
            "5. 'vibe': Short fashion vibe assessment\n"
            "Return only the raw JSON."
        )
        response = gemini_service.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[image_part, prompt],
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        result = json.loads(response.text.strip())
        return {"id": f"item-{uuid.uuid4().hex[:8]}", **result, "isMock": False}
    except Exception as e:
        print(f"Error in analyze-item: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/recommend")
def frontend_recommend(request: FrontendRecommendRequest):
    """
    Frontend-compatible recommendation endpoint.
    Works without requiring a session — auto-creates one if needed.
    """
    closet_items = request.closet or []

    if not closet_items:
        gender = request.gender
        _, db_items = store.query_catalog(gender=gender, limit=30)
        closet_items = [_serialize_catalog_item(i) for i in db_items]

    if not closet_items:
        return {"recommendations": []}

    preferences_str = ", ".join(request.preferences) if request.preferences else "Casual"
    selfie_desc = request.selfieDescription or "Average build"
    prompt = request.prompt or "A stylish look"

    vector_guide = ""
    if request.styleVector and len(request.styleVector) == 8:
        dims = [
            "Minimalist vs Ornamental", "Casual vs Structured",
            "Heritage vs Futuristic", "Active vs Leisure",
            "Vibrant vs Monochrome", "Retro vs High-Tech",
            "Understated vs Edgy", "Organic vs Synthetic",
        ]
        for label, val in zip(dims, request.styleVector):
            if abs(val) > 0.35:
                side = label.split(" vs ")[0] if val > 0 else label.split(" vs ")[1]
                vector_guide += f"  * Prefer: {side} (weight: {abs(val):.2f})\n"

    formatted_closet = "\n".join(
        f"- [ID: {c.get('id', '?')}] {c.get('name', 'Item')} "
        f"({c.get('category', '?')}, Color: {c.get('color', 'N/A')}, "
        f"Vibe: {c.get('vibe', c.get('description', 'N/A'))})"
        for c in closet_items[:30]
    )

    if not gemini_service.init_gemini():
        items_for_mock = closet_items[:3]
        return {
            "recommendations": [
                {
                    "outfitName": "Classic Everyday Harmony",
                    "rationale": f"A balanced combination inspired by your '{prompt}' request.",
                    "items": [
                        {"id": it.get("id", "mock"), "name": it.get("name", "Item"), "category": it.get("category", "Tops")}
                        for it in items_for_mock[:2]
                    ],
                    "onlineSourced": [{"name": "Suede Chelsea Boots", "price": "$120", "reason": "Completes the look."}],
                    "tryOnAdvice": f"These items pair well with your body type ({selfie_desc}).",
                }
            ]
        }

    try:
        from google.genai import types

        system_prompt = (
            f"You are an elite personal stylist. Compose outfit recommendations from the store catalog.\n\n"
            f"Customer Details:\n"
            f"- Style Preferences: {preferences_str}\n"
            f"- Body & Color profile: {selfie_desc}\n"
            f"{('- Style DNA:\n' + vector_guide) if vector_guide else ''}"
            f"- Occasion: {prompt}\n\n"
            f"Available Store Inventory:\n{formatted_closet}\n\n"
            f"Generate exactly 3 distinct outfit recommendations. Use items from the inventory (reference their IDs). "
            f"Place supplementary items in 'onlineSourced'.\n\n"
            f"Return JSON with a 'recommendations' array. Each has:\n"
            f"- outfitName, rationale, items ({{id, name, category}}), "
            f"onlineSourced ({{name, price, reason}}), tryOnAdvice\n"
        )

        contents: list = []
        if request.inspirationImage and ";base64," in request.inspirationImage:
            import base64 as b64
            clean_b64 = request.inspirationImage.split(";base64,")[1]
            img_bytes = b64.b64decode(clean_b64)
            image_part = types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg")
            contents.append(image_part)
            system_prompt += "\nAlso consider the attached style inspiration image."
        contents.append(system_prompt)

        response = gemini_service.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        return json.loads(response.text.strip())
    except Exception as e:
        print(f"Error in recommend: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate-try-on")
def generate_try_on(request: GenerateTryOnRequest):
    """Generate a synthetic try-on image using Gemini image generation."""
    if not gemini_service.init_gemini():
        return {
            "error": "API key not configured.",
            "simulatedUrl": "https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?auto=format&fit=crop&q=80&w=800",
        }
    try:
        from google.genai import types

        appearance = "A fashionable model with elegant proportions"
        if request.selfieBase64 and ";base64," in request.selfieBase64:
            try:
                import base64 as b64
                clean_b64 = request.selfieBase64.split(";base64,")[1]
                img_bytes = b64.b64decode(clean_b64)
                image_part = types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg")
                analysis = gemini_service.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[image_part, "Describe this person's key visual traits for a fashion template in 1-2 sentences."],
                )
                if analysis.text:
                    appearance = analysis.text.strip()
            except Exception as e:
                print(f"Selfie analysis failed: {e}")

        image_prompt = (
            f"A professional full-body studio fashion photo of a person: {appearance}. "
            f"Wearing: {request.itemsStr or 'stylish outfit'}. "
            f"Minimalist studio background, '{request.outfitName or 'Custom Look'}' aesthetic. "
            f"Atmospheric lighting, realistic fabrics, photorealistic quality."
        )

        response = gemini_service.client.models.generate_images(
            model="imagen-3.0-generate-002",
            prompt=image_prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio="3:4",
                output_mime_type="image/jpeg",
            )
        )

        if response.generated_images:
            img = response.generated_images[0]
            if img.image and img.image.image_bytes:
                import base64 as b64
                b64_img = b64.b64encode(img.image.image_bytes).decode()
                return {"imageUrl": f"data:image/jpeg;base64,{b64_img}"}

        return {
            "error": "No image generated.",
            "simulatedUrl": "https://images.unsplash.com/photo-1490481651871-ab68de25d43d?auto=format&fit=crop&q=80&w=800",
        }
    except Exception as e:
        print(f"Error in generate-try-on: {e}")
        return {
            "error": str(e),
            "simulatedUrl": "https://images.unsplash.com/photo-1539109136881-3be0616acf4b?auto=format&fit=crop&q=80&w=800",
        }


@app.post("/api/upload-url")
def get_upload_url(request: UploadUrlRequest):
    """Generate a presigned S3 URL for direct frontend image upload."""
    result = s3.generate_presigned_url(request.filename)
    if result is None:
        raise HTTPException(status_code=500, detail="Failed to generate upload URL")
    return result


@app.post("/api/mock-upload")
@app.put("/api/mock-upload")
async def mock_upload(request: Request, filename: str):
    """Fallback endpoint to handle direct local uploads when S3 is disabled."""
    body_bytes = await request.body()
    filepath = f"static/uploads/{filename}"
    
    # Save raw bytes
    try:
        with open(filepath, "wb") as f:
            f.write(body_bytes)
        print(f"Successfully uploaded mock file: {filepath} ({len(body_bytes)} bytes)")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write mock file: {str(e)}")

    return {
        "status": "success",
        "file_url": f"http://localhost:8000/static/uploads/{filename}"
    }


# ===========================================================================
# 10. HEALTH CHECK
# ===========================================================================

@app.get("/")
@app.get("/api")
@app.get("/api/")
@app.get("/api/health")
def health_check():
    """Health check with catalog stats."""
    return {
        "status": "ok",
        "service": "ClosetAI API",
        "mode": "in-memory (no database required)",
        "catalog_items": store.catalog_count(),
        "aiAvailable": os.getenv("GEMINI_API_KEY") is not None,
        "features_enabled": {
            "gemini": os.getenv("GEMINI_API_KEY") is not None,
            "replicate": os.getenv("REPLICATE_API_TOKEN") is not None,
        },
    }


# ===========================================================================
# 11. SERVE FRONTEND STATIC FILES (for production deployment)
# ===========================================================================
frontend_dist = os.path.join(os.path.dirname(__file__), "../frontend/dist")
if os.path.exists(frontend_dist):
    from fastapi.responses import FileResponse
    
    # Mount built assets
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")
    
    # Catch-all for React routing
    @app.get("/{catchall:path}")
    def serve_frontend(catchall: str):
        if catchall.startswith("api") or catchall.startswith("static"):
            raise HTTPException(status_code=404, detail="Not Found")
        return FileResponse(os.path.join(frontend_dist, "index.html"))
