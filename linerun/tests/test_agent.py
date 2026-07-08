import tempfile
from linerun.workspace import WorkspaceFS
from linerun.providers import MockProvider
from linerun.agent import Agent

def test_tool_parsing():
    agent = Agent(MockProvider(), WorkspaceFS(tempfile.gettempdir()))
    
    # Test write tool parsing
    text_write = "Here is the plan:\n<write_file path=\"src/main.py\">\nprint('hello')\n</write_file>\nLet me know."
    tool = agent.parse_tool(text_write)
    assert tool is not None
    assert tool["tool"] == "write_file"
    assert tool["path"] == "src/main.py"
    assert "print('hello')" in tool["content"]
    
    # Test read tool parsing
    text_read = "I'll check it:\n<read_file path=\"src/main.py\" />"
    tool = agent.parse_tool(text_read)
    assert tool is not None
    assert tool["tool"] == "read_file"
    assert tool["path"] == "src/main.py"
    
    # Test list files parsing
    text_list = "<list_files path=\"subdir\" />"
    tool = agent.parse_tool(text_list)
    assert tool is not None
    assert tool["tool"] == "list_files"
    assert tool["path"] == "subdir"
    
    # Test delete file parsing
    text_delete = "<delete_file path=\"temp.log\" />"
    tool = agent.parse_tool(text_delete)
    assert tool is not None
    assert tool["tool"] == "delete_file"
    assert tool["path"] == "temp.log"

def test_agent_multi_turn_run():
    with tempfile.TemporaryDirectory() as tmpdir:
        ws = WorkspaceFS(tmpdir)
        # We will inject pre-set responses to simulate a multi-turn tool interaction.
        # Turn 1: Assistant calls write_file
        # Turn 2: Assistant completes task
        responses = [
            "I will write the file.\n<write_file path=\"test_run.txt\">Agent Output</write_file>",
            "All done!"
        ]
        provider = MockProvider(responses=responses)
        agent = Agent(provider, ws)
        
        res = agent.run("Please write a test file.")
        
        # Verify result contains the final reply
        assert res["reply"] == "All done!"
        
        # Verify the file was actually written to the sandbox
        assert ws.exists("test_run.txt")
        assert ws.read_text("test_run.txt") == "Agent Output"
        
        # Verify actions log contains the steps
        actions = res["actions"]
        assert len(actions) > 0
        action_types = [a["type"] for a in actions]
        assert "input" in action_types
        assert "llm_call" in action_types
        assert "thought" in action_types
        assert "tool_call" in action_types
        assert "tool_result" in action_types
