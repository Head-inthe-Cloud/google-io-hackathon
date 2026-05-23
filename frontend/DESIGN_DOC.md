# Architectural Design Document: AI Personal Closet Advisor

Integrated System and Algorithm Specs for an AI-PoweredWardrobe Agent.

---

## 1. Executive Summary
The **AI Personal Closet Advisor** is a full-stack, highly personalized wardrobe companion. The application solves a common daily friction: *"What should I wear today based on my exact current wardrobe, my physical traits, and the specific event vibe?"*

By establishing a **user styling portfolio**, analyzing uploaded **closet garments** and a **full-body selfie** via server-side Multimodal Gemini models, and implementing an iterative, stateful **Like/Dislike selection queue**, the system delivers refined styling recommendations and synthetic try-on previews. If the current closet lacks specific layers, the AI agent dynamically sources missing items from an integrated online catalog.

---

## 2. Core Functional Requirements

### 2.1 Stage 1: Cold Start Style Profiling (Onboarding)
- **Objective**: Learn the user's fashion aesthetic before requiring image inputs.
- **Spectrum**: Show 6 distinctive visual style cards:
  1. *Minimalist Casual (简约休闲)* – Neutral tones, functional, clean silhouettes.
  2. *Streetwear / Grunge (街头潮酷)* – Oversized cuts, graphic accents, casual edge.
  3. *Business Formal / Smart Casual (职场通勤)* – Tailored blazers, pleat trousers, polished look.
  4. *Vintage / Retro (复古怀旧)* – Classic patterns, warm earthy textures, 70s-90s nods.
  5. *Academic / Preppy (学院风)* – Sweaters, collared shirts, pleated skirts, timeless prep.
  6. *Sporty / Gorpcore (运动户外)* – Techwear fabrics, utilitarian compartments, high function.
- **Action**: User selects one or more favorites, which are parsed by the underlying AI Agent with customized prompt weighting.

### 2.2 Stage 2: Closet Digitization & Selfie Register (First Use)
- **Virtual Closet Storage**: Users can register closet garments. Includes a pre-populated wardrobe of standard staple garments for a direct, zero-friction trial.
- **Computer Vision Auto-Tagging**: Upon file upload (Base64 JPEG/PNG):
  - Express backend streams the frame to Gemini for analysis.
  - Gemini outputs a structured JSON describing the garment: **Name**, **Category** (*Tops, Bottoms, Outerwear, Shoes, Accessories*), **Dominant Color**, **Pattern/Fabric**, and a **Vibe Description**.
- **Personal Body Model (Selfie)**: Users upload a full-body selfie. The AI Agent extracts morphological pointers (height frame, skin undertone, base canvas colors) to guide try-on composites and contextual advices.

### 2.3 Stage 3: Dynamic Style Querying (Next Uses)
- **Multi-Modal Prompt Input**: Users can supply:
  - Text prompts (e.g., *"Business lunch on a chilly autumn day"*, *"Summer seaside date"*).
  - Optional style inspiration images (mood boards, magazines, celebrity snapshots).

### 2.4 Stage 4: Wardrobe Reasoning & Feedback Queue (The Recommendation Matcher)
- **Matching Algorithm (AI Agent Reasoning)**:
  - Combines: Selected style profile + Digital closet metadata + Full-body selfie details + Prompt context + Optional reference images.
  - Gemini compiles **3 sequential recommendations** sorted by style adherence, formatted inside a structured payload.
- **The Try-On Engine**:
  - The agent suggests a visual composition (laying out the closet clothes as flat layers overlaid next to the user's selfie).
  - A synthetic representation is displayed alongside styling rationale detailing why this matches the user's physical framework in the selfie.
  - If a paid API key is available, the client allows generating a photorealistic synthesis of the outfit modeled on a matched silhouette.
- **Dislike / Like Stateful Queue**:
  - The UI presents recommendation **#1**.
  - **Click Dislike**: Rec #1 is discarded, and Rec #2 is smoothly slid into view.
  - **Click Like**: Saves the outfit to "Loved Wardrobes" and records the successful style vector to self-train subsequent recommendations.
- **Online Recommendations Fallback**:
  - If the user's closet contains insufficient items (or lacks a recommended category, e.g., missing suitable boots for a business formal look), the AI dynamically creates a **"Sourced Online Accessories / Clothing"** section with exact item specs to complete the styled look.

---

## 3. Technology Stack & Directory Strategy

Our application runs as a **Full-Stack Node.js/TypeScript application in a unified Cloud Run environment**.

- **Frontend**: React 19, Vite, Tailwind CSS v4, Motion (animations), and Lucide React.
- **Backend Server**: Express Router + Gemini TypeScript SDK (`@google/genai`).
- **Dev Runner**: `tsx` for live compilation; `esbuild` for production bundling.

---

## 4. API Specification

### 4.1 `POST /api/analyze-item`
Parses an uploaded closet garment.
- **Input**: `{ image: "base64..." }`
- **Output**:
```json
{
  "id": "item-10928",
  "name": "Oversized Charcoal Wool Sweater",
  "category": "Tops",
  "color": "Charcoal Grey",
  "pattern": "Solid knit",
  "vibe": "Cozy, warm minimalist, retro academic vibes"
}
```

### 4.2 `POST /api/recommend`
Processes user prompt and current closet states to yield three sequential outfits.
- **Input**:
```json
{
  "preferences": ["Minimalist Casual", "Academic"],
  "closet": [...],
  "selfieDescription": "Sandy undertone, athletic build",
  "prompt": "Cozy evening bookstore rendezvous",
  "inspirationImage": "base64..."
}
```
- **Output**:
```json
{
  "recommendations": [
    {
      "outfitName": "Classic Ivy Warmth",
      "rationale": "Perfect for a bookstore date. The charcoal wool sweater coordinates beautifully with your beige khaki pants, reflecting your preferred Minimalist and Academic aesthetics.",
      "items": [
        { "id": "1", "name": "Charcoal Knit Sweater", "category": "Tops" },
        { "id": "2", "name": "Beige Cotton Chinos", "category": "Bottoms" }
      ],
      "onlineSourced": [
        { "name": "Brown Suede Derby Shoes", "price": "$89", "reason": "Adds a sophisticated collegiate finish to the chinowear." }
      ],
      "tryOnAdvice": "Since your selfie features neutral skin undertones, this warm brown and charcoal mix will highlight your natural tones beautifully without drowning you out."
    },
    ...
  ]
}
```

---

## 5. Architectural Flow Chart

```
[ User Onboarding Visual Choices ] ---> [ Save Style Profile to LocalState ]
                                              |
[ Closet Garments + Selfie Upload ] --> [ POST /api/analyze-item ] -> [ Gemini Vision Tagging ]
                                              |
[ Prompt + Optional Vibes Image ]   --> [ POST /api/recommend ]
                                              |
                                              v
                                   [ Server-side AI Agent Context Synthesis ]
                                              | (Queries gemini-3.5-flash)
                                              v
                                   [ Response: 3 Sorted Outfit Recommendations ]
                                              |
                     ----------------------------------------------------
                     |                                                  |
                     v                                                  v
          [ Display Current Outfit Card ]                      [ Sourced Online Fallbacks ]
            |                      |
    (Likes Outfit)          (Dislikes Outfit)
            |                      |
            v                      v
    [ Save to Loved Sets ]   [ Slide Next Card in Queue ]
```

---

*This document guides the complete implementation of the AI Personal Closet Advisor, providing an accessible reference for both system integrity and downstream intelligence optimization.*
