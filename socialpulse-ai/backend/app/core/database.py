from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    pass


db_url = settings.resolved_database_url
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+psycopg://", 1)
elif db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)

engine_options: dict = {"pool_pre_ping": True}
if db_url.startswith("sqlite"):
    engine_options["connect_args"] = {"check_same_thread": False}
else:
    engine_options.update({"pool_size": 5, "max_overflow": 10, "pool_recycle": 1800})

engine = create_engine(db_url, **engine_options)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def ensure_schema() -> None:
    """Development/test-only schema bootstrap; production schemas use Alembic."""
    Base.metadata.create_all(bind=engine)
    if not db_url.startswith("sqlite"):
        return

    inspector = inspect(engine)
    if "dataset_records" in inspector.get_table_names():
        existing_cols = {col["name"] for col in inspector.get_columns("dataset_records")}
        migrations = {
            "invalid_record_count": "INTEGER DEFAULT 0",
            "status": "VARCHAR(50) DEFAULT 'ready'",
            "cleaning_summary_json": "TEXT DEFAULT '{}'",
            "is_bundled": "BOOLEAN DEFAULT 0",
            "owner_id": "INTEGER NULL",
        }
        with engine.begin() as conn:
            for col_name, col_def in migrations.items():
                if col_name not in existing_cols:
                    conn.execute(
                        text(f"ALTER TABLE dataset_records ADD COLUMN {col_name} {col_def}")
                    )


def verify_production_schema() -> None:
    """Verify production schema has been migrated to the current Alembic head."""
    from alembic.config import Config
    from alembic.script import ScriptDirectory
    from pathlib import Path

    required_tables = set(Base.metadata.tables)
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
        inspector = inspect(connection)
        missing = required_tables - set(inspector.get_table_names())
        if missing:
            raise RuntimeError("Production database is missing tables: " + ", ".join(sorted(missing)))
        if "alembic_version" not in inspector.get_table_names():
            raise RuntimeError("Production schema is not migrated: alembic_version is missing.")
        current_revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one_or_none()

    alembic_ini = Path(__file__).resolve().parents[2] / "alembic.ini"
    script = ScriptDirectory.from_config(Config(str(alembic_ini)))
    expected_revision = script.get_current_head()
    if current_revision != expected_revision:
        raise RuntimeError(
            f"Production database revision {current_revision!r} does not match expected {expected_revision!r}."
        )


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
