from abc import ABC, abstractmethod
from typing import List, Dict

class LLMProvider(ABC):
    """
    Abstract Base Class for LLM providers.
    """
    @abstractmethod
    def send(self, messages: List[Dict[str, str]], system_prompt: str = None) -> str:
        """
        Sends a list of messages to the provider and returns the raw response text.
        
        messages: List of dicts, e.g. [{"role": "user", "content": "hello"}]
        system_prompt: Optional instructions passed to the system role.
        """
        pass
