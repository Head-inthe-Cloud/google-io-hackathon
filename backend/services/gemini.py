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

def fetch_image_bytes(image_url: str) -> bytes:
    # ... (remains the same)
    if "mock" in image_url or image_url.startswith("http://localhost"):
        # Return a small mock 1x1 transparent GIF/JPEG or placeholder
        return b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b'
    
    try:
        req = urllib.request.Request(
            image_url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req) as response:
            return response.read()
    except Exception as e:
        print(f"Error fetching image from URL {image_url}: {e}")
        raise ValueError(f"Could not retrieve image from url: {image_url}")

def analyze_clothing_item(image_url: str) -> Dict[str, Any]:
    """
    Sends an image of a wardrobe item to Gemini 1.5 to analyze and output structured metadata.
    """
    if not init_gemini():
        # Fallback for testing without real API keys
        return {
            "category": "top",
            "sub_category": "t-shirt",
            "color": "navy blue",
            "season": "all-season",
            "style_tags": ["casual", "minimalist", "cotton"]
        }
        
    try:
        image_data = fetch_image_bytes(image_url)
        
        # Prepare content for Gemini
        image_part = types.Part.from_bytes(
            data=image_data,
            mime_type="image/jpeg"
        )
        
        prompt = (
            "Analyze this wardrobe item. Extract the following metadata in a flat JSON structure with "
            "lowercase values:\n"
            "1. 'category' (e.g., top, bottom, outerwear, footwear, accessory)\n"
            "2. 'sub_category' (e.g., t-shirt, button-up, jeans, sneakers, dress, blazer)\n"
            "3. 'color' (dominant color)\n"
            "4. 'season' (spring, summer, fall, winter, all-season)\n"
            "5. 'style_tags' (array of strings, e.g., ['casual', 'formal', 'grunge', 'streetwear', 'vintage'])\n"
            "\n"
            "Return only the raw JSON, with no markdown codeblocks."
        )
        
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=[image_part, prompt],
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        
        # Parse output
        data = json.loads(response.text.strip())
        return data
        
    except Exception as e:
        print(f"Error in Gemini image analysis: {e}")
        # Return fallback on error to ensure API doesn't crash
        return {
            "category": "unknown",
            "sub_category": "unknown",
            "color": "unknown",
            "season": "all-season",
            "style_tags": []
        }

def get_style_embedding(text_content: str) -> List[float]:
    """
    Generate standard vector embedding (768 dimensions) for a styling tag or search prompt.
    """
    if not init_gemini():
        # Return a zero vector of 768 dimensions for testing without API Key
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

def design_outfits_with_gemini(prompt: str, weather: str, closet_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Uses Gemini as a professional personal stylist to compose 3-5 elegant, cohesive outfit combinations
    from the retrieved subset of closet items.
    """
    if not init_gemini() or not closet_items:
        # Fallback
        return [
            {
                "outfit_id": "outfit_1",
                "description": f"A default stylist option for: {prompt}",
                "items": closet_items[:3] if closet_items else []
            }
        ]
        
    try:
        # Stringify list of available closet items for the model
        items_description = []
        for item in closet_items:
            items_description.append({
                "id": item["id"],
                "category": item["category"],
                "sub_category": item["sub_category"],
                "color": item["color"],
                "season": item["season"],
                "style_tags": item["style_tags"]
            })
            
        system_instruction = (
            "You are an elite fashion designer and personal stylist. Your goal is to compose cohesive outfits "
            "strictly using the user's available closet items listed in the prompt.\n"
            "Generate 1 to 3 distinct outfits tailored to their style prompt and weather context.\n"
            "Return a JSON response containing an array of 'outfits'. Each outfit must have:\n"
            "- 'outfit_id': Unique identifier (e.g., 'outfit_1')\n"
            "- 'description': Stylist's reasoning and guide for why these items go together, matching the vibe of the prompt.\n"
            "- 'items': Array of items chosen, where each item contains only the 'item_id' (integer) matching the original item ID.\n"
            "Make sure the outfits are practical (e.g., including at least a top and a bottom, or a one-piece dress, matching shoes if present)."
        )
        
        user_prompt = f"Styling Prompt: {prompt}\nWeather Context: {weather}\n\nAvailable Closet Items:\n{json.dumps(items_description)}"
        
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=f"{system_instruction}\n\n{user_prompt}",
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        
        data = json.loads(response.text.strip())
        
        # Map item details (like S3 URLs) back into the output outfits for user-friendly display on frontend
        items_by_id = {item["id"]: item for item in closet_items}
        
        structured_outfits = []
        for outfit in data.get("outfits", []):
            mapped_items = []
            for item in outfit.get("items", []):
                # Handle cases where gemini returns integer ids or dicts with item_id
                item_id = item if isinstance(item, int) else item.get("item_id")
                if item_id in items_by_id:
                    original_item = items_by_id[item_id]
                    mapped_items.append({
                        "item_id": original_item["id"],
                        "category": original_item["category"],
                        "sub_category": original_item["sub_category"],
                        "color": original_item["color"],
                        "s3_image_url": original_item["s3_image_url"]
                    })
            if mapped_items:
                structured_outfits.append({
                    "outfit_id": outfit.get("outfit_id", "outfit"),
                    "description": outfit.get("description", "A perfectly styled outfit."),
                    "items": mapped_items
                })
                
        return structured_outfits
        
    except Exception as e:
        print(f"Error styling outfits with Gemini: {e}")
        return []
