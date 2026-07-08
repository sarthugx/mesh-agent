import json
from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from linerun.providers import get_provider

router = APIRouter()

def load_config(config_file_path) -> dict:
    try:
        with open(config_file_path, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def save_config(config_file_path, config_data: dict):
    with open(config_file_path, "w") as f:
        json.dump(config_data, f, indent=4)

@router.get("/config", response_class=HTMLResponse)
async def get_config_page(request: Request):
    config_path = request.app.state.config_file
    config = load_config(config_path)
    
    # Sanitize keys so we don't display them in full in the HTML form
    masked_openai = "••••••••••••••••" if config.get("openai_key") else ""
    masked_anthropic = "••••••••••••••••" if config.get("anthropic_key") else ""
    masked_gemini = "••••••••••••••••" if config.get("gemini_key") else ""
    
    context = {
        "request": request,
        "active_tab": "config",
        "provider": config.get("provider", "mock"),
        "openai_key": masked_openai,
        "openai_model": config.get("openai_model", "gpt-4o-mini"),
        "anthropic_key": masked_anthropic,
        "anthropic_model": config.get("anthropic_model", "claude-3-5-sonnet-20240620"),
        "gemini_key": masked_gemini,
        "gemini_model": config.get("gemini_model", "gemini-2.5-flash"),
        "message": None,
        "error": None
    }
    
    templates = request.app.state.templates
    return templates.TemplateResponse(request=request, name="config.html", context=context)

@router.post("/config", response_class=HTMLResponse)
async def save_config_form(
    request: Request,
    provider: str = Form(...),
    openai_key: str = Form(""),
    openai_model: str = Form("gpt-4o-mini"),
    anthropic_key: str = Form(""),
    anthropic_model: str = Form("claude-3-5-sonnet-20240620"),
    gemini_key: str = Form(""),
    gemini_model: str = Form("gemini-2.5-flash")
):
    config_path = request.app.state.config_file
    current_config = load_config(config_path)
    
    # Only update API keys if they are not the masked placeholder
    new_openai_key = openai_key
    if openai_key == "••••••••••••••••":
        new_openai_key = current_config.get("openai_key", "")
        
    new_anthropic_key = anthropic_key
    if anthropic_key == "••••••••••••••••":
        new_anthropic_key = current_config.get("anthropic_key", "")
        
    new_gemini_key = gemini_key
    if gemini_key == "••••••••••••••••":
        new_gemini_key = current_config.get("gemini_key", "")
        
    updated_config = {
        "provider": provider,
        "openai_key": new_openai_key,
        "openai_model": openai_model,
        "anthropic_key": new_anthropic_key,
        "anthropic_model": anthropic_model,
        "gemini_key": new_gemini_key,
        "gemini_model": gemini_model
    }
    
    save_config(config_path, updated_config)
    
    masked_openai = "••••••••••••••••" if new_openai_key else ""
    masked_anthropic = "••••••••••••••••" if new_anthropic_key else ""
    masked_gemini = "••••••••••••••••" if new_gemini_key else ""
    
    context = {
        "request": request,
        "active_tab": "config",
        "provider": provider,
        "openai_key": masked_openai,
        "openai_model": openai_model,
        "anthropic_key": masked_anthropic,
        "anthropic_model": anthropic_model,
        "gemini_key": masked_gemini,
        "gemini_model": gemini_model,
        "message": "Configuration saved successfully!",
        "error": None
    }
    
    templates = request.app.state.templates
    return templates.TemplateResponse(request=request, name="config.html", context=context)

@router.post("/api/config/test")
async def test_llm_connection(request: Request):
    """Test connecting to the selected provider using current configuration."""
    config_path = request.app.state.config_file
    config = load_config(config_path)
    
    provider_name = config.get("provider", "mock")
    
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
        
        # Simple test prompt
        test_messages = [{"role": "user", "content": "Hello! Reply with exactly 'Success'"}]
        response = provider.send(test_messages)
        
        return JSONResponse({
            "status": "success",
            "message": f"Successfully connected! LLM response: '{response}'"
        })
    except Exception as e:
        return JSONResponse({
            "status": "error",
            "message": f"Connection failed: {str(e)}"
        }, status_code=400)
