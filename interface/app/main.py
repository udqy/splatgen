import os
from pathlib import Path
from typing import Optional

from fastapi import (
    FastAPI,
    Request,
    Form,
    UploadFile,
    File,
    HTTPException,
    status,
)
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles


# --- FastAPI App Setup ---
app = FastAPI(title="SplatGen Interface")

# --- Static Files Setup ---
static_dir = Path(__file__).parent.parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# --- Templates Setup ---
templates_dir = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=templates_dir)

DATA_DIR = Path("./data")


@app.get("/", response_class=HTMLResponse, name="serve_create_page")
async def serve_create_page(request: Request):
    """Serves the main page with the upload form."""
    return templates.TemplateResponse("create.html", {"request": request})


@app.get("/gallery", response_class=HTMLResponse, name="serve_gallery_page")
async def serve_gallery_page(request: Request):
    """Serves the gallery page (placeholder)."""
    # Pass empty list as no jobs are being tracked here
    return templates.TemplateResponse("gallery.html", {"request": request, "jobs": []})


@app.post("/create_job", status_code=status.HTTP_303_SEE_OTHER, name="create_job")
async def create_job(
    request: Request,
    video_file: UploadFile = File(...),
    splat_name: str = Form(...),
    description: Optional[str] = Form(None),
    num_frames: int = Form(...),
    iterations: int = Form(...),
):
    """
    Handles the form submission.
    Currently only acknowledges data and redirects. NO file saving, DB interaction, or Celery dispatch.
    """

    # --- Basic Validation (Keep) ---
    if not video_file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No filename provided")
    if not video_file.content_type or not video_file.content_type.startswith("video/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid file type, must be video")

    # --- Print Received Data (For verification) ---
    print("--- Received Job Creation Request ---")
    print(f"Filename: {video_file.filename}")
    print(f"Content Type: {video_file.content_type}")
    print(f"Splat Name: {splat_name}")
    print(f"Description: {description}")
    print(f"Num Frames: {num_frames}")
    print(f"Iterations: {iterations}")
    print("------------------------------------")

    try:
        video_file.file.close()
    except Exception as e:
        print(f"Warning: Could not close uploaded file handle: {e}")


    # --- Redirect to Gallery ---
    # Redirect to the gallery page. Since no job is created, the gallery will remain empty.
    # The user gets feedback that the form was submitted.
    # Using url_for requires the endpoint function name ('serve_gallery_page')
    redirect_url = request.url_for('serve_gallery_page')
    print(f"Redirecting to: {redirect_url}")
    return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)