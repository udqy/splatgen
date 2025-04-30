# splatgen
Reconstruct scenes/objects from Videos using Gaussian Splatting

**Requirements**:
- Docker (nvidia-container-toolkit, docker-compose)
- CUDA Enabled GPU
- NVIDIA Container Toolkit >= 11.8

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