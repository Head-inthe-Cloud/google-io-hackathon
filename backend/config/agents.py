"""Centralized model IDs and thresholds for agent pipeline."""

import os


PRIMARY_GEMINI_MODEL = os.getenv("GEMINI_MODEL") or os.getenv("RECOMMENDER_MODEL") or "gemini-3.5-flash"
TRYON_MODEL = os.getenv("TRYON_MODEL") or "gemini-2.5-flash-image"
GUARDRAIL_MODEL = os.getenv("GUARDRAIL_MODEL") or PRIMARY_GEMINI_MODEL

GUARDRAIL_PASS_THRESHOLD = 0.75

GUARDRAIL_WEIGHTS = {
    "identity_consistency": 0.30,
    "garment_category_match": 0.15,
    "color_fidelity": 0.20,
    "pattern_fidelity": 0.15,
    "fit_and_placement": 0.10,
    "artifact_check": 0.10,
}

TRYON_API_DELAY_SECONDS = 1.5
