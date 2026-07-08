import os
from pathlib import Path
import json
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Setup directory paths
BASE_DIR = Path(__file__).resolve().parent.parent
WORKSPACE_DIR = BASE_DIR / "workspace"
CONFIG_DIR = BASE_DIR / "config"

# Ensure directories exist
WORKSPACE_DIR.mkdir(exist_ok=True)
CONFIG_DIR.mkdir(exist_ok=True)

# Path to config file
CONFIG_FILE = CONFIG_DIR / "config.json"

# Default config if not present
if not CONFIG_FILE.exists():
    CONFIG_FILE.write_text(json.dumps({
        "provider": "mock",
        "openai_key": "",
        "openai_model": "gpt-4o-mini",
        "anthropic_key": "",
        "anthropic_model": "claude-3-5-sonnet-20240620",
        "gemini_key": "",
        "gemini_model": "gemini-2.5-flash"
    }, indent=4))

# Setup FastAPI App
app = FastAPI(title="Mesh-Agent Panel", description="Sleek interface to interact with your local sandbox AI agent")

# Mount Static Files
static_dir = BASE_DIR / "app" / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Templates
templates_dir = BASE_DIR / "app" / "templates"
templates_dir.mkdir(parents=True, exist_ok=True)
templates = Jinja2Templates(directory=str(templates_dir))

# Expose templates to routes via app state
app.state.templates = templates
app.state.workspace_dir = WORKSPACE_DIR
app.state.config_file = CONFIG_FILE

# Import and include routers (we will define them in subsequent steps)
from app.routes.chat import router as chat_router
from app.routes.workspace import router as workspace_router
from app.routes.config import router as config_router

app.include_router(chat_router)
app.include_router(workspace_router)
app.include_router(config_router)

@app.get("/")
async def root():
    """Redirect home to the chat page."""
    return RedirectResponse(url="/chat")

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    # Enable template routes to know the active path for navbar styling
    request.state.path = request.url.path
    response = await call_next(request)
    return response
