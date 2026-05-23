# Backend API Surface Refinement Plan (v3 — Pre-loaded Store Catalog)

## Business Context

A retailer (e.g. Gymshark) gives us their product catalog as a JSON file. We load it once into our database, run AI enrichment on it, and then serve outfit recommendations to shoppers visiting the store. No Shopify API calls at runtime. No user-uploaded closet.

**Data source:** `gymshark_closet_inventory.json` — a flat JSON with `mens` and `womens` arrays. Each item has:
```json
{
  "name": "Gymshark Crest T-Shirt - Black",
  "image_url": "https://cdn.shopify.com/...",
  "description": "Regular-fit cotton-blend tee with the signature embroidered Crest shark logo.",
  "category": "Tops"
}
```

---

## What the Backend Needs to Do

1. **Seed the catalog** — load items from JSON into the DB on startup (or via a one-time endpoint)
2. **Serve catalog to frontend** — `GET /api/catalog` with filters (gender, category)
3. **Accept shopper preferences** — lightweight session with selfie, style prefs, occasion
4. **Recommend outfits** — agent picks items from catalog based on shopper context
5. **Virtual try-on** — shopper sees themselves wearing recommended items
6. **Guardrail + ranking** — agent pipeline endpoints (stubs for colleagues)

---

## Plan of Changes

### 1. Database Models (`models.py`)

**a. Replace `ClosetItem` → `CatalogItem`**
```
id              (Integer, PK)
name            (String)            — "Gymshark Crest T-Shirt - Black"
image_url       (String)            — Shopify CDN URL
description     (String)            — product description from JSON (or enriched by agent later)
category        (String)            — "Tops", "Bottoms", "Outerwear", "Sports Bras", "Accessories", "One-Piece"
gender          (String)            — "mens" or "womens"
colors          (JSON, nullable)    — extracted by agent later, e.g. ["black"]
style_tags      (JSON, nullable)    — extracted by agent later, e.g. ["casual", "streetwear"]
style_vector    (Vector(768), nullable) — embedding for similarity search
created_at      (DateTime)
```

**b. New model: `ShopperSession`**
```
id                  (Integer, PK)
session_token       (String, unique)    — frontend session ID
selfie_url          (String, nullable)  — uploaded selfie for try-on
gender_preference   (String, nullable)  — "mens", "womens", or null for both
favorite_colors     (JSON, nullable)
disliked_styles     (JSON, nullable)
occasion            (String, nullable)  — "gym", "casual", "date night"
notes               (String, nullable)  — free-form style input
created_at          (DateTime)
```

**c. Expand `Outfit`**
```
id                  (Integer, PK)
session_id          (Integer, FK → ShopperSession, nullable)
outfit_id_label     (String)            — "rec_001"
item_ids            (JSON)              — list of CatalogItem IDs
reason              (String, nullable)
style_tags          (JSON, nullable)
styling_tip         (String, nullable)
confidence_score    (Float, nullable)
ranking             (Integer, nullable)
total_price         (Float, nullable)
created_at          (DateTime)
```

---

### 2. Catalog Seeding

On server startup (in `lifespan`), check if `CatalogItem` table is empty. If so, load from `gymshark_closet_inventory.json`:

```python
# Pseudocode in lifespan()
if db.query(CatalogItem).count() == 0:
    data = json.load("gymshark_closet_inventory.json")
    for gender in ["mens", "womens"]:
        for item in data[gender]:
            db.add(CatalogItem(
                name=item["name"],
                image_url=item["image_url"],
                description=item["description"],
                category=item["category"],
                gender=gender,
            ))
    db.commit()
```

No sync endpoint needed. Just restart the server to re-seed if the JSON changes.

---

### 3. Endpoints

**a. Catalog (read-only)**
- `GET /api/catalog` — list all items
  - Query params: `gender` (optional), `category` (optional)
  - Response:
    ```json
    {
      "count": 52,
      "items": [
        {
          "id": 1,
          "name": "Gymshark Crest T-Shirt - Black",
          "image_url": "https://cdn.shopify.com/...",
          "description": "Regular-fit cotton-blend tee...",
          "category": "Tops",
          "gender": "mens",
          "colors": ["black"],
          "style_tags": ["casual", "minimal"]
        }
      ]
    }
    ```
- `GET /api/catalog/{item_id}` — get single item detail

**b. Shopper Session**
- `POST /api/sessions` — create session
  - Request: `{ "selfie_url"?, "gender_preference"?, "favorite_colors"?, "disliked_styles"?, "occasion"?, "notes"? }`
  - Response: `{ "session_id": 1, "session_token": "abc-123" }`
- `GET /api/sessions/{session_token}` — get session
- `PATCH /api/sessions/{session_token}` — update preferences

**c. Outfit Recommendation**
- `POST /api/sessions/{session_token}/recommend`
  - Request:
    ```json
    {
      "prompt": "I need a matching gym outfit for leg day",
      "image_prompt_url": null,
      "partner_image_url": null,
      "occasion": "gym",
      "weather_context": null
    }
    ```
  - Response:
    ```json
    {
      "outfits": [
        {
          "outfit_id": "rec_001",
          "items": [
            {
              "item_id": 1,
              "name": "Gymshark Crest T-Shirt - Black",
              "category": "Tops",
              "image_url": "https://cdn.shopify.com/...",
              "description": "Regular-fit cotton-blend tee..."
            },
            {
              "item_id": 10,
              "name": "Gymshark Arrival 5\" Shorts - Black",
              "category": "Bottoms",
              "image_url": "https://cdn.shopify.com/..."
            }
          ],
          "reason": "Classic gym pairing — breathable tee with lightweight training shorts.",
          "style_tags": ["gym", "performance", "minimal"],
          "styling_tip": "Pair with crew socks and a backpack for a clean gym look.",
          "confidence_score": 0.91
        }
      ],
      "top_choice": "rec_001",
      "optional_purchase_tip": null
    }
    ```

**d. Virtual Try-On (unchanged)**
- `POST /api/virtual-try-on` — single try-on
- `POST /api/virtual-try-on/batch` — batch try-on per recommendation
- `GET /api/virtual-try-on/status/{prediction_id}` — poll status

**e. Agent Pipeline Stubs**
- `POST /api/guardrail-check` — validate try-on image faithfulness
- `POST /api/rank-outfits` — Fashion Master final ranking

**f. Health Check**
- `GET /` — health check + catalog stats

---

### 4. Endpoints to Remove

| Old Endpoint | Reason |
|---|---|
| `GET /api/upload-url` | No user uploads — images come from pre-loaded JSON |
| `POST /api/mock-upload` | Same |
| `POST /api/process-item` | Replaced by auto-seed on startup |
| `GET /api/closet` | Replaced by `GET /api/catalog` |
| `POST /api/generate-outfit` | Replaced by `POST /api/sessions/{token}/recommend` |

---

### 5. Files to Modify

| File | Changes |
|---|---|
| `backend/models.py` | Replace `ClosetItem` → `CatalogItem`; add `ShopperSession`; expand `Outfit` |
| `backend/main.py` | Remove old endpoints; add catalog/session/recommend/batch endpoints; add catalog seed logic |
| `backend/services/s3.py` | Keep minimal — only for shopper selfie uploads |
| `backend/services/gemini.py` | No changes — agents plug in later |
| `backend/services/replicate_service.py` | No changes |
| `backend/README.md` | Rewrite to reflect store catalog model |

---

### 6. What We Are NOT Doing
- No Shopify API integration — catalog is pre-downloaded
- No sync/scraping logic
- No agent implementation — stubs only with TODO markers
- Endpoint handlers will use existing `gemini.py` service for basic recommendations until agents are plugged in

---

### 7. Final API Surface

```
# Catalog (read-only, served from DB)
GET    /api/catalog                               — list items (filter: gender, category)
GET    /api/catalog/{item_id}                     — single item detail

# Shopper Sessions
POST   /api/sessions                              — create session
GET    /api/sessions/{session_token}              — get session
PATCH  /api/sessions/{session_token}              — update preferences

# Outfit Recommendation
POST   /api/sessions/{session_token}/recommend    — generate outfit recommendations

# Virtual Try-On
POST   /api/virtual-try-on                        — single try-on
POST   /api/virtual-try-on/batch                  — batch try-on per recommendation
GET    /api/virtual-try-on/status/{prediction_id} — poll status

# Agent Pipeline Stubs
POST   /api/guardrail-check                       — validate try-on image
POST   /api/rank-outfits                          — Fashion Master final ranking

# Utility
GET    /                                          — health check + catalog stats
```
