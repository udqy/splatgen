import logging
from worker.database import get_sync_session
from typing import Optional
from datetime import datetime, timezone # Import datetime components

# Import directly - assumes PYTHONPATH=/app is set in the worker container
# and the interface code is mounted at /app/interface
try:
    from interface.app.models import Job, JobStatus
except ImportError as e:
     # This error is critical if it happens at runtime
     logging.critical(f"CRITICAL: Failed to import Job model/enum from interface.app.models in utils: {e}. Worker cannot function correctly. Check PYTHONPATH and volume mounts.", exc_info=True)
     # You might want to raise the error to stop the worker from starting improperly
     raise RuntimeError("Worker utils could not import necessary models.") from e


log = logging.getLogger(__name__)

# Use the direct type hint now that import should work
def update_job_status(job_id: str, status: Optional[JobStatus] = None,
                      failed_step: Optional[str] = None, error_msg: Optional[str] = None,
                      output_path: Optional[str] = None):
    """Helper to update job status and optionally other fields in the database."""
    log_prefix = f"[Job {job_id}]"
    try:
        with get_sync_session() as session:
            # Use session.get for primary key lookup
            job = session.get(Job, job_id)
            if not job:
                log.error(f"{log_prefix} Job not found in database during status update.")
                return

            updated = False
            update_log = []

            # Update status if provided and different
            if status is not None and isinstance(status, JobStatus) and job.status != status:
                job.status = status
                updated = True
                update_log.append(f"status={status.name}")

            # Handle failure conditions
            if failed_step is not None:
                job.failed_at_step = failed_step
                # Automatically set status to FAILED on failure, unless already completed/failed
                if job.status not in [JobStatus.FAILED, JobStatus.COMPLETED]:
                    job.status = JobStatus.FAILED
                    if status != JobStatus.FAILED: # Avoid duplicate log if status was already set to FAILED
                        update_log.append(f"status=FAILED")
                updated = True
                update_log.append(f"failed_at_step='{failed_step}'")

            # Update error message if provided
            if error_msg is not None:
                job.error_message = error_msg[:1000] # Truncate to prevent overflow
                updated = True
                # Log the error message content separately if needed for debugging

            # Update output path if provided
            if output_path is not None:
                job.output_splat_path = output_path
                updated = True
                update_log.append(f"output_splat_path='{output_path}'")

            # Set completion timestamp if status is now COMPLETED or FAILED
            # and it hasn't been set yet (DB default might handle this too)
            if job.status in [JobStatus.COMPLETED, JobStatus.FAILED] and job.completed_at is None:
                 job.completed_at = datetime.now(timezone.utc)
                 updated = True
                 update_log.append("completed_at=now()")


            # If any changes were made, log them
            if updated:
                # session.add(job) is not strictly needed if object was fetched from session
                # and modified, but explicit doesn't hurt.
                session.add(job)
                # Commit happens automatically due to the context manager `get_sync_session`
                log.info(f"{log_prefix} DB updated: {', '.join(update_log)}")
            else:
                 log.debug(f"{log_prefix} No DB changes needed for this update call.")

    except Exception as db_e:
        # Log critical error if DB update fails
        log.critical(f"{log_prefix} CRITICAL: Failed to update job in database: {db_e}", exc_info=True)
        # Re-raise the exception so Celery knows the task might have failed here
        raise
