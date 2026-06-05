from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="CRE コンサルティング営業向けローカルデモアプリケーションの API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health_check() -> dict[str, str]:
    """Return service status for frontend/backend connectivity checks."""

    return {
        "status": "ok",
        "app": settings.app_name,
        "mode": settings.ai_mode,
        "database": "sqlite",
    }


@app.get("/api/config")
def frontend_config() -> dict[str, str]:
    """Return non-sensitive configuration values for the browser UI."""

    return {
        "appName": settings.app_name,
        "aiMode": settings.ai_mode,
        "language": "ja",
    }
