from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = Path(__file__).resolve().parents[3]
REPO_ROOT = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    app_env: str = "development"
    seed_demo_data: bool = False
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    database_url: str = f"sqlite:///{(BACKEND_DIR / 'socialpulse.db').as_posix()}"
    secret_key: str = "change-this-development-secret"
    demo_password: str = ""
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    max_upload_bytes: int = 10 * 1024 * 1024
    supabase_url: str = ""
    supabase_service_key: str = ""
    supabase_dataset_bucket: str = "socialpulse-datasets"
    supabase_report_bucket: str = "socialpulse-reports"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"

    model_config = SettingsConfigDict(
        env_file=[str(PROJECT_ROOT / ".env"), str(BACKEND_DIR / ".env"), ".env"],
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def resolved_database_url(self) -> str:
        if self.database_url == "sqlite:///./socialpulse.db":
            return f"sqlite:///{(BACKEND_DIR / 'socialpulse.db').as_posix()}"
        return self.database_url

    @property
    def cors_origin_list(self) -> list[str]:
        origins = [item.strip() for item in self.cors_origins.split(",") if item.strip()]
        return origins or ["http://localhost:5173", "http://127.0.0.1:5173"]


settings = Settings()
