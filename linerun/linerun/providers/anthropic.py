from typing import List, Dict
import httpx
from linerun.providers.base import LLMProvider

class AnthropicProvider(LLMProvider):
    """
    Anthropic API Provider implementing LLMProvider.
    Uses httpx to call /v1/messages.
    """
    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20240620"):
        self.api_key = api_key
        self.model = model
        self.url = "https://api.anthropic.com/v1/messages"

    def send(self, messages: List[Dict[str, str]], system_prompt: str = None) -> str:
        if not self.api_key:
            raise ValueError("Anthropic API Key is missing. Please configure it in the Config view.")

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }

        # Filter messages. Anthropic requires alternating user/assistant messages.
        # System messages must be passed as the 'system' field.
        formatted_messages = []
        for msg in messages:
            role = msg["role"]
            if role not in ("user", "assistant"):
                role = "user"  # fallback
            formatted_messages.append({
                "role": role,
                "content": msg["content"]
            })

        payload = {
            "model": self.model,
            "messages": formatted_messages,
            "max_tokens": 4000,
            "temperature": 0.2
        }

        if system_prompt:
            payload["system"] = system_prompt

        try:
            with httpx.Client(timeout=45.0) as client:
                response = client.post(self.url, headers=headers, json=payload)
                response.raise_for_status()
                result = response.json()
                return result["content"][0]["text"]
        except httpx.HTTPStatusError as e:
            error_detail = ""
            try:
                error_detail = e.response.json().get("error", {}).get("message", "")
            except Exception:
                error_detail = e.response.text
            raise RuntimeError(f"Anthropic API Error ({e.response.status_code}): {error_detail or str(e)}")
        except Exception as e:
            raise RuntimeError(f"Anthropic Connection Failed: {str(e)}")
