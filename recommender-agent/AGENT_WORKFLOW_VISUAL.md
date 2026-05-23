# Agentic Product-Set Recommender

## Flow

```mermaid
flowchart LR
    A[Preference Stack<br/>questionnaire-derived] --> C[Context Compiler<br/>LLM Agent]
    B[Live Query] --> C
    I["User Image(s)"] --> C
    F[Catalog Facets] --> C

    C --> L[LLM Filter + Query Planner]
    L --> Q[Tool Query<br/>category/product filters]
    Q --> T[Catalog Tool]
    T --> N[Category/Product Nodes]
    N --> L
    L --> R[Leaf Candidate Pools]

    R --> O[Stylist Set Builder<br/>LLM Agent]
    C --> O
    O --> K[Critic<br/>LLM Agent]
    K --> Z[Product Sets<br/>items to buy]
```

## Agent Roles

| Agent | Decides | Does Not Do |
|---|---|---|
| Context Compiler | user goal, image meaning, set shape | pick products |
| LLM Filter + Query Planner | which catalog nodes to enter, when to go deeper, when to stop | fetch products directly |
| Catalog Tool | returns categories, counts, and product candidates for an LLM-authored query | interpret style |
| Set Builder | product combinations to buy from leaf pools | invent items |
| Critic | approve/reject sets | add new products |

## Runtime Loop

```mermaid
sequenceDiagram
    participant U as User/App
    participant C as Context Compiler LLM
    participant P as Filter + Query Planner LLM
    participant DB as Catalog Tool
    participant S as Stylist Set Builder LLM
    participant X as Critic LLM

    U->>C: preference stack + query + image(s) + facet summary
    C-->>U: shopping context + set brief

    loop until useful leaf pools
        U->>P: context + current nodes + search trace
        P-->>U: next tool queries + go deeper/stop decisions
        U->>DB: retrieve categories/products for LLM-authored queries
        DB-->>U: category nodes, counts, candidate products
    end

    U->>S: context + leaf candidate pools
    S-->>U: proposed product sets
    U->>X: proposed sets + candidate lookup
    X-->>U: approved/rejected sets
    U-->>U: hydrate approved sets with product data
```

## Catalog Traversal

```mermaid
flowchart TB
    R[Root Catalog] --> G[LLM selects high-level filters]
    G --> C1[Category Node<br/>lifting + bottoms]
    G --> C2[Category Node<br/>lifting + tops]
    G --> C3[Category Node<br/>neutral accessories]

    C1 --> D1{Go deeper?}
    D1 -->|yes| L1[Leaf Pool<br/>shorts / pants / leggings]
    D1 -->|no| B1[Broaden or stop]

    C2 --> D2{Go deeper?}
    D2 -->|yes| L2[Leaf Pool<br/>tees / tanks / hoodies]

    C3 --> D3{Useful for set?}
    D3 -->|yes| L3[Leaf Pool<br/>socks / straps / bags]

    L1 --> S[Set Builder LLM]
    L2 --> S
    L3 --> S
```

## Tool Query Shape

```json
{
  "query_id": "q_003",
  "goal": "find bottoms for the lifting set",
  "filters": {
    "activity": ["lifting"],
    "category": ["shorts", "pants", "leggings"]
  },
  "exclude_filters": {},
  "return": "category_nodes_or_products",
  "why": "The set still needs a practical lower-body item."
}
```

## Leaf Rule

```mermaid
flowchart LR
    A[LLM sees node] --> B{Enough to build sets?}
    B -->|No| C[Construct deeper tool query]
    C --> D[Catalog tool retrieves next node]
    D --> A
    B -->|Yes| E[Mark as leaf candidate pool]
```

## Output Shape

```mermaid
flowchart TB
    O[Output JSON] --> T[recommendation_type: product_sets]
    O --> S1[product_sets]
    S1 --> A[Set 1]
    S1 --> B[Set 2]
    S1 --> C[Set 3]
    A --> I1[Top]
    A --> I2[Bottom]
    A --> I3[Accessory]
    I1 --> P1[Real product link + image]
    I2 --> P2[Real product link + image]
    I3 --> P3[Real product link + image]
```

## Final JSON Skeleton

```json
{
  "output_format_version": "agentic_product_set_recommender.v1",
  "recommendation_type": "product_sets",
  "product_sets": [
    {
      "set_id": "set_001",
      "set_name": "Minimal Leg Day Set",
      "items": [
        {
          "role": "top",
          "why_this_item": "...",
          "product": {
            "product_name": "...",
            "image_url": "...",
            "product_link": "..."
          }
        }
      ],
      "why_this_set": "...",
      "preference_alignment": ["..."],
      "query_alignment": ["..."],
      "visual_alignment": ["..."],
      "tradeoffs": [],
      "confidence_score": 0.91
    }
  ]
}
```

## Rule

```mermaid
flowchart LR
    LLM[LLM Agents] --> D[All taste, style, query, image, and set decisions]
    Code[Local Code] --> C[Catalog retrieval, candidate IDs, hydration, validation]
```

No hardcoded query breakdown. No hardcoded style rules. No individual-product recommendation as the final answer.
