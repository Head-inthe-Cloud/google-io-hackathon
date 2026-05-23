import os
import json
import uuid
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from database import engine, SessionLocal, Base, get_db
from models import CatalogItem, ShopperSession, Outfit
from services import gemini as gemini_service
from services import replicate_service

# ---------------------------------------------------------------------------
# Catalog seeding helper
# ---------------------------------------------------------------------------
CATALOG_JSON_PATH = Path(__file__).resolve().parent.parent / "gymshark_closet_inventory.json"


def seed_catalog(db: Session):
    """Load catalog items from JSON into DB if the table is empty."""
    if db.query(CatalogItem).count() > 0:
        print(f"Catalog already seeded ({db.query(CatalogItem).count()} items). Skipping.")
        return

    if not CATALOG_JSON_PATH.exists():
        print(f"Warning: catalog file not found at {CATALOG_JSON_PATH}. Skipping seed.")
        return

    with open(CATALOG_JSON_PATH, "r") as f:
        data = json.load(f)

    count = 0
    for gender in ["mens", "womens"]:
        for item in data.get(gender, []):
            db.add(CatalogItem(
                name=item["name"],
                image_url=item["image_url"],
                description=item.get("description"),
                category=item["category"],
                gender=gender,
            ))
            count += 1

    db.commit()
    print(f"Seeded {count} catalog items from {CATALOG_JSON_PATH.name}.")


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting ClosetAI Backend...")

    # pgvector extension
    try:
        with SessionLocal() as db:
            db.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            db.commit()
            print("Verified PostgreSQL vector extension.")
    except Exception as e:
        print(f"Note: pgvector extension check skipped: {e}")

    # Create tables
    try:
        Base.metadata.create_all(bind=engine)
        print("Database schemas created.")
    except Exception as e:
        print(f"Warning: Database table creation failed: {e}")

    # Seed catalog
    try:
        with SessionLocal() as db:
            seed_catalog(db)
    except Exception as e:
        print(f"Warning: Catalog seeding failed: {e}")

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

# ---------------------------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------------------------

# -- Sessions --
class CreateSessionRequest(BaseModel):
    selfie_url: Optional[str] = None
    gender_preference: Optional[str] = None
    favorite_colors: Optional[List[str]] = None
    disliked_styles: Optional[List[str]] = None
    occasion: Optional[str] = None
    notes: Optional[str] = None

class UpdateSessionRequest(BaseModel):
    selfie_url: Optional[str] = None
    gender_preference: Optional[str] = None
    favorite_colors: Optional[List[str]] = None
    disliked_styles: Optional[List[str]] = None
    occasion: Optional[str] = None
    notes: Optional[str] = None

# -- Recommendations --
class RecommendRequest(BaseModel):
    prompt: str
    image_prompt_url: Optional[str] = None
    partner_image_url: Optional[str] = None
    occasion: Optional[str] = None
    weather_context: Optional[str] = None

# -- Virtual Try-On --
class VirtualTryOnRequest(BaseModel):
    selfie_url: str
    garment_url: str

class BatchTryOnOutfit(BaseModel):
    outfit_id: str
    garment_urls: List[str]

class BatchTryOnRequest(BaseModel):
    session_token: str
    selfie_url: str
    outfits: List[BatchTryOnOutfit]

# -- Guardrail --
class GuardrailCheckRequest(BaseModel):
    outfit_id: str
    tryon_image_url: str
    selfie_url: str
    garment_urls: List[str]

# -- Rank Outfits --
class RankOutfitsRequest(BaseModel):
    session_token: str
    outfits: List[Dict[str, Any]]
    guardrail_results: Optional[List[Dict[str, Any]]] = None


# ===========================================================================
# ENDPOINTS
# ===========================================================================

# ---------------------------------------------------------------------------
# 1. Catalog (read-only)
# ---------------------------------------------------------------------------
@app.get("/api/catalog")
def list_catalog(
    gender: Optional[str] = Query(None, description="Filter by gender: mens or womens"),
    category: Optional[str] = Query(None, description="Filter by category: Tops, Bottoms, etc."),
    db: Session = Depends(get_db),
):
    """Browse the store catalog with optional filters."""
    query = db.query(CatalogItem)
    if gender:
        query = query.filter(CatalogItem.gender == gender)
    if category:
        query = query.filter(CatalogItem.category == category)

    items = query.all()
    return {
        "count": len(items),
        "items": [_serialize_catalog_item(i) for i in items],
    }


@app.get("/api/catalog/{item_id}")
def get_catalog_item(item_id: int, db: Session = Depends(get_db)):
    """Get a single catalog item by ID."""
    item = db.query(CatalogItem).filter(CatalogItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return _serialize_catalog_item(item)


# ---------------------------------------------------------------------------
# 2. Shopper Sessions
# ---------------------------------------------------------------------------
@app.post("/api/sessions")
def create_session(request: CreateSessionRequest, db: Session = Depends(get_db)):
    """Create a new shopper session."""
    token = str(uuid.uuid4())
    session = ShopperSession(
        session_token=token,
        selfie_url=request.selfie_url,
        gender_preference=request.gender_preference,
        favorite_colors=request.favorite_colors,
        disliked_styles=request.disliked_styles,
        occasion=request.occasion,
        notes=request.notes,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return {"session_id": session.id, "session_token": session.session_token}


@app.get("/api/sessions/{session_token}")
def get_session(session_token: str, db: Session = Depends(get_db)):
    """Retrieve a shopper session by token."""
    session = _get_session_or_404(session_token, db)
    return _serialize_session(session)


@app.patch("/api/sessions/{session_token}")
def update_session(session_token: str, request: UpdateSessionRequest, db: Session = Depends(get_db)):
    """Update shopper preferences mid-session."""
    session = _get_session_or_404(session_token, db)
    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(session, field, value)
    db.commit()
    db.refresh(session)
    return _serialize_session(session)


# ---------------------------------------------------------------------------
# 3. Outfit Recommendation
# ---------------------------------------------------------------------------
@app.post("/api/sessions/{session_token}/recommend")
def recommend_outfits(session_token: str, request: RecommendRequest, db: Session = Depends(get_db)):
    """
    Generate outfit recommendations from the store catalog.
    TODO: Wire up the full agent pipeline (Intent → Matching → Fashion Master).
    Currently uses a basic Gemini call as a placeholder.
    """
    session = _get_session_or_404(session_token, db)

    # --- Retrieve candidate catalog items ---
    query = db.query(CatalogItem)
    if session.gender_preference:
        query = query.filter(CatalogItem.gender == session.gender_preference)

    # Try vector search first, fall back to full catalog
    try:
        prompt_vector = gemini_service.get_style_embedding(request.prompt)
        candidates = (
            query
            .filter(CatalogItem.style_vector.isnot(None))
            .order_by(CatalogItem.style_vector.cosine_distance(prompt_vector))
            .limit(20)
            .all()
        )
        # If no items have vectors yet, fall back
        if not candidates:
            candidates = query.limit(30).all()
    except Exception:
        candidates = query.limit(30).all()

    if not candidates:
        return {"outfits": [], "top_choice": None, "optional_purchase_tip": None}

    serialized = [_serialize_catalog_item(i) for i in candidates]

    # --- Call Gemini stylist (placeholder until agent is wired) ---
    # TODO: Replace with Intent Understanding Agent → Clothes Matching Agent → Fashion Master Agent
    weather = request.weather_context or ""
    occasion = request.occasion or session.occasion or ""
    full_prompt = request.prompt
    if occasion:
        full_prompt += f"\nOccasion: {occasion}"
    if weather:
        full_prompt += f"\nWeather: {weather}"
    if session.favorite_colors:
        full_prompt += f"\nPreferred colors: {', '.join(session.favorite_colors)}"
    if session.disliked_styles:
        full_prompt += f"\nAvoid styles: {', '.join(session.disliked_styles)}"
    if session.notes:
        full_prompt += f"\nAdditional notes: {session.notes}"

    outfits = gemini_service.design_outfits_with_gemini(full_prompt, weather, serialized)

    # Persist outfits to DB
    for outfit in outfits:
        item_ids = [itm.get("item_id") for itm in outfit.get("items", [])]
        db.add(Outfit(
            session_id=session.id,
            outfit_id_label=outfit.get("outfit_id"),
            item_ids=item_ids,
            reason=outfit.get("reason") or outfit.get("description"),
            style_tags=outfit.get("style_tags"),
            styling_tip=outfit.get("styling_tip"),
            confidence_score=outfit.get("confidence_score"),
        ))
    db.commit()

    return {
        "outfits": outfits,
        "top_choice": outfits[0]["outfit_id"] if outfits else None,
        "optional_purchase_tip": None,  # TODO: Fashion Master Agent populates this
    }


# ---------------------------------------------------------------------------
# 4. Virtual Try-On
# ---------------------------------------------------------------------------
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
    """
    Trigger try-on jobs for multiple outfits in one call.
    Sends one try-on per outfit (using the first garment URL).
    TODO: Support composite multi-garment try-on when agent is ready.
    """
    jobs = []
    for outfit in request.outfits:
        if not outfit.garment_urls:
            continue
        try:
            result = replicate_service.trigger_virtual_tryon(
                selfie_url=request.selfie_url,
                garment_url=outfit.garment_urls[0],  # primary garment
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


# ---------------------------------------------------------------------------
# 5. Agent Pipeline Stubs
# ---------------------------------------------------------------------------
@app.post("/api/guardrail-check")
def guardrail_check(request: GuardrailCheckRequest):
    """
    Validate a try-on image for faithfulness.
    TODO: Implement Guardrail Agent — compare generated image against inputs.
    """
    # Stub response
    return {
        "outfit_id": request.outfit_id,
        "pass": True,
        "faithfulness_score": 0.0,
        "issues": [],
        "_note": "Stub — Guardrail Agent not yet implemented.",
    }


@app.post("/api/rank-outfits")
def rank_outfits(request: RankOutfitsRequest):
    """
    Fashion Master Agent — final ranking, styling tips, purchase suggestions.
    TODO: Implement Fashion Master Agent.
    """
    # Stub: return outfits in the same order with placeholder ranking
    ranked = []
    for i, outfit in enumerate(request.outfits):
        ranked.append({
            **outfit,
            "ranking": i + 1,
        })
    return {
        "ranked_outfits": ranked,
        "top_choice": ranked[0].get("outfit_id") if ranked else None,
        "styling_tip": None,
        "optional_purchase_tip": None,
        "_note": "Stub — Fashion Master Agent not yet implemented.",
    }


# ---------------------------------------------------------------------------
# 6. Health Check
# ---------------------------------------------------------------------------
@app.get("/")
def health_check(db: Session = Depends(get_db)):
    """Health check with catalog stats."""
    try:
        catalog_count = db.query(CatalogItem).count()
    except Exception:
        catalog_count = -1

    return {
        "status": "ok",
        "service": "ClosetAI API",
        "catalog_items": catalog_count,
        "features_enabled": {
            "gemini": os.getenv("GEMINI_API_KEY") is not None,
            "replicate": os.getenv("REPLICATE_API_TOKEN") is not None,
            "database": os.getenv("DATABASE_URL") is not None,
        },
    }


# ===========================================================================
# Helpers
# ===========================================================================
def _serialize_catalog_item(item: CatalogItem) -> Dict[str, Any]:
    return {
        "id": item.id,
        "name": item.name,
        "image_url": item.image_url,
        "description": item.description,
        "category": item.category,
        "gender": item.gender,
        "colors": item.colors,
        "style_tags": item.style_tags,
    }


def _serialize_session(session: ShopperSession) -> Dict[str, Any]:
    return {
        "session_id": session.id,
        "session_token": session.session_token,
        "selfie_url": session.selfie_url,
        "gender_preference": session.gender_preference,
        "favorite_colors": session.favorite_colors,
        "disliked_styles": session.disliked_styles,
        "occasion": session.occasion,
        "notes": session.notes,
        "created_at": session.created_at.isoformat() if session.created_at else None,
    }


def _get_session_or_404(session_token: str, db: Session) -> ShopperSession:
    session = db.query(ShopperSession).filter(
        ShopperSession.session_token == session_token
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session
