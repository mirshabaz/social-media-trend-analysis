import html
import io
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import HTTPException, UploadFile
from sqlalchemy import or_, update
from sqlalchemy.orm import Session

from app.core.config import PROJECT_ROOT, REPO_ROOT, settings
from app.models.dataset import DatasetActivation, DatasetRecord
from app.services.activity_service import record_event
from app.services.nlp_service import enrich_sentiment_columns, extract_hashtags_from_row
from app.services.cloud_storage import delete_object, ensure_local_file, upload_bytes


DATA_DIR = PROJECT_ROOT / "dataset_uploads"
DATA_DIR.mkdir(parents=True, exist_ok=True)

BUNDLED_DATASET_CANDIDATES = [
    REPO_ROOT / "dataset" / "social_media_data.csv",
    PROJECT_ROOT / "dataset" / "social_media_data.csv",
]

COLUMN_ALIASES = {
    "post_id": ["post_id", "postid", "id", "post"],
    "author": ["author", "username", "user", "handle", "creator", "account"],
    "platform": ["platform", "network", "channel", "source", "social_network"],
    "post_content": ["post_content", "text", "content", "message", "body", "tweet", "caption"],
    "topic": ["topic", "theme", "category", "subject", "niche"],
    "hashtags": ["hashtags", "hashtag", "tags"],
    "likes": ["likes", "like_count", "likes_count", "reactions", "favorites"],
    "shares": ["shares", "share_count", "retweets", "reposts", "forwards"],
    "comments": ["comments", "comment_count", "reply_count", "responses", "replies"],
    "sentiment": ["sentiment", "label", "sentiment_label", "polarity_label"],
    "timestamp": ["timestamp", "date", "datetime", "created_at", "post_date", "time", "published_at"],
    "impressions": ["impressions", "views", "reach", "followers", "audience_size"],
}

SUPPORTED_FIELDS = [
    {"key": "post_content", "label": "Post Content", "required": True, "description": "Primary social post text, caption, or tweet body"},
    {"key": "post_id", "label": "Post ID", "required": False, "description": "Unique identifier for each post"},
    {"key": "platform", "label": "Platform", "required": False, "description": "Social channel (Instagram, LinkedIn, Twitter/X, Facebook)"},
    {"key": "timestamp", "label": "Date / Timestamp", "required": False, "description": "Post creation date or datetime"},
    {"key": "likes", "label": "Likes", "required": False, "description": "Numeric like or reaction count"},
    {"key": "shares", "label": "Shares / Reposts", "required": False, "description": "Numeric share or retweet count"},
    {"key": "comments", "label": "Comments / Replies", "required": False, "description": "Numeric comment or reply count"},
    {"key": "hashtags", "label": "Hashtags", "required": False, "description": "Space or comma-separated hashtags"},
    {"key": "topic", "label": "Topic / Category", "required": False, "description": "Topic or theme label"},
    {"key": "sentiment", "label": "Sentiment Label", "required": False, "description": "Existing sentiment label (auto-classified via NLP if omitted)"},
    {"key": "author", "label": "Author / Handle", "required": False, "description": "Creator username or account handle"},
    {"key": "impressions", "label": "Impressions / Reach / Followers", "required": False, "description": "Optional denominator for engagement rate calculation"},
]


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


def _parse_csv_bytes(content: bytes) -> pd.DataFrame:
    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return pd.read_csv(io.BytesIO(content), encoding=encoding)
        except UnicodeDecodeError:
            continue
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"Invalid CSV file: {exc}") from exc
    raise HTTPException(status_code=422, detail="Unable to decode CSV file with supported text encodings.")


def _validate_upload_bytes(filename: str | None, content: bytes) -> None:
    if not filename:
        raise HTTPException(status_code=422, detail="A CSV file name is required.")
    if not filename.lower().endswith(".csv"):
        raise HTTPException(status_code=415, detail="Only CSV files are supported.")
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="CSV file exceeds the 10 MB upload limit.")
    if not content:
        raise HTTPException(status_code=422, detail="The uploaded CSV file is empty.")


def clean_dataframe_with_stats(
    df: pd.DataFrame, mapping: dict[str, str]
) -> tuple[pd.DataFrame, dict[str, Any]]:
    cleaned = df.copy()
    original_rows = len(cleaned)

    for canonical, source in mapping.items():
        if source and source in cleaned.columns and canonical != source:
            cleaned[canonical] = cleaned[source]

    if "post_content" not in cleaned.columns:
        raise HTTPException(
            status_code=422,
            detail="Missing required text column. Include or map a post_content, text, content, or tweet column.",
        )

    had_post_id = "post_id" in cleaned.columns
    if not had_post_id:
        cleaned["post_id"] = [f"POST_{index + 1:05d}" for index in range(len(cleaned))]
    else:
        missing_ids = cleaned["post_id"].isna() | (cleaned["post_id"].astype(str).str.strip() == "")
        if missing_ids.any():
            fallback_ids = [f"POST_{index + 1:05d}" for index in range(len(cleaned))]
            cleaned["post_id"] = cleaned["post_id"].where(~missing_ids, pd.Series(fallback_ids, index=cleaned.index))
        cleaned["post_id"] = cleaned["post_id"].astype(str).str.strip()

    cleaned["post_content"] = cleaned["post_content"].fillna("").astype(str)
    cleaned["clean_text"] = cleaned["post_content"].map(clean_text)

    non_empty_mask = cleaned["clean_text"].str.len() > 0
    empty_or_invalid_text = int((~non_empty_mask).sum())
    cleaned = cleaned[non_empty_mask].copy()

    before_content_dedup = len(cleaned)
    cleaned = cleaned.drop_duplicates(subset=["clean_text"], keep="first")
    content_duplicates_removed = before_content_dedup - len(cleaned)

    id_duplicates_removed = 0
    if had_post_id:
        before_id_dedup = len(cleaned)
        cleaned = cleaned.drop_duplicates(subset=["post_id"], keep="first")
        id_duplicates_removed = before_id_dedup - len(cleaned)

    invalid_numeric_cells = 0
    for column in ("likes", "shares", "comments"):
        if column in cleaned.columns:
            numeric_raw = pd.to_numeric(cleaned[column], errors="coerce")
            invalid_numeric_cells += int((cleaned[column].notna() & numeric_raw.isna()).sum())
            cleaned[column] = numeric_raw.fillna(0).clip(lower=0).astype(int)
        else:
            cleaned[column] = 0

    cleaned["total_engagement"] = (
        cleaned["likes"] + cleaned["shares"] + cleaned["comments"]
    )
    cleaned["char_length"] = cleaned["post_content"].str.len()

    invalid_timestamps = 0
    if "timestamp" in cleaned.columns:
        raw_ts = cleaned["timestamp"]
        parsed_ts = pd.to_datetime(raw_ts, errors="coerce")
        invalid_timestamps = int((raw_ts.notna() & parsed_ts.isna()).sum())
        cleaned["timestamp"] = parsed_ts

    if "platform" not in cleaned.columns:
        cleaned["platform"] = "Unknown"
    else:
        cleaned["platform"] = (
            cleaned["platform"]
            .fillna("Unknown")
            .astype(str)
            .str.strip()
            .replace({"": "Unknown", "nan": "Unknown", "None": "Unknown"})
        )

    if "author" not in cleaned.columns:
        cleaned["author"] = "Unknown"
    else:
        cleaned["author"] = (
            cleaned["author"]
            .fillna("Unknown")
            .astype(str)
            .str.strip()
            .replace({"": "Unknown", "nan": "Unknown", "None": "Unknown"})
        )

    if "topic" not in cleaned.columns:
        cleaned["topic"] = "Uncategorized"
    else:
        cleaned["topic"] = (
            cleaned["topic"]
            .fillna("Uncategorized")
            .astype(str)
            .str.strip()
            .replace({"": "Uncategorized", "nan": "Uncategorized", "None": "Uncategorized"})
        )

    if "hashtags" not in cleaned.columns:
        cleaned["hashtags"] = ""
    else:
        cleaned["hashtags"] = cleaned["hashtags"].fillna("").astype(str)

    # Extract hashtags cleanly from either hashtags column or inline post content
    extracted_lists = [
        extract_hashtags_from_row(h, c)
        for h, c in zip(cleaned["hashtags"], cleaned["post_content"])
    ]
    cleaned["hashtags"] = [" ".join(tags) for tags in extracted_lists]
    cleaned["hashtag_count"] = [len(tags) for tags in extracted_lists]

    if "impressions" in cleaned.columns:
        cleaned["impressions"] = (
            pd.to_numeric(cleaned["impressions"], errors="coerce").fillna(0).clip(lower=0)
        )

    cleaned = enrich_sentiment_columns(cleaned)

    total_duplicates = int(content_duplicates_removed + id_duplicates_removed)
    invalid_records = int(empty_or_invalid_text + invalid_timestamps)
    missing_values = int(df.isna().sum().sum())

    summary = {
        "original_rows": int(original_rows),
        "cleaned_rows": int(len(cleaned)),
        "duplicates_removed": total_duplicates,
        "content_duplicates_removed": int(content_duplicates_removed),
        "id_duplicates_removed": int(id_duplicates_removed),
        "empty_content_removed": int(empty_or_invalid_text),
        "invalid_timestamps": int(invalid_timestamps),
        "invalid_numeric_cells": int(invalid_numeric_cells),
        "invalid_records": invalid_records,
        "missing_values_detected": missing_values,
        "sentiment_mode": (
            "mixed_or_labelled"
            if (cleaned["sentiment_source"] == "dataset_label").any()
            else "automated_nlp"
        ),
        "has_engagement_denominator": bool(
            "impressions" in cleaned.columns and (cleaned["impressions"] > 0).any()
        ),
    }

    return cleaned.reset_index(drop=True), summary


def clean_dataframe(df: pd.DataFrame, mapping: dict[str, str]) -> pd.DataFrame:
    cleaned, _ = clean_dataframe_with_stats(df, mapping)
    return cleaned


async def inspect_csv_upload(file: UploadFile) -> dict[str, Any]:
    content = await file.read()
    _validate_upload_bytes(file.filename, content)
    df = _parse_csv_bytes(content)
    if df.empty:
        raise HTTPException(status_code=422, detail="The CSV file contains no data rows.")

    columns = [str(col) for col in df.columns]
    detected_mapping = detect_column_mapping(columns)
    missing_values = {str(col): int(df[col].isna().sum()) for col in df.columns if df[col].isna().sum() > 0}

    estimated_duplicates = 0
    if "post_content" in detected_mapping:
        src = detected_mapping["post_content"]
        estimated_duplicates = int(df[src].fillna("").astype(str).duplicated(keep="first").sum())

    sample_df = df.head(12)
    sample_rows = sample_df.where(pd.notna(sample_df), None).to_dict(orient="records")

    return {
        "filename": file.filename,
        "suggested_name": Path(file.filename or "dataset").stem,
        "file_size_bytes": len(content),
        "row_count": int(len(df)),
        "column_count": int(len(columns)),
        "columns": columns,
        "detected_mapping": detected_mapping,
        "missing_values": missing_values,
        "total_missing_values": int(df.isna().sum().sum()),
        "estimated_duplicates": estimated_duplicates,
        "sample_rows": sample_rows,
        "supported_fields": SUPPORTED_FIELDS,
    }


def _find_bundled_csv() -> Path | None:
    for candidate in BUNDLED_DATASET_CANDIDATES:
        if candidate.exists():
            return candidate
    return None


def ensure_bundled_dataset(db: Session) -> DatasetRecord | None:
    existing_count = db.query(DatasetRecord).count()
    if existing_count > 0:
        return (
            db.query(DatasetRecord)
            .filter(DatasetRecord.owner_id.is_(None), DatasetRecord.is_active.is_(True))
            .order_by(DatasetRecord.created_at.desc())
            .first()
        )
    if settings.app_env.lower() != "development" or not settings.seed_demo_data:
        return None

    bundled_path = _find_bundled_csv()
    if bundled_path is None:
        return None

    df = pd.read_csv(bundled_path)
    if df.empty:
        return None

    mapping = detect_column_mapping([str(col) for col in df.columns])
    cleaned, summary = clean_dataframe_with_stats(df, mapping)

    stored_filename = "bundled_social_media_original.csv"
    cleaned_filename = "bundled_social_media_cleaned.csv"
    original_path = DATA_DIR / stored_filename
    cleaned_path = DATA_DIR / cleaned_filename
    df.to_csv(original_path, index=False)
    cleaned.to_csv(cleaned_path, index=False)
    if settings.supabase_url and settings.supabase_service_key:
        upload_bytes(settings.supabase_dataset_bucket, stored_filename, original_path.read_bytes(), "text/csv")
        upload_bytes(settings.supabase_dataset_bucket, cleaned_filename, cleaned_path.read_bytes(), "text/csv")

    record = DatasetRecord(
        name="SocialPulse Benchmark Dataset",
        original_filename=bundled_path.name,
        stored_filename=stored_filename,
        cleaned_filename=cleaned_filename,
        row_count=int(len(df)),
        cleaned_row_count=int(len(cleaned)),
        column_count=int(len(df.columns)),
        duplicate_count=summary["duplicates_removed"],
        missing_value_count=summary["missing_values_detected"],
        invalid_record_count=summary["invalid_records"],
        status="ready",
        column_mapping_json=json.dumps(mapping),
        cleaning_summary_json=json.dumps(summary),
        is_bundled=True,
        is_active=True,
        owner_id=None,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    record_event(
        db,
        action="dataset_seeded",
        title="Demo Dataset Ready",
        message=f"Bundled dataset '{record.name}' initialized ({record.cleaned_row_count:,} cleaned posts).",
        category="dataset",
        severity="info",
        target_type="dataset",
        target_name=record.name,
        meta={"dataset_id": record.id},
    )
    return record


async def upload_dataset(
    db: Session,
    file: UploadFile,
    *,
    column_mapping_json: str | None = None,
    dataset_name: str | None = None,
    activate: bool = True,
    owner_id: int | None = None,
) -> DatasetRecord:
    ensure_bundled_dataset(db)
    content = await file.read()
    _validate_upload_bytes(file.filename, content)

    df = _parse_csv_bytes(content)
    if df.empty:
        raise HTTPException(status_code=422, detail="The CSV file contains no data rows.")

    auto_mapping = detect_column_mapping([str(col) for col in df.columns])
    mapping = dict(auto_mapping)
    if column_mapping_json:
        try:
            user_mapping = json.loads(column_mapping_json)
            if isinstance(user_mapping, dict):
                cleaned_user_mapping = {
                    str(k): str(v)
                    for k, v in user_mapping.items()
                    if v and str(v) in df.columns
                }
                mapping = cleaned_user_mapping if cleaned_user_mapping else auto_mapping
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=422, detail=f"Invalid column mapping JSON: {exc}") from exc

    try:
        cleaned, summary = clean_dataframe_with_stats(df, mapping)
    except HTTPException as exc:
        record_event(
            db,
            action="dataset_upload_failed",
            title="Dataset Processing Failed",
            message=f"Could not process '{file.filename}': {exc.detail}",
            category="dataset",
            severity="error",
            target_type="dataset",
            target_name=file.filename or "upload.csv",
            user_id=owner_id,
        )
        raise

    if cleaned.empty:
        raise HTTPException(
            status_code=422,
            detail="All rows were empty or invalid after text cleaning.",
        )

    upload_id = uuid.uuid4().hex
    stored_filename = f"{upload_id}_original.csv"
    cleaned_filename = f"{upload_id}_cleaned.csv"
    original_path = DATA_DIR / stored_filename
    cleaned_path = DATA_DIR / cleaned_filename
    df.to_csv(original_path, index=False)
    cleaned.to_csv(cleaned_path, index=False)
    if settings.supabase_url and settings.supabase_service_key:
        upload_bytes(settings.supabase_dataset_bucket, stored_filename, original_path.read_bytes(), "text/csv")
        upload_bytes(settings.supabase_dataset_bucket, cleaned_filename, cleaned_path.read_bytes(), "text/csv")

    if activate and owner_id is None:
        db.execute(
            update(DatasetRecord)
            .where(DatasetRecord.owner_id.is_(None))
            .values(is_active=False)
        )

    final_name = (dataset_name or "").strip() or Path(file.filename or "dataset").stem

    record = DatasetRecord(
        name=final_name,
        original_filename=file.filename or "dataset.csv",
        stored_filename=stored_filename,
        cleaned_filename=cleaned_filename,
        row_count=int(len(df)),
        cleaned_row_count=int(len(cleaned)),
        column_count=int(len(df.columns)),
        duplicate_count=summary["duplicates_removed"],
        missing_value_count=summary["missing_values_detected"],
        invalid_record_count=summary["invalid_records"],
        status="ready",
        column_mapping_json=json.dumps(mapping),
        cleaning_summary_json=json.dumps(summary),
        is_bundled=False,
        is_active=activate and owner_id is None,
        owner_id=owner_id,
    )
    db.add(record)
    db.flush()
    if activate and owner_id is not None:
        activation = db.get(DatasetActivation, owner_id)
        if activation is None:
            activation = DatasetActivation(user_id=owner_id, dataset_id=record.id)
            db.add(activation)
        else:
            activation.dataset_id = record.id
            activation.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(record)

    record_event(
        db,
        action="dataset_uploaded",
        title="Dataset Uploaded & Cleaned",
        message=(
            f"'{record.name}' processed: {record.cleaned_row_count:,} clean rows "
            f"({record.duplicate_count} duplicates removed, {record.missing_value_count} missing cells detected)."
        ),
        category="dataset",
        severity="success",
        target_type="dataset",
        target_name=record.name,
        user_id=owner_id,
        meta={"dataset_id": record.id},
    )
    return record


def _accessible_query(db: Session, user_id: int | None):
    query = db.query(DatasetRecord)
    if user_id is None:
        return query.filter(DatasetRecord.owner_id.is_(None))
    return query.filter(or_(DatasetRecord.owner_id.is_(None), DatasetRecord.owner_id == user_id))


def list_datasets(db: Session, user_id: int | None = None) -> list[DatasetRecord]:
    ensure_bundled_dataset(db)
    return (
        _accessible_query(db, user_id)
        .order_by(DatasetRecord.is_active.desc(), DatasetRecord.created_at.desc())
        .all()
    )


def get_dataset(db: Session, dataset_id: int, user_id: int | None = None) -> DatasetRecord:
    ensure_bundled_dataset(db)
    record = db.query(DatasetRecord).filter(DatasetRecord.id == dataset_id).first()
    if record is None:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    if record.owner_id is not None and record.owner_id != user_id:
        raise HTTPException(status_code=403, detail="You do not have access to this dataset.")
    return record


def get_active_dataset_record(
    db: Session, dataset_id: int | None = None, user_id: int | None = None
) -> DatasetRecord | None:
    ensure_bundled_dataset(db)
    if dataset_id is not None:
        return get_dataset(db, dataset_id, user_id=user_id)
    if user_id is not None:
        activation = db.get(DatasetActivation, user_id)
        if activation is not None:
            return get_dataset(db, activation.dataset_id, user_id=user_id)
        owned_active = (
            db.query(DatasetRecord)
            .filter(DatasetRecord.owner_id == user_id, DatasetRecord.is_active.is_(True))
            .order_by(DatasetRecord.created_at.desc())
            .first()
        )
        if owned_active is not None:
            return owned_active
    return (
        db.query(DatasetRecord)
        .filter(DatasetRecord.owner_id.is_(None), DatasetRecord.is_active.is_(True))
        .order_by(DatasetRecord.created_at.desc())
        .first()
    )


def activate_dataset(
    db: Session, dataset_id: int, user_id: int | None = None
) -> DatasetRecord:
    record = get_dataset(db, dataset_id, user_id=user_id)
    if user_id is None:
        db.execute(
            update(DatasetRecord)
            .where(DatasetRecord.owner_id.is_(None))
            .values(is_active=False)
        )
        record.is_active = True
    else:
        activation = db.get(DatasetActivation, user_id)
        if activation is None:
            db.add(DatasetActivation(user_id=user_id, dataset_id=record.id))
        else:
            activation.dataset_id = record.id
            activation.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(record)

    record_event(
        db,
        action="dataset_activated",
        title="Active Dataset Switched",
        message=f"Analytics workspace switched to '{record.name}' ({record.cleaned_row_count:,} posts).",
        category="dataset",
        severity="info",
        target_type="dataset",
        target_name=record.name,
        user_id=user_id,
        meta={"dataset_id": record.id},
    )
    return record


def delete_dataset(
    db: Session, dataset_id: int, user_id: int | None = None
) -> dict[str, Any]:
    record = get_dataset(db, dataset_id, user_id=user_id)
    if user_id is not None and record.owner_id != user_id:
        raise HTTPException(status_code=403, detail="Only the dataset owner can delete this dataset.")
    if record.is_bundled:
        raise HTTPException(
            status_code=400,
            detail="The bundled demonstration dataset cannot be deleted.",
        )

    activation = db.get(DatasetActivation, user_id) if user_id is not None else None
    was_active = record.is_active or (activation is not None and activation.dataset_id == record.id)
    name = record.name
    filenames = (record.stored_filename, record.cleaned_filename)
    if settings.supabase_url and settings.supabase_service_key:
        for filename in filenames:
            delete_object(settings.supabase_dataset_bucket, filename)
    if activation is not None and activation.dataset_id == record.id:
        db.delete(activation)
    db.delete(record)
    db.commit()
    for filename in filenames:
        path = DATA_DIR / filename
        if path.exists():
            path.unlink()

    new_active = None
    if was_active:
        fallback = (
            _accessible_query(db, user_id)
            .order_by(DatasetRecord.created_at.desc())
            .first()
        )
        if fallback:
            if user_id is None:
                fallback.is_active = True
            else:
                db.add(DatasetActivation(user_id=user_id, dataset_id=fallback.id))
            db.commit()
            db.refresh(fallback)
            new_active = fallback

    record_event(
        db,
        action="dataset_deleted",
        title="Dataset Deleted",
        message=f"Removed dataset '{name}'." + (f" Activated '{new_active.name}'." if new_active else ""),
        category="dataset",
        severity="warning",
        target_type="dataset",
        target_name=name,
        user_id=user_id,
    )
    return {"deleted_id": dataset_id, "new_active_id": new_active.id if new_active else None}


def get_cleaned_dataframe(record: DatasetRecord) -> pd.DataFrame:
    cleaned_path = DATA_DIR / record.cleaned_filename
    try:
        cached_path = ensure_local_file(
            cleaned_path, settings.supabase_dataset_bucket, record.cleaned_filename
        )
        return pd.read_csv(cached_path)
    except FileNotFoundError:
        pass
    bundled = _find_bundled_csv()
    if record.is_bundled and bundled:
        df = pd.read_csv(bundled)
        mapping = json.loads(record.column_mapping_json or "{}")
        cleaned = clean_dataframe(df, mapping)
        cleaned.to_csv(cleaned_path, index=False)
        return cleaned
    raise HTTPException(status_code=404, detail="Cleaned dataset file is missing from local and configured cloud storage.")


def dataset_preview(
    db: Session, dataset_id: int, limit: int = 30, user_id: int | None = None
) -> dict:
    record = get_dataset(db, dataset_id, user_id=user_id)
    df = get_cleaned_dataframe(record)
    missing = {str(column): int(count) for column, count in df.isna().sum().items() if count}
    summary = json.loads(record.cleaning_summary_json or "{}")

    return {
        "id": record.id,
        "name": record.name,
        "columns": [str(col) for col in df.columns],
        "rows": df.head(limit).where(pd.notna(df.head(limit)), None).to_dict(orient="records"),
        "row_count": record.row_count,
        "cleaned_row_count": record.cleaned_row_count,
        "missing_values": missing,
        "duplicate_count": record.duplicate_count,
        "invalid_record_count": record.invalid_record_count,
        "column_mapping": json.loads(record.column_mapping_json or "{}"),
        "cleaning_summary": summary,
    }
