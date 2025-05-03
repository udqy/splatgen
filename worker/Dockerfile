FROM nvidia/cuda:11.8.0-cudnn8-devel-ubuntu22.04

# avoid configuration prompts
ENV DEBIAN_FRONTEND=noninteractive
# headless execution of COLMAP
ENV QT_QPA_PLATFORM=offscreen

# --- Install System Dependencies ---
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    cmake \
    build-essential \
    wget \
    unzip \
    ffmpeg \
    # Python
    python3 \
    python3-pip \
    python3-dev \
	libxcb-xinerama0 \
	libxcb-cursor0 \
    # Install COLMAP itself from apt
    colmap \
    # Clean up
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# --- Install Python Dependencies ---
# Set working directory BEFORE installing python packages that might build extensions
WORKDIR /app

# copy before for layer caching
COPY requirements.txt ./

# Install PyTorch matching the CUDA version
# Pin versions from your previous Dockerfile for consistency
RUN pip3 install --no-cache-dir \
    torch==2.0.1+cu118 \
    torchvision==0.15.2+cu118 \
    torchaudio==2.0.2 \
    --index-url https://download.pytorch.org/whl/cu118

# Installs the rest of the Python dependencies from requirements.txt
RUN pip3 install --no-cache-dir -r requirements.txt

# Gaussian Splatting Submodules - compile within image
ARG GSPLAT_REPO_URL="https://github.com/graphdeco-inria/gaussian-splatting.git"
RUN git clone --recursive ${GSPLAT_REPO_URL} /opt/gaussian-splatting

# Required ENV for building submodules if using specific GPU architectures
# Adjust '8.9' based on your target GPU (e.g., 7.5, 8.0, 8.6, 9.0)
# Find your architecture using `nvidia-smi --query-gpu=name,compute_cap --format=csv`
# You can also find it the official website: https://developer.nvidia.com/cuda-gpus
# Set the CUDA architectures for building submodules
ENV TORCH_CUDA_ARCH_LIST="7.5;8.6;8.9"

# Build submodules
RUN TORCH_CUDA_ARCH_LIST=$TORCH_CUDA_ARCH_LIST && \
    cd /opt/gaussian-splatting && \
    pip3 install ./submodules/diff-gaussian-rasterization && \
    pip3 install ./submodules/simple-knn

# --- Application Code ---
# Copy the worker application code (celery_app.py, tasks/)
COPY . .

# Create the base data directory within the image (will be mounted over)
RUN mkdir -p /app/data

# Default command is not strictly needed as docker-compose provides it
# CMD ["/bin/bash"]