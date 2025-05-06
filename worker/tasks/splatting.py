import logging
import time
from worker.celery_app import celery_app
from worker.tasks.utils import update_job_status, Job, JobStatus

log = logging.getLogger(__name__)

@celery_app.task(name="worker.tasks.splatting.train_splatting")
def train_splatting_task(job_id: str):
    log.info(f"[Job {job_id}] Task: Starting Gaussian Splatting training...")
    update_job_status(job_id, status=JobStatus.RUNNING_SPLATTING)
    try:
        # --- Todo: Add actual Gaussian Splatting training logic ---
        # This step implicitly saves the .ply file based on train.py parameters
        log.info(f"[Job {job_id}] Task: Gaussian Splatting training simulation (long step)...")
        time.sleep(15) # Simulate long GPU work
        log.info(f"[Job {job_id}] Task: Gaussian Splatting training finished.")
        return job_id
    except Exception as e:
        log.error(f"[Job {job_id}] Task: Error during Gaussian Splatting training: {e}", exc_info=True)
        update_job_status(job_id, failed_step="train_splatting", error_msg=str(e))
        raise
