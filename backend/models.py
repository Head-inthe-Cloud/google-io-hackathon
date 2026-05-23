"""
Pydantic request/response schemas for the ClosetAI API.

No SQLAlchemy — all data lives in the in-memory store (store.py).
Schemas follow the contracts defined in docs/AGENT_WORKFLOW.md,
docs/backend_api_surface.md, and docs/db_handoff_tryon_guardrail_agents.md.
"""

from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


# ===== Catalog ================================================================

class CatalogIngestRequest(BaseModel):
    image_url: str
    source_url: Optional[str] = None
    sku: Optional[str] = None
    name: Optional[str] = None
    price: Optional[float] = None

class CatalogIngestBatchRequest(BaseModel):
    items: List[CatalogIngestRequest]


# ===== Sessions ===============================================================

class CreateSessionRequest(BaseModel):
    worker_id: Optional[str] = None
    store_id: Optional[str] = None
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


# ===== Intake & Refinement (core agent loop) =================================

class IntakeRequest(BaseModel):
    """POST /api/sessions/{session_id}/intake"""
    prompt: str
    reference_image_url: Optional[str] = None
    customer_photo_url: Optional[str] = None

class RefineRequest(BaseModel):
    """POST /api/sessions/{session_id}/refine"""
    feedback: str
    feedback_type: str = "text"  # "text" | "chip"
    rejected_recommendation_ids: Optional[List[str]] = None

class SessionTryOnRequest(BaseModel):
    """POST /api/sessions/{session_id}/try-on"""
    recommendation_id: str
    customer_photo_url: Optional[str] = None

class CloseSessionRequest(BaseModel):
    """PATCH /api/sessions/{session_id}/close"""
    outcome: Optional[str] = None  # "tried_on" | "purchased" | "left"
    notes: Optional[str] = None


# ===== Recommendations (session-scoped) =======================================

class RecommendRequest(BaseModel):
    prompt: str
    image_prompt_url: Optional[str] = None
    partner_image_url: Optional[str] = None
    occasion: Optional[str] = None
    weather_context: Optional[str] = None


# ===== Virtual Try-On =========================================================

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


# ===== Guardrail ==============================================================

class GuardrailCheckRequest(BaseModel):
    outfit_id: str
    tryon_image_url: str
    selfie_url: str
    garment_urls: List[str]


# ===== Rank Outfits ===========================================================

class RankOutfitsRequest(BaseModel):
    session_token: str
    outfits: List[Dict[str, Any]]
    guardrail_results: Optional[List[Dict[str, Any]]] = None


# ===== Frontend-compatible endpoints ==========================================

class AnalyzeItemRequest(BaseModel):
    image: str  # base64-encoded image data
    filename: Optional[str] = None

class FrontendRecommendRequest(BaseModel):
    preferences: Optional[List[str]] = None
    closet: Optional[List[Dict[str, Any]]] = None
    selfieDescription: Optional[str] = None
    prompt: Optional[str] = None
    inspirationImage: Optional[str] = None  # base64
    styleVector: Optional[List[float]] = None
    preferenceProfile: Optional[str] = None
    gender: Optional[str] = None

class PreferenceProfileRequest(BaseModel):
    preferences: Optional[List[str]] = None
    likedQuizOutfits: Optional[List[Dict[str, Any]]] = None
    selfieDescription: Optional[str] = None
    selfieImage: Optional[str] = None
    prompt: Optional[str] = None
    inspirationImage: Optional[str] = None
    styleVector: Optional[List[float]] = None
    gender: Optional[str] = None

class GenerateTryOnRequest(BaseModel):
    outfitName: Optional[str] = None
    prompt: Optional[str] = None
    itemsStr: Optional[str] = None
    selfieBase64: Optional[str] = None

class UploadUrlRequest(BaseModel):
    filename: str
