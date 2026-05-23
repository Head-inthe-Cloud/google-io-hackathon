# Stylist Copilot: Google AI Studio Integration

How Stylist Copilot maps to Google AI Studio, Gemini, and managed agent patterns for the hackathon.

---

## 1. Architecture Mapping

| System Component | Google AI Studio / Gemini Feature |
|------------------|-----------------------------------|
| Catalog Ingestion Agent | Multimodal image + text → structured JSON |
| Customer Understanding Agent | Multimodal intake + system instructions |
| Catalog Retrieval Agent | Embeddings + semantic search (pgvector) + JSON outfit composition |
| Conversational Stylist Agent | Multi-turn session with conversation history |
| Try-On Visualization Agent | External VTON (Replicate) or Imagen where applicable |
| Guardrail Agent | Multimodal comparison (input vs. output images) |
| Fashion Master Agent | Structured ranking + explanation JSON |

---

## 2. Multimodal Inputs

**Models:** `gemini-2.0-flash` or `gemini-1.5-pro` for latency vs. quality tradeoffs.

**Use cases:**

- Catalog item images → descriptions and tags (Catalog Ingestion Agent)
- Customer reference images → intent parsing (Customer Understanding Agent)
- Customer photo + garment images → guardrail comparison (Guardrail Agent)
- Interleaved text + images in refinement turns (Conversational Stylist Agent)

**Formats:** JPEG, PNG, WebP. Prefer consistent aspect ratios for catalog images.

---

## 3. Structured Output

Every agent should use:

- **System instructions** grounding the agent role (stylist, catalog indexer, guardrail reviewer)
- **`responseMimeType: "application/json"`** with a strict JSON schema per agent
- **Low temperature (~0.2)** for retrieval, ingestion, guardrails
- **Moderate temperature (~0.5–0.7)** for Conversational Stylist and Fashion Master explanations

Example schema fragment (Catalog Ingestion):

```json
{
  "type": "object",
  "properties": {
    "single_item_detected": { "type": "boolean" },
    "category": { "type": "string" },
    "description": { "type": "string" },
    "colors": { "type": "array", "items": { "type": "string" } },
    "style_tags": { "type": "array", "items": { "type": "string" } }
  },
  "required": ["single_item_detected", "category", "description"]
}
```

---

## 4. Managed Agents (Hackathon Alignment)

Each pipeline stage maps to a distinct agent role. Implement as separate Gemini calls (or AI Studio agent configs) with dedicated system prompts:

1. **Catalog Ingestion Agent** — offline; batch over scraped catalog
2. **Customer Understanding Agent** — session start
3. **Catalog Retrieval Agent** — semantic query + outfit assembly
4. **Conversational Stylist Agent** — refinement loop (highlight in demo)
5. **Try-On Visualization Agent** — optional GPU worker
6. **Guardrail Agent** — multimodal faithfulness check
7. **Fashion Master Agent** — final ranking and worker-facing copy

Orchestration lives in FastAPI; each step invokes the appropriate agent with session-scoped context.

---

## 5. Embeddings & Retrieval

- Generate embeddings for catalog item descriptions via Gemini embedding API.
- Store in Supabase pgvector (`catalog_items.embedding`).
- At recommendation time: embed the intent summary or retrieval query → nearest-neighbor search → pass top candidates to Catalog Retrieval Agent for outfit composition.

This replaces the B2C "closet vector search" pattern with **store catalog semantic retrieval**.

---

## 6. Session Memory (Conversational Stylist)

The Conversational Stylist Agent requires **full session history**, not just the latest message.

Pass to the model:

- Original intake prompt and images
- Structured intent (current version)
- Previous recommendations and which were rejected
- All prior feedback turns

Persist in `conversation_turns` and assemble into the prompt context window. Gemini's large context window supports multi-turn refinement without external memory services for the hackathon.

---

## 7. Try-On & Guardrails

**Try-on:** Replicate IDM-VTON (or similar) — customer photo + garment image(s) → composite. Not native Gemini; orchestrated by FastAPI.

**Guardrails:** Gemini multimodal call comparing:

- Customer photo vs. generated try-on (identity consistency)
- Garment images vs. generated outfit (color, shape, pattern fidelity)

Return structured pass/fail + `faithfulness_score`. Hide or regenerate failed outputs.

---

## 8. Demo Resilience

- Pre-ingest catalog before live demo (avoid cold-start ingestion).
- Cache Fashion Master explanations for top demo prompts if needed.
- Fallback: if VTON fails, show outfit cards with catalog images only — conversational refinement still demos without try-on.
- Mock inventory/size filters if scrape lacks stock data.

---

## 9. Related Docs

- [AGENT_WORKFLOW.md](./AGENT_WORKFLOW.md) — agent roles and JSON contracts
- [backend_api_surface.md](./backend_api_surface.md) — API endpoints
- [Google I_O Hackathon Doc.md](./Google%20I_O%20Hackathon%20Doc.md) — product design and demo script
