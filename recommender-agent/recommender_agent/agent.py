from .catalog import normalize_text, value_matches


CONTEXT_COMPILER_PROMPT = """
You are the Context Compiler Agent for a retail styling recommender.

Inputs:
- Raw user preference stack text from a questionnaire-derived profile.
- Live user query text.
- Optional user images already attached to this multimodal request.
- Catalog facet summary showing searchable fields and values.

Do not recommend products in this step.
Compile the user's current shopping problem into a search strategy.
Use only catalog facet fields that exist in the facet summary.
If images are present, infer visual constraints such as colors, garment types,
occasion signals, matching/complementing needs, and style direction.

Return JSON:
{
  "shopping_context": {
    "goal": "string",
    "recommendation_mode": "product_sets",
    "needed_set_shape": "string",
    "must_haves": ["string"],
    "nice_to_haves": ["string"],
    "avoid": ["string"],
    "visual_observations": ["string"]
  },
  "active_preference_stack": {
    "summary": "string",
    "style_priorities": ["string"],
    "avoid": ["string"],
    "tradeoff_rules": ["string"]
  },
  "business_filters": {
    "filters": {"field": ["value"]},
    "exclude_filters": {"field": ["value"]}
  },
  "initial_search_branches": [
    {
      "branch_id": "b1",
      "goal": "string",
      "filters": {"field": ["value"]},
      "exclude_filters": {"field": ["value"]},
      "why": "string"
    }
  ],
  "set_assembly_brief": {
    "target_number_of_sets": 5,
    "set_rules": ["string"],
    "item_role_guidance": ["string"]
  }
}
"""


SEARCH_EXPANDER_PROMPT = """
You are the Search Expansion Agent.

You receive the compiled context, catalog facet summary, and breadth-first search
trace so far. Decide the next layer of search branches.

Do not recommend final products. Do not choose final sets.
Expand breadth-first: propose sibling branches that cover plausible alternatives,
tradeoffs, or missing item roles. Use only catalog facet fields and values present
in the facet summary.

Return JSON:
{
  "continue_search": true,
  "next_branches": [
    {
      "branch_id": "b_next",
      "goal": "string",
      "filters": {"field": ["value"]},
      "exclude_filters": {"field": ["value"]},
      "why": "string"
    }
  ],
  "stop_reason": "string or null"
}
"""


SET_BUILDER_PROMPT = """
You are the Stylist Set Builder Agent.

Your only job is to recommend buyable product sets for the user.
Each recommendation must be a combination set: a list of catalog items to buy.
Use only candidate_id values present in the candidate pools. Do not invent products.
Respect the user's query, preference stack, visual inputs, and search evidence.

Return JSON:
{
  "product_sets": [
    {
      "set_id": "set_001",
      "set_name": "string",
      "items": [
        {
          "candidate_id": "string",
          "role": "string",
          "why_this_item": "string"
        }
      ],
      "why_this_set": "string",
      "preference_alignment": ["string"],
      "query_alignment": ["string"],
      "visual_alignment": ["string"],
      "tradeoffs": ["string"],
      "confidence_score": 0.0
    }
  ]
}
"""


CRITIC_PROMPT = """
You are the Recommendation Critic Agent.

Validate the proposed product sets against:
- user query
- preference stack
- visual observations
- catalog item evidence

Reject invented candidate IDs, incoherent sets, and sets that clearly violate the
compiled context. Return JSON:
{
  "approved_product_sets": ["set_id"],
  "rejected_product_sets": [
    {"set_id": "set_id", "reason": "string"}
  ],
  "notes": ["string"]
}
"""


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _normalize_filter_map(raw):
    result = {}
    for field, values in (raw or {}).items():
        normalized_values = []
        for value in _as_list(values):
            value = normalize_text(value)
            if value and value not in normalized_values:
                normalized_values.append(value)
        if normalized_values:
            result[field] = normalized_values
    return result


def _matches_filter_map(product, filters):
    for field, values in _normalize_filter_map(filters).items():
        if not value_matches(product, field, values):
            return False
    return True


def _matches_any_exclude(product, exclude_filters):
    for field, values in _normalize_filter_map(exclude_filters).items():
        if value_matches(product, field, values):
            return True
    return False


def _merge_filters(*filter_maps):
    merged = {}
    for filter_map in filter_maps:
        for field, values in _normalize_filter_map(filter_map).items():
            merged.setdefault(field, [])
            for value in values:
                if value not in merged[field]:
                    merged[field].append(value)
    return merged


def _branch_signature(branch):
    return (
        tuple(sorted((field, tuple(values)) for field, values in _normalize_filter_map(branch.get("filters")).items())),
        tuple(sorted((field, tuple(values)) for field, values in _normalize_filter_map(branch.get("exclude_filters")).items())),
    )


def retrieve_branch_candidates(catalog, branch, business_filters, limit):
    filters = _merge_filters(business_filters.get("filters"), branch.get("filters"))
    exclude_filters = _merge_filters(
        business_filters.get("exclude_filters"),
        branch.get("exclude_filters"),
    )

    matches = []
    for index, product in enumerate(catalog.products):
        if not _matches_filter_map(product, filters):
            continue
        if _matches_any_exclude(product, exclude_filters):
            continue
        matches.append(catalog.compact_product(product, f"p{index}"))
        if len(matches) >= limit:
            break
    return matches


def _emit_progress(progress_callback, event_type, **payload):
    if progress_callback:
        progress_callback({"type": event_type, **payload})


def compile_context(llm_client, catalog, preference_stack, query, images, target_sets):
    return llm_client.generate_json(
        CONTEXT_COMPILER_PROMPT,
        {
            "preference_stack": preference_stack,
            "query": query,
            "image_inputs": [
                {key: value for key, value in image.items() if key != "bytes"}
                for image in images
            ],
            "catalog_facet_summary": catalog.facet_summary(),
            "target_number_of_sets": target_sets,
        },
        images=images,
    )


def expand_search(llm_client, catalog, compiled_context, trace, depth):
    return llm_client.generate_json(
        SEARCH_EXPANDER_PROMPT,
        {
            "depth": depth,
            "compiled_context": compiled_context,
            "catalog_facet_summary": catalog.facet_summary(),
            "search_trace": trace,
            "instruction": "Return the next breadth layer, not per-branch deepening.",
        },
    )


def build_product_sets(llm_client, compiled_context, trace, candidate_pools, target_sets):
    return llm_client.generate_json(
        SET_BUILDER_PROMPT,
        {
            "compiled_context": compiled_context,
            "search_trace": trace,
            "candidate_pools": candidate_pools,
            "target_number_of_sets": target_sets,
        },
    )


def critique_product_sets(llm_client, compiled_context, product_sets, candidate_lookup):
    return llm_client.generate_json(
        CRITIC_PROMPT,
        {
            "compiled_context": compiled_context,
            "product_sets": product_sets,
            "candidate_lookup": candidate_lookup,
        },
    )


def hydrate_product_sets(product_sets, candidate_lookup):
    hydrated = []
    for product_set in product_sets:
        hydrated_items = []
        for item in product_set.get("items", []):
            candidate_id = item.get("candidate_id")
            product = candidate_lookup.get(candidate_id)
            if not product:
                continue
            hydrated_items.append(
                {
                    "candidate_id": candidate_id,
                    "role": item.get("role"),
                    "why_this_item": item.get("why_this_item"),
                    "product": product,
                }
            )
        if hydrated_items:
            updated = dict(product_set)
            updated["items"] = hydrated_items
            hydrated.append(updated)
    return hydrated


def recommend_product_sets(
    catalog,
    llm_client,
    query,
    preference_stack,
    images=None,
    target_sets=5,
    max_depth=2,
    max_branches_per_layer=12,
    candidates_per_branch=24,
    include_debug=False,
    progress_callback=None,
):
    images = images or []
    _emit_progress(
        progress_callback,
        "started",
        target_sets=target_sets,
        max_depth=max_depth,
        max_branches_per_layer=max_branches_per_layer,
        candidates_per_branch=candidates_per_branch,
    )
    _emit_progress(progress_callback, "context_compiler.started")
    compiled_context = compile_context(
        llm_client,
        catalog,
        preference_stack,
        query,
        images,
        target_sets,
    )

    business_filters = compiled_context.get("business_filters") or {}
    current_layer = list(compiled_context.get("initial_search_branches") or [])
    _emit_progress(
        progress_callback,
        "context_compiler.completed",
        shopping_context=compiled_context.get("shopping_context"),
        initial_search_branch_count=len(current_layer),
    )
    visited = set()
    trace = []
    candidate_pools = []
    candidate_lookup = {}

    for depth in range(max_depth + 1):
        if not current_layer:
            _emit_progress(
                progress_callback,
                "search_layer.skipped",
                depth=depth,
                reason="No search branches available.",
            )
            break

        _emit_progress(
            progress_callback,
            "search_layer.started",
            depth=depth,
            branch_count=min(len(current_layer), max_branches_per_layer),
        )
        processed_this_layer = []
        for branch in current_layer[:max_branches_per_layer]:
            signature = _branch_signature(branch)
            if signature in visited:
                _emit_progress(
                    progress_callback,
                    "branch.skipped",
                    depth=depth,
                    branch_id=branch.get("branch_id"),
                    reason="Branch filters were already visited.",
                )
                continue
            visited.add(signature)
            processed_this_layer.append(branch)

            _emit_progress(
                progress_callback,
                "branch_retrieval.started",
                depth=depth,
                branch_id=branch.get("branch_id"),
                goal=branch.get("goal"),
                filters=branch.get("filters") or {},
                exclude_filters=branch.get("exclude_filters") or {},
            )
            candidates = retrieve_branch_candidates(
                catalog,
                branch,
                business_filters,
                candidates_per_branch,
            )
            pool = {
                "depth": depth,
                "branch": branch,
                "candidate_count": len(candidates),
                "candidates": candidates,
            }
            candidate_pools.append(pool)
            trace.append(
                {
                    "depth": depth,
                    "branch": branch,
                    "candidate_count": len(candidates),
                    "sample_candidate_ids": [candidate["candidate_id"] for candidate in candidates[:5]],
                }
            )
            _emit_progress(
                progress_callback,
                "branch_retrieval.completed",
                depth=depth,
                branch_id=branch.get("branch_id"),
                candidate_count=len(candidates),
                sample_candidates=[
                    {
                        "candidate_id": candidate.get("candidate_id"),
                        "product_name": candidate.get("product_name"),
                    }
                    for candidate in candidates[:5]
                ],
            )
            for candidate in candidates:
                candidate_lookup[candidate["candidate_id"]] = candidate

        if depth >= max_depth or not processed_this_layer:
            _emit_progress(
                progress_callback,
                "search_layer.completed",
                depth=depth,
                processed_branch_count=len(processed_this_layer),
                stop_reason="Reached max depth or no new branches were processed.",
            )
            break

        _emit_progress(progress_callback, "search_expander.started", next_depth=depth + 1)
        expansion = expand_search(llm_client, catalog, compiled_context, trace, depth + 1)
        current_layer = expansion.get("next_branches", [])
        _emit_progress(
            progress_callback,
            "search_expander.completed",
            next_depth=depth + 1,
            continue_search=expansion.get("continue_search", True),
            next_branch_count=len(current_layer),
            stop_reason=expansion.get("stop_reason"),
        )
        if not expansion.get("continue_search", True):
            break

    _emit_progress(
        progress_callback,
        "set_builder.started",
        candidate_pool_count=len(candidate_pools),
        unique_candidate_count=len(candidate_lookup),
    )
    built = build_product_sets(
        llm_client,
        compiled_context,
        trace,
        candidate_pools,
        target_sets,
    )
    product_sets = built.get("product_sets", [])
    _emit_progress(
        progress_callback,
        "set_builder.completed",
        proposed_product_set_count=len(product_sets),
    )

    _emit_progress(progress_callback, "critic.started", proposed_product_set_count=len(product_sets))
    critique = critique_product_sets(
        llm_client,
        compiled_context,
        product_sets,
        candidate_lookup,
    )
    _emit_progress(
        progress_callback,
        "critic.completed",
        approved_product_set_count=len(critique.get("approved_product_sets") or []),
        rejected_product_set_count=len(critique.get("rejected_product_sets") or []),
    )
    if "approved_product_sets" in critique:
        approved = set(critique.get("approved_product_sets") or [])
        product_sets = [product_set for product_set in product_sets if product_set.get("set_id") in approved]

    hydrated_product_sets = hydrate_product_sets(product_sets, candidate_lookup)
    result = {
        "output_format_version": "agentic_product_set_recommender.v1",
        "recommendation_type": "product_sets",
        "product_sets": hydrated_product_sets,
    }
    if include_debug:
        result["debug"] = {
            "user_query": query,
            "compiled_context": compiled_context,
            "search_trace": {
                "strategy": "llm_planned_breadth_first_candidate_search",
                "visited_branches": len(visited),
                "max_depth": max_depth,
                "max_branches_per_layer": max_branches_per_layer,
                "candidates_per_branch": candidates_per_branch,
                "branches": trace,
            },
            "critic": critique,
        }
    _emit_progress(
        progress_callback,
        "completed",
        product_set_count=len(hydrated_product_sets),
        visited_branch_count=len(visited),
    )
    return result
