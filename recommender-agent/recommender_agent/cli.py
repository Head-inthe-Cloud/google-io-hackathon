import argparse
import json
import sys

from .agent import recommend_product_sets
from .catalog import Catalog
from .llm import GeminiJSONClient


def read_text_argument(value, path):
    if path:
        with open(path, encoding="utf-8") as file:
            return file.read()
    return value or ""


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Run the agentic product-set recommender over a product catalog."
    )
    parser.add_argument("--catalog", required=True, help="Path to product catalog JSON array.")
    parser.add_argument("--query", required=True, help="Live shopper query.")
    parser.add_argument("--preference-stack", help="Raw preference stack text blob.")
    parser.add_argument("--preference-stack-file", help="Path to raw preference stack text blob.")
    parser.add_argument("--image", action="append", default=[], help="Optional user image path or URL. Repeatable.")
    parser.add_argument("--output", help="Write JSON output to this file. Defaults to stdout.")
    parser.add_argument("--target-sets", type=int, default=5)
    parser.add_argument("--max-depth", type=int, default=3)
    parser.add_argument("--max-branches-per-layer", type=int, default=12)
    parser.add_argument("--candidates-per-branch", type=int, default=24)
    parser.add_argument("--model", default="gemini-3.5-flash")
    parser.add_argument("--include-debug", action="store_true")
    args = parser.parse_args(argv)

    preference_stack = read_text_argument(args.preference_stack, args.preference_stack_file)
    catalog = Catalog.load(args.catalog)
    images = [
        {"url": image} if image.startswith("http://") or image.startswith("https://") else {"path": image}
        for image in args.image
    ]
    llm_client = GeminiJSONClient(model=args.model)
    result = recommend_product_sets(
        catalog,
        llm_client,
        args.query,
        preference_stack,
        images=images,
        target_sets=args.target_sets,
        max_depth=args.max_depth,
        max_branches_per_layer=args.max_branches_per_layer,
        candidates_per_branch=args.candidates_per_branch,
        include_debug=args.include_debug,
    )

    if args.output:
        with open(args.output, "w", encoding="utf-8") as file:
            json.dump(result, file, ensure_ascii=False, indent=2)
            file.write("\n")
    else:
        json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")


if __name__ == "__main__":
    main()
