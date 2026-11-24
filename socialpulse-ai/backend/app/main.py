from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.datasets import router as datasets_router
from app.api.analytics import router as analytics_router
from app.core.database import Base, engine
from app.models.dataset import DatasetRecord

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="SOCIALPULSE AI API",
    version="0.1.0",
    description="CSV-based social media intelligence API",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(datasets_router)
app.include_router(analytics_router)


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok", "service": "socialpulse-ai-api", "version": "0.1.0"}
