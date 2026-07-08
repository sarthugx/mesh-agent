from typing import List, Dict
import httpx
from linerun.providers.base import LLMProvider

class GeminiProvider(LLMProvider):
    """
    Google Gemini API Provider implementing LLMProvider.
    Uses httpx to call generateContent.
    """
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        self.api_key = api_key
        self.model = model

    def send(self, messages: List[Dict[str, str]], system_prompt: str = None) -> str:
        if not self.api_key:
            raise ValueError("Gemini API Key is missing. Please configure it in the Config view.")

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        headers = {
            "Content-Type": "application/json"
        }

        # Convert roles: user -> user, assistant -> model
        contents = []
        for msg in messages:
            role = msg["role"]
            if role == "assistant":
                role = "model"
            elif role not in ("user", "model"):
                role = "user"  # fallback

            contents.append({
                "role": role,
                "parts": [{"text": msg["content"]}]
            })

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": 0.2
            }
        }

        if system_prompt:
            payload["systemInstruction"] = {
                "parts": [{"text": system_prompt}]
            }

        try:
            with httpx.Client(timeout=45.0) as client:
                response = client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                result = response.json()
                
                # Check for errors in response candidates
                candidates = result.get("candidates", [])
                if not candidates:
                    raise RuntimeError(f"Gemini returned empty candidates: {result}")
                
                parts = candidates[0].get("content", {}).get("parts", [])
                if not parts:
                    raise RuntimeError(f"Gemini candidate has no parts content: {result}")
                
                return parts[0].get("text", "")
                
        except httpx.HTTPStatusError as e:
            error_detail = ""
            try:
                error_detail = e.response.json().get("error", {}).get("message", "")
            except Exception:
                error_detail = e.response.text
            raise RuntimeError(f"Gemini API Error ({e.response.status_code}): {error_detail or str(e)}")
        except Exception as e:
            raise RuntimeError(f"Gemini Connection Failed: {str(e)}")
