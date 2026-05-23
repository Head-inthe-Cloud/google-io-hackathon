import os
import replicate
from typing import Dict, Any, Optional

def init_replicate():
    api_token = os.getenv("REPLICATE_API_TOKEN")
    if not api_token:
        return False
    # Set standard environment variable for replicate SDK
    os.environ["REPLICATE_API_TOKEN"] = api_token
    return True

def crop_item_with_sam2(image_url: str) -> Optional[str]:
    """
    Uses Replicate to remove background or isolate clothing items from flat-lays or raw images.
    Using a popular background-removal or segmentation model like 'lucataco/sandbox' or 'cjwbby/rembg'.
    """
    if not init_replicate():
        print("Replicate API key not found. Skipping item segmentation.")
        return image_url # Return original url as fallback
        
    try:
        # Using a highly reliable, fast background-removal model on Replicate
        # We can also use facebookresearch/sam-2 if precise interactive segmentation is preferred,
        # but for automatic flat-lay cropping, rembg/background-removal is the standard industry practice.
        output = replicate.run(
            "cjwbby/rembg:fb8a0045a050dc45beec97302d70cb66e36585bbdb40775d02c1e4db909a9016",
            input={"image": image_url}
        )
        # Returns a URL to the transparency-masked/cropped PNG image
        return output
    except Exception as e:
        print(f"Error during Replicate image cropping: {e}")
        return image_url

def trigger_virtual_tryon(selfie_url: str, garment_url: str) -> Dict[str, Any]:
    """
    Triggers an IDM-VTON (Virtual Try-On) model execution on Replicate.
    IDM-VTON takes a human selfie and a garment flat-lay image and performs high-fidelity try-on.
    """
    if not init_replicate():
        return {
            "status": "mocked",
            "message": "Replicate key not configured. Returning simulated try-on output.",
            "output_url": selfie_url # Mock fallback: returns original selfie
        }
        
    try:
        # IDM-VTON expects 'human_img' (selfie) and 'garm_img' (clothing item)
        # Model identifier: 'yisol/idm-vton'
        # We start the prediction asynchronously so the API remains highly responsive,
        # or run it synchronously if desired. Since virtual try-on takes 10-15s,
        # creating a prediction and returning the replication task ID is recommended.
        
        prediction = replicate.predictions.create(
            version="yisol/idm-vton:bfb99026c4f3f35fe361cf4521798ec4cc90b8f1d5be7fa22409748b0416955d", # popular standard version of IDM-VTON
            input={
                "human_img": selfie_url,
                "garm_img": garment_url,
                "garment_des": "clothing item" # standard description
            }
        )
        
        return {
            "status": "processing",
            "replicate_id": prediction.id,
            "status_url": f"https://api.replicate.com/v1/predictions/{prediction.id}"
        }
    except Exception as e:
        print(f"Error launching virtual try-on: {e}")
        return {
            "status": "error",
            "message": str(e)
        }

def get_prediction_status(prediction_id: str) -> Dict[str, Any]:
    """
    Retrieve the current status of an ongoing Replicate prediction job.
    """
    if not init_replicate():
        return {"status": "succeeded", "output": "http://example.com/mock-output.jpg"}
        
    try:
        prediction = replicate.predictions.get(prediction_id)
        return {
            "id": prediction.id,
            "status": prediction.status, # 'starting', 'processing', 'succeeded', 'failed', 'canceled'
            "output": prediction.output, # contains resulting image URL if succeeded
            "error": prediction.error
        }
    except Exception as e:
        print(f"Error fetching prediction status: {e}")
        return {"status": "failed", "error": str(e)}
