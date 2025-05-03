# splatgen
Reconstruct scenes/objects from Videos using Gaussian Splatting

**Requirements**:
- Docker (nvidia-container-toolkit, docker-compose)
- CUDA Enabled GPU
- NVIDIA Container Toolkit >= 11.8

<br>

**Stack**:
*   **Web Framework:** **FastAPI** (for handling HTTP requests, located in `interface/`)
*   **Database:** **PostgreSQL** + **SQLAlchemy** + **`asyncpg`** (for storing job status and metadata)
*   **Task Queue:** **Celery** (for defining, managing, and executing background tasks, located in `worker/`)
*   **Message Broker:** **RabbitMQ** (mediates communication between FastAPI and Celery workers)
*   **Containerization:** **Docker** & **Docker Compose** (for environment definition, build, orchestration, and configuration)



<br>

**Architecture**:

<details>
<summary>High-Level architecture</summary>

![diagram](docs/diagrams/high-level.excalidraw.png)

</details>

<details>
<summary>Stack Overview</summary>

![diagram](docs/diagrams/arch.excalidraw.png)

</details>

<br>

**Directory Structure**:

```bash
splatgen/
├── docker-compose.yml      # for orchestration - ties in fastapi + celery + rabbitmq
├── .env
├── .gitignore
├── .dockerignore
│
├── interface/              # fastapi app
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   ├── static/             # For CSS and JS files
│   │   ├── css/
│   │   │   └── style.css
│   │   └── js/
│   │       └── script.js
│   └── templates/          # For HTML files
│       ├── upload.html
│       ├── list_splats.html
│       └── view_splat.html
│
├── worker/                 # celery worker with queues
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── celery_app.py
│   └── tasks/              # all pipelined tasks
│
└── data/              # Mounted volume for persistent I/O
    └── <job_id_1>/
    └── <job_id_2>/
```

The current setup works for a single GPU of 8.9 CUDA Compute Capability.
To extend this to other GPUs, get your Compute Capability with this command (Ex. 8.7, 8.9):
```bash
nvidia-smi --query-gpu=name,compute_cap --format=csv
```

If you want to use more than one GPUs:
```bash
NUM_GPUS=$(nvidia-smi --query-gpu=count --format=csv,noheader)
docker-compose up --build --scale gpu_worker=$NUM_GPUS -d
```