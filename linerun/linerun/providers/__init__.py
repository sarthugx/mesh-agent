from typing import Optional
from linerun.providers.base import LLMProvider
from linerun.providers.mock import MockProvider
from linerun.providers.openai import OpenAIProvider
from linerun.providers.anthropic import AnthropicProvider
from linerun.providers.gemini import GeminiProvider

__all__ = ["LLMProvider", "MockProvider", "OpenAIProvider", "AnthropicProvider", "GeminiProvider", "get_provider"]

def get_provider(name: str, api_key: Optional[str] = None, model: Optional[str] = None) -> LLMProvider:
    """
    Factory function to retrieve a provider instance by name.
    """
    prov_name = name.strip().lower()
    
    if prov_name == "mock":
        return MockProvider(api_key=api_key)
    elif prov_name == "openai":
        # default to gpt-4o-mini if model is not set
        model_name = model or "gpt-4o-mini"
        return OpenAIProvider(api_key=api_key, model=model_name)
    elif prov_name == "anthropic":
        # default to claude-3-5-sonnet if model not set
        model_name = model or "claude-3-5-sonnet-20240620"
        return AnthropicProvider(api_key=api_key, model=model_name)
    elif prov_name == "gemini":
        model_name = model or "gemini-1.5-flash"
        return GeminiProvider(api_key=api_key, model=model_name)
    else:
        raise ValueError(f"Unknown LLM provider: {name}. Supported: mock, openai, anthropic, gemini")
