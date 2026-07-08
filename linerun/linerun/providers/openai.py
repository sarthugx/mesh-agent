from typing import List, Dict
import httpx
from linerun.providers.base import LLMProvider

class OpenAIProvider(LLMProvider):
    """
    OpenAI API Provider implementing LLMProvider.
    Uses httpx to perform raw API calls, avoiding library version pinning conflicts.
    """
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.model = model
        self.url = "https://api.openai.com/v1/chat/completions"

    def send(self, messages: List[Dict[str, str]], system_prompt: str = None) -> str:
        if not self.api_key:
            raise ValueError("OpenAI API Key is missing. Please configure it in the Config view.")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # Structure messages array
        formatted_messages = []
        if system_prompt:
            formatted_messages.append({"role": "system", "content": system_prompt})
        
        for msg in messages:
            formatted_messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })

        payload = {
            "model": self.model,
            "messages": formatted_messages,
            "temperature": 0.2
        }

        try:
            with httpx.Client(timeout=45.0) as client:
                response = client.post(self.url, headers=headers, json=payload)
                response.raise_for_status()
                result = response.json()
                return result["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as e:
            error_detail = ""
            try:
                error_detail = e.response.json().get("error", {}).get("message", "")
            except Exception:
                error_detail = e.response.text
            raise RuntimeError(f"OpenAI API Error ({e.response.status_code}): {error_detail or str(e)}")
        except Exception as e:
            raise RuntimeError(f"OpenAI Connection Failed: {str(e)}")
