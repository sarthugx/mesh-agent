from typing import List, Dict
from linerun.providers.base import LLMProvider

class MockProvider(LLMProvider):
    """
    Mock LLM provider for testing and API-keyless runs.
    Simulates agent tool-calls based on inputs.
    """
    def __init__(self, api_key: str = None, responses: List[str] = None):
        self.api_key = api_key
        self.responses = responses or []
        self.call_count = 0

    def send(self, messages: List[Dict[str, str]], system_prompt: str = None) -> str:
        self.call_count += 1
        
        # If specific test responses were injected, return them in order
        if self.responses:
            idx = min(self.call_count - 1, len(self.responses) - 1)
            return self.responses[idx]

        # Analyze the conversation history to simulate an agent loop
        last_msg = messages[-1]["content"] if messages else ""

        # Check if the last assistant message returned a tool result and we are in the next turn
        tool_results_present = False
        for msg in reversed(messages):
            if msg["role"] == "user" and "tool_result:" in msg["content"]:
                tool_results_present = True
                break

        # Simulate dynamic tool calls depending on keywords in user prompt
        if tool_results_present:
            return "I have completed the requested operation. Is there anything else you need me to do?"

        # Trigger tool requests based on words in prompt
        msg_lower = last_msg.lower()
        if "write" in msg_lower and "hello.txt" in msg_lower:
            return "Let me create that file for you.\n<write_file path=\"hello.txt\">Hello world from Mock Agent!</write_file>\nI will wait for the result."
        
        if "read" in msg_lower and "hello.txt" in msg_lower:
            return "I'll read that file now.\n<read_file path=\"hello.txt\" />\nReading file..."

        if "list" in msg_lower or "files" in msg_lower or "directory" in msg_lower:
            return "Checking workspace folder structure:\n<list_files />"

        if "delete" in msg_lower and "hello.txt" in msg_lower:
            return "Deleting hello.txt:\n<delete_file path=\"hello.txt\" />"

        # Default standard reply
        return f"Hello! I am the Mesh-Agent (running Mock Provider). You said: '{last_msg}'. You can ask me to: 'write hello.txt', 'read hello.txt', 'list files', or 'delete hello.txt' to test my tools."
