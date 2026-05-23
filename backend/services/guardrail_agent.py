"""
Guardrail Agent — Gemini 3.5 Flash multimodal faithfulness check.

Compares customer photo, garment references, and generated try-on output.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from google.genai import types

from config.agents import GUARDRAIL_MODEL, GUARDRAIL_PASS_THRESHOLD
from services.gemini import fetch_image_bytes, init_gemini
from services.tryon_agent import _mime_type_for_bytes, _mime_type_for_path

logger = logging.getLogger(__name__)

GUARDRAIL_SYSTEM_INSTRUCTION = """You are the Virtual Try-On Guardrail Agent for an in-store retail stylist copilot.

Decide whether a generated try-on image is faithful enough and safe to show a store worker and customer.

You receive:
1. Original customer photo
2. Catalog garment reference image(s)
3. Generated try-on image
4. Outfit metadata (recommendation_id, intended items, categories, colors)

Evaluate each dimension (0.0–1.0):
- identity_consistency: same person as customer photo (face, skin tone, body proportions)
- garment_category_match: correct garment type and body placement (top/bottom/outerwear/bra)
- color_fidelity: dominant colors match catalog reference
- pattern_fidelity: logos, textures, seams, prints reasonably preserved
- fit_and_placement: garment worn naturally, not floating or misaligned
- artifact_check: no duplicated limbs, melted fabric, extra phantom garments, NSFW content

Scoring:
- faithfulness_score = weighted average:
  identity 0.30, category 0.15, color 0.20, pattern 0.15, fit 0.10, artifacts 0.10
- pass = true ONLY if faithfulness_score >= 0.75 AND issues contains no CRITICAL entries

CRITICAL issues (always fail):
- wrong_person
- wrong_garment_category
- severe_face_distortion
- nsfw_or_unsafe
- completely_wrong_garment_color

Return ONLY valid JSON:
{
  "recommendation_id": "string",
  "pass": boolean,
  "faithfulness_score": number,
  "issues": ["string"],
  "dimension_scores": {
    "identity_consistency": number,
    "garment_category_match": number,
    "color_fidelity": number,
    "pattern_fidelity": number,
    "fit_and_placement": number,
    "artifact_check": number
  }
}"""


def build_guardrail_metadata(
    recommendation: Dict[str, Any],
    catalog_items: List[Dict[str, Any]],
    primary_garment_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Build metadata block sent to the guardrail agent."""
    return {
        "recommendation_id": recommendation.get("recommendation_id"),
        "reason": recommendation.get("reason"),
        "primary_garment_id": primary_garment_id,
        "items": [
            {
                "item_id": item.get("item_id"),
                "name": item.get("name"),
                "category": item.get("category"),
                "colors": item.get("colors", []),
            }
            for item in catalog_items
        ],
    }


def check_tryon_guardrail(
    customer_image: bytes,
    garment_images: List[bytes],
    tryon_image: bytes,
    metadata: Dict[str, Any],
    customer_mime: str = "image/jpeg",
    garment_mimes: Optional[List[str]] = None,
    tryon_mime: str = "image/jpeg",
) -> Dict[str, Any]:
    """
    Run the Guardrail Agent on a generated try-on result.

    Returns structured pass/fail JSON from the model.
    """
    if not init_gemini():
        raise RuntimeError("GEMINI_API_KEY not configured")

    from services.gemini import get_client

    client = get_client()
    if client is None:
        raise RuntimeError("GEMINI_API_KEY not configured")

    garment_mimes = garment_mimes or [
        _mime_type_for_bytes(img) for img in garment_images
    ]

    user_text = (
        "Validate this try-on result.\n\n"
        f"Metadata:\n{json.dumps(metadata, indent=2)}\n\n"
        "Image order:\n"
        "1 = customer photo\n"
        f"2..{1 + len(garment_images)} = catalog garment references (in item order)\n"
        f"Last image = generated try-on output"
    )

    parts: List[types.Part] = [
        types.Part.from_bytes(data=customer_image, mime_type=customer_mime),
    ]
    for img_bytes, mime in zip(garment_images, garment_mimes):
        parts.append(types.Part.from_bytes(data=img_bytes, mime_type=mime))
    parts.append(types.Part.from_bytes(data=tryon_image, mime_type=tryon_mime))
    parts.append(types.Part.from_text(text=user_text))

    logger.info(
        "guardrail_agent.check_tryon_guardrail model=%s recommendation_id=%s",
        GUARDRAIL_MODEL,
        metadata.get("recommendation_id"),
    )

    response = client.models.generate_content(
        model=GUARDRAIL_MODEL,
        contents=parts,
        config=types.GenerateContentConfig(
            system_instruction=GUARDRAIL_SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
        ),
    )

    result = json.loads(response.text.strip())
    result.setdefault("recommendation_id", metadata.get("recommendation_id"))
    result.setdefault("pass_threshold", GUARDRAIL_PASS_THRESHOLD)
    return result


def check_tryon_from_paths(
    customer_photo_path: Path,
    tryon_image_path: Path,
    recommendation: Dict[str, Any],
    catalog_items: List[Dict[str, Any]],
    primary_garment_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Run guardrail check using local file paths and catalog item URLs."""
    customer_bytes = customer_photo_path.read_bytes()
    tryon_bytes = tryon_image_path.read_bytes()

    garment_images = [fetch_image_bytes(item["image_url"]) for item in catalog_items]
    metadata = build_guardrail_metadata(recommendation, catalog_items, primary_garment_id)

    return check_tryon_guardrail(
        customer_image=customer_bytes,
        garment_images=garment_images,
        tryon_image=tryon_bytes,
        metadata=metadata,
        customer_mime=_mime_type_for_path(customer_photo_path),
        tryon_mime=_mime_type_for_path(tryon_image_path),
    )
