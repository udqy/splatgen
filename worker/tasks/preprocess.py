import logging
import time
from worker.celery_app import celery_app
from worker.tasks.utils import update_job_status, Job, JobStatus

log = logging.getLogger(__name__)

@celery_app.task(name="worker.tasks.preprocess.extract_frames")
def extract_frames_task(job_id: str):
    log.info(f"[Job {job_id}] Task: Starting frame extraction...")
    update_job_status(job_id, status=JobStatus.PREPROCESSING)
    try:
        # --- Todo: Add actual ffmpeg logic ---
        time.sleep(3) # Simulate work
        log.info(f"[Job {job_id}] Task: Frame extraction finished.")
        return job_id # Pass job_id to the next task
    except Exception as e:
        log.error(f"[Job {job_id}] Task: Error during frame extraction: {e}", exc_info=True)
        update_job_status(job_id, failed_step="extract_frames", error_msg=str(e))
        raise

@celery_app.task(name="worker.tasks.preprocess.remove_background")
def remove_background_task(job_id: str):
    log.info(f"[Job {job_id}] Task: Starting background removal...")
    # Status remains PREPROCESSING
    try:
        # --- TODO: Add actual rembg/SAM logic ---
        time.sleep(5) # Simulate work
        log.info(f"[Job {job_id}] Task: Background removal finished.")
        return job_id
    except Exception as e:
        log.error(f"[Job {job_id}] Task: Error during background removal: {e}", exc_info=True)
        update_job_status(job_id, failed_step="remove_background", error_msg=str(e))
        raise
    