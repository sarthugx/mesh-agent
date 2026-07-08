from fastapi import APIRouter, Request, Query, Body, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from linerun.workspace import WorkspaceFS

router = APIRouter()

def get_workspace(request: Request) -> WorkspaceFS:
    return WorkspaceFS(request.app.state.workspace_dir)

@router.get("/workspace", response_class=HTMLResponse)
async def get_workspace_page(request: Request):
    """Renders the workspace dashboard visualizer."""
    ws = get_workspace(request)
    try:
        files = ws.list_dir("")
    except Exception as e:
        files = []
        
    templates = request.app.state.templates
    return templates.TemplateResponse(request=request, name="workspace.html", context={
        "active_tab": "workspace",
        "files": files
    })

@router.get("/api/workspace/files")
async def list_files_api(request: Request, path: str = Query("")):
    """JSON API to list files inside the workspace sandbox."""
    ws = get_workspace(request)
    try:
        files = ws.list_dir(path)
        return JSONResponse({"status": "success", "files": files})
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/workspace/file")
async def get_file_content_api(request: Request, path: str = Query(...)):
    """JSON API to read the contents of a text file."""
    ws = get_workspace(request)
    try:
        content = ws.read_text(path)
        return JSONResponse({"status": "success", "content": content})
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/workspace/file")
async def save_file_content_api(
    request: Request,
    path: str = Body(..., embed=True),
    content: str = Body(..., embed=True)
):
    """JSON API to save or create a text file inside the workspace sandbox."""
    ws = get_workspace(request)
    try:
        ws.write_text(path, content)
        return JSONResponse({"status": "success", "message": f"File '{path}' saved successfully."})
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/api/workspace/file")
async def delete_file_api(request: Request, path: str = Query(...)):
    """JSON API to delete a file or folder inside the workspace sandbox."""
    ws = get_workspace(request)
    try:
        ws.delete(path)
        return JSONResponse({"status": "success", "message": f"Path '{path}' deleted successfully."})
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
