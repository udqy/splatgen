# interface/app/main.py
import os
from pathlib import Path
from typing import Optional, List
import logging
from contextlib import asynccontextmanager
import aiofiles
import shutil

from fastapi import (
    FastAPI,
    Request,
    Form,
    UploadFile,
    File,
    HTTPException,
    status,
    Depends,
)
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from celery import chain # Import chain

# Import local modules
from .database import get_async_session, engine
from .models import Base, Job, JobStatus
import nanoid

# Import task signatures from the worker modules
# This relies on the worker code potentially being accessible in the interface's environment
# during development (e.g., via mounted volumes and PYTHONPATH adjustments) or installed as a package.
try:
    from worker.tasks.preprocess import extract_frames_task, remove_background_task
    from worker.tasks.colmap import (
        feature_extraction_task,
        feature_matching_task,
        sparse_mapping_task,
        image_undistortion_task
    )
    from worker.tasks.splatting import train_splatting_task
    from worker.tasks.convert import convert_ply_to_splat_task
    CAN_IMPORT_TASKS = True
except ImportError as import_err:
     logging.warning(f"Could not import worker tasks, Celery dispatch will be disabled: {import_err}")
     CAN_IMPORT_TASKS = False


# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)

# --- Lifespan Management ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("FastAPI application starting up...")
    try:
        # Test connection on startup
        async with engine.connect() as connection:
            log.info("Database connection successful on startup.")
    except Exception as e:
        log.critical(f"Database connection failed on startup: {e}")
        # Consider if the app should exit or continue without DB
    yield
    log.info("FastAPI application shutting down...")
    await engine.dispose()
    log.info("Database engine disposed.")


# --- FastAPI App Setup ---
app = FastAPI(title="SplatGen Interface", lifespan=lifespan)

# --- Static Files Setup ---
static_dir = Path(__file__).parent.parent / "static"
if not static_dir.exists():
     log.warning(f"Static directory not found at {static_dir}, creating.")
     static_dir.mkdir(parents=True, exist_ok=True) # Create if doesn't exist
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# --- Templates Setup ---
templates_dir = Path(__file__).parent.parent / "templates"
if not templates_dir.exists():
     log.error(f"Templates directory not found at {templates_dir}. UI will not work.")
     # Handle error appropriately - maybe raise exception or create dummy dir?
templates = Jinja2Templates(directory=templates_dir)

# --- Constants ---
APP_ROOT = Path(__file__).parent.parent.parent # Should be /app in container
DATA_DIR = APP_ROOT / "data" # /app/data in container

# Ensure data directory exists on startup (within the container)
DATA_DIR.mkdir(parents=True, exist_ok=True)
log.info(f"Data directory ensured at: {DATA_DIR}")

# --- Helper Functions ---
def get_file_extension(filename: str) -> Optional[str]:
    """Safely get the lowercase file extension."""
    try:
        ext = Path(filename).suffix.lower()
        return ext if ext else None # Return None if no extension
    except Exception:
        return None

# --- Routes ---

@app.get("/", response_class=HTMLResponse, name="serve_create_page")
async def serve_create_page(request: Request):
    """Serves the main page with the upload form."""
    return templates.TemplateResponse("create.html", {"request": request})


@app.get("/gallery", response_class=HTMLResponse, name="serve_gallery_page")
async def serve_gallery_page(
    request: Request,
    session: AsyncSession = Depends(get_async_session)
):
    """Serves the gallery page, fetching jobs from the database."""
    job_list: List[Job] = []
    error_message: Optional[str] = None
    try:
        stmt = select(Job).order_by(Job.created_at.desc())
        result = await session.execute(stmt)
        job_list = result.scalars().all()
        log.info(f"Fetched {len(job_list)} jobs for gallery.")
    except Exception as e:
        log.error(f"Error fetching jobs from database: {e}", exc_info=True)
        error_message = "Could not fetch job list from database."

    return templates.TemplateResponse(
        "gallery.html",
        {"request": request, "jobs": job_list, "error_message": error_message}
    )


@app.post("/create_job", status_code=status.HTTP_303_SEE_OTHER, name="create_job")
async def create_job(
    request: Request,
    video_file: UploadFile = File(...),
    splat_name: str = Form(...),
    description: Optional[str] = Form(None),
    num_frames: int = Form(...),
    iterations: int = Form(...),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Handles the form submission: Validates, saves file, creates DB record,
    dispatches Celery chain, updates DB with task ID, and redirects.
    """
    log.info("--- Received Job Creation Request ---")

    # --- 1. Validation ---
    if not video_file.filename:
        log.error("Validation failed: No filename provided.")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No filename provided")

    original_filename = video_file.filename
    file_extension = get_file_extension(original_filename)
    if not file_extension:
         log.error(f"Validation failed: Could not determine file extension for {original_filename}.")
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not determine file extension")

    if not video_file.content_type or not video_file.content_type.startswith("video/"):
        log.error(f"Validation failed: Invalid content type '{video_file.content_type}' for {original_filename}.")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid file type '{video_file.content_type}', must be video")

    # --- 2. Generate Job ID and Paths ---
    job_id = nanoid.generate('abcdefghijklmnopqrstuvwxyz', size=12) # Use specified alphabet
    log.info(f"Generated Job ID: {job_id}")
    target_filename = f"input{file_extension}"
    job_dir = DATA_DIR / job_id
    input_dir = job_dir / "input"
    output_dir = job_dir / "output"
    full_input_video_path = input_dir / target_filename
    relative_input_video_path = Path(job_id) / "input" / target_filename
    log.info(f"Original Filename: {original_filename}, Target Filename: {target_filename}")
    log.info(f"Splat Name: {splat_name}, Job Directory: {job_dir}")

    # --- 3. Create Directories ---
    try:
        input_dir.mkdir(parents=True, exist_ok=True)
        output_dir.mkdir(parents=True, exist_ok=True)
        log.info(f"Created directories: {input_dir}, {output_dir}")
    except OSError as e:
        log.error(f"Failed to create directories for job {job_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not create job directories.")

    # --- 4. Save Uploaded File Asynchronously ---
    try:
        async with aiofiles.open(full_input_video_path, 'wb') as out_file:
            while content := await video_file.read(1024 * 1024): # Read in 1MB chunks
                await out_file.write(content)
        log.info(f"Successfully saved uploaded video to {full_input_video_path}")
    except Exception as e:
        log.error(f"Failed to save uploaded file for job {job_id}: {e}", exc_info=True)
        shutil.rmtree(job_dir, ignore_errors=True) # Attempt cleanup
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not save uploaded video file.")
    finally:
        await video_file.close()
        log.debug(f"Closed upload file handle for {original_filename}")

    # --- 5. Create Job Record in Database ---
    db_job: Optional[Job] = None
    try:
        async with session.begin(): # Use transaction block
            new_job = Job(
                jobid=job_id,
                name=splat_name,
                description=description,
                status=JobStatus.QUEUED,
                input_filename=original_filename,
                input_video_path=str(relative_input_video_path),
            )
            session.add(new_job)
            # Flush to get object state before commit (within transaction)
            await session.flush()
            await session.refresh(new_job) # Ensure all attributes (like defaults) are loaded
            db_job = new_job
        log.info(f"Successfully created database record for job {job_id}")
    except Exception as e:
        log.error(f"Failed to create database record for job {job_id}: {e}", exc_info=True)
        shutil.rmtree(job_dir, ignore_errors=True) # Attempt cleanup
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not create job record in database.")

    if not db_job:
        log.critical(f"Job object is None after successful DB transaction for job {job_id}. This should not happen.")
        shutil.rmtree(job_dir, ignore_errors=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve job details after creation.")

    # --- 6. Define and Dispatch Celery Chain ---
    celery_task_id: Optional[str] = None
    if CAN_IMPORT_TASKS:
        try:
            # Define the granular pipeline chain
            pipeline = chain(
                extract_frames_task.s(job_id).set(queue='cpu_queue') |
                remove_background_task.s(job_id).set(queue='cpu_queue') | # Route as needed
                feature_extraction_task.s(job_id).set(queue='cpu_queue') |
                feature_matching_task.s(job_id).set(queue='cpu_queue') |
                sparse_mapping_task.s(job_id).set(queue='cpu_queue') | # Check if needs GPU later
                image_undistortion_task.s(job_id).set(queue='cpu_queue') |
                train_splatting_task.s(job_id).set(queue='gpu_queue') |  # Route to GPU
                convert_ply_to_splat_task.s(job_id).set(queue='cpu_queue')
            )

            task_result = pipeline.apply_async()
            celery_task_id = task_result.id
            log.info(f"Dispatched Celery chain for job {job_id}. Task ID: {celery_task_id}")

        except Exception as e:
            log.error(f"Failed to dispatch Celery chain for job {job_id}: {e}", exc_info=True)
            # Attempt to mark job as FAILED in DB if dispatch fails
            try:
                 async with session.begin():
                     job_to_fail = await session.get(Job, job_id) # Fetch fresh object
                     if job_to_fail:
                         job_to_fail.status = JobStatus.FAILED
                         job_to_fail.failed_at_step = "dispatch"
                         job_to_fail.error_message = f"Failed to queue tasks: {str(e)[:450]}"
                         log.info(f"Set job {job_id} status to FAILED due to dispatch error.")
                     else: log.error(f"Could not find job {job_id} to mark as FAILED after dispatch error.")
            except Exception as db_e: log.error(f"[Job {job_id}] CRITICAL: Failed to update job status to FAILED after dispatch error: {db_e}", exc_info=True)
            # Decide if to raise HTTP 500 or just redirect with job marked as failed
            # raise HTTPException(status_code=500, detail="Failed to queue processing tasks.")
    else:
         log.error(f"Cannot dispatch Celery chain for job {job_id}: Worker tasks could not be imported.")
         # Mark job as FAILED because processing cannot start
         try:
             async with session.begin():
                 job_to_fail = await session.get(Job, job_id)
                 if job_to_fail:
                     job_to_fail.status = JobStatus.FAILED
                     job_to_fail.failed_at_step = "import"
                     job_to_fail.error_message = "Interface could not import worker tasks."
                     log.info(f"Set job {job_id} status to FAILED due to task import error.")
                 else: log.error(f"Could not find job {job_id} to mark as FAILED after import error.")
         except Exception as db_e: log.error(f"[Job {job_id}] CRITICAL: Failed to update job status to FAILED after import error: {db_e}", exc_info=True)


    # --- 7. Update Job Record with Celery Task ID ---
    if celery_task_id:
        try:
            async with session.begin():
                 job_to_update = await session.get(Job, job_id) # Fetch fresh object
                 if job_to_update:
                    job_to_update.celery_task_id = celery_task_id
                    log.info(f"Successfully updated job {job_id} with Celery task ID.")
                 else:
                    # This indicates a potential problem if the job disappears between creation and update
                    log.error(f"Could not find job {job_id} to update with Celery task ID {celery_task_id}.")
        except Exception as e:
            log.error(f"Failed to update job {job_id} with Celery task ID {celery_task_id}: {e}", exc_info=True)
            # Job is already queued, log error but don't stop the redirect

    # --- 8. Redirect to Gallery ---
    redirect_url = request.url_for('serve_gallery_page')
    log.info(f"Job {job_id} creation endpoint finished. Redirecting to gallery: {redirect_url}")
    log.info("------------------------------------\n")
    return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)


@app.get("/health")
async def health_check(session: AsyncSession = Depends(get_async_session)):
    """Basic health check including database connectivity."""
    db_status = "connected"
    try:
        # Simple query to ensure connection is truly working
        stmt = select(Job.jobid).limit(1) # Query something simple
        await session.execute(stmt)
    except Exception as e:
        log.warning(f"Health check DB query failed: {e}", exc_info=True) # Use warning for health check failure
        db_status = "disconnected/error"

    return {"status": "ok", "database": db_status}
