"""
Try-On Visualization Agent — Nano Banana 2 (Gemini 3.1 Flash Image).

Generates a virtual try-on image from a customer photo and catalog garment image.
Used by the test script and optionally by FastAPI try-on endpoints.
"""

import logging
import mimetypes
from pathlib import Path
from typing import Any, Dict, List, Optional

from google.genai import types

from config.agents import TRYON_MODEL
from services.gemini import fetch_image_bytes, init_gemini

logger = logging.getLogger(__name__)

TRYON_PROMPT_TEMPLATE = """You are the Virtual Try-On Visualization Agent for an in-store AI stylist copilot.

Generate ONE photorealistic image showing the person from the customer photo wearing the garment from the catalog product image.

Hard rules:
- Preserve the customer's identity: face, skin tone, hair, body proportions, and pose.
- Preserve the background and lighting style from the customer photo when possible.
- Apply ONLY the specified catalog garment to the correct body region (top on torso, bottom on legs, outerwear as a layer).
- Match garment color, silhouette, neckline/sleeve length, and visible patterns/logos from the product image.
- Do NOT swap the person for a different model or change their gender/age.
- Do NOT add text overlays, watermarks, collages, or extra garments not in the outfit plan.
- If the customer photo is upper-body only, generate an upper-body result; do not invent full legs.

Outfit metadata:
- recommendation_id: {recommendation_id}
- outfit_reason: {reason}
- primary_garment: {garment_name} ({category})
- garment_colors: {colors}
- all_outfit_items: {item_names_list}

For multi-item outfits, render ONLY the primary garment in this pass (v1). Other items are context only."""


def pick_primary_garment(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Pick the primary garment for v1 single-garment try-on."""
    priority = ("top", "sports bra", "sports_bra", "bra", "bottom", "outerwear")
    for category in priority:
        for item in items:
            if item.get("category", "").lower().replace("_", " ") == category.replace("_", " "):
                return item
            if category.replace("_", " ") in item.get("category", "").lower():
                return item
    return items[0]


def _mime_type_for_bytes(data: bytes, fallback: str = "image/jpeg") -> str:
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return fallback


def _mime_type_for_path(path: Path) -> str:
    guessed, _ = mimetypes.guess_type(str(path))
    return guessed or "image/jpeg"


def build_tryon_prompt(
    recommendation: Dict[str, Any],
    primary_garment: Dict[str, Any],
    all_items: List[Dict[str, Any]],
) -> str:
    """Build the try-on generation prompt from recommendation metadata."""
    item_names = [item.get("name", item.get("item_id", "unknown")) for item in all_items]
    colors = primary_garment.get("colors", [])
    return TRYON_PROMPT_TEMPLATE.format(
        recommendation_id=recommendation.get("recommendation_id", "unknown"),
        reason=recommendation.get("reason", ""),
        garment_name=primary_garment.get("name", "unknown"),
        category=primary_garment.get("category", "unknown"),
        colors=", ".join(colors) if colors else "unknown",
        item_names_list=", ".join(item_names),
    )


def generate_tryon_image(
    customer_image: bytes,
    garment_image: bytes,
    prompt: str,
    customer_mime: str = "image/jpeg",
    garment_mime: str = "image/jpeg",
) -> bytes:
    """
    Call Nano Banana 2 to generate a try-on image.

    Returns PNG/JPEG bytes from the model response.
    """
    if not init_gemini():
        raise RuntimeError("GEMINI_API_KEY not configured")

    from services.gemini import get_client

    client = get_client()
    if client is None:
        raise RuntimeError("GEMINI_API_KEY not configured")

    logger.info(
        "tryon_agent.generate_tryon_image model=%s prompt_len=%d",
        TRYON_MODEL,
        len(prompt),
    )

    contents = [
        types.Part.from_bytes(data=customer_image, mime_type=customer_mime),
        types.Part.from_bytes(data=garment_image, mime_type=garment_mime),
        types.Part.from_text(text=prompt),
    ]

    config = types.GenerateContentConfig(
        response_modalities=["TEXT", "IMAGE"],
    )

    response = client.models.generate_content(
        model=TRYON_MODEL,
        contents=contents,
        config=config,
    )

    if not response.candidates:
        raise RuntimeError("Try-on model returned no candidates")

    for part in response.candidates[0].content.parts:
        if part.inline_data and part.inline_data.data:
            logger.info("tryon_agent.generate_tryon_image output_bytes=%d", len(part.inline_data.data))
            return part.inline_data.data

    raise RuntimeError("Try-on model returned no image in response")


def generate_tryon_from_recommendation(
    customer_photo_path: Path,
    recommendation: Dict[str, Any],
    catalog_items: List[Dict[str, Any]],
    output_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Run try-on for a recommendation using a local customer photo and catalog items.

    Returns metadata including output path and primary garment used.
    """
    primary = pick_primary_garment(catalog_items)
    prompt = build_tryon_prompt(recommendation, primary, catalog_items)

    customer_bytes = customer_photo_path.read_bytes()
    garment_bytes = fetch_image_bytes(primary["image_url"])

    image_bytes = generate_tryon_image(
        customer_image=customer_bytes,
        garment_image=garment_bytes,
        prompt=prompt,
        customer_mime=_mime_type_for_path(customer_photo_path),
        garment_mime=_mime_type_for_bytes(garment_bytes),
    )

    result: Dict[str, Any] = {
        "recommendation_id": recommendation.get("recommendation_id"),
        "primary_garment_id": primary.get("item_id"),
        "primary_garment_name": primary.get("name"),
        "prompt": prompt,
        "model": TRYON_MODEL,
    }

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(image_bytes)
        result["output_path"] = str(output_path)
        logger.info("tryon_agent saved output_path=%s", output_path)

    result["image_bytes_len"] = len(image_bytes)
    return result
