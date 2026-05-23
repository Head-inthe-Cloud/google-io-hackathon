# Agent Workflow: In-Store Stylist Copilot

Structured design reference for agent roles, data flow, and JSON contracts. Paste-friendly for Google Docs or GitHub.

---

## 1. Goal

Build an agentic fashion assistant that recommends outfits from a **store catalog** based on customer preferences, occasion, social context, and optional reference images. A store worker uses the system as a copilot: present recommendations, collect feedback, refine iteratively, and optionally show virtual try-on previews before guiding the customer to physical items.

**Objective:** Help undecided shoppers and increase their confidence.

**Primary user:** Store worker (employee copilot).

---

## 2. Core Data Structure: Store Catalog

### Bootstrap Input

Catalog items are loaded from a scraped store website:

- Product images
- Optional metadata (name, price, category, URL, SKU)

### Catalog Ingestion Agent

For each catalog image, this agent:

1. Detects whether the image contains exactly one clothing item.
2. If multiple items are present, flags the record for manual review or re-scrape.
3. Generates a detailed text description of the item.
4. Produces embeddings for semantic retrieval.

**Example output:**

```json
{
  "item_id": "cat_top_001",
  "category": "top",
  "description": "Black oversized cotton T-shirt with minimal graphic print, casual streetwear style.",
  "colors": ["black"],
  "style_tags": ["casual", "streetwear", "minimal"],
  "formality": "casual",
  "season": ["spring", "summer", "fall"],
  "image_url": "https://...",
  "source_url": "https://store.example.com/products/...",
  "price": 89.00
}
```

The result is a **catalog database**: image-description pairs with metadata and embeddings.

---

## 3. Styling Session Flow

### Step 1: Customer Intake (Worker-Initiated)

The worker captures customer context:

- Text prompt
- Optional reference image (partner outfit, inspo, event context)
- Optional customer photo (for try-on)
- Optional occasion / location / social context

**Example prompt:**

> "My girlfriend is wearing a red dress. What should I wear to match her at dinner?"

---

## 4. Customer Understanding Agent

Summarizes the customer's need using:

- Worker-entered text prompt
- Uploaded reference images
- Optional customer photo
- Session context (if refining)

**Output:**

```json
{
  "occasion": "dinner date",
  "style_goal": "match partner without overdressing",
  "needed_items": ["top", "bottom", "shoes"],
  "constraints": ["use store catalog", "smart casual", "color harmony"],
  "customer_preference_summary": "prefers clean silhouettes and darker tones",
  "confidence_goal": "help undecided shopper feel intentional but not overdressed"
}
```

Passed to **Catalog Retrieval Agent** (initial pass) or **Conversational Stylist Agent** (refinement pass).

---

## 5. Catalog Retrieval Agent

Receives:

- Customer intent summary
- Store catalog (descriptions, images, metadata)
- Optional inventory filters (mocked for hackathon)

Decides retrieval scope:

- Full outfit
- Top only / bottom only / shoes / accessories
- Missing category flags

Generates a semantic query over catalog descriptions, retrieves candidates, and composes **5 outfit recommendations**.

**Example query (internal):**

> "Find smart casual dark-toned tops and pants that visually complement a red dress."

**Example recommendation:**

```json
{
  "recommendation_id": "rec_001",
  "items": ["cat_top_001", "cat_bottom_004", "cat_shoes_002"],
  "reason": "Dark neutral outfit complements the partner's red dress while keeping the customer slightly understated.",
  "style_tags": ["smart casual", "date night", "coordinated"],
  "confidence_score": 0.82
}
```

---

## 6. Conversational Stylist Agent (Core Differentiator)

Handles **iterative refinement** within an active styling session.

**Inputs:**

- Full session conversation history
- Latest customer/worker feedback
- Previous recommendations (liked/disliked signals)
- Customer intent summary (updated)

**Example feedback:**

- *"Less formal"*
- *"More colorful"*
- *"Something trendier"*
- *"Better shoes"*
- *"Match my partner's dress more closely"*

**Behavior:**

1. Interprets feedback in context of prior turns.
2. Updates the intent summary or retrieval constraints.
3. Re-queries the catalog and produces a **new set of recommendations**.
4. Explains what changed and why.

**Example output:**

```json
{
  "session_id": "sess_abc123",
  "turn_id": "turn_004",
  "updated_intent": {
    "style_goal": "relaxed smart casual with more color",
    "constraints": ["add earth tones", "less structured silhouette"]
  },
  "recommendations": [
    {
      "recommendation_id": "rec_006",
      "items": ["cat_top_012", "cat_bottom_008", "cat_shoes_005"],
      "reason": "Swapped structured blazer for a relaxed linen shirt; added terracotta tones per feedback.",
      "style_tags": ["relaxed", "smart casual", "earth tones"]
    }
  ],
  "worker_message": "I loosened the formality and introduced warmer tones. Here are three updated options."
}
```

This agent is the **centerpiece of the demo** — static recommenders cannot do this.

---

## 7. Try-On Visualization Agent

Receives:

- Customer photo (optional)
- Clothing item images from each recommendation
- Outfit description
- Style constraints

Generates one virtual try-on image per recommendation (when customer photo is provided).

**Output:**

```json
{
  "recommendation_id": "rec_001",
  "generated_tryon_image": "https://...",
  "input_items": ["cat_top_001", "cat_bottom_004", "cat_shoes_002"]
}
```

**Note:** Try-on is a demo multiplier, not the primary pitch. Physical try-on in-store is the real outcome.

---

## 8. Guardrail Agent

Checks whether each generated image is faithful and safe to show.

Compares:

- Customer input photo vs. generated person
- Clothing input images vs. generated outfit
- Body/face identity consistency
- Color, shape, pattern, and garment fidelity
- Obvious hallucinations or visual artifacts

**Output:**

```json
{
  "recommendation_id": "rec_001",
  "pass": true,
  "faithfulness_score": 0.87,
  "issues": []
}
```

If a result fails: regenerate or hide from the worker UI.

---

## 9. Fashion Master Agent

Final ranking and explanation layer.

Receives:

- Customer intent
- Outfit recommendations (initial or refined)
- Try-on images (if available)
- Guardrail scores
- Session feedback history

Produces the worker-facing final result:

**Output:**

```json
{
  "top_choice": "rec_003",
  "ranked_recommendations": ["rec_003", "rec_001", "rec_005"],
  "reason": "Best balance of occasion fit, partner coordination, and inferred customer style.",
  "styling_tip": "Add a silver watch or minimal necklace to make the outfit feel more intentional.",
  "confidence_score": 0.91,
  "optional_alternatives": "If the customer wants more edge, swap to rec_001."
}
```

---

## 10. Full Agent Pipeline

```
[Offline] Scrape store website
        ↓
Catalog Ingestion Agent
        ↓
Catalog Database
        ↓
[Live] Worker starts styling session + customer intake
        ↓
Customer Understanding Agent
        ↓
Catalog Retrieval Agent
        ↓
5 outfit recommendations
        ↓
Try-On Visualization Agent (optional)
        ↓
Guardrail Agent
        ↓
Fashion Master Agent
        ↓
Worker presents to customer
        ↓
Customer feedback
        ↓
Conversational Stylist Agent → refined recommendations
        ↓
(repeat refine loop as needed)
        ↓
Worker guides customer to physical items
```

---

## 11. Agent Summary Table

| Agent | Role | Trigger |
|-------|------|---------|
| **Catalog Ingestion Agent** | Describe and index catalog items | Offline bootstrap |
| **Customer Understanding Agent** | Parse intake into structured intent | Session start, major context change |
| **Catalog Retrieval Agent** | Query catalog, compose outfit sets | Initial recommendation |
| **Conversational Stylist Agent** | Refine based on feedback | Each worker refinement turn |
| **Try-On Visualization Agent** | Generate customer try-on previews | After recommendations (optional) |
| **Guardrail Agent** | Validate try-on faithfulness | After try-on generation |
| **Fashion Master Agent** | Rank, explain, add styling tips | Before presenting to worker |

---

## 12. Hackathon Alignment

Maps cleanly to **managed agents** and **Gemini multimodal** capabilities:

- Multimodal intake (text + images)
- Structured JSON output per agent
- Conversational session memory
- Human-in-the-loop (store worker)
- Real-time refinement (Gemini Flash for latency)

**Pitch line:**

> An agentic AI stylist copilot that understands your store catalog, your customer's social context, and their visual environment — to recommend outfits they can actually try on.
