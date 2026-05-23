import json
import mimetypes
import os
import urllib.request


class LLMConfigurationError(RuntimeError):
    pass


def _load_google_genai():
    try:
        from google import genai
        from google.genai import types
    except Exception as exc:
        raise LLMConfigurationError(
            "google-genai is not installed. Install it or pass precompiled LLM outputs."
        ) from exc
    return genai, types


def _read_image_bytes(image):
    if image.get("bytes"):
        return image["bytes"]
    if image.get("path"):
        with open(image["path"], "rb") as file:
            return file.read()
    if image.get("url"):
        request = urllib.request.Request(
            image["url"],
            headers={"User-Agent": "Mozilla/5.0"},
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.read()
    return None


def _image_mime_type(image):
    mime_type = image.get("mime_type")
    if mime_type:
        return mime_type
    path = image.get("path") or image.get("url") or ""
    guessed, _ = mimetypes.guess_type(path)
    return guessed or "image/jpeg"


class GeminiJSONClient:
    def __init__(self, model="gemini-3.5-flash", api_key=None):
        genai, types = _load_google_genai()
        api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise LLMConfigurationError("GEMINI_API_KEY is required for LLM recommendation calls.")
        self._types = types
        self._client = genai.Client(api_key=api_key)
        self.model = model

    def generate_json(self, system_instruction, user_payload, images=None):
        parts = []
        for image in images or []:
            image_bytes = _read_image_bytes(image)
            if image_bytes:
                parts.append(
                    self._types.Part.from_bytes(
                        data=image_bytes,
                        mime_type=_image_mime_type(image),
                    )
                )

        parts.append(
            "\n\n".join(
                [
                    system_instruction.strip(),
                    "User payload JSON:",
                    json.dumps(user_payload, ensure_ascii=False, indent=2),
                    "Return only valid JSON. Do not include markdown.",
                ]
            )
        )

        response = self._client.models.generate_content(
            model=self.model,
            contents=parts,
            config=self._types.GenerateContentConfig(response_mime_type="application/json"),
        )
        return json.loads(response.text.strip())
