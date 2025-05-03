from fastapi import FastAPI
import os

app = FastAPI(title="SplatGen Interface")

@app.get("/")
async def read_root():
    db_url = os.getenv("DATABASE_URL", "Not Set")
    mq_url = os.getenv("RABBITMQ_URL", "Not Set")
    return {
        "message": "Hello World from SplatGen Interface!",
        "database_url_set": "****" if "password" not in db_url else db_url.split('@')[0] + "@...",
        "rabbitmq_url_set": bool(mq_url)
    }

@app.get("/health")
async def health_check():
    return {"status": "ok"}

print("FastAPI app instance created.")
