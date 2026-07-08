import json
from fastapi import APIRouter, Request, Body, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from linerun.workspace import WorkspaceFS
from linerun.providers import get_provider
from linerun.agent import Agent

router = APIRouter()

def load_config(config_file_path) -> dict:
    try:
        with open(config_file_path, "r") as f:
            return json.load(f)
    except Exception:
        return {}

# Store terminal logs in app state. We populate this in app.main.
# Let's ensure a list is initialized if not present.
def get_terminal_logs(request: Request) -> list:
    if not hasattr(request.app.state, "terminal_logs"):
        request.app.state.terminal_logs = []
    return request.app.state.terminal_logs

@router.get("/chat", response_class=HTMLResponse)
async def get_chat_page(request: Request):
    """Renders the chat interface view."""
    templates = request.app.state.templates
    return templates.TemplateResponse(request=request, name="chat.html", context={
        "active_tab": "chat"
    })

@router.get("/terminal", response_class=HTMLResponse)
async def get_terminal_page(request: Request):
    """Renders the read-only terminal emulator view."""
    templates = request.app.state.templates
    return templates.TemplateResponse(request=request, name="terminal.html", context={
        "active_tab": "terminal"
    })

@router.post("/api/chat")
async def chat_api(
    request: Request,
    message: str = Body(..., embed=True),
    history: list = Body([], embed=True)
):
    """
    Main communication endpoint. Runs the Agent and executes file actions.
    Appends execution steps to the server terminal_logs.
    """
    config_path = request.app.state.config_file
    config = load_config(config_path)
    
    provider_name = config.get("provider", "mock")
    
    # Instantiate active provider
    try:
        if provider_name == "openai":
            key = config.get("openai_key")
            model = config.get("openai_model")
        elif provider_name == "anthropic":
            key = config.get("anthropic_key")
            model = config.get("anthropic_model")
        elif provider_name == "gemini":
            key = config.get("gemini_key")
            model = config.get("gemini_model")
        else:
            key = None
            model = None
            
        provider = get_provider(provider_name, api_key=key, model=model)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to load active LLM Provider '{provider_name}': {str(e)}")

    # Instantiate workspace filesystem and agent
    try:
        workspace = WorkspaceFS(request.app.state.workspace_dir)
        agent = Agent(provider, workspace)
        
        # Execute agent loop
        result = agent.run(message, chat_history=history)
        
        # Store actions in the server-side terminal log
        logs = get_terminal_logs(request)
        for act in result["actions"]:
            logs.append(act)
            
        # Limit server-side log memory to 1000 items
        if len(logs) > 1000:
            request.app.state.terminal_logs = logs[-1000:]
            
        return JSONResponse({
            "status": "success",
            "reply": result["reply"],
            "actions": result["actions"],
            "messages": result["messages"]
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent loop failure: {str(e)}")

@router.get("/api/terminal/logs")
async def get_logs_api(request: Request):
    """Returns all cached terminal/execution logs."""
    logs = get_terminal_logs(request)
    return JSONResponse({"status": "success", "logs": logs})

@router.post("/api/terminal/clear")
async def clear_logs_api(request: Request):
    """Clears all cached terminal/execution logs."""
    request.app.state.terminal_logs = []
    return JSONResponse({"status": "success", "message": "Terminal logs cleared."})
