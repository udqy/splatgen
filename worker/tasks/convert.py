# worker/tasks/convert.py
import logging
import time
from pathlib import Path
from worker.celery_app import celery_app
from worker.tasks.utils import update_job_status, Job, JobStatus

log = logging.getLogger(__name__)

@celery_app.task(name="worker.tasks.convert.convert_ply_to_splat")
def convert_ply_to_splat_task(job_id: str):
    log.info(f"[Job {job_id}] Task: Starting PLY to SPLAT conversion...")
    update_job_status(job_id, status=JobStatus.POSTPROCESSING)
    try:
        # --- TODO: Add actual conversion logic here ---
        time.sleep(2) # Simulate work
        log.info(f"[Job {job_id}] Task: PLY to SPLAT conversion finished.")

        # --- Final Step: Update job status to COMPLETED and set output path ---
        relative_output_path = str(Path(job_id) / "output" / "output.splat") # Example path
        update_job_status(job_id, status=JobStatus.COMPLETED, output_path=relative_output_path)
        log.info(f"[Job {job_id}] Task: Pipeline finished successfully.")
        return job_id # End of the chain
    except Exception as e:
        log.error(f"[Job {job_id}] Task: Error during PLY to SPLAT conversion: {e}", exc_info=True)
        update_job_status(job_id, failed_step="convert_ply_to_splat", error_msg=str(e))
        raise
    