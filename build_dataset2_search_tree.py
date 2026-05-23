#!/usr/bin/env python3
import argparse
import json
from collections import Counter


DEFAULT_INPUT = "dataset2_products.json"
DEFAULT_OUTPUT = "dataset2_search_tree.json"
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


def title_label(value):
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


def product_value(product, field):
    categories = product.get("categories") or {}
    value = categories.get(field)
    if isinstance(value, list):
        return value
    return value


def make_node(field, value, count, children=None):
    node = {
        "field": field,
        "value": value,
        "label": title_label(value),
        "count": count,
    }
    if children:
        node["children"] = children
    return node


def build_navigation(products, fields):
    if not fields:
        return []

    field = fields[0]
    buckets = {}
    for product in products:
        value = product_value(product, field) or "uncategorized"
        buckets.setdefault(value, []).append(product)

    nodes = []
    for value, bucket in buckets.items():
        children = build_navigation(bucket, fields[1:])
        nodes.append(make_node(field, value, len(bucket), children))

    nodes.sort(key=lambda node: (-node["count"], node["label"]))
    return nodes


def build_facets(products):
    facets = {}
    for field in FACET_FIELDS:
        counter = Counter()
        for product in products:
            value = product_value(product, field)
            if value is None:
                continue
            if isinstance(value, list):
                counter.update(item for item in value if item)
            elif value:
                counter[value] += 1

        facets[field] = [
            {
                "value": value,
                "label": title_label(value),
                "count": count,
            }
            for value, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))
        ]

    return facets


def main():
    parser = argparse.ArgumentParser(description="Build dataset 2 product search tree from compact product JSON.")
    parser.add_argument("-i", "--input", default=DEFAULT_INPUT, help=f"Input product JSON, default: {DEFAULT_INPUT}")
    parser.add_argument("-o", "--output", default=DEFAULT_OUTPUT, help=f"Output search tree JSON, default: {DEFAULT_OUTPUT}")
    args = parser.parse_args()

    with open(args.input, encoding="utf-8") as file:
        products = json.load(file)

    if not isinstance(products, list):
        raise ValueError("Expected a top-level product array.")

    payload = {
        "total_products": len(products),
        "navigation_order": NAVIGATION_FIELDS,
        "navigation_tree": build_navigation(products, NAVIGATION_FIELDS),
        "facet_fields": FACET_FIELDS,
        "facets": build_facets(products),
    }

    with open(args.output, "w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)
        file.write("\n")

    print(f"wrote search tree for {len(products)} products to {args.output}")


if __name__ == "__main__":
    main()
