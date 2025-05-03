FROM python:3.13-slim-bookworm

# Set working directory
WORKDIR /app

# requirements.txt is copied first for layer caching - installs required dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Default command will be overridden by docker-compose
# CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]