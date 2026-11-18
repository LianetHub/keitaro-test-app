from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import campaigns, meta

settings = get_settings()

app = FastAPI(title="Keitaro Wrapper", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(campaigns.router)
app.include_router(meta.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
