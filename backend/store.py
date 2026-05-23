"""
In-memory data store — replaces PostgreSQL for hackathon development.

Provides the same data access patterns as the ORM layer but stores
everything in Python dicts.  Data is seeded from the catalog JSON on
startup and lives only for the lifetime of the process.
"""

from __future__ import annotations

import json
import uuid
import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
CATALOG_JSON_PATH = Path(__file__).resolve().parent.parent / "gymshark_closet_inventory.json"

# ---------------------------------------------------------------------------
# In-memory tables
# ---------------------------------------------------------------------------
_catalog_items: Dict[int, Dict[str, Any]] = {}
_sessions: Dict[str, Dict[str, Any]] = {}           # keyed by session_token
_outfits: Dict[str, Dict[str, Any]] = {}             # keyed by outfit_id_label
_conversation_turns: Dict[str, List[Dict[str, Any]]] = {}  # session_token → [turns]
_next_catalog_id = 1
_next_session_id = 1
_next_outfit_db_id = 1


# ===== Catalog ==============================================================

def seed_catalog() -> int:
    """Load catalog items from JSON. Returns count of items loaded."""
    global _next_catalog_id
    if _catalog_items:
        return len(_catalog_items)

    if not CATALOG_JSON_PATH.exists():
        print(f"Warning: catalog file not found at {CATALOG_JSON_PATH}")
        return 0

    with open(CATALOG_JSON_PATH) as f:
        data = json.load(f)

    count = 0
    for gender in ("mens", "womens"):
        for item in data.get(gender, []):
            cid = _next_catalog_id
            _next_catalog_id += 1
            _catalog_items[cid] = {
                "id": cid,
                "name": item["name"],
                "image_url": item["image_url"],
                "description": item.get("description"),
                "category": item["category"],
                "gender": gender,
                "color": item.get("color"),
                "fit": item.get("fit"),
                "activity": item.get("activity"),
                "collection": item.get("collection"),
                "product_link": item.get("product_link"),
                "colors": None,
                "style_tags": None,
                "style_vector": None,
                "created_at": datetime.datetime.utcnow().isoformat(),
            }
            count += 1

    print(f"Seeded {count} catalog items from {CATALOG_JSON_PATH.name}.")
    return count


def catalog_count() -> int:
    return len(_catalog_items)


def get_catalog_item(item_id: int) -> Optional[Dict[str, Any]]:
    return _catalog_items.get(item_id)


def query_catalog(
    *,
    gender: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
    color: Optional[str] = None,
    activity: Optional[str] = None,
    collection: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[int, List[Dict[str, Any]]]:
    """Return (total_matching, page_of_items)."""
    results = list(_catalog_items.values())

    if gender:
        results = [i for i in results if i["gender"] == gender]
    if category:
        results = [i for i in results if i["category"] == category]
    if color:
        lc = color.lower()
        results = [i for i in results if i.get("color") and lc in i["color"].lower()]
    if activity:
        la = activity.lower()
        results = [i for i in results if i.get("activity") and la in i["activity"].lower()]
    if collection:
        lco = collection.lower()
        results = [i for i in results if i.get("collection") and lco in i["collection"].lower()]
    if search:
        ls = search.lower()
        results = [
            i for i in results
            if ls in (i["name"] or "").lower()
            or ls in (i["description"] or "").lower()
        ]

    total = len(results)
    page = results[offset : offset + limit]
    return total, page


def category_counts() -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for item in _catalog_items.values():
        cat = item["category"]
        counts[cat] = counts.get(cat, 0) + 1
    return counts


def add_catalog_item(item_data: Dict[str, Any]) -> Dict[str, Any]:
    """Insert a new catalog item (e.g. from /api/catalog/ingest)."""
    global _next_catalog_id
    cid = _next_catalog_id
    _next_catalog_id += 1
    row = {
        "id": cid,
        "name": item_data.get("name", "Unknown"),
        "image_url": item_data.get("image_url", ""),
        "description": item_data.get("description"),
        "category": item_data.get("category", "Tops"),
        "gender": item_data.get("gender", "mens"),
        "color": item_data.get("color"),
        "fit": item_data.get("fit"),
        "activity": item_data.get("activity"),
        "collection": item_data.get("collection"),
        "product_link": item_data.get("product_link") or item_data.get("source_url"),
        "colors": item_data.get("colors"),
        "style_tags": item_data.get("style_tags"),
        "style_vector": None,
        "created_at": datetime.datetime.utcnow().isoformat(),
    }
    _catalog_items[cid] = row
    return row


# ===== Sessions ==============================================================

def create_session(
    *,
    worker_id: Optional[str] = None,
    store_id: Optional[str] = None,
    selfie_url: Optional[str] = None,
    gender_preference: Optional[str] = None,
    favorite_colors: Optional[List[str]] = None,
    disliked_styles: Optional[List[str]] = None,
    occasion: Optional[str] = None,
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    global _next_session_id
    token = str(uuid.uuid4())
    sid = _next_session_id
    _next_session_id += 1
    session = {
        "id": sid,
        "session_token": token,
        "worker_id": worker_id,
        "store_id": store_id,
        "status": "intake",
        "selfie_url": selfie_url,
        "gender_preference": gender_preference,
        "favorite_colors": favorite_colors,
        "disliked_styles": disliked_styles,
        "occasion": occasion,
        "notes": notes,
        "intent": None,
        "customer_photo_url": None,
        "created_at": datetime.datetime.utcnow().isoformat(),
    }
    _sessions[token] = session
    _conversation_turns[token] = []
    return session


def get_session(token: str) -> Optional[Dict[str, Any]]:
    return _sessions.get(token)


def update_session(token: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    session = _sessions.get(token)
    if not session:
        return None
    for k, v in updates.items():
        if v is not None:
            session[k] = v
    return session


def close_session(token: str, outcome: Optional[str] = None, notes: Optional[str] = None) -> Optional[Dict[str, Any]]:
    session = _sessions.get(token)
    if not session:
        return None
    session["status"] = "closed"
    if outcome:
        session["outcome"] = outcome
    if notes:
        session["close_notes"] = notes
    return session


# ===== Conversation Turns ====================================================

def add_conversation_turn(
    session_token: str,
    *,
    role: str,
    content: str,
    turn_id: Optional[str] = None,
    recommendations_snapshot: Optional[List[Dict[str, Any]]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    tid = turn_id or f"turn_{uuid.uuid4().hex[:8]}"
    turn = {
        "turn_id": tid,
        "session_token": session_token,
        "role": role,
        "content": content,
        "recommendations_snapshot": recommendations_snapshot,
        "metadata": metadata,
        "created_at": datetime.datetime.utcnow().isoformat(),
    }
    _conversation_turns.setdefault(session_token, []).append(turn)
    return turn


def get_conversation_history(session_token: str) -> List[Dict[str, Any]]:
    return _conversation_turns.get(session_token, [])


# ===== Outfits ===============================================================

def save_outfit(
    *,
    session_token: str,
    outfit_id_label: str,
    item_ids: List[int],
    reason: Optional[str] = None,
    style_tags: Optional[List[str]] = None,
    styling_tip: Optional[str] = None,
    confidence_score: Optional[float] = None,
    ranking: Optional[int] = None,
) -> Dict[str, Any]:
    global _next_outfit_db_id
    oid = _next_outfit_db_id
    _next_outfit_db_id += 1
    outfit = {
        "id": oid,
        "session_token": session_token,
        "outfit_id_label": outfit_id_label,
        "item_ids": item_ids,
        "reason": reason,
        "style_tags": style_tags,
        "styling_tip": styling_tip,
        "confidence_score": confidence_score,
        "ranking": ranking,
        "total_price": None,
        # Try-on fields (db_handoff_tryon_guardrail_agents.md)
        "tryon_image_url": None,
        "tryon_status": None,
        "tryon_model": None,
        "tryon_created_at": None,
        # Guardrail fields
        "guardrail_pass": None,
        "guardrail_score": None,
        "guardrail_issues": None,
        "guardrail_dimension_scores": None,
        "guardrail_checked_at": None,
        "created_at": datetime.datetime.utcnow().isoformat(),
    }
    _outfits[outfit_id_label] = outfit
    return outfit


def get_outfit(outfit_id_label: str) -> Optional[Dict[str, Any]]:
    return _outfits.get(outfit_id_label)


def get_outfits_for_session(session_token: str) -> List[Dict[str, Any]]:
    return [
        o for o in _outfits.values()
        if o["session_token"] == session_token
    ]


def update_outfit(outfit_id_label: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    outfit = _outfits.get(outfit_id_label)
    if not outfit:
        return None
    for k, v in updates.items():
        outfit[k] = v
    return outfit


def resolve_outfit_items(item_ids: List[int]) -> List[Dict[str, Any]]:
    """Look up full catalog item data for a list of IDs."""
    return [_catalog_items[iid] for iid in item_ids if iid in _catalog_items]
