#!/usr/bin/env python3
"""
CLI test runner for Try-On Visualization + Guardrail agents.

Loads fixture catalog/recommendations, runs Nano Banana 2 try-on generation,
then Gemini 3.5 Flash guardrail validation. Writes outputs under tests/fixtures/outputs/.

Usage:
  conda activate ai2
  cd backend && python scripts/test_tryon_guardrail.py --dry-run
  cd backend && python scripts/test_tryon_guardrail.py --scenario rec_m_gym_001
  cd backend && python scripts/test_tryon_guardrail.py --all
"""

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

# Repo paths
BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_DIR.parent
FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures"
OUTPUTS_DIR = FIXTURES_DIR / "outputs"
DEFAULT_CUSTOMER_PHOTO = FIXTURES_DIR / "customers" / "customer_01_fullbody.jpeg"
DEFAULT_CUSTOMER_PHOTO_UPPER = FIXTURES_DIR / "customers" / "customer_02_upperbody.jpeg"

sys.path.insert(0, str(BACKEND_DIR))
load_dotenv(BACKEND_DIR / ".env")

from config.agents import TRYON_API_DELAY_SECONDS
from services.tryon_agent import (
    build_tryon_prompt,
    generate_tryon_from_recommendation,
    pick_primary_garment,
)
from services.guardrail_agent import check_tryon_from_paths


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("test_tryon_guardrail")


def load_json(path: Path) -> Dict[str, Any]:
    with open(path, "r") as f:
        return json.load(f)


def load_catalog() -> Dict[str, Dict[str, Any]]:
    data = load_json(FIXTURES_DIR / "sample_catalog.json")
    return {item["item_id"]: item for item in data["items"]}


def load_recommendations() -> List[Dict[str, Any]]:
    data = load_json(FIXTURES_DIR / "sample_recommendations.json")
    return data["recommendations"]


def resolve_recommendation_items(
    recommendation: Dict[str, Any],
    catalog_by_id: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    items = []
    for item_id in recommendation.get("items", []):
        if item_id not in catalog_by_id:
            raise KeyError(f"Catalog item not found: {item_id}")
        items.append(catalog_by_id[item_id])
    return items


def select_recommendations(
    all_recs: List[Dict[str, Any]],
    scenario: Optional[str],
    run_all: bool,
) -> List[Dict[str, Any]]:
    if run_all:
        return all_recs
    if scenario:
        matches = [r for r in all_recs if r["recommendation_id"] == scenario]
        if not matches:
            ids = [r["recommendation_id"] for r in all_recs]
            raise ValueError(f"Unknown scenario {scenario!r}. Available: {ids}")
        return matches
    return [all_recs[0]]


def dry_run_scenario(
    recommendation: Dict[str, Any],
    catalog_by_id: Dict[str, Dict[str, Any]],
    customer_photo: Path,
) -> None:
    items = resolve_recommendation_items(recommendation, catalog_by_id)
    primary = pick_primary_garment(items)
    prompt = build_tryon_prompt(recommendation, primary, items)

    print(f"\n--- {recommendation['recommendation_id']} ---")
    print(f"Scenario: {recommendation.get('scenario', 'n/a')}")
    print(f"Customer photo: {customer_photo} (exists={customer_photo.exists()})")
    print(f"Primary garment: {primary.get('item_id')} — {primary.get('name')}")
    print(f"Items: {[i['item_id'] for i in items]}")
    print(f"\nTry-on prompt preview:\n{prompt[:500]}...\n")


def run_scenario(
    recommendation: Dict[str, Any],
    catalog_by_id: Dict[str, Dict[str, Any]],
    customer_photo: Path,
    skip_guardrail: bool,
) -> Dict[str, Any]:
    rec_id = recommendation["recommendation_id"]
    items = resolve_recommendation_items(recommendation, catalog_by_id)
    primary = pick_primary_garment(items)

    output_png = OUTPUTS_DIR / f"{rec_id}.png"
    tryon_result = generate_tryon_from_recommendation(
        customer_photo_path=customer_photo,
        recommendation=recommendation,
        catalog_items=items,
        output_path=output_png,
    )

    summary: Dict[str, Any] = {
        "recommendation_id": rec_id,
        "tryon": tryon_result,
        "guardrail": None,
    }

    if skip_guardrail:
        return summary

    guardrail_result = check_tryon_from_paths(
        customer_photo_path=customer_photo,
        tryon_image_path=output_png,
        recommendation=recommendation,
        catalog_items=items,
        primary_garment_id=primary.get("item_id"),
    )

    guardrail_path = OUTPUTS_DIR / f"{rec_id}_guardrail.json"
    guardrail_path.parent.mkdir(parents=True, exist_ok=True)
    with open(guardrail_path, "w") as f:
        json.dump(guardrail_result, f, indent=2)

    summary["guardrail"] = guardrail_result
    summary["guardrail_path"] = str(guardrail_path)
    return summary


def print_summary(results: List[Dict[str, Any]]) -> None:
    print("\n=== Results ===")
    print(f"{'Scenario':<22} {'Pass':<6} {'Score':<8} {'Output'}")
    print("-" * 70)
    for row in results:
        rec_id = row["recommendation_id"]
        guardrail = row.get("guardrail") or {}
        passed = guardrail.get("pass", "n/a")
        score = guardrail.get("faithfulness_score", "n/a")
        output = row.get("tryon", {}).get("output_path", "")
        if isinstance(score, float):
            score = f"{score:.2f}"
        print(f"{rec_id:<22} {str(passed):<6} {str(score):<8} {output}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Test Try-On + Guardrail agents")
    parser.add_argument("--scenario", help="Run a single recommendation ID")
    parser.add_argument("--all", action="store_true", help="Run all fixture scenarios")
    parser.add_argument(
        "--customer-photo",
        type=Path,
        default=DEFAULT_CUSTOMER_PHOTO,
        help="Path to customer test photo",
    )
    parser.add_argument("--dry-run", action="store_true", help="Validate fixtures only")
    parser.add_argument("--skip-guardrail", action="store_true", help="Try-on only")
    args = parser.parse_args()

    catalog_by_id = load_catalog()
    all_recs = load_recommendations()
    selected = select_recommendations(all_recs, args.scenario, args.all)

    if args.dry_run:
        for rec in selected:
            dry_run_scenario(rec, catalog_by_id, args.customer_photo)
        print(f"\nDry run complete for {len(selected)} scenario(s).")
        return 0

    if not args.customer_photo.exists():
        logger.error("Customer photo not found: %s", args.customer_photo)
        return 1

    results = []
    for i, rec in enumerate(selected):
        logger.info("Running scenario %s (%d/%d)", rec["recommendation_id"], i + 1, len(selected))
        try:
            result = run_scenario(
                rec,
                catalog_by_id,
                args.customer_photo,
                skip_guardrail=args.skip_guardrail,
            )
            results.append(result)
        except Exception as e:
            logger.exception("Scenario %s failed: %s", rec["recommendation_id"], e)
            results.append({"recommendation_id": rec["recommendation_id"], "error": str(e)})

        if i < len(selected) - 1:
            time.sleep(TRYON_API_DELAY_SECONDS)

    print_summary(results)
    failures = [r for r in results if r.get("error") or (r.get("guardrail") and not r["guardrail"].get("pass"))]
    return 1 if failures and not args.skip_guardrail else 0


if __name__ == "__main__":
    raise SystemExit(main())
