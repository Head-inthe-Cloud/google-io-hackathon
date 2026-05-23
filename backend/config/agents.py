"""Centralized model IDs and thresholds for agent pipeline."""

TRYON_MODEL = "gemini-3.1-flash-image-preview"
GUARDRAIL_MODEL = "gemini-3.5-flash"

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
