from fastapi import APIRouter, Depends, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.dataset_service import (
    activate_dataset,
    dataset_preview,
    get_cleaned_dataframe,
    get_dataset,
    list_datasets,
    upload_dataset,
)

router = APIRouter(prefix="/api", tags=["datasets"])


def serialize(record) -> dict:
    import json

    return {
        "id": record.id,
        "name": record.name,
        "original_filename": record.original_filename,
        "row_count": record.row_count,
        "cleaned_row_count": record.cleaned_row_count,
        "column_count": record.column_count,
        "duplicate_count": record.duplicate_count,
        "missing_value_count": record.missing_value_count,
        "column_mapping": json.loads(record.column_mapping_json),
        "is_active": record.is_active,
        "created_at": record.created_at,
    }


@router.post("/upload")
async def upload(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> dict:
    record = await upload_dataset(db, file)
    return {"status": "success", "dataset": serialize(record)}


@router.get("/datasets")
async def datasets(db: Session = Depends(get_db)) -> dict:
    records = list_datasets(db)
    return {"status": "success", "datasets": [serialize(record) for record in records]}


@router.get("/dataset")
async def active_dataset(db: Session = Depends(get_db)) -> dict:
    records = list_datasets(db)
    active = next((record for record in records if record.is_active), None)
    if active is None:
        return {"status": "success", "dataset": None}
    return {"status": "success", "dataset": serialize(active)}


@router.get("/dataset/{dataset_id}")
async def dataset_detail(dataset_id: int, db: Session = Depends(get_db)) -> dict:
    record = get_dataset(db, dataset_id)
    return {"status": "success", "dataset": serialize(record), "preview": dataset_preview(db, dataset_id)}


@router.post("/dataset/{dataset_id}/activate")
async def activate(dataset_id: int, db: Session = Depends(get_db)) -> dict:
    record = activate_dataset(db, dataset_id)
    return {"status": "success", "dataset": serialize(record)}


@router.get("/dataset/{dataset_id}/download")
async def download(dataset_id: int, db: Session = Depends(get_db)) -> FileResponse:
    record = get_dataset(db, dataset_id)
    download_path = record_cleaned_path(record)
    return FileResponse(
        path=download_path,
        filename=f"{record.name}_cleaned.csv",
        media_type="text/csv",
    )


def record_cleaned_path(record):
    from app.services.dataset_service import DATA_DIR
    return DATA_DIR / record.cleaned_filename
