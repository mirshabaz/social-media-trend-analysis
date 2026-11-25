import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.models.user import User
from app.services.auth_service import get_optional_user
from app.services.cloud_storage import ensure_local_file
from app.services.dataset_service import (
    DATA_DIR,
    activate_dataset,
    dataset_preview,
    delete_dataset,
    get_active_dataset_record,
    get_dataset,
    inspect_csv_upload,
    list_datasets,
    upload_dataset,
)

router = APIRouter(prefix="/api", tags=["datasets"])


def serialize(record, active_dataset_id: int | None = None) -> dict:
    return {
        "id": record.id,
        "name": record.name,
        "original_filename": record.original_filename,
        "row_count": record.row_count,
        "cleaned_row_count": record.cleaned_row_count,
        "column_count": record.column_count,
        "duplicate_count": record.duplicate_count,
        "missing_value_count": record.missing_value_count,
        "invalid_record_count": getattr(record, "invalid_record_count", 0) or 0,
        "status": getattr(record, "status", "ready") or "ready",
        "column_mapping": json.loads(record.column_mapping_json or "{}"),
        "cleaning_summary": json.loads(getattr(record, "cleaning_summary_json", "{}") or "{}"),
        "is_bundled": bool(getattr(record, "is_bundled", False)),
        "is_active": active_dataset_id == record.id if active_dataset_id is not None else False,
        "owner_id": getattr(record, "owner_id", None),
        "created_at": record.created_at,
    }


@router.post("/upload/preview")
async def upload_preview(file: UploadFile = File(...)) -> dict:
    preview = await inspect_csv_upload(file)
    return {"status": "success", "preview": preview}


@router.post("/upload")
async def upload(
    file: UploadFile = File(...),
    column_mapping: str | None = Form(default=None),
    dataset_name: str | None = Form(default=None),
    activate: bool = Form(default=True),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> dict:
    user_id = current_user.id if current_user else None
    record = await upload_dataset(
        db,
        file,
        column_mapping_json=column_mapping,
        dataset_name=dataset_name,
        activate=activate,
        owner_id=user_id,
    )
    active = get_active_dataset_record(db, user_id=user_id)
    return {"status": "success", "dataset": serialize(record, active.id if active else None)}


@router.get("/datasets")
async def datasets(
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> dict:
    user_id = current_user.id if current_user else None
    records = list_datasets(db, user_id=user_id)
    active = get_active_dataset_record(db, user_id=user_id)
    active_id = active.id if active else None
    return {"status": "success", "datasets": [serialize(record, active_id) for record in records]}


@router.get("/dataset")
async def active_dataset(
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> dict:
    active = get_active_dataset_record(
        db, user_id=current_user.id if current_user else None
    )
    if active is None:
        return {"status": "success", "dataset": None}
    return {"status": "success", "dataset": serialize(active, active.id)}


@router.get("/dataset/{dataset_id}")
async def dataset_detail(
    dataset_id: int,
    limit: int = Query(default=30, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> dict:
    uid = current_user.id if current_user else None
    record = get_dataset(db, dataset_id, user_id=uid)
    active = get_active_dataset_record(db, user_id=uid)
    return {
        "status": "success",
        "dataset": serialize(record, active.id if active else None),
        "preview": dataset_preview(db, dataset_id, limit=limit, user_id=uid),
    }


@router.post("/dataset/{dataset_id}/activate")
async def activate(
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> dict:
    user_id = current_user.id if current_user else None
    record = activate_dataset(db, dataset_id, user_id=user_id)
    return {"status": "success", "dataset": serialize(record, record.id)}


@router.get("/dataset/{dataset_id}/download")
async def download(
    dataset_id: int,
    cleaned: bool = Query(default=True),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> FileResponse:
    record = get_dataset(
        db, dataset_id, user_id=current_user.id if current_user else None
    )
    filename = record.cleaned_filename if cleaned else record.stored_filename
    suffix = "cleaned" if cleaned else "original"
    try:
        download_path = ensure_local_file(
            DATA_DIR / filename, settings.supabase_dataset_bucket, filename
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Dataset file is unavailable.") from exc
    return FileResponse(
        path=download_path,
        filename=f"{record.name}_{suffix}.csv",
        media_type="text/csv",
    )


@router.delete("/dataset/{dataset_id}")
async def remove_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> dict:
    result = delete_dataset(
        db, dataset_id, user_id=current_user.id if current_user else None
    )
    return {"status": "success", **result}


def record_cleaned_path(record):
    return DATA_DIR / record.cleaned_filename
