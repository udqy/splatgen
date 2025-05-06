# worker/tasks/colmap.py
import logging
import time
from worker.celery_app import celery_app
from worker.tasks.utils import update_job_status, Job, JobStatus

log = logging.getLogger(__name__)

@celery_app.task(name="worker.tasks.colmap.feature_extraction")
def feature_extraction_task(job_id: str):
    log.info(f"[Job {job_id}] Task: Starting COLMAP feature extraction...")
    update_job_status(job_id, status=JobStatus.RUNNING_COLMAP)
    try:
        # --- TODO: Add COLMAP feature_extractor logic ---
        time.sleep(4) # Simulate work
        log.info(f"[Job {job_id}] Task: COLMAP feature extraction finished.")
        return job_id
    except Exception as e:
        log.error(f"[Job {job_id}] Task: Error during feature extraction: {e}", exc_info=True)
        update_job_status(job_id, failed_step="feature_extraction", error_msg=str(e))
        raise

@celery_app.task(name="worker.tasks.colmap.feature_matching")
def feature_matching_task(job_id: str):
    log.info(f"[Job {job_id}] Task: Starting COLMAP feature matching...")
    # Status remains RUNNING_COLMAP
    try:
        # --- TODO: Add COLMAP matcher logic ---
        time.sleep(4) # Simulate work
        log.info(f"[Job {job_id}] Task: COLMAP feature matching finished.")
        return job_id
    except Exception as e:
        log.error(f"[Job {job_id}] Task: Error during feature matching: {e}", exc_info=True)
        update_job_status(job_id, failed_step="feature_matching", error_msg=str(e))
        raise

@celery_app.task(name="worker.tasks.colmap.sparse_mapping")
def sparse_mapping_task(job_id: str):
    log.info(f"[Job {job_id}] Task: Starting COLMAP sparse mapping...")
    # Status remains RUNNING_COLMAP
    try:
        # --- TODO: Add COLMAP mapper logic ---
        time.sleep(6) # Simulate work
        log.info(f"[Job {job_id}] Task: COLMAP sparse mapping finished.")
        return job_id
    except Exception as e:
        log.error(f"[Job {job_id}] Task: Error during sparse mapping: {e}", exc_info=True)
        update_job_status(job_id, failed_step="sparse_mapping", error_msg=str(e))
        raise

@celery_app.task(name="worker.tasks.colmap.image_undistortion")
def image_undistortion_task(job_id: str):
    log.info(f"[Job {job_id}] Task: Starting COLMAP image undistortion...")
    # Status remains RUNNING_COLMAP
    try:
        # --- TODO: Add COLMAP image_undistorter logic ---
        time.sleep(3) # Simulate work
        log.info(f"[Job {job_id}] Task: COLMAP image undistortion finished.")
        return job_id
    except Exception as e:
        log.error(f"[Job {job_id}] Task: Error during image undistortion: {e}", exc_info=True)
        update_job_status(job_id, failed_step="image_undistortion", error_msg=str(e))
        raise
    