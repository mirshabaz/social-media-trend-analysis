import html
import json
import re
import uuid
from pathlib import Path

import pandas as pd
from fastapi import HTTPException, UploadFile
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.dataset import DatasetRecord


DATA_DIR = Path(__file__).resolve().parents[3] / "dataset_uploads"
DATA_DIR.mkdir(parents=True, exist_ok=True)

COLUMN_ALIASES = {
    "post_id": ["post_id", "postid", "id", "post"],
    "author": ["author", "username", "user", "handle", "creator"],
    "platform": ["platform", "network", "channel", "source"],
    "post_content": ["post_content", "text", "content", "message", "body", "tweet"],
    "topic": ["topic", "theme", "category", "subject"],
    "hashtags": ["hashtags", "hashtag", "tags"],
    "likes": ["likes", "like_count", "likes_count", "reactions"],
    "shares": ["shares", "share_count", "retweets", "reposts"],
    "comments": ["comments", "comment_count", "reply_count", "responses"],
    "sentiment": ["sentiment", "label", "sentiment_label"],
    "timestamp": ["timestamp", "date", "datetime", "created_at", "post_date", "time"],
}


def normalize_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def detect_column_mapping(columns: list[str]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    normalized_columns = {normalize_name(column): column for column in columns}

    for canonical, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            normalized_alias = normalize_name(alias)
            if normalized_alias in normalized_columns:
                mapping[canonical] = normalized_columns[normalized_alias]
                break

    return mapping


def clean_text(value: object) -> str:
    if pd.isna(value):
        return ""
    text = html.unescape(str(value).lower())
    text = re.sub(r"https?://\S+|www\.\S+", " ", text)
    text = re.sub(r"@[A-Za-z0-9_]+", " ", text)
    text = re.sub(r"[^a-z0-9\s#]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def clean_dataframe(df: pd.DataFrame, mapping: dict[str, str]) -> pd.DataFrame:
    cleaned = df.copy()

    for canonical, source in mapping.items():
        if canonical not in cleaned.columns:
            cleaned[canonical] = cleaned[source]

    if "post_content" not in cleaned.columns:
        raise HTTPException(
            status_code=422,
            detail="Missing required text column. Include a post_content, text, content, or tweet column.",
        )

    if "post_id" not in cleaned.columns:
        cleaned["post_id"] = [f"POST_{index + 1:05d}" for index in range(len(cleaned))]

    cleaned["post_content"] = cleaned["post_content"].fillna("").astype(str)
    cleaned["clean_text"] = cleaned["post_content"].map(clean_text)
    cleaned = cleaned[cleaned["clean_text"].str.len() > 0].copy()
    cleaned = cleaned.drop_duplicates(subset=["clean_text"], keep="first")

    for column in ("likes", "shares", "comments"):
        if column in cleaned.columns:
            cleaned[column] = pd.to_numeric(cleaned[column], errors="coerce").fillna(0).clip(lower=0)
        else:
            cleaned[column] = 0

    cleaned["total_engagement"] = (
        cleaned["likes"] + cleaned["shares"] + cleaned["comments"]
    )
    cleaned["char_length"] = cleaned["post_content"].str.len()

    if "timestamp" in cleaned.columns:
        cleaned["timestamp"] = pd.to_datetime(cleaned["timestamp"], errors="coerce")
    if "platform" not in cleaned.columns:
        cleaned["platform"] = "Unknown"
    if "author" not in cleaned.columns:
        cleaned["author"] = "Unknown"
    if "topic" not in cleaned.columns:
        cleaned["topic"] = "Uncategorized"
    if "hashtags" not in cleaned.columns:
        cleaned["hashtags"] = ""
    if "sentiment" not in cleaned.columns:
        cleaned["sentiment"] = "Neutral"

    return cleaned


async def upload_dataset(db: Session, file: UploadFile) -> DatasetRecord:
    if not file.filename:
        raise HTTPException(status_code=422, detail="A CSV file name is required.")
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=415, detail="Only CSV files are supported.")

    content = await file.read()
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="CSV file exceeds the 10 MB upload limit.")
    if not content:
        raise HTTPException(status_code=422, detail="The uploaded CSV file is empty.")

    try:
        df = pd.read_csv(pd.io.common.BytesIO(content))
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Invalid CSV file: {exc}") from exc

    if df.empty:
        raise HTTPException(status_code=422, detail="The CSV file contains no data rows.")

    mapping = detect_column_mapping(list(df.columns))
    row_count = len(df)
    duplicate_count = 0
    if "post_content" in mapping:
        source = mapping["post_content"]
        duplicate_count = int(df[source].duplicated(keep="first").sum())

    cleaned = clean_dataframe(df, mapping)
    missing_count = int(df.isna().sum().sum())

    upload_id = uuid.uuid4().hex
    stored_filename = f"{upload_id}_original.csv"
    cleaned_filename = f"{upload_id}_cleaned.csv"
    df.to_csv(DATA_DIR / stored_filename, index=False)
    cleaned.to_csv(DATA_DIR / cleaned_filename, index=False)

    db.execute(update(DatasetRecord).values(is_active=False))

    record = DatasetRecord(
        name=Path(file.filename).stem,
        original_filename=file.filename,
        stored_filename=stored_filename,
        cleaned_filename=cleaned_filename,
        row_count=row_count,
        cleaned_row_count=len(cleaned),
        column_count=len(df.columns),
        duplicate_count=duplicate_count,
        missing_value_count=missing_count,
        column_mapping_json=json.dumps(mapping),
        is_active=True,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def list_datasets(db: Session) -> list[DatasetRecord]:
    return db.query(DatasetRecord).order_by(DatasetRecord.created_at.desc()).all()


def get_dataset(db: Session, dataset_id: int) -> DatasetRecord:
    record = db.query(DatasetRecord).filter(DatasetRecord.id == dataset_id).first()
    if record is None:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    return record


def activate_dataset(db: Session, dataset_id: int) -> DatasetRecord:
    record = get_dataset(db, dataset_id)
    db.execute(update(DatasetRecord).values(is_active=False))
    record.is_active = True
    db.commit()
    db.refresh(record)
    return record


def get_cleaned_dataframe(record: DatasetRecord) -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / record.cleaned_filename)


def dataset_preview(db: Session, dataset_id: int) -> dict:
    record = get_dataset(db, dataset_id)
    df = get_cleaned_dataframe(record)
    missing = {column: int(count) for column, count in df.isna().sum().items() if count}

    return {
        "id": record.id,
        "name": record.name,
        "columns": list(df.columns),
        "rows": df.head(25).where(pd.notna(df.head(25)), None).to_dict(orient="records"),
        "row_count": record.row_count,
        "cleaned_row_count": record.cleaned_row_count,
        "missing_values": missing,
        "duplicate_count": record.duplicate_count,
        "column_mapping": json.loads(record.column_mapping_json),
    }
