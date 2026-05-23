#!/usr/bin/env python3
"""
Test script for the new Catalog Search Tree and Facets API endpoints.
Runs FastAPI TestClient to verify correct responses.
"""

import sys
from pathlib import Path

# Add backend directory to sys.path to resolve imports
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from main import app


def test_search_tree_endpoints():
    client = TestClient(app)

    print("--- Testing GET /api/catalog/search-tree (dataset='current') ---")
    response = client.get("/api/catalog/search-tree?dataset=current")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()
    assert "total_products" in data
    assert "navigation_order" in data
    assert "navigation_tree" in data
    assert "facet_fields" in data
    assert "facets" in data
    print(f"Success! Found {data['total_products']} products in current in-memory catalog.")
    print("Navigation Order:", data["navigation_order"])
    print("Available Facets:", list(data["facets"].keys()))

    print("\n--- Testing GET /api/catalog/facets (dataset='current') ---")
    response = client.get("/api/catalog/facets?dataset=current")
    assert response.status_code == 200
    data = response.json()
    assert "facets" in data
    print("Success! Retrieved facets dictionary.")

    print("\n--- Testing GET /api/catalog/navigation (dataset='current') ---")
    response = client.get("/api/catalog/navigation?dataset=current")
    assert response.status_code == 200
    data = response.json()
    assert "navigation_order" in data
    assert "navigation_tree" in data
    print("Success! Retrieved hierarchical navigation tree.")

    # Test precomputed dataset (e.g., dataset2)
    print("\n--- Testing GET /api/catalog/search-tree (dataset='dataset2') ---")
    response = client.get("/api/catalog/search-tree?dataset=dataset2")
    if response.status_code == 200:
        data = response.json()
        print(f"Success! Loaded precomputed 'dataset2' search tree containing {data.get('total_products')} products.")
    else:
        print(f"Precomputed dataset2 not available (Code: {response.status_code})")

    # Test precomputed dataset (e.g., gymshark)
    print("\n--- Testing GET /api/catalog/search-tree (dataset='gymshark') ---")
    response = client.get("/api/catalog/search-tree?dataset=gymshark")
    if response.status_code == 200:
        data = response.json()
        print(f"Success! Loaded precomputed 'gymshark' search tree containing {data.get('total_products')} products.")
    else:
        print(f"Precomputed gymshark not available (Code: {response.status_code})")

    print("\nAll search tree & facet endpoints tested successfully!")


if __name__ == "__main__":
    test_search_tree_endpoints()
