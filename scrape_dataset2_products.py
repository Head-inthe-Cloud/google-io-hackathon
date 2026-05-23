#!/usr/bin/env python3
import argparse
import json
import random
import re
import time
from html import unescape
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from curl_cffi import requests


STORES = [
    {
        "store": "fashion_nova",
        "label": "Fashion Nova",
        "base_url": "https://fashionnova.com",
        "products_endpoint": "https://fashionnova.com/products.json",
    },
    {
        "store": "taylor_stitch",
        "label": "Taylor Stitch",
        "base_url": "https://www.taylorstitch.com",
        "products_endpoint": "https://www.taylorstitch.com/products.json",
    },
    {
        "store": "everlane",
        "label": "Everlane",
        "base_url": "https://www.everlane.com",
        "products_endpoint": "https://www.everlane.com/products.json",
    },
]
DEFAULT_OUTPUT = "dataset2_products.json"


def clean_text(value):
    value = unescape(str(value or ""))
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def strip_body_html(body_html):
    if not body_html:
        return []

    soup = BeautifulSoup(body_html, "html.parser")
    text = soup.get_text("\n", strip=True)
    text = re.sub(r"\s*•\s*", "\n", text)
    text = re.sub(r"\s+-\s+(?=[A-Za-z0-9])", "\n", text)

    chunks = []
    for raw_chunk in text.splitlines():
        chunk = clean_text(raw_chunk.lstrip("- "))
        if not chunk:
            continue
        normalized = chunk.lower().rstrip(":")
        if normalized in {"details", "description", "materials", "materials & care", "size & fit"}:
            continue
        if normalized.startswith("sku"):
            continue
        if re.match(r"^[0-9]+% ", chunk):
            continue
        chunks.append(chunk)
    return chunks


def normalize_phrase(value):
    value = clean_text(value)
    value = value.replace("_", " ").replace("-", " ")
    value = re.sub(r"\s+", " ", value)
    return value


def search_value(value):
    value = normalize_phrase(value).lower()
    value = value.replace("&", "and")
    value = value.replace("'", "")
    value = re.sub(r"[^a-z0-9/]+", " ", value)
    value = re.sub(r"\s+", " ", value)
    value = value.strip()
    mapping = {
        "mens": "men",
        "womens": "women",
        "woman": "women",
        "man": "men",
    }
    return mapping.get(value, value or None)


def unique_values(values):
    seen = set()
    result = []
    for value in values:
        value = search_value(value)
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def split_tags(tags):
    if isinstance(tags, str):
        raw_tags = tags.split(",")
    else:
        raw_tags = tags or []
    return [clean_text(tag) for tag in raw_tags if clean_text(tag)]


def tag_value(tags, prefixes):
    prefixes = [prefix.lower() + ":" for prefix in prefixes]
    for tag in tags:
        tag_lower = tag.lower()
        for prefix in prefixes:
            if tag_lower.startswith(prefix):
                return clean_text(tag.split(":", 1)[1])
    return None


def title_color(title):
    title = title or ""
    separators = [" | ", " - ", " in "]
    for separator in separators:
        if separator in title:
            return clean_text(title.rsplit(separator, 1)[-1])
    return None


def product_image_url(product):
    images = product.get("images") or []
    if images:
        image = images[0]
        if isinstance(image, dict):
            return image.get("src")
    image = product.get("image") or {}
    if isinstance(image, dict):
        return image.get("src")
    return None


def product_link(store, product):
    handle = product.get("handle")
    if not handle:
        return None
    return urljoin(store["base_url"], f"/products/{handle}")


def infer_gender(product, tags):
    text = " ".join(
        [
            product.get("title") or "",
            product.get("product_type") or "",
            " ".join(tags),
        ]
    ).lower()
    women_terms = ["women", "womens", "woman", "ladies", "girl", "girls", "female"]
    men_terms = ["men", "mens", "man", "male", "guys"]
    if any(re.search(rf"\b{term}\b", text) for term in women_terms):
        return "women"
    if any(re.search(rf"\b{term}\b", text) for term in men_terms):
        return "men"
    return "unisex"


def category_from_title_or_type(product):
    text = " ".join([product.get("title") or "", product.get("product_type") or ""]).lower()
    keyword_map = [
        ("jumpsuit", "jumpsuit"),
        ("romper", "romper"),
        ("dress", "dress"),
        ("skirt", "skirt"),
        ("jean", "jeans"),
        ("denim", "jeans"),
        ("pant", "pants"),
        ("trouser", "pants"),
        ("chino", "pants"),
        ("short", "shorts"),
        ("legging", "leggings"),
        ("sweatpant", "sweatpants"),
        ("jogger", "joggers"),
        ("hoodie", "hoodie"),
        ("sweatshirt", "sweatshirt"),
        ("sweater", "sweater"),
        ("cardigan", "cardigan"),
        ("jacket", "jacket"),
        ("coat", "coat"),
        ("blazer", "blazer"),
        ("shirt", "shirt"),
        ("tee", "t-shirt"),
        ("t-shirt", "t-shirt"),
        ("tank", "tank"),
        ("bodysuit", "bodysuit"),
        ("bra", "bra"),
        ("swim", "swimwear"),
        ("bikini", "swimwear"),
        ("shoe", "shoes"),
        ("boot", "boots"),
        ("sandal", "sandals"),
        ("heel", "heels"),
        ("sneaker", "sneakers"),
        ("bag", "bag"),
        ("belt", "belt"),
        ("hat", "hat"),
        ("cap", "cap"),
        ("sock", "socks"),
        ("jewelry", "jewelry"),
    ]
    for keyword, category in keyword_map:
        if keyword in text:
            return category
    return search_value(product.get("product_type")) or "product"


def infer_department(category, product_type):
    category = search_value(category)
    product_type = search_value(product_type)
    accessories = {
        "bag", "belt", "hat", "cap", "socks", "jewelry", "shoes", "boots",
        "sandals", "heels", "sneakers",
    }
    if category in accessories or product_type in accessories:
        return "accessories"
    if category in {"bra", "swimwear"}:
        return "intimates"
    if category:
        return "apparel"
    return None


def parent_category(product_type):
    product_type = search_value(product_type)
    groups = {
        "dresses": {"dress"},
        "one pieces": {"jumpsuit", "romper"},
        "tops": {"shirt", "t-shirt", "tank", "bodysuit", "sweater", "cardigan", "hoodie", "sweatshirt"},
        "bottoms": {"jeans", "pants", "shorts", "leggings", "sweatpants", "joggers", "skirt"},
        "outerwear": {"jacket", "coat", "blazer"},
        "shoes": {"shoes", "boots", "sandals", "heels", "sneakers"},
        "accessories": {"bag", "belt", "hat", "cap", "socks", "jewelry"},
        "intimates": {"bra"},
        "swimwear": {"swimwear"},
    }
    for category, values in groups.items():
        if product_type in values:
            return category
    return product_type


def infer_fit(product, tags, body_points):
    text = " ".join([product.get("title") or "", product.get("product_type") or "", " ".join(tags + body_points)]).lower()
    fit_patterns = [
        ("oversized", "oversized"),
        ("relaxed fit", "relaxed fit"),
        ("slim fit", "slim fit"),
        ("skinny", "skinny"),
        ("straight", "straight"),
        ("wide leg", "wide leg"),
        ("boxy", "boxy"),
        ("cropped", "cropped"),
        ("fitted", "fitted"),
    ]
    for needle, value in fit_patterns:
        if needle in text:
            return value
    return search_value(tag_value(tags, ["fit"]))


def infer_features(tags, body_points):
    raw_features = []
    feature_terms = [
        "stretch", "organic cotton", "linen", "cotton", "silk", "cashmere",
        "wool", "water resistant", "waterproof", "lightweight", "breathable",
        "pockets", "zip", "ribbed", "vegan", "recycled", "sustainable",
        "high waisted", "low rise", "mid rise", "button front", "washable",
        "machine washable",
    ]
    text = " ".join(tags + body_points).lower()
    for term in feature_terms:
        if term in text:
            raw_features.append(term)
    for tag in tags:
        tag_key = search_value(tag)
        if not tag_key:
            continue
        if ":" in tag:
            continue
        if re.match(r"^(all promo|best seller|category|colorfam|edp|final sale|filter|full price|hazmat|hidden|no returns|no returns exchanges|onsale|prop65|regprice|restocked|sync|women|men|ygroup)", tag_key):
            continue
        if re.search(r"\b(false|true|missing|new badge|no badge)\b", tag_key):
            continue
        if len(tag_key.split()) <= 4:
            raw_features.append(tag_key)
    return unique_values(raw_features)[:12]


def infer_activity(product, tags):
    text = " ".join([product.get("title") or "", product.get("product_type") or "", " ".join(tags)]).lower()
    for activity in ["workout", "active", "running", "training", "swim", "workwear", "casual", "formal", "wedding"]:
        if activity in text:
            if activity == "workout":
                return "training"
            if activity == "active":
                return "activewear"
            return activity
    return None


def infer_availability(product):
    variants = product.get("variants") or []
    if variants and all(not variant.get("available", True) for variant in variants):
        return "sold out"
    return "active"


def build_description(store, product, categories, body_points):
    audience = categories.get("gender") or store["label"]
    if audience == "women":
        audience = "Women's"
    elif audience == "men":
        audience = "Men's"
    elif audience == "unisex":
        audience = "Unisex"
    else:
        audience = store["label"]

    pieces = [
        audience,
        categories.get("fit"),
        categories.get("color"),
        categories.get("product_type") or categories.get("category"),
    ]
    description = " ".join(piece for piece in pieces if piece)
    support = []
    for point in body_points:
        normalized = point.lower()
        if normalized.startswith("available in "):
            continue
        if normalized in {"final sale", "sale", "new"}:
            continue
        support.append(point)
        if len(support) >= 2:
            break
    if support:
        description += " with " + " and ".join(clean_text(point).lower() for point in support)
    if categories.get("activity"):
        description += f" for {categories['activity']}"
    return description[:700].rstrip(" .") + "."


def build_categories(store, product, tags, body_points):
    item_type = category_from_title_or_type(product)
    product_type = search_value(item_type)
    category = parent_category(product_type)
    gender = infer_gender(product, tags)
    department = infer_department(category, product_type)
    color = search_value(tag_value(tags, ["color", "colour", "filter color", "filter-colour"]) or title_color(product.get("title")))
    collection = search_value(product.get("vendor")) if product.get("vendor") and product.get("vendor") != store["label"] else None

    categories = {
        "store": store["store"],
        "brand": search_value(store["label"]),
        "gender": gender,
        "department": department,
        "category": category,
        "product_type": product_type,
        "activity": infer_activity(product, tags),
        "collection": collection,
        "color": color,
        "fit": infer_fit(product, tags, body_points),
        "support": search_value(tag_value(tags, ["support"])),
        "features": infer_features(tags, body_points),
        "season": search_value(tag_value(tags, ["season"])),
        "availability": infer_availability(product),
        "category_path": unique_values([store["store"], store["label"], gender, department, category, product_type]),
    }
    return categories


def compact_product(store, product):
    tags = split_tags(product.get("tags"))
    body_points = strip_body_html(product.get("body_html"))
    categories = build_categories(store, product, tags, body_points)
    return {
        "product_name": clean_text(product.get("title")),
        "image_url": product_image_url(product),
        "description": build_description(store, product, categories, body_points),
        "product_link": product_link(store, product),
        "categories": categories,
    }


def fetch_page(store, page, limit, retries):
    params = {"limit": str(limit), "page": str(page)}
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            response = requests.get(
                store["products_endpoint"],
                params=params,
                impersonate="chrome",
                timeout=45,
                headers={"Accept": "application/json,text/plain,*/*"},
            )
            if response.status_code == 200:
                return response.json().get("products", [])
            if response.status_code == 400 and "Page * Limit exceeds the 25000 limit" in response.text:
                return []
            last_error = f"HTTP {response.status_code}: {response.text[:200]}"
        except Exception as exc:
            last_error = repr(exc)
        time.sleep(min(2 * attempt, 10))
    raise RuntimeError(f"Failed to fetch {store['label']} page {page}: {last_error}")


def scrape_store(store, limit, delay, retries, max_pages=None, max_products=None):
    products = []
    seen_ids = set()
    page = 1
    while True:
        if max_products and len(products) >= max_products:
            break
        if max_pages and page > max_pages:
            break
        page_products = fetch_page(store, page, limit, retries)
        print(f"{store['label']} page {page}: {len(page_products)} products", flush=True)
        if not page_products:
            break
        for product in page_products:
            product_id = product.get("id") or product.get("handle")
            if product_id in seen_ids:
                continue
            seen_ids.add(product_id)
            products.append(compact_product(store, product))
            if max_products and len(products) >= max_products:
                break
        if len(page_products) < limit:
            break
        page += 1
        time.sleep(delay)
    return products


def representative_sample(products_by_store, total_limit, seed):
    all_products = [
        product
        for products in products_by_store.values()
        for product in products
    ]
    if not total_limit or len(all_products) <= total_limit:
        return all_products

    rng = random.Random(seed)
    store_names = list(products_by_store)
    base_quota = total_limit // len(store_names)
    remainder = total_limit % len(store_names)
    sampled = []
    sampled_ids = set()
    overflow = []

    for index, store_name in enumerate(store_names):
        products = products_by_store[store_name]
        quota = base_quota + (1 if index < remainder else 0)
        if len(products) <= quota:
            chosen = products
        else:
            chosen = rng.sample(products, quota)

        for product in chosen:
            key = product.get("product_link") or product.get("product_name")
            sampled_ids.add(key)
            sampled.append(product)

        for product in products:
            key = product.get("product_link") or product.get("product_name")
            if key not in sampled_ids:
                overflow.append(product)

    if len(sampled) < total_limit and overflow:
        needed = total_limit - len(sampled)
        sampled.extend(rng.sample(overflow, min(needed, len(overflow))))

    sampled.sort(key=lambda product: (
        product.get("categories", {}).get("store") or "",
        product.get("product_name") or "",
        product.get("product_link") or "",
    ))
    return sampled[:total_limit]


def main():
    parser = argparse.ArgumentParser(description="Scrape dataset 2 catalogs from products.json endpoints.")
    parser.add_argument("-o", "--output", default=DEFAULT_OUTPUT, help=f"Output path, default: {DEFAULT_OUTPUT}")
    parser.add_argument("--limit", type=int, default=250, help="Products per page, max 250.")
    parser.add_argument("--delay", type=float, default=0.25, help="Delay between pages in seconds.")
    parser.add_argument("--retries", type=int, default=3, help="Retries per page.")
    parser.add_argument("--max-pages", type=int, help="Optional max pages per store for testing.")
    parser.add_argument("--max-products-per-store", type=int, help="Optional collection cap per store before sampling.")
    parser.add_argument("--total-limit", type=int, default=10000, help="Representative output cap across all stores.")
    parser.add_argument("--sample-seed", type=int, default=42, help="Deterministic random seed for representative sampling.")
    args = parser.parse_args()

    products_by_store = {}
    for store in STORES:
        products_by_store[store["store"]] = scrape_store(
            store,
            min(args.limit, 250),
            args.delay,
            args.retries,
            max_pages=args.max_pages,
            max_products=args.max_products_per_store,
        )

    all_products = representative_sample(products_by_store, args.total_limit, args.sample_seed)
    before_counts = {store: len(products) for store, products in products_by_store.items()}
    after_counts = {
        store: sum(1 for product in all_products if product.get("categories", {}).get("store") == store)
        for store in products_by_store
    }
    print(f"store counts before sampling: {json.dumps(before_counts, sort_keys=True)}", flush=True)
    print(f"store counts after sampling: {json.dumps(after_counts, sort_keys=True)}", flush=True)

    with open(args.output, "w", encoding="utf-8") as file:
        json.dump(all_products, file, ensure_ascii=False, indent=2)
        file.write("\n")

    print(f"wrote {len(all_products)} products to {args.output}", flush=True)


if __name__ == "__main__":
    main()
