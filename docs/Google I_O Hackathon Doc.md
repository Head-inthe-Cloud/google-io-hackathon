# Design Doc: Agentic In-Store Stylist Copilot

## Overview

**Stylist Copilot** is a B2B agentic AI system for boutique and stylist-assisted retail. Store workers use it as a conversational copilot when helping undecided shoppers. The system understands customer preferences, occasion, and social context; retrieves coordinated outfits from the **store catalog**; supports live refinement through natural feedback; and optionally generates virtual try-on previews before the worker brings the customer to the rack.

The core thesis: most retail recommenders are static feed engines. Stylist Copilot is a **multimodal, conversational, human-in-the-loop styling system** that helps shoppers feel confident about what to try on — and gives store staff a premium AI assistant rather than replacing them.

**Hackathon pitch:** An agentic AI stylist copilot that understands your store catalog, your customer's social context, and their visual preferences — to recommend outfits they can actually try on in-store.

## Target Context

| Dimension | Choice |
|-----------|--------|
| **Primary user** | Store worker (employee copilot) |
| **End beneficiary** | In-store customer (undecided shopper) |
| **Store type** | Boutique / higher-end / stylist-assisted retail |
| **Recommendation goal** | Increase shopper confidence; help undecided customers |
| **Autonomy** | Conversational recommendations + iterative refinement; worker remains in the loop |
| **Catalog source** | Scraped from a real store website (bootstrap for demo) |

## Demo Flow (3-Minute Script)

1. **Customer walks in** — worker opens Stylist Copilot on a tablet.
2. **Quick intake** — customer (or worker on their behalf) enters:
   - Text: *"I need an outfit for a rooftop dinner"*
   - Optional reference image (partner's dress, Pinterest inspo, etc.)
   - Optional customer photo for try-on previews
3. **AI builds customer profile** — Customer Understanding Agent infers occasion, style goals, and constraints.
4. **AI retrieves 5 coordinated outfits** from the store catalog — Catalog Retrieval Agent composes ranked recommendations with reasoning.
5. **Worker shows recommendations** — tablet displays outfit cards with item links, styling rationale, and optional try-on previews.
6. **Customer refines** — *"Less formal."* / *"More artistic."* / *"Match my girlfriend's red dress."*
7. **Conversational Stylist Agent refines live** — new recommendations without restarting the session.
8. **Optional try-on visualization** — customer sees themselves in top picks (Guardrail Agent filters bad generations).
9. **Worker guides to the rack** — customer tries on physical items in the fitting room.

**Wow moment:** Conversational refinement in physical retail — not a one-shot recommendation list.

## User Workflow

### Worker: Session Start

1. Worker starts a new **styling session** for a walk-in customer.
2. Worker captures customer context via copilot intake form:
   - Text prompt (occasion, vibe, constraints)
   - Optional reference image
   - Optional customer photo
   - Optional notes (purchase history, repeat customer — post-MVP)
3. System runs the agent pipeline and returns 5 outfit recommendations.

### Worker: Present & Refine

1. Worker walks the customer through recommendations on the tablet.
2. Customer reacts verbally or via quick feedback chips (*"too formal"*, *"more color"*, *"different shoes"*).
3. Worker enters feedback; **Conversational Stylist Agent** refines the search within the same session.
4. Loop continues until the customer is ready to try on items physically.

### Worker: Close Session

1. Worker notes which items the customer tried on or purchased (optional for demo).
2. Session is saved for future visits (post-MVP: repeat customer memory).

## Agent Pipeline

```
Store catalog (scraped website)
        ↓
Catalog Ingestion Agent
        ↓
Catalog Database (image-description pairs + metadata)
        ↓
Customer walks in → worker starts session
        ↓
Customer Understanding Agent
        ↓
Catalog Retrieval Agent → 5 outfit recommendations
        ↓
Try-On Visualization Agent (optional)
        ↓
Guardrail Agent
        ↓
Fashion Master Agent → ranked results + styling tips
        ↓
Worker presents to customer
        ↓
Customer feedback → Conversational Stylist Agent → refined recommendations
        ↓
Worker brings customer to physical items
```

See [AGENT_WORKFLOW.md](./AGENT_WORKFLOW.md) for agent roles, JSON schemas, and data flow details.

## Key Differentiator

This is **not** a recommendation engine. It is an **agentic, multimodal, in-store stylist system** with:

- Real store catalog (not a generic product feed)
- Social and contextual reasoning (occasion, partner coordination, environment)
- Conversational refinement loop (human-in-the-loop via store worker)
- Optional try-on realism with faithfulness guardrails
- Worker copilot UX (deployable, not gimmicky kiosk-only)

**Strongest pitch angle:** AI-guided conversational refinement in physical retail.

## Component Design

### Frontend (Next.js — Employee Copilot UI)

The client is a **worker-facing tablet/dashboard**, not a consumer closet app.

- **Session intake form** — text prompt, optional image upload, optional customer photo.
- **Recommendation cards** — outfit composition, item thumbnails, catalog links, styling rationale, confidence score.
- **Refinement panel** — feedback input + quick chips; shows conversation history within the session.
- **Try-on preview gallery** — loading states during VTON generation (*"Fitting top…"*, *"Adjusting colors…"*).
- **Catalog item detail** — SKU, category, colors, store location (if available).

Polish matters for the demo: smooth transitions (Framer Motion), clear hierarchy, and fast perceived response times.

### Backend & Storage (Supabase)

- **File storage** — customer photos, reference images, catalog item images, generated try-ons.
- **Vector search** — pgvector over catalog item descriptions for semantic retrieval.
- **Session state** — styling sessions, conversation turns, recommendations, refinement history.

Tables (conceptual):

- `catalog_items` — scraped/described store inventory
- `styling_sessions` — one per customer visit
- `conversation_turns` — worker feedback + agent responses
- `recommendations` — outfit sets with items, scores, and try-on URLs

### AI Orchestration (FastAPI)

FastAPI acts as the glue between Supabase, Gemini (Google AI Studio), and optional GPU workers (Replicate for VTON).

- **Managed agents** — each pipeline stage maps to a distinct agent role (see AGENT_WORKFLOW.md).
- **Structured JSON** — all agents return parseable schemas for the copilot UI.
- **Session-scoped context** — refinement agents receive full session history, not just the latest prompt.

### Catalog Bootstrap (Pre-Demo)

1. Scrape product images and metadata from a boutique store website.
2. Run **Catalog Ingestion Agent** over each item to generate rich descriptions, tags, and embeddings.
3. Load into `catalog_items` table before the live demo.

## Team Split (Hackathon)

### Person A: Employee Copilot UI

- Session intake, recommendation cards, refinement panel, try-on gallery
- Framer Motion polish, loading states, responsive tablet layout

### Person B: Backend & Session Orchestration

- Supabase schema, storage buckets, session lifecycle
- FastAPI routes (see [backend_api_surface.md](./backend_api_surface.md))
- Agent pipeline wiring and state management

### Person C: AI Integration & Catalog Bootstrap

- Catalog scrape + ingestion pipeline
- Gemini prompt engineering per agent role
- Optional Replicate VTON + Guardrail Agent logic
- Mock/fallback data for demo resilience

## Out of Scope (Hackathon MVP)

- Full POS / inventory integration
- Customer-facing kiosk (worker copilot only for v1)
- Repeat customer memory / purchase history (noted as post-MVP)
- Real-time inventory size lookup (can be mocked)
- Multi-store deployment

## Related Docs

- [AGENT_WORKFLOW.md](./AGENT_WORKFLOW.md) — agent roles, JSON schemas, full pipeline
- [backend_api_surface.md](./backend_api_surface.md) — API endpoints and data contracts
- [RETAIL_STYLIST_STUDIO.md](./RETAIL_STYLIST_STUDIO.md) — Google AI Studio integration notes
