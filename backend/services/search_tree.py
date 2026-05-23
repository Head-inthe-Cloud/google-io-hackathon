import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional

# Constants
NAVIGATION_FIELDS = ["store", "brand", "gender", "department", "category", "product_type"]
FACET_FIELDS = [
    "store",
    "brand",
    "gender",
    "department",
    "category",
    "product_type",
    "activity",
    "collection",
    "color",
    "fit",
    "support",
    "features",
    "season",
    "availability",
]

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


def title_label(value: Any) -> str:
    if not value:
        return "Uncategorized"
    value = str(value).replace("_", " ").replace("-", " ")
    acronyms = {"ss": "Short Sleeve", "ls": "Long Sleeve"}
    small_words = {"and", "or", "of", "the"}
    words = []
    for index, word in enumerate(value.split()):
        if word in acronyms:
            words.append(acronyms[word])
        elif index > 0 and word in small_words:
            words.append(word)
        else:
            words.append(word.title())
    return " ".join(words)


def product_value(product: Dict[str, Any], field: str) -> Any:
    """
    Get the value of a field from a product.
    Supports both nested 'categories' objects (scraped format) and flat keys (in-memory format).
    """
    # 1. Try nested categories
    categories = product.get("categories") or {}
    value = categories.get(field)
    if value is not None:
        return value

    # 2. Try direct property
    value = product.get(field)
    if value is not None:
        return value

    # 3. Intelligent defaults for missing fields to keep trees coherent
    if field == "brand" or field == "store":
        return product.get("brand", "Gymshark")
    if field == "gender":
        g = product.get("gender")
        if g == "mens" or g == "men":
            return "men"
        if g == "womens" or g == "women":
            return "women"
        return g

    return None


def make_node(field: str, value: Any, count: int, children: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    node = {
        "field": field,
        "value": value,
        "label": title_label(value),
        "count": count,
    }
    if children:
        node["children"] = children
    return node


def build_navigation(products: List[Dict[str, Any]], fields: List[str]) -> List[Dict[str, Any]]:
    if not fields:
        return []

    field = fields[0]
    buckets = {}
    for product in products:
        val = product_value(product, field)
        
        # If value is a list (e.g., features), take the first or use stringified
        if isinstance(val, list):
            val = val[0] if val else "uncategorized"
            
        val = val or "uncategorized"
        buckets.setdefault(val, []).append(product)

    nodes = []
    for val, bucket in buckets.items():
        children = build_navigation(bucket, fields[1:])
        nodes.append(make_node(field, val, len(bucket), children))

    nodes.sort(key=lambda node: (-node["count"], node["label"]))
    return nodes


def build_facets(products: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    facets = {}
    for field in FACET_FIELDS:
        counter = Counter()
        for product in products:
            val = product_value(product, field)
            if val is None:
                continue
            if isinstance(val, list):
                counter.update(item for item in val if item)
            elif val:
                counter[val] += 1

        facets[field] = [
            {
                "value": value,
                "label": title_label(value),
                "count": count,
            }
            for value, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))
        ]

    return facets


def get_search_tree_payload(products: List[Dict[str, Any]], custom_nav_fields: Optional[List[str]] = None, custom_facet_fields: Optional[List[str]] = None) -> Dict[str, Any]:
    """Generates a search tree payload dynamically for a given list of products."""
    nav_fields = custom_nav_fields or NAVIGATION_FIELDS
    facet_fields = custom_facet_fields or FACET_FIELDS

    return {
        "total_products": len(products),
        "navigation_order": nav_fields,
        "navigation_tree": build_navigation(products, nav_fields),
        "facet_fields": facet_fields,
        "facets": build_facets(products),
    }


def load_precomputed_search_tree(dataset: str) -> Optional[Dict[str, Any]]:
    """Loads a precomputed search tree JSON from the data directory if it exists."""
    file_map = {
        "dataset2": "dataset2_search_tree.json",
        "gymshark": "gymshark_search_tree.json",
    }
    filename = file_map.get(dataset)
    if not filename:
        return None

    filepath = DATA_DIR / filename
    if filepath.exists():
        try:
            with open(filepath, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading precomputed search tree {filename}: {e}")
            return None
    return None
