"""
Full Flow Integration Test — exercises the complete agentic pipeline.

Simulates:
1. Customer Walk-In & Session Start
2. Customer Selfie / Photo Upload (using local mock S3 fallback)
3. Session Intake (Intake prompt + uploaded selfie)
4. AI Agent Pipeline: Customer Understanding & Catalog Retrieval
5. On-Demand Try-On generation on the uploaded photo
6. Guardrail Agent faithfulness check on the generated composite
7. Outfits final ranking and styling advice

Run with:
    cd backend
    .venv/bin/python ../tests/test_full_flow.py
"""

import os
import sys
import json
from pathlib import Path

# Add backend directory to sys.path so we can import models and app
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from main import app
import store

# ---------------------------------------------------------------------------
# Setup Paths & Data
# ---------------------------------------------------------------------------
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
CUSTOMER_PIC_PATH = FIXTURES_DIR / "customers" / "customer_01_fullbody.jpeg"

def run_integration_test():
    print("=" * 70)
    print("STARTING CLOSENT AI AGENTIC PIPELINE FLOW INTEGRATION TEST")
    print("=" * 70)

    # 1. Ensure catalog is seeded in-memory
    store.seed_catalog()
    print(f"Loaded store catalog count: {store.catalog_count()} items.")

    # 2. Check customer test image exists
    if not CUSTOMER_PIC_PATH.exists():
        print(f"Error: Customer image not found at {CUSTOMER_PIC_PATH}")
        sys.exit(1)
    
    with open(CUSTOMER_PIC_PATH, "rb") as f:
        photo_bytes = f.read()
    print(f"Loaded customer test photo ({len(photo_bytes)} bytes) successfully.")

    # 3. Create FastAPI TestClient
    client = TestClient(app)

    # 4. Request Upload URL
    print("\n[Step 1] Requesting presigned upload URL...")
    filename = "test_customer_selfie.jpg"
    upload_url_response = client.post("/api/upload-url", json={"filename": filename})
    assert upload_url_response.status_code == 200, "Failed to get upload URL"
    
    upload_data = upload_url_response.json()
    upload_target = upload_data.get("upload_url")
    file_public_url = upload_data.get("file_url")
    print(f"  - Target Upload Endpoint: {upload_target}")
    print(f"  - Resulting Public File URL: {file_public_url}")

    # 5. Upload customer selfie photo using the mock fallback path
    print("\n[Step 2] Uploading customer photo bytes...")
    # S3 mock target contains '/api/mock-upload?filename=...'
    # If using local mock, we post/put directly to that path of the client
    if "api/mock-upload" in upload_target:
        mock_upload_path = upload_target.split("http://localhost:8000")[1]
        upload_response = client.put(mock_upload_path, content=photo_bytes)
    else:
        # If a real presigned URL is returned, trigger real PUT (mocked here in Client context)
        upload_response = client.put(upload_target, content=photo_bytes)
        
    assert upload_response.status_code == 200, "Photo upload failed"
    print("  - Selfie photo uploaded successfully!")

    # 6. Verify static file serving retrieves the uploaded image
    print("\n[Step 3] Verifying uploaded photo is accessible and served...")
    static_file_path = f"/static/uploads/{filename}"
    static_get_response = client.get(static_file_path)
    assert static_get_response.status_code == 200, f"Served upload at {static_file_path} failed"
    print(f"  - Upload is verified and active at: {static_file_path} ({len(static_get_response.content)} bytes served)")

    # 7. Start a walk-in Customer Session
    print("\n[Step 4] Initializing walk-in Shopper Session...")
    session_response = client.post("/api/sessions", json={
        "worker_id": "copilot_employee_01",
        "store_id": "gymshark_london_01",
        "occasion": "rooftop active dinner",
        "gender_preference": "womens",
        "favorite_colors": ["black", "charcoal"],
    })
    assert session_response.status_code == 200, "Failed to start session"
    session_data = session_response.json()
    session_token = session_data["session_token"]
    print(f"  - Shopper Session created! Token: {session_token[:12]}...")

    # 8. Trigger Customer Intake (Intake Prompt + uploaded photo URL)
    print("\n[Step 5] Launching Customer Intake Agent Pipeline...")
    intake_prompt = "I need a matching comfortable, modern training set for gym-to-dinner rooftop events."
    intake_response = client.post(f"/api/sessions/{session_token}/intake", json={
        "prompt": intake_prompt,
        "customer_photo_url": file_public_url
    })
    assert intake_response.status_code == 200, "Failed to complete intake"
    intake_data = intake_response.json()
    print(f"  - Intake complete! Compiled {len(intake_data['recommendations'])} coordinated outfits.")
    
    # Verify the Multi-Agent Pipeline steps returned
    stages = intake_data.get("pipeline_stages", {})
    print("\n  - Pipeline Agent Telemetry Verification:")
    print(f"    * Customer Understanding Agent: {stages.get('customer_understanding', {}).get('style_goal')}")
    print(f"    * Catalog Retrieval Agent: Compiled {len(stages.get('catalog_retrieval', []))} outfits.")
    print(f"    * Fashion Master Agent Top Recommendation: {stages.get('fashion_master', {}).get('top_choice')}")

    # 9. Perform On-Demand Try-On for the top pick outfit
    print("\n[Step 6] Generating Synthetic Virtual Try-On for Top Outfit...")
    top_outfit_id = intake_data["top_choice"]
    tryon_response = client.post(f"/api/sessions/{session_token}/try-on", json={
        "recommendation_id": top_outfit_id,
        "customer_photo_url": file_public_url
    })
    assert tryon_response.status_code == 200, "Failed to trigger try-on"
    tryon_data = tryon_response.json()
    print(f"  - Try-On finished! Status: {tryon_data['status']}")
    print(f"  - Try-On Composite URL: {tryon_data['tryon_image_url']}")

    # 10. Run the Guardrail Agent check
    print("\n[Step 7] Running Guardrail Agent Multimodal Faithfulness check...")
    guardrail_response = client.post("/api/guardrail-check", json={
        "outfit_id": top_outfit_id,
        "tryon_image_url": tryon_data["tryon_image_url"],
        "selfie_url": file_public_url,
        "garment_urls": [tryon_data["tryon_image_url"]]
    })
    assert guardrail_response.status_code == 200, "Failed to run guardrail"
    guardrail_data = guardrail_response.json()
    print(f"  - Guardrail evaluation pass: {guardrail_data['pass']}")
    print(f"  - Overall Faithfulness Score: {guardrail_data['faithfulness_score']}")
    
    dims = guardrail_data.get("dimension_scores", {})
    print("    * Dimension Scores:")
    for metric, score in dims.items():
         print(f"      - {metric:25}: {score}")

    # 11. Refine Recommendations converationally
    print("\n[Step 8] Triggering Conversational Stylist refinement loop...")
    refine_response = client.post(f"/api/sessions/{session_token}/refine", json={
        "feedback": "Something slightly warmer with outerwear layering",
        "feedback_type": "text",
        "rejected_recommendation_ids": [top_outfit_id]
    })
    assert refine_response.status_code == 200, "Failed to refine recommendations"
    refine_data = refine_response.json()
    print(f"  - Refinement loop done! Worker message: {refine_data['worker_message']}")
    
    refine_stages = refine_data.get("pipeline_stages", {})
    print(f"    * Conversational Stylist Agent message: {refine_stages.get('conversational_stylist', {}).get('worker_message')}")

    # 12. Complete/Close the Session
    print("\n[Step 9] Closing Shopper Session with purchase logging...")
    close_response = client.patch(f"/api/sessions/{session_token}/close", json={
        "outcome": "purchased",
        "notes": f"Customer bought matching set after trying on {top_outfit_id}"
    })
    assert close_response.status_code == 200, "Failed to close session"
    print(f"  - Session status changed to: {close_response.json()['status']}")
    print("=" * 70)
    print("SUCCESS: INTEGRATION TEST COMPLETED SUCCESSFULLY!")
    print("=" * 70)

if __name__ == "__main__":
    run_integration_test()
