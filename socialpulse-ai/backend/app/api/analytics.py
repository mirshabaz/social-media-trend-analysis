from fastapi import APIRouter

from app.analytics.dataset_analytics import engagement, overview, sentiment, trends

router = APIRouter(prefix="/api", tags=["analytics"])


@router.get("/overview")
async def get_overview() -> dict:
    return {"status": "success", "data": overview()}


@router.get("/trends")
async def get_trends() -> dict:
    return {"status": "success", "data": trends()}


@router.get("/sentiment")
async def get_sentiment() -> dict:
    return {"status": "success", "data": sentiment()}


@router.get("/engagement")
async def get_engagement() -> dict:
    return {"status": "success", "data": engagement()}


@router.get("/platforms")
async def get_platforms() -> dict:
    return {"status": "success", "data": overview()["platforms"]}


@router.get("/insights")
async def get_insights() -> dict:
    data = overview()
    kpis = data["kpis"]
    top_topic = data["topics"][0]["name"] if data["topics"] else "Not available"
    top_platform = (
        max(data["platforms"], key=lambda item: item["engagement"])["name"]
        if data["platforms"]
        else "Not available"
    )
    top_hashtag = data["hashtags"][0]["name"] if data["hashtags"] else "Not available"
    insights = [
        f"The most discussed topic is {top_topic}.",
        f"{top_platform} has the highest recorded platform engagement.",
        f"The most frequent hashtag is {top_hashtag}.",
        f"Positive sentiment represents {kpis.get('positive_sentiment', 0)}% of labelled posts.",
        f"The dataset contains {kpis.get('total_posts', 0):,} cleaned or source posts.",
    ]
    return {"status": "success", "insights": insights, "data": data}
