from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.analytics import router as analytics_router
from app.api.auth import router as auth_router
from app.api.datasets import router as datasets_router
from app.api.system import router as system_router
from app.core.config import settings
from app.core.database import SessionLocal, ensure_schema, verify_production_schema
from app.models.dataset import DatasetActivation, DatasetRecord  # noqa: F401
from app.models.system import ActivityRecord, NotificationRecord, ReportRecord  # noqa: F401
from app.models.user import User  # noqa: F401
from app.services.auth_service import ensure_demo_user
from app.services.dataset_service import ensure_bundled_dataset


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.app_env.lower() == "production":
        if settings.secret_key == "change-this-development-secret":
            raise RuntimeError("SECRET_KEY must be configured in production.")
        if "*" in settings.cors_origins:
            raise RuntimeError("CORS_ORIGINS must not contain wildcards in production.")
        if settings.database_url.startswith("sqlite"):
            raise RuntimeError("DATABASE_URL must use PostgreSQL in production.")
        if not settings.supabase_url or not settings.supabase_service_key:
            raise RuntimeError("Supabase Storage credentials must be configured in production.")
        verify_production_schema()
    elif settings.app_env.lower() == "development":
        ensure_schema()
        if settings.seed_demo_data:
            db = SessionLocal()
            try:
                ensure_demo_user(db)
                ensure_bundled_dataset(db)
            finally:
                db.close()
    yield

app = FastAPI(
    title="SOCIALPULSE AI API",
    version="0.2.0",
    description="CSV-based social media intelligence and trend analysis API",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)
app.include_router(datasets_router)
app.include_router(analytics_router)
app.include_router(system_router)


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok", "service": "socialpulse-ai-api", "version": "0.2.0"}
