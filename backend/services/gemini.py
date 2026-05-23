import os
import json
import urllib.request
from google import genai
from google.genai import types
from typing import Dict, Any, List

# Global client
client = None


def init_gemini():
    global client
    if client is not None:
        return True

    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        client = genai.Client(api_key=api_key)
        return True
    return False


def get_client():
    """Return the initialized Gemini client, or None if not configured."""
    if not init_gemini():
        return None
    return client


def fetch_image_bytes(image_url: str) -> bytes:
    """Fetch image bytes from a URL."""
    if "mock" in image_url or image_url.startswith("http://localhost"):
        return b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b'

    try:
        req = urllib.request.Request(
            image_url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
        )
        with urllib.request.urlopen(req) as response:
            return response.read()
    except Exception as e:
        print(f"Error fetching image from URL {image_url}: {e}")
        raise ValueError(f"Could not retrieve image from url: {image_url}")


def analyze_clothing_item(image_url: str) -> Dict[str, Any]:
    """
    Sends an image of a wardrobe item to Gemini to analyze and output structured metadata.
    """
    if not init_gemini():
        return {
            "category": "top",
            "description": "A basic clothing item.",
            "colors": ["unknown"],
            "style_tags": ["casual"],
        }

    try:
        image_data = fetch_image_bytes(image_url)
        image_part = types.Part.from_bytes(data=image_data, mime_type="image/jpeg")

        prompt = (
            "Analyze this wardrobe item. Extract the following metadata in a flat JSON structure with "
            "lowercase values:\n"
            "1. 'category' (e.g., Tops, Bottoms, Outerwear, Sports Bras, Accessories, One-Piece)\n"
            "2. 'description' (short sentence describing the item)\n"
            "3. 'colors' (array of dominant colors)\n"
            "4. 'style_tags' (array of strings, e.g., ['casual', 'streetwear', 'minimal'])\n"
            "\n"
            "Return only the raw JSON, with no markdown codeblocks."
        )

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[image_part, prompt],
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        return json.loads(response.text.strip())

    except Exception as e:
        print(f"Error in Gemini image analysis: {e}")
        return {
            "category": "unknown",
            "description": "unknown",
            "colors": ["unknown"],
            "style_tags": [],
        }


def get_style_embedding(text_content: str) -> List[float]:
    """Generate a 768-dim vector embedding for text."""
    if not init_gemini():
        return [0.0] * 768

    try:
        response = client.models.embed_content(
            model="text-embedding-004",
            contents=text_content,
        )
        return response.embeddings[0].values
    except Exception as e:
        print(f"Error generating style embedding: {e}")
        return [0.0] * 768


def design_outfits_with_gemini(
    prompt: str, weather: str, catalog_items: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Uses Gemini as a professional stylist to compose outfit combinations
    from the given catalog items.

    TODO: This is a placeholder — the full agent pipeline (Intent Understanding →
    Clothes Matching → Fashion Master) will replace this function.
    """
    if not init_gemini() or not catalog_items:
        return [
            {
                "outfit_id": "rec_001",
                "items": catalog_items[:3] if catalog_items else [],
                "reason": f"Default recommendation for: {prompt}",
                "style_tags": [],
                "styling_tip": None,
                "confidence_score": None,
            }
        ]

    try:
        items_description = []
        for item in catalog_items:
            items_description.append(
                {
                    "id": item["id"],
                    "name": item.get("name"),
                    "category": item.get("category"),
                    "description": item.get("description"),
                    "colors": item.get("colors"),
                    "style_tags": item.get("style_tags"),
                }
            )

        system_instruction = (
            "You are an elite fashion designer and personal stylist working for an online store. "
            "Your goal is to compose cohesive outfits strictly using the available catalog items.\n"
            "Generate 3 to 5 distinct outfit recommendations tailored to the shopper's prompt.\n"
            "Return a JSON object with an 'outfits' array. Each outfit must have:\n"
            "- 'outfit_id': e.g. 'rec_001'\n"
            "- 'item_ids': array of item id integers from the catalog\n"
            "- 'reason': why these items work together for the prompt\n"
            "- 'style_tags': array of style tags for the outfit\n"
            "- 'styling_tip': a short actionable styling tip\n"
            "- 'confidence_score': float 0-1 representing how well the outfit matches the request\n"
            "Outfits should be practical — include at least a top and bottom, or a one-piece."
        )

        user_prompt = f"Styling Prompt: {prompt}"
        if weather:
            user_prompt += f"\nWeather: {weather}"
        user_prompt += f"\n\nAvailable Catalog Items:\n{json.dumps(items_description)}"

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=f"{system_instruction}\n\n{user_prompt}",
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )

        data = json.loads(response.text.strip())

        # Map item details back into the outfits
        items_by_id = {item["id"]: item for item in catalog_items}

        structured_outfits = []
        for outfit in data.get("outfits", []):
            item_ids = outfit.get("item_ids", [])
            mapped_items = []
            for item_id in item_ids:
                if item_id in items_by_id:
                    orig = items_by_id[item_id]
                    mapped_items.append(
                        {
                            "item_id": orig["id"],
                            "name": orig.get("name"),
                            "category": orig.get("category"),
                            "image_url": orig.get("image_url"),
                            "description": orig.get("description"),
                        }
                    )

            if mapped_items:
                structured_outfits.append(
                    {
                        "outfit_id": outfit.get("outfit_id", f"rec_{len(structured_outfits)+1:03d}"),
                        "items": mapped_items,
                        "reason": outfit.get("reason", ""),
                        "style_tags": outfit.get("style_tags", []),
                        "styling_tip": outfit.get("styling_tip"),
                        "confidence_score": outfit.get("confidence_score"),
                    }
                )

        return structured_outfits

    except Exception as e:
        print(f"Error styling outfits with Gemini: {e}")
        return []
