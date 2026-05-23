import json
import re
from collections import Counter


def normalize_text(value):
    value = str(value or "").lower()
    value = value.replace("&", " and ")
    value = value.replace("'", "")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def category_value(product, field):
    categories = product.get("categories") or {}
    return categories.get(field)


def value_matches(product, field, allowed_values):
    value = category_value(product, field)
    if value is None:
        return False

    allowed = {normalize_text(item) for item in allowed_values if item is not None}
    if isinstance(value, list):
        return bool({normalize_text(item) for item in value if item is not None} & allowed)
    return normalize_text(value) in allowed


def searchable_text(product):
    categories = product.get("categories") or {}
    chunks = [
        product.get("product_name"),
        product.get("description"),
        product.get("product_link"),
    ]
    for value in categories.values():
        if isinstance(value, list):
            chunks.extend(value)
        else:
            chunks.append(value)
    return normalize_text(" ".join(str(chunk or "") for chunk in chunks))


class Catalog:
    def __init__(self, products):
        self.products = products
        self._search_text = {id(product): searchable_text(product) for product in products}
        self.facets = self._build_facets()

    @classmethod
    def load(cls, path):
        with open(path, encoding="utf-8") as file:
            products = json.load(file)
        if not isinstance(products, list):
            raise ValueError("Catalog must be a top-level JSON array of products.")
        return cls(products)

    def text_for(self, product):
        return self._search_text[id(product)]

    def _build_facets(self):
        counters = {}
        for field in [
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
        ]:
            counter = Counter()
            for product in self.products:
                value = category_value(product, field)
                if value is None:
                    continue
                if isinstance(value, list):
                    counter.update(normalize_text(item) for item in value if item)
                else:
                    counter[normalize_text(value)] += 1
            counters[field] = counter
        return counters

    def facet_values(self, field, min_count=1):
        counter = self.facets.get(field, Counter())
        return [
            value
            for value, count in counter.most_common()
            if value and count >= min_count
        ]

    def facet_summary(self, per_field=30):
        return {
            field: [
                {"value": value, "count": count}
                for value, count in counter.most_common(per_field)
            ]
            for field, counter in self.facets.items()
        }

    def compact_product(self, product, item_id):
        categories = product.get("categories") or {}
        return {
            "candidate_id": item_id,
            "product_name": product.get("product_name"),
            "description": product.get("description"),
            "product_link": product.get("product_link"),
            "image_url": product.get("image_url"),
            "categories": categories,
        }
