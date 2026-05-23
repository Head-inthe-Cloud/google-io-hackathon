# Architecture Decision Framework

## Decision

Build an agentic product-set recommender, not a hardcoded product ranker.

The system recommends combinations of catalog items to buy. Every semantic decision is made by LLM agents:

```text
preference stack + live query + optional user images + catalog facets
→ Context Compiler Agent
→ LLM Filter + Query Planner Agent
→ Catalog Tool retrieves category/product nodes
→ repeat until useful leaf candidate pools
→ Stylist Set Builder Agent
→ Critic Agent
→ product_sets
```

Local code is orchestration and tooling only. It must not contain handcrafted rules like "not too tight means compression" or "minimal means black." Those judgments belong to the LLM agents.

## Inputs

### Preference Stack

Long-lived style profile from questionnaire processing.

Example:

```text
The shopper prefers understated gymwear, likes neutral palettes, wants pieces
that feel versatile, and avoids loud statement looks.
```

The recommender treats this as preference context, not executable code and not a static rules file.

### Query

The immediate shopping request.

Example:

```text
Find me a set for leg day that works with this reference image.
```

The query has higher precedence than the preference stack.

### Images

Optional user-provided images can represent:

- outfit inspiration
- partner/event context
- shopper photo
- item they already own
- visual mood reference

Images are interpreted by the multimodal Context Compiler Agent. Local code does not inspect images.

### Catalog

The catalog provides products and structured facets:

```text
gender, department, category, product_type, activity, collection,
color, fit, support, features, season, availability
```

Local code may filter by these facets only after an LLM agent asks it to.

## Agent Roles

### 1. Context Compiler Agent

Inputs:

- raw preference stack
- live query
- optional images
- catalog facet summary

Responsibilities:

- understand the user goal
- interpret visual inputs
- decide what kind of product set is needed
- produce initial search branches
- define set assembly guidance

It returns internal planning JSON. That JSON is not part of the default user-facing output.

### 2. LLM Filter + Query Planner Agent

Inputs:

- compiled context
- catalog facet summary
- current category/product nodes
- traversal trace

Responsibilities:

- filter the catalog conceptually using the preference stack, query, and images
- construct the next catalog tool query
- decide whether to go deeper, broaden, or stop
- mark useful nodes as leaf candidate pools
- use only available catalog facets and product IDs returned by tools

The local tool executes the LLM-authored query and returns category/product nodes. The LLM decides the search direction.

### 3. Stylist Set Builder Agent

Inputs:

- compiled context
- search trace
- candidate pools

Responsibilities:

- assemble product sets
- select items by candidate ID only
- explain why each item belongs in the set
- explain why the whole set fits the user

This is the main recommendation step.

### 4. Critic Agent

Inputs:

- compiled context
- proposed product sets
- candidate lookup

Responsibilities:

- reject invented products
- reject incoherent combinations
- reject sets that violate context
- approve final product sets

## Catalog Traversal Shape

The search is LLM-directed and tool-executed. The core loop is:

```text
LLM filters current context
→ LLM constructs tool query
→ catalog tool retrieves products/categories
→ LLM decides: go deeper, broaden, or leaf
```

The LLM planner may create a query like:

```json
{
  "query_id": "q_004",
  "goal": "find breathable lifting bottoms in the user's preferred palette",
  "filters": {
    "activity": ["lifting"],
    "category": ["shorts", "pants"],
    "color": ["black", "grey"]
  }
}
```

The catalog tool executes that query against the catalog and returns:

```json
{
  "category_nodes": [],
  "product_candidates": [],
  "counts": {}
}
```

The LLM then decides whether this is a useful leaf pool for set assembly.

## Scale Decision

At the current catalog size, roughly 8.7k products, bounded LLM-planned BFS over facets is acceptable.

The scalable pattern is:

```text
1 Context Compiler call
+ N Filter + Query Planner calls, one per traversal layer
+ N Catalog Tool retrievals, capped by branches per layer
+ 1 Set Builder call
+ 1 Critic call
```

The system does not call an LLM once per product. It processes capped tool queries per layer and capped candidates per leaf pool.

For a much larger catalog, add retrieval infrastructure behind the same branch execution interface:

- faceted database indexes
- vector search within each branch
- inventory/location filters
- personalization embeddings
- candidate reranking model

The LLM agent contract stays the same.

## Public Output Contract

Default output is intentionally small:

```json
{
  "output_format_version": "agentic_product_set_recommender.v1",
  "recommendation_type": "product_sets",
  "product_sets": [
    {
      "set_id": "set_001",
      "set_name": "string",
      "items": [
        {
          "candidate_id": "p123",
          "role": "top",
          "why_this_item": "string",
          "product": {
            "product_name": "string",
            "image_url": "string",
            "description": "string",
            "product_link": "string",
            "categories": {}
          }
        }
      ],
      "why_this_set": "string",
      "preference_alignment": ["string"],
      "query_alignment": ["string"],
      "visual_alignment": ["string"],
      "tradeoffs": ["string"],
      "confidence_score": 0.91
    }
  ]
}
```

Debug output can include compiled context and search trace, but it is opt-in.

## Non-Goals

The recommender should not:

- hardcode query breakdown rules
- hand-author style taxonomies in Python
- return individual product rankings as the main output
- invent products outside the retrieved catalog
- expose internal interpreted query data by default

## Acceptance Criteria

The architecture is acceptable when:

- recommendations are product sets
- product choices are made by LLM agents
- local code only executes catalog tools and validation
- image inputs are handled by a multimodal LLM agent
- public output contains product sets and reasoning
- debug planning details are optional
