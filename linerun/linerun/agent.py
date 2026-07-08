import re
import time
from typing import List, Dict, Any, Optional
from linerun.providers.base import LLMProvider
from linerun.workspace import WorkspaceFS

SYSTEM_PROMPT = """You are an autonomous AI coding agent operating inside a secure, sandboxed workspace.
You can read, write, list, and delete files in this workspace to complete the user's tasks.

To interact with files, you must use one of the custom XML tags below. After issuing a tool tag, you MUST stop writing text immediately so the execution environment can run the tool and return the output. Only use ONE tool tag per turn.

AVAILABLE TOOLS:

1. Write File:
<write_file path="relative/path/to/file">
file content here
</write_file>

2. Read File:
<read_file path="relative/path/to/file" />

3. List Files (list files in a folder, or leave path empty for workspace root):
<list_files path="optional/folder" />

4. Delete File:
<delete_file path="relative/path/to/file" />

GUIDELINES:
- All paths are relative to the workspace root. Do not use absolute paths.
- The environment will execute the tool and append a response starting with 'tool_result:'.
- Analyze the output of the tool in the next turn and complete the user's request.
- Once the task is fully achieved, summarize your work and conclude your response without calling any more tools.
"""

# Regex compilation for robust tool-parsing
WRITE_PATTERN = re.compile(r'<write_file\s+path=["\']([^"\']+)["\']\s*>(.*?)</write_file>', re.DOTALL)
READ_PATTERN = re.compile(r'<read_file\s+path=["\']([^"\']+)["\']\s*/?>')
LIST_PATTERN = re.compile(r'<list_files(?:\s+path=["\']([^"\']+)["\'])?\s*/?>')
DELETE_PATTERN = re.compile(r'<delete_file\s+path=["\']([^"\']+)["\']\s*/?>')

class Agent:
    """
    Agent coordinates multi-turn reasoning and tool execution.
    It takes an LLM provider and a sandboxed workspace.
    """
    def __init__(self, provider: LLMProvider, workspace: WorkspaceFS, max_turns: int = 8):
        self.provider = provider
        self.workspace = workspace
        self.max_turns = max_turns

    def parse_tool(self, text: str) -> Optional[Dict[str, Any]]:
        """Parses the first tool tag found in the text response."""
        # Check write file
        match = WRITE_PATTERN.search(text)
        if match:
            return {"tool": "write_file", "path": match.group(1), "content": match.group(2)}

        # Check read file
        match = READ_PATTERN.search(text)
        if match:
            return {"tool": "read_file", "path": match.group(1)}

        # Check list files
        match = LIST_PATTERN.search(text)
        if match:
            return {"tool": "list_files", "path": match.group(1) or ""}

        # Check delete file
        match = DELETE_PATTERN.search(text)
        if match:
            return {"tool": "delete_file", "path": match.group(1)}

        return None

    def run(self, user_msg: str, chat_history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """
        Runs the agent loop.
        
        chat_history: past messages in the conversation, format: [{"role": "user"|"assistant", "content": "..."}]
        Returns:
            {
                "reply": "final response to user",
                "actions": [list of execution actions for terminal logs],
                "messages": [updated conversation history]
            }
        """
        history = list(chat_history) if chat_history else []
        history.append({"role": "user", "content": user_msg})

        actions = []
        turn = 0
        final_reply = ""

        actions.append({
            "timestamp": time.time(),
            "type": "input",
            "summary": "Received user message",
            "details": user_msg
        })

        while turn < self.max_turns:
            turn += 1
            
            # Step 1: Prompt LLM
            actions.append({
                "timestamp": time.time(),
                "type": "llm_call",
                "summary": f"Prompting LLM (Turn {turn}/{self.max_turns})",
                "details": f"Messages count: {len(history)}"
            })

            try:
                response = self.provider.send(history, system_prompt=SYSTEM_PROMPT)
            except Exception as e:
                err_msg = f"LLM error: {str(e)}"
                actions.append({
                    "timestamp": time.time(),
                    "type": "error",
                    "summary": "LLM call failed",
                    "details": err_msg
                })
                final_reply = f"Sorry, I encountered an issue talking to the LLM backend: {str(e)}"
                break

            history.append({"role": "assistant", "content": response})

            # Log thoughts/text output
            actions.append({
                "timestamp": time.time(),
                "type": "thought",
                "summary": f"Agent responded (Turn {turn})",
                "details": response
            })

            # Step 2: Parse Tool Call
            tool_call = self.parse_tool(response)
            if not tool_call:
                # No tool call, Agent has finished reasoning
                final_reply = response
                break

            tool_name = tool_call["tool"]
            tool_path = tool_call["path"]

            actions.append({
                "timestamp": time.time(),
                "type": "tool_call",
                "summary": f"Executing tool: {tool_name} on '{tool_path}'",
                "details": str(tool_call)
            })

            # Step 3: Execute Tool
            tool_result = ""
            try:
                if tool_name == "write_file":
                    content = tool_call["content"]
                    self.workspace.write_text(tool_path, content)
                    tool_result = f"File successfully written to '{tool_path}'"
                
                elif tool_name == "read_file":
                    content = self.workspace.read_text(tool_path)
                    # Limit output length to prevent overloading prompt context
                    if len(content) > 10000:
                        tool_result = content[:10000] + "\n... [TRUNCATED DUE TO SIZE] ..."
                    else:
                        tool_result = content
                
                elif tool_name == "list_files":
                    files = self.workspace.list_dir(tool_path)
                    if not files:
                        tool_result = "Directory is empty."
                    else:
                        lines = []
                        for f in files:
                            kind = "DIR " if f["is_dir"] else "FILE"
                            size = f"{f['size']} B" if not f["is_dir"] else "-"
                            lines.append(f"{kind} - {f['path']} ({size})")
                        tool_result = "\n".join(lines)
                
                elif tool_name == "delete_file":
                    self.workspace.delete(tool_path)
                    tool_result = f"File/folder '{tool_path}' successfully deleted."
                    
            except Exception as e:
                tool_result = f"Error: {str(e)}"
                actions.append({
                    "timestamp": time.time(),
                    "type": "error",
                    "summary": f"Tool execution failed for '{tool_name}'",
                    "details": tool_result
                })

            actions.append({
                "timestamp": time.time(),
                "type": "tool_result",
                "summary": f"Tool '{tool_name}' result received",
                "details": tool_result
            })

            # Append the result of the tool back into the LLM history
            history.append({
                "role": "user",
                "content": f"tool_result: {tool_result}"
            })

        if turn >= self.max_turns and not final_reply:
            final_reply = "I reached my maximum interaction turns without finalizing a reply. Here is my current state."
            actions.append({
                "timestamp": time.time(),
                "type": "error",
                "summary": "Max turns reached",
                "details": "Agent run stopped because max_turns was exceeded."
            })

        return {
            "reply": final_reply,
            "actions": actions,
            "messages": history
        }
