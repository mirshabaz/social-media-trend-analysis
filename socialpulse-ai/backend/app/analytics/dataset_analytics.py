from pathlib import Path
from typing import Any

import pandas as pd

DATASET_PATH = Path(__file__).resolve().parents[4] / "dataset" / "social_media_data.csv"


def load_active_dataframe() -> pd.DataFrame:
    if DATASET_PATH.exists():
        df = pd.read_csv(DATASET_PATH)
    else:
        df = pd.DataFrame()
    if df.empty:
        return df

    for column in ("likes", "shares", "comments"):
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0)
        else:
            df[column] = 0
    df["total_engagement"] = df["likes"] + df["shares"] + df["comments"]
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    return df


def overview() -> dict[str, Any]:
    df = load_active_dataframe()
    if df.empty:
        return {"kpis": {}, "activity": [], "platforms": [], "topics": [], "sentiment": []}

    sentiment_col = "sentiment" if "sentiment" in df.columns else None
    sentiment_counts = (
        df[sentiment_col].value_counts().to_dict()
        if sentiment_col
        else {}
    )
    sentiment_total = sum(sentiment_counts.values()) or 1

    activity = []
    if "timestamp" in df.columns:
        dates = (
            df.dropna(subset=["timestamp"])
            .groupby(df.dropna(subset=["timestamp"])["timestamp"].dt.date)
            .agg(posts=("post_id", "size"), engagement=("total_engagement", "sum"))
        )
        activity = [
            {"date": str(index), "posts": int(row.posts), "engagement": int(row.engagement)}
            for index, row in dates.reset_index().iterrows()
        ]

    platforms = []
    if "platform" in df.columns:
        platform_df = df.groupby("platform").agg(
            posts=("post_id", "size"),
            engagement=("total_engagement", "sum"),
            likes=("likes", "sum"),
            shares=("shares", "sum"),
            comments=("comments", "sum"),
        )
        platforms = [
            {
                "name": str(index),
                "posts": int(row.posts),
                "engagement": int(row.engagement),
                "likes": int(row.likes),
                "shares": int(row.shares),
                "comments": int(row.comments),
            }
            for index, row in platform_df.reset_index().iterrows()
        ]

    topics = []
    if "topic" in df.columns:
        topic_df = df.groupby("topic").agg(
            posts=("post_id", "size"),
            engagement=("total_engagement", "sum"),
        ).sort_values("posts", ascending=False).head(10)
        topics = [
            {"name": str(index), "posts": int(row.posts), "engagement": int(row.engagement)}
            for index, row in topic_df.reset_index().iterrows()
        ]

    hashtags = []
    if "hashtags" in df.columns:
        counts: dict[str, int] = {}
        for value in df["hashtags"].dropna():
            for tag in str(value).replace(",", " ").split():
                clean_tag = tag.strip().lower()
                if clean_tag:
                    counts[clean_tag] = counts.get(clean_tag, 0) + 1
        hashtags = [
            {"name": name if name.startswith("#") else f"#{name}", "count": count}
            for name, count in sorted(counts.items(), key=lambda item: item[1], reverse=True)[:10]
        ]

    return {
        "kpis": {
            "total_posts": int(len(df)),
            "total_engagement": int(df["total_engagement"].sum()),
            "total_likes": int(df["likes"].sum()),
            "total_comments": int(df["comments"].sum()),
            "total_shares": int(df["shares"].sum()),
            "avg_engagement": round(float(df["total_engagement"].mean()), 2),
            "positive_sentiment": round(sentiment_counts.get("Positive", 0) / sentiment_total * 100, 1),
            "negative_sentiment": round(sentiment_counts.get("Negative", 0) / sentiment_total * 100, 1),
        },
        "activity": activity,
        "platforms": platforms,
        "topics": topics,
        "hashtags": hashtags,
        "sentiment": [
            {"name": name, "value": int(value)}
            for name, value in sentiment_counts.items()
        ],
    }


def trends() -> dict[str, Any]:
    data = overview()
    return {
        "topics": data["topics"],
        "hashtags": data["hashtags"],
    }


def sentiment() -> dict[str, Any]:
    df = load_active_dataframe()
    if df.empty or "sentiment" not in df.columns:
        return {"distribution": [], "by_platform": [], "by_topic": []}

    distribution = [
        {"name": name, "value": int(count)}
        for name, count in df["sentiment"].value_counts().items()
    ]

    by_platform = []
    if "platform" in df.columns:
        table = pd.crosstab(df["platform"], df["sentiment"], normalize="index").round(4)
        by_platform = [
            {"name": str(platform), **{str(sentiment): round(float(value) * 100, 1) for sentiment, value in row.items()}}
            for platform, row in table.iterrows()
        ]

    by_topic = []
    if "topic" in df.columns:
        table = pd.crosstab(df["topic"], df["sentiment"], normalize="index").round(4)
        by_topic = [
            {"name": str(topic), **{str(sentiment): round(float(value) * 100, 1) for sentiment, value in row.items()}}
            for topic, row in table.iterrows()
        ]

    return {
        "distribution": distribution,
        "by_platform": by_platform,
        "by_topic": by_topic,
    }


def engagement() -> dict[str, Any]:
    df = load_active_dataframe()
    if df.empty:
        return {"top_posts": [], "platforms": [], "topics": []}

    top_posts = []
    if "post_content" in df.columns:
        top_posts = [
            {
                "post_id": str(row.get("post_id", "")),
                "content": str(row.get("post_content", ""))[:220],
                "platform": str(row.get("platform", "Unknown")),
                "likes": int(row["likes"]),
                "shares": int(row["shares"]),
                "comments": int(row["comments"]),
                "engagement": int(row["total_engagement"]),
            }
            for _, row in df.nlargest(10, "total_engagement").iterrows()
        ]

    platforms = []
    if "platform" in df.columns:
        platform_table = df.groupby("platform").agg(
            average=("total_engagement", "mean"),
            total=("total_engagement", "sum"),
        )
        platforms = [
            {
                "name": str(index),
                "average": round(float(row.average), 2),
                "total": int(row.total),
            }
            for index, row in platform_table.reset_index().iterrows()
        ]

    topics = []
    if "topic" in df.columns:
        topic_table = df.groupby("topic").agg(
            average=("total_engagement", "mean"),
            total=("total_engagement", "sum"),
        ).sort_values("average", ascending=False).head(10)
        topics = [
            {"name": str(index), "average": round(float(row.average), 2), "total": int(row.total)}
            for index, row in topic_table.reset_index().iterrows()
        ]

    return {"top_posts": top_posts, "platforms": platforms, "topics": topics}
