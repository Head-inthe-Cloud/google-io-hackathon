# Stylist Copilot Backend API Surface

FastAPI orchestration layer between the employee copilot UI (Next.js), Supabase (Postgres + Storage + pgvector), Google AI Studio (Gemini agents), and optional GPU workers (Replicate for VTON).

## Base URL

Local development: `http://localhost:8000`

---

## 1. Storage & Uploads

### `GET /api/upload-url`

Generates a pre-signed upload URL for direct client uploads (customer photos, reference images).

**Query parameters:**

- `filename` (string, required) — e.g. `session_abc_ref.jpg`
- `bucket` (string, optional) — `customer-photos` | `reference-images` | `tryons` (default: `customer-photos`)

**Response:**

```json
{
  "upload_url": "https://...",
  "file_url": "https://..."
}
```

**Frontend action:** `PUT` binary to `upload_url`, then pass `file_url` to session endpoints.

---

## 2. Catalog (Offline Bootstrap)

### `POST /api/catalog/ingest`

Process a single catalog item image through the Catalog Ingestion Agent and insert into `catalog_items`.

**Request body:**

```json
{
  "image_url": "string",
  "source_url": "string (optional, product page URL)",
  "sku": "string (optional)",
  "name": "string (optional)",
  "price": 89.00
}
```

**Backend workflow:**

1. Send image to Gemini (Catalog Ingestion Agent) → structured description, tags, category.
2. Validate single-item detection; flag multi-item images.
3. Generate embedding via Gemini embedding API.
4. Insert row into `catalog_items`.

**Response:**

```json
{
  "status": "success",
  "item_id": "cat_top_001",
  "extracted_data": {
    "category": "top",
    "description": "Black oversized cotton T-shirt...",
    "colors": ["black"],
    "style_tags": ["casual", "streetwear"]
  }
}
```

### `POST /api/catalog/ingest-batch`

Bulk ingest from scrape output (array of items). Used during demo setup.

**Request body:**

```json
{
  "items": [
    { "image_url": "...", "source_url": "...", "name": "...", "price": 89.00 }
  ]
}
```

**Response:**

```json
{
  "status": "success",
  "ingested": 42,
  "flagged": 3,
  "errors": []
}
```

### `GET /api/catalog/items`

List or search catalog items (for debugging / worker browse).

**Query parameters:**

- `category` (optional)
- `query` (optional) — semantic search string
- `limit` (default: 20)

---

## 3. Styling Sessions

### `POST /api/sessions`

Start a new styling session for a walk-in customer.

**Request body:**

```json
{
  "worker_id": "string (optional)",
  "store_id": "string (optional, default for demo)"
}
```

**Response:**

```json
{
  "session_id": "sess_abc123",
  "status": "intake",
  "created_at": "2026-05-23T10:00:00Z"
}
```

### `POST /api/sessions/{session_id}/intake`

Submit customer context and run initial agent pipeline.

**Request body:**

```json
{
  "prompt": "I need an outfit for a rooftop dinner. My girlfriend is wearing a red dress.",
  "reference_image_url": "string (optional)",
  "customer_photo_url": "string (optional, for try-on)"
}
```

**Backend workflow:**

1. **Customer Understanding Agent** → structured intent.
2. **Catalog Retrieval Agent** → 5 outfit recommendations.
3. If `customer_photo_url` provided: **Try-On Visualization Agent** → **Guardrail Agent**.
4. **Fashion Master Agent** → ranked results + styling tips.
5. Persist intent, recommendations, and conversation turn.

**Response:**

```json
{
  "session_id": "sess_abc123",
  "intent": {
    "occasion": "dinner date",
    "style_goal": "match partner without overdressing",
    "needed_items": ["top", "bottom", "shoes"],
    "constraints": ["smart casual", "color harmony"]
  },
  "recommendations": [
    {
      "recommendation_id": "rec_001",
      "items": [
        { "item_id": "cat_top_001", "category": "top", "image_url": "...", "name": "..." }
      ],
      "reason": "Dark neutral outfit complements the partner's red dress.",
      "style_tags": ["smart casual", "date night"],
      "tryon_image_url": "string (optional)",
      "guardrail_pass": true
    }
  ],
  "top_choice": "rec_003",
  "styling_tip": "Add a silver watch to make the outfit feel more intentional.",
  "confidence_score": 0.91
}
```

---

## 4. Conversational Refinement (Core Loop)

### `POST /api/sessions/{session_id}/refine`

Worker submits customer feedback; Conversational Stylist Agent produces updated recommendations.

**Request body:**

```json
{
  "feedback": "Less formal, more color",
  "feedback_type": "text",
  "rejected_recommendation_ids": ["rec_001", "rec_002"]
}
```

`feedback_type` values: `text` | `chip` (predefined: `too_formal`, `too_casual`, `more_color`, `different_shoes`, etc.)

**Backend workflow:**

1. Append turn to `conversation_turns`.
2. **Conversational Stylist Agent** — interpret feedback with full session history.
3. **Catalog Retrieval Agent** (re-query with updated constraints).
4. Optional try-on + guardrail for new top picks.
5. **Fashion Master Agent** — re-rank and explain changes.

**Response:**

```json
{
  "session_id": "sess_abc123",
  "turn_id": "turn_004",
  "worker_message": "I loosened the formality and added warmer tones.",
  "updated_intent": {
    "style_goal": "relaxed smart casual with more color"
  },
  "recommendations": [ "...same shape as intake response..." ],
  "top_choice": "rec_006",
  "styling_tip": "..."
}
```

### `GET /api/sessions/{session_id}`

Retrieve full session state (intent, all turns, current recommendations).

### `GET /api/sessions/{session_id}/history`

Conversation history for the refinement panel.

---

## 5. Try-On (On Demand)

### `POST /api/sessions/{session_id}/try-on`

Generate try-on for a specific recommendation (if not generated during intake/refine).

**Request body:**

```json
{
  "recommendation_id": "rec_001",
  "customer_photo_url": "string"
}
```

**Backend workflow:**

1. Resolve recommendation items → garment image URLs.
2. Call IDM-VTON (Replicate) or equivalent.
3. **Guardrail Agent** validates output.
4. Store result; return URL or processing status.

**Response:**

```json
{
  "status": "processing | complete | failed",
  "recommendation_id": "rec_001",
  "tryon_image_url": "string (when complete)",
  "guardrail": {
    "pass": true,
    "faithfulness_score": 0.87,
    "issues": []
  },
  "replicate_id": "req_xyz123"
}
```

---

## 6. Session Lifecycle

### `PATCH /api/sessions/{session_id}/close`

Mark session complete; optional outcome notes for demo analytics.

**Request body:**

```json
{
  "outcome": "tried_on | purchased | left",
  "notes": "Customer tried rec_003, bought the shirt."
}
```

---

## Data Model (Conceptual)

### `catalog_items`

| Column | Type | Notes |
|--------|------|-------|
| `item_id` | string | Primary key |
| `image_url` | string | Product image |
| `source_url` | string | Store product page |
| `name` | string | Product name |
| `price` | decimal | Optional |
| `category` | string | top, bottom, shoes, etc. |
| `description` | text | Agent-generated |
| `colors` | jsonb | Array of strings |
| `style_tags` | jsonb | Array of strings |
| `embedding` | vector | pgvector for semantic search |

### `styling_sessions`

| Column | Type | Notes |
|--------|------|-------|
| `session_id` | string | Primary key |
| `worker_id` | string | Optional |
| `status` | enum | intake, active, closed |
| `intent` | jsonb | Latest Customer Understanding output |
| `customer_photo_url` | string | Optional |
| `created_at` | timestamp | |

### `conversation_turns`

| Column | Type | Notes |
|--------|------|-------|
| `turn_id` | string | Primary key |
| `session_id` | string | FK |
| `role` | enum | worker, agent |
| `content` | text | Feedback or agent message |
| `recommendations_snapshot` | jsonb | Recommendations after this turn |

### `recommendations`

| Column | Type | Notes |
|--------|------|-------|
| `recommendation_id` | string | Primary key |
| `session_id` | string | FK |
| `turn_id` | string | FK |
| `item_ids` | jsonb | Array of catalog item IDs |
| `reason` | text | |
| `style_tags` | jsonb | |
| `tryon_image_url` | string | Optional |
| `guardrail_pass` | boolean | |
| `rank` | int | Fashion Master ranking |

---

## Error Handling

All endpoints return standard error shape:

```json
{
  "error": "human-readable message",
  "code": "CATALOG_ITEM_MULTI_DETECTED | SESSION_NOT_FOUND | GUARDRAIL_FAILED | ..."
}
```

For guardrail failures on try-on: return `guardrail_pass: false` and omit image URL rather than showing a bad generation.
