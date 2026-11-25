import json

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy import or_, update
from sqlalchemy.orm import Session

from app.analytics.dataset_analytics import (
    hashtags_intelligence,
    load_active_dataframe_with_record,
    overview,
    posts_explorer,
)
from app.core.database import get_db
from app.core.config import settings
from app.models.system import ActivityRecord, NotificationRecord
from app.models.user import User
from app.schemas.dataset import ReportGenerateRequest
from app.services.auth_service import get_optional_user
from app.services.dataset_service import list_datasets
from app.services.cloud_storage import ensure_local_file
from app.services.report_service import (
    REPORTS_DIR,
    delete_report,
    generate_report,
    get_report,
    list_reports,
)

router = APIRouter(prefix="/api", tags=["system"])

SEARCHABLE_MODULES = [
    {"label": "Overview Dashboard", "path": "/", "category": "Navigation", "keywords": "overview kpis dashboard summary"},
    {"label": "Social Media Trend Explorer", "path": "/trending-topics", "category": "Analytics", "keywords": "trends emerging topics velocity"},
    {"label": "Sentiment Intelligence", "path": "/sentiment", "category": "Analytics", "keywords": "sentiment positive negative neutral emotion"},
    {"label": "Engagement Analytics", "path": "/engagement", "category": "Analytics", "keywords": "engagement likes shares comments viral"},
    {"label": "Platform Comparison", "path": "/platforms", "category": "Analytics", "keywords": "instagram linkedin twitter facebook compare"},
    {"label": "Hashtag Intelligence", "path": "/hashtags", "category": "Analytics", "keywords": "hashtags tags frequency co-occurrence"},
    {"label": "Topic Clustering (ML)", "path": "/topic-clustering", "category": "Advanced ML", "keywords": "clusters kmeans tfidf nlp topics"},
    {"label": "Content Performance", "path": "/viral-content", "category": "Analytics", "keywords": "content posts best worst length"},
    {"label": "Time & Posting Window Analysis", "path": "/posting-time", "category": "Advanced ML", "keywords": "time hourly weekday heatmap schedule"},
    {"label": "Anomaly Detection", "path": "/anomalies", "category": "Advanced ML", "keywords": "anomalies outliers zscore isolation forest spikes"},
    {"label": "AI Insights Center", "path": "/ai-insights", "category": "AI Intelligence", "keywords": "ai insights recommendations observations"},
    {"label": "AI Analytics Assistant", "path": "/assistant", "category": "AI Intelligence", "keywords": "assistant chat ask questions"},
    {"label": "Dataset Management Center", "path": "/datasets", "category": "Data", "keywords": "upload csv clean mapping preview datasets"},
    {"label": "Report Generation Center", "path": "/reports", "category": "Exports", "keywords": "reports pdf csv excel xlsx json download"},
    {"label": "Account & Security Settings", "path": "/profile", "category": "Account", "keywords": "profile password auth account"},
]


def _serialize_report(record) -> dict:
    return {
        "id": record.id,
        "dataset_id": record.dataset_id,
        "dataset_name": record.dataset_name,
        "report_type": record.report_type,
        "format": record.format,
        "filename": record.filename,
        "title": record.title,
        "summary": json.loads(record.summary_json or "{}"),
        "created_at": record.created_at,
    }


@router.get("/reports")
async def get_reports(
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> dict:
    records = list_reports(db, user_id=current_user.id if current_user else None)
    return {"status": "success", "reports": [_serialize_report(r) for r in records]}


@router.post("/reports/generate")
async def create_report(
    payload: ReportGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> dict:
    record = generate_report(
        db,
        report_type=payload.report_type,
        fmt=payload.format,
        dataset_id=payload.dataset_id,
        user_id=current_user.id if current_user else None,
        platform=payload.platform,
        start_date=payload.start_date,
        end_date=payload.end_date,
        title=payload.title,
    )
    return {"status": "success", "report": _serialize_report(record)}


@router.get("/reports/{report_id}/download")
async def download_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> FileResponse:
    record = get_report(db, report_id, user_id=current_user.id if current_user else None)
    try:
        path = ensure_local_file(
            REPORTS_DIR / record.filename, settings.supabase_report_bucket, record.filename
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Generated report file is unavailable.") from exc
    if not path.exists():
        raise HTTPException(status_code=404, detail="Generated report file missing on disk.")

    media_types = {
        "pdf": "application/pdf",
        "csv": "text/csv",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "json": "application/json",
    }
    safe_title = "".join(ch if ch.isalnum() or ch in "-_ " else "_" for ch in record.title).strip().replace(" ", "_")
    return FileResponse(
        path=path,
        filename=f"{safe_title or 'socialpulse_report'}.{record.format}",
        media_type=media_types.get(record.format, "application/octet-stream"),
    )


@router.delete("/reports/{report_id}")
async def remove_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> dict:
    res = delete_report(db, report_id, user_id=current_user.id if current_user else None)
    return {"status": "success", **res}


@router.get("/activity")
async def get_activity(
    limit: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> dict:
    uid = current_user.id if current_user else None
    query = db.query(ActivityRecord)
    if uid is None:
        query = query.filter(ActivityRecord.user_id.is_(None))
    else:
        query = query.filter(or_(ActivityRecord.user_id.is_(None), ActivityRecord.user_id == uid))
    rows = query.order_by(ActivityRecord.created_at.desc()).limit(limit).all()
    return {
        "status": "success",
        "activity": [
            {
                "id": r.id,
                "action": r.action,
                "target_type": r.target_type,
                "target_name": r.target_name,
                "details": r.details,
                "created_at": r.created_at,
            }
            for r in rows
        ],
    }


@router.get("/notifications")
async def get_notifications(
    limit: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> dict:
    uid = current_user.id if current_user else None
    query = db.query(NotificationRecord)
    if uid is None:
        query = query.filter(NotificationRecord.user_id.is_(None))
    else:
        query = query.filter(or_(NotificationRecord.user_id.is_(None), NotificationRecord.user_id == uid))
    rows = query.order_by(NotificationRecord.created_at.desc()).limit(limit).all()
    unread_count = sum(1 for r in rows if not r.is_read)
    return {
        "status": "success",
        "unread_count": unread_count,
        "notifications": [
            {
                "id": r.id,
                "title": r.title,
                "message": r.message,
                "category": r.category,
                "severity": r.severity,
                "is_read": r.is_read,
                "meta": json.loads(r.meta_json or "{}"),
                "created_at": r.created_at,
            }
            for r in rows
        ],
    }


@router.post("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> dict:
    uid = current_user.id if current_user else None
    row = db.query(NotificationRecord).filter(NotificationRecord.id == notification_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Notification not found.")
    if row.user_id is not None and row.user_id != uid:
        raise HTTPException(status_code=403, detail="Access denied.")
    row.is_read = True
    db.commit()
    return {"status": "success", "id": notification_id}


@router.post("/notifications/read-all")
async def mark_all_notifications_read(
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> dict:
    uid = current_user.id if current_user else None
    stmt = update(NotificationRecord).values(is_read=True)
    if uid is None:
        stmt = stmt.where(NotificationRecord.user_id.is_(None))
    else:
        stmt = stmt.where(or_(NotificationRecord.user_id.is_(None), NotificationRecord.user_id == uid))
    db.execute(stmt)
    db.commit()
    return {"status": "success"}


@router.get("/search")
async def global_search(
    q: str = Query(default="", max_length=200),
    dataset_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> dict:
    uid = current_user.id if current_user else None
    term = q.strip().lower()
    if not term:
        return {
            "status": "success",
            "results": {
                "modules": SEARCHABLE_MODULES[:6],
                "topics": [],
                "hashtags": [],
                "platforms": [],
                "datasets": [],
                "posts": [],
            },
        }

    ov = overview(db=db, dataset_id=dataset_id, user_id=uid)
    tags = hashtags_intelligence(db=db, dataset_id=dataset_id, user_id=uid, search=term)["hashtags"][:6]
    matching_posts = posts_explorer(
        db=db, dataset_id=dataset_id, user_id=uid, search=term, page=1, page_size=6
    )["posts"]
    all_datasets = list_datasets(db, user_id=uid)

    modules = [
        m
        for m in SEARCHABLE_MODULES
        if term in m["label"].lower() or term in m["keywords"].lower()
    ][:6]

    topics = [t for t in ov["topics"] if term in t["name"].lower()][:6]
    platforms = [p for p in ov["platforms"] if term in p["name"].lower()][:5]
    datasets = [
        {"id": d.id, "name": d.name, "cleaned_row_count": d.cleaned_row_count, "is_active": d.is_active}
        for d in all_datasets
        if term in d.name.lower() or term in d.original_filename.lower()
    ][:5]

    return {
        "status": "success",
        "results": {
            "modules": modules,
            "topics": topics,
            "hashtags": tags,
            "platforms": platforms,
            "datasets": datasets,
            "posts": matching_posts,
        },
    }

