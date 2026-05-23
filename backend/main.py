import os
import shutil
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, Query, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text, select
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from database import engine, SessionLocal, Base, get_db
from models import ClosetItem, Outfit
from services import s3 as s3_service
from services import gemini as gemini_service
from services import replicate_service

# Lifespan context manager for startup and shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup tasks
    print("Starting ClosetAI Backend...")
    try:
        # Enable pgvector extension inside PostgreSQL if it exists
        with SessionLocal() as db:
            db.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            db.commit()
            print("Verified PostgreSQL vector extension.")
    except Exception as e:
        print(f"Note: Could not automatically verify pgvector extension (might not be a pg database or missing superuser privileges): {e}")

    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("Database schemas created.")
    except Exception as e:
        print(f"Warning: Database table creation failed: {e}")
        
    # Ensure static directory exists for mock uploads
    os.makedirs("./static/uploads", exist_ok=True)
    yield
    # Shutdown tasks
    print("Shutting down ClosetAI Backend...")

app = FastAPI(title="ClosetAI Backend", lifespan=lifespan)

# Allow Next.js frontend to connect (local development and custom origins)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this to your Next.js domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve local static uploads directory so mock uploads can be previewed directly
# Since static/ is at the root, and we are running from backend/, go up one level
app.mount("/static", StaticFiles(directory="../static"), name="static")

# --- Schemas ---

class ProcessItemRequest(BaseModel):
    user_id: str
    file_url: str

class GenerateOutfitRequest(BaseModel):
    user_id: str
    prompt: str
    weather_context: Optional[str] = "70°F, Sunny"

class VirtualTryOnRequest(BaseModel):
    user_id: str
    selfie_url: str
    garment_url: str

# --- Endpoints ---

@app.get("/api/upload-url")
def get_upload_url(filename: str = Query(..., description="The name of the file to be uploaded")):
    """
    Generates a secure, pre-signed AWS S3 URL.
    If S3 keys are missing, gracefully falls back to a mock local upload endpoint.
    """
    url_details = s3_service.generate_presigned_url(filename)
    if not url_details:
        raise HTTPException(status_code=500, detail="Failed to generate upload URL")
    return url_details

@app.post("/api/mock-upload")
async def mock_upload(file: UploadFile = File(...)):
    """
    Fallback endpoint to accept direct local file uploads when S3 is not configured.
    """
    upload_dir = "./static/uploads"
    os.makedirs(upload_dir, exist_ok=True)
    
    file_path = os.path.join(upload_dir, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    local_url = f"http://localhost:8000/static/uploads/{file.filename}"
    return {
        "status": "success",
        "file_url": local_url,
        "filename": file.filename
    }

@app.post("/api/process-item")
def process_item(request: ProcessItemRequest, db: Session = Depends(get_db)):
    """
    Triggered after successful image upload.
    Coordinates SAM-2/Rembg cropping, Gemini 1.5 categorization, 
    and Vector Embeddings insertion to pgvector.
    """
    try:
        file_url = request.file_url
        
        # 1. OPTIONAL: Crop individual item from image using Replicate/SAM-2 style background removal
        cropped_url = replicate_service.crop_item_with_sam2(file_url)
        active_url = cropped_url if cropped_url else file_url
        
        # 2. ANALYSIS: Feed cropped/processed image to Gemini 1.5 to get structured attributes
        metadata = gemini_service.analyze_clothing_item(active_url)
        
        # 3. EMBEDDING: Formulate a semantic text summary of the clothing piece and embed it with text-embedding-004
        tags_str = ", ".join(metadata.get("style_tags", []))
        embedding_source_text = f"A {metadata.get('color', 'unknown')} {metadata.get('sub_category', 'item')} for {metadata.get('season', 'all-season')} wear. Tags: {tags_str}"
        
        style_vector = gemini_service.get_style_embedding(embedding_source_text)
        
        # 4. DATABASE: Store new closet item
        db_item = ClosetItem(
            user_id=request.user_id,
            s3_image_url=active_url,
            category=metadata.get("category"),
            sub_category=metadata.get("sub_category"),
            color=metadata.get("color"),
            season=metadata.get("season"),
            style_tags=metadata.get("style_tags", []),
            style_vector=style_vector
        )
        
        db.add(db_item)
        db.commit()
        db.refresh(db_item)
        
        return {
            "status": "success",
            "item_id": db_item.id,
            "extracted_data": {
                "category": db_item.category,
                "sub_category": db_item.sub_category,
                "color": db_item.color,
                "season": db_item.season,
                "style_tags": db_item.style_tags,
                "s3_image_url": db_item.s3_image_url
            }
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to process closet item: {str(e)}")

@app.post("/api/generate-outfit")
def generate_outfit(request: GenerateOutfitRequest, db: Session = Depends(get_db)):
    """
    Performs pgvector similarity matching against user's closet items
    and uses Gemini to construct 3 elegant outfit combinations.
    """
    try:
        # 1. Generate text embedding of the styling prompt
        prompt_vector = gemini_service.get_style_embedding(request.prompt)
        
        # 2. Vector search via pgvector to retrieve top matching items
        # Fallback query if vector similarity is not supported or raises an error
        try:
            # cosine_distance is standard in pgvector
            closet_items_query = db.query(ClosetItem)\
                .filter(ClosetItem.user_id == request.user_id)\
                .order_by(ClosetItem.style_vector.cosine_distance(prompt_vector))\
                .limit(15).all()
        except Exception as vec_err:
            print(f"Vector search failed (falling back to conventional database query): {vec_err}")
            # Fallback to standard selection
            closet_items_query = db.query(ClosetItem).filter(ClosetItem.user_id == request.user_id).limit(20).all()
            
        if not closet_items_query:
            return {
                "message": "No clothing items found in your closet yet. Please upload items first!",
                "outfits": []
            }
            
        # Convert DB models to pure dictionary representations for Gemini service
        serialized_items = []
        for item in closet_items_query:
            serialized_items.append({
                "id": item.id,
                "category": item.category,
                "sub_category": item.sub_category,
                "color": item.color,
                "season": item.season,
                "style_tags": item.style_tags,
                "s3_image_url": item.s3_image_url
            })
            
        # 3. Call Gemini acting as a personal stylist to design outfits
        weather = request.weather_context or "70°F, Sunny"
        outfits = gemini_service.design_outfits_with_gemini(request.prompt, weather, serialized_items)
        
        # 4. Optional: Save outfits history to DB
        for outfit in outfits:
            item_ids = [itm["item_id"] for itm in outfit.get("items", [])]
            db_outfit = Outfit(
                user_id=request.user_id,
                description=outfit.get("description"),
                item_ids=item_ids
            )
            db.add(db_outfit)
        db.commit()
        
        return {
            "outfits": outfits
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to generate outfits: {str(e)}")

@app.post("/api/virtual-try-on")
def virtual_try_on(request: VirtualTryOnRequest):
    """
    Submits a serverless virtual try-on prediction on Replicate (IDM-VTON).
    """
    try:
        response = replicate_service.trigger_virtual_tryon(
            selfie_url=request.selfie_url,
            garment_url=request.garment_url
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to launch try-on request: {str(e)}")

@app.get("/api/try-on/status/{prediction_id}")
def try_on_status(prediction_id: str):
    """
    Polls the status of a specific virtual try-on generation on Replicate.
    """
    try:
        status_info = replicate_service.get_prediction_status(prediction_id)
        return status_info
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check try-on status: {str(e)}")

@app.get("/api/closet")
def list_closet(user_id: str = Query(..., description="Filter items by user ID"), db: Session = Depends(get_db)):
    """
    Lists all closet items for a specific user.
    """
    try:
        items = db.query(ClosetItem).filter(ClosetItem.user_id == user_id).all()
        return {
            "count": len(items),
            "items": [
                {
                    "id": item.id,
                    "s3_image_url": item.s3_image_url,
                    "category": item.category,
                    "sub_category": item.sub_category,
                    "color": item.color,
                    "season": item.season,
                    "style_tags": item.style_tags,
                    "created_at": item.created_at
                }
                for item in items
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch closet: {str(e)}")

@app.get("/")
def health_check():
    """Simple API health check endpoint."""
    return {
        "status": "ok",
        "service": "ClosetAI API",
        "features_enabled": {
            "s3": os.getenv("AWS_ACCESS_KEY_ID") is not None,
            "gemini": os.getenv("GEMINI_API_KEY") is not None,
            "replicate": os.getenv("REPLICATE_API_TOKEN") is not None,
            "database": os.getenv("DATABASE_URL") is not None
        }
    }
