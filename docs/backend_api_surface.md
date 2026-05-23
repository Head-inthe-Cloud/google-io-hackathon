# ClosetAI Backend API Surface

This document outlines the core FastAPI endpoints acting as the orchestration middleware between the Next.js frontend, Amazon S3, Google AI Studio (Gemini), Replicate (SAM-2 / VTON), and our PostgreSQL database.

## Base URL
Local development: `http://localhost:8000`

---

## 1. Storage & Uploads

### `GET /api/upload-url`
Generates a secure, pre-signed AWS S3 URL. The Next.js frontend should use this to directly upload large image files (selfies, closet flat-lays) without passing them through the FastAPI server.

*   **Query Parameters:**
    *   `filename` (string, required): The intended name of the file to be uploaded (e.g., `user_123_selfie.jpg`).
*   **Response:**
    ```json
    {
      "upload_url": "https://your-bucket.s3.amazonaws.com/user_123_selfie.jpg?AWSAccessKeyId=...&Signature=...",
      "file_url": "https://your-bucket.s3.amazonaws.com/user_123_selfie.jpg"
    }
    ```
*   **Frontend Action:** Execute an HTTP `PUT` request to `upload_url` with the binary file data. Once successful, save the `file_url` to pass to subsequent endpoints.

---

## 2. Onboarding & Processing

### `POST /api/process-item`
Triggered by the frontend after a successful S3 upload of a closet image. This endpoint coordinates the AI extraction and database insertion.

*   **Request Body:**
    ```json
    {
      "user_id": "string",
      "file_url": "string (S3 Object URL)"
    }
    ```
*   **Backend Workflow:**
    1.  **Extraction:** (Optional) Call Replicate SAM-2 to crop individual items from flat-lays.
    2.  **Analysis:** Send the cropped `file_url` to Gemini 1.5. Gemini returns a structured JSON schema detailing color, category, season, etc.
    3.  **Embedding:** Generate a style vector for the image using Gemini's embedding API.
    4.  **Database:** Insert a new row into the Postgres `closet_items` table containing the `s3_image_url`, metadata, and the `style_vector` (using pgvector).
*   **Response:**
    ```json
    {
      "status": "success",
      "item_id": 1024,
      "extracted_data": {
        "category": "top",
        "color": "navy blue"
      }
    }
    ```

---

## 3. Outfit Generation & Try-On

### `POST /api/generate-outfit`
Takes a user's styling prompt, queries their existing wardrobe using pgvector, and generates coherent outfits.

*   **Request Body:**
    ```json
    {
      "user_id": "string",
      "prompt": "brunch with friends, 70°F, want to look put-together",
      "weather_context": "70°F, Sunny"
    }
    ```
*   **Backend Workflow:**
    1.  Embed the text prompt.
    2.  Perform a vector search via Postgres/pgvector against `closet_items` to find the most relevant items for the user.
    3.  Pass the retrieved items to Gemini (with system instructions to act as a stylist) to compose 3-5 structured outfit combinations.
*   **Response:**
    ```json
    {
      "outfits": [
        {
          "outfit_id": "outfit_1",
          "description": "A casual but elevated look.",
          "items": [
            {"item_id": 101, "category": "top", "s3_image_url": "..."},
            {"item_id": 204, "category": "bottom", "s3_image_url": "..."}
          ]
        }
      ]
    }
    ```

### `POST /api/virtual-try-on`
Initiates a serverless GPU job to composite a selected clothing item onto the user's selfie.

*   **Request Body:**
    ```json
    {
      "user_id": "string",
      "selfie_url": "string (S3 Object URL)",
      "garment_url": "string (S3 Object URL)"
    }
    ```
*   **Backend Workflow:**
    1. Send `selfie_url` and `garment_url` to IDM-VTON on Replicate.
    2. Return the task ID or the final rendered image URL.
*   **Response:**
    ```json
    {
      "status": "processing",
      "replicate_id": "req_xyz123"
    }
    ```
