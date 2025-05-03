# worker/celery_app.py
from celery import Celery
import os
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

broker_url = os.getenv('RABBITMQ_URL', 'amqp://guest:guest@localhost:5672//')
result_backend_url = os.getenv('CELERY_RESULT_BACKEND')

log.info("Initializing Celery Worker...")
log.info(f"Using Broker URL: {broker_url.split('@')[0] + '@...' if '@' in broker_url else broker_url}")

if not result_backend_url:
    log.warning("CELERY_RESULT_BACKEND environment variable not set. Task result storage will be disabled.")
    result_backend_url = None
else:
    log.info(f"Using Result Backend URL: {result_backend_url.split('@')[0] + '@...' if '@' in result_backend_url else result_backend_url}")

celery_app = None
_max_retries = 5
_retry_delay = 5

for attempt in range(1, _max_retries + 1):
    try:
        log.info(f"Attempt {attempt}/{_max_retries} to initialize Celery and connect...")
        app_instance = Celery(
            'worker',
            broker=broker_url,
            backend=result_backend_url,
            include=['worker.tasks.pipeline']
        )

        app_instance.conf.update(
            task_serializer='json',
            accept_content=['json'],
            result_serializer='json',
            timezone='UTC',
            enable_utc=True,
            task_queues={
                'cpu_queue': {'exchange': 'cpu_queue', 'routing_key': 'cpu_queue'},
                'gpu_queue': {'exchange': 'gpu_queue', 'routing_key': 'gpu_queue'},
            },
            task_default_queue='cpu_queue',
            task_default_exchange='cpu_queue',
            task_default_routing_key='cpu_queue',
            broker_connection_retry_on_startup=True,
        )

        log.info("Testing broker connection...")
        conn = app_instance.broker_connection()
        # Use ensure_connection for broker - it works here
        conn.ensure_connection(max_retries=3, interval_start=0, interval_step=0.2, interval_max=0.5, errback=lambda exc, interval: log.error(f"Broker connection error during test: {exc}"))
        conn.release()
        log.info("Broker connection test successful.")

        # --- REMOVED RESULT BACKEND TEST ---
        if app_instance.conf.result_backend:
             log.info("Result backend is configured. Connection will be tested implicitly on first use.")
        else:
             log.info("Result backend is not configured.")

        # If broker connection test passed, assign app and break loop
        celery_app = app_instance
        log.info("Celery app initialized successfully.")
        break

    except Exception as e:
        log.error(f"Attempt {attempt} failed: Could not initialize Celery or establish connections: {e}", exc_info=False)
        if attempt == _max_retries:
            log.critical(f"Celery failed to initialize after {_max_retries} attempts. Worker might not function correctly.")
            celery_app = None
            break
        else:
            log.info(f"Retrying in {_retry_delay} seconds...")
            time.sleep(_retry_delay)

if celery_app is None:
     log.critical("Celery application object ('celery_app') is None after initialization attempts. Worker cannot process tasks.")

# Define tasks only if app initialized
if celery_app:
    @celery_app.task(name="worker.celery_app.health_check_task")
    def health_check_task():
        log.info("Executing health_check_task!")
        return "Celery worker is alive and processing tasks!"
else:
    log.error("Cannot define Celery tasks as the app object failed to initialize.")

# Optional main guard
if __name__ == '__main__':
    log.info("celery_app.py executed directly.")
    if celery_app:
         log.info("Celery app object is available.")
    else:
         log.info("Celery app object is None (initialization failed).")