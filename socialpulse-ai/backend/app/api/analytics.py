from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.analytics.dataset_analytics import (
    anomalies,
    content_performance,
    engagement,
    hashtags_intelligence,
    insights,
    overview,
    platforms_comparison,
    post_detail,
    posts_explorer,
    sentiment,
    time_analysis,
    topics_clustering,
    trends,
)
from app.core.database import get_db
from app.models.user import User
from app.schemas.dataset import AssistantQueryRequest
from app.services.assistant_service import answer_assistant_query
from app.services.auth_service import get_optional_user

router = APIRouter(prefix="/api", tags=["analytics"])


@router.get("/overview")
async def get_overview(
    dataset_id: int | None = Query(default=None),
    platform: str | None = Query(default=None),
    sentiment_filter: str | None = Query(default=None, alias="sentiment"),
    topic: str | None = Query(default=None),
    hashtag: str | None = Query(default=None),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    search: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> dict:
    return {
        "status": "success",
        "data": overview(
            db=db,
            dataset_id=dataset_id,
            user_id=current_user.id if current_user else None,
            platform=platform,
            sentiment=sentiment_filter,
            topic=topic,
            hashtag=hashtag,
            start_date=start_date,
            end_date=end_date,
            search=search,
        ),
    }


@router.get("/trends")
async def get_trends(
    dataset_id: int | None = Query(default=None),
    platform: str | None = Query(default=None),
    sentiment_filter: str | None = Query(default=None, alias="sentiment"),
    topic: str | None = Query(default=None),
    hashtag: str | None = Query(default=None),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    search: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> dict:
    return {
        "status": "success",
        "data": trends(
            db=db,
            dataset_id=dataset_id,
            user_id=current_user.id if current_user else None,
            platform=platform,
            sentiment=sentiment_filter,
            topic=topic,
            hashtag=hashtag,
            start_date=start_date,
            end_date=end_date,
            search=search,
        ),
    }


@router.get("/sentiment")
async def get_sentiment(
    dataset_id: int | None = Query(default=None),
    platform: str | None = Query(default=None),
    sentiment_filter: str | None = Query(default=None, alias="sentiment"),
    topic: str | None = Query(default=None),
    hashtag: str | None = Query(default=None),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    search: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> dict:
    return {
        "status": "success",
        "data": sentiment(
            db=db,
            dataset_id=dataset_id,
            user_id=current_user.id if current_user else None,
            platform=platform,
            sentiment_filter=sentiment_filter,
            topic=topic,
            hashtag=hashtag,
            start_date=start_date,
            end_date=end_date,
            search=search,
        ),
    }


@router.get("/engagement")
async def get_engagement(
    dataset_id: int | None = Query(default=None),
    platform: str | None = Query(default=None),
    sentiment_filter: str | None = Query(default=None, alias="sentiment"),
    topic: str | None = Query(default=None),
    hashtag: str | None = Query(default=None),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    search: str | None = Query(default=None),
    sort_by: str = Query(default="total_engagement"),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> dict:
    return {
        "status": "success",
        "data": engagement(
            db=db,
            dataset_id=dataset_id,
            user_id=current_user.id if current_user else None,
            platform=platform,
            sentiment_filter=sentiment_filter,
            topic=topic,
            hashtag=hashtag,
            start_date=start_date,
            end_date=end_date,
            search=search,
            sort_by=sort_by,
            limit=limit,
        ),
    }


@router.get("/platforms")
async def get_platforms(
    dataset_id: int | None = Query(default=None),
    platforms: str | None = Query(default=None),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> dict:
    res = platforms_comparison(
        db=db,
        dataset_id=dataset_id,
        user_id=current_user.id if current_user else None,
        selected_platforms=platforms,
        start_date=start_date,
        end_date=end_date,
    )
    return {"status": "success", "data": res["platforms"], "meta": res["meta"]}


@router.get("/insights")
async def get_insights(
    dataset_id: int | None = Query(default=None),
    platform: str | None = Query(default=None),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> dict:
    res = insights(
        db=db,
        dataset_id=dataset_id,
        user_id=current_user.id if current_user else None,
        platform=platform,
        start_date=start_date,
        end_date=end_date,
    )
    return {"status": "success", **res}


@router.get("/hashtags")
async def get_hashtags(
    dataset_id: int | None = Query(default=None),
    platform: str | None = Query(default=None),
    sentiment_filter: str | None = Query(default=None, alias="sentiment"),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    search: str | None = Query(default=None),
    tag: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> dict:
    return {
        "status": "success",
        "data": hashtags_intelligence(
            db=db,
            dataset_id=dataset_id,
            user_id=current_user.id if current_user else None,
            platform=platform,
            sentiment_filter=sentiment_filter,
            start_date=start_date,
            end_date=end_date,
            search=search,
            selected_tag=tag,
        ),
    }


@router.get("/content-performance")
async def get_content_performance(
    dataset_id: int | None = Query(default=None),
    platform: str | None = Query(default=None),
    sentiment_filter: str | None = Query(default=None, alias="sentiment"),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    search: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> dict:
    return {
        "status": "success",
        "data": content_performance(
            db=db,
            dataset_id=dataset_id,
            user_id=current_user.id if current_user else None,
            platform=platform,
            sentiment_filter=sentiment_filter,
            start_date=start_date,
            end_date=end_date,
            search=search,
        ),
    }


@router.get("/topics")
async def get_topics(
    dataset_id: int | None = Query(default=None),
    platform: str | None = Query(default=None),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> dict:
    return {
        "status": "success",
        "data": topics_clustering(
            db=db,
            dataset_id=dataset_id,
            user_id=current_user.id if current_user else None,
            platform=platform,
            start_date=start_date,
            end_date=end_date,
        ),
    }


@router.get("/time-analysis")
async def get_time_analysis(
    dataset_id: int | None = Query(default=None),
    platform: str | None = Query(default=None),
    granularity: str = Query(default="daily"),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> dict:
    return {
        "status": "success",
        "data": time_analysis(
            db=db,
            dataset_id=dataset_id,
            user_id=current_user.id if current_user else None,
            platform=platform,
            granularity=granularity,
            start_date=start_date,
            end_date=end_date,
        ),
    }


@router.get("/anomalies")
async def get_anomalies(
    dataset_id: int | None = Query(default=None),
    platform: str | None = Query(default=None),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> dict:
    return {
        "status": "success",
        "data": anomalies(
            db=db,
            dataset_id=dataset_id,
            user_id=current_user.id if current_user else None,
            platform=platform,
            start_date=start_date,
            end_date=end_date,
        ),
    }


@router.get("/posts")
async def get_posts(
    dataset_id: int | None = Query(default=None),
    platform: str | None = Query(default=None),
    sentiment_filter: str | None = Query(default=None, alias="sentiment"),
    topic: str | None = Query(default=None),
    hashtag: str | None = Query(default=None),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    search: str | None = Query(default=None),
    sort_by: str = Query(default="total_engagement"),
    sort_dir: str = Query(default="desc"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> dict:
    return {
        "status": "success",
        "data": posts_explorer(
            db=db,
            dataset_id=dataset_id,
            user_id=current_user.id if current_user else None,
            platform=platform,
            sentiment_filter=sentiment_filter,
            topic=topic,
            hashtag=hashtag,
            start_date=start_date,
            end_date=end_date,
            search=search,
            sort_by=sort_by,
            sort_dir=sort_dir,
            page=page,
            page_size=page_size,
        ),
    }


@router.get("/posts/{post_id}")
async def get_post_detail(
    post_id: str,
    dataset_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> dict:
    return {
        "status": "success",
        "data": post_detail(
            post_id=post_id,
            db=db,
            dataset_id=dataset_id,
            user_id=current_user.id if current_user else None,
        ),
    }


@router.post("/assistant/query")
async def query_assistant(
    payload: AssistantQueryRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> dict:
    result = await answer_assistant_query(
        payload.question,
        db,
        dataset_id=payload.dataset_id,
        user_id=current_user.id if current_user else None,
    )
    return {"status": "success", "data": result}
