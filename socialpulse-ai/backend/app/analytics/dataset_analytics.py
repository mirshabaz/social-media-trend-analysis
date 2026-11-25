from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from fastapi import HTTPException
from sklearn.ensemble import IsolationForest
from sqlalchemy.orm import Session

from app.core.config import REPO_ROOT
from app.core.database import SessionLocal
from app.models.dataset import DatasetRecord
from app.services.dataset_service import get_active_dataset_record, get_cleaned_dataframe
from app.services.nlp_service import (
    compute_topic_clusters,
    enrich_sentiment_columns,
    extract_hashtags_from_row,
    extract_top_keywords,
    tokenize_meaningful_words,
)

DATASET_PATH = REPO_ROOT / "dataset" / "social_media_data.csv"

SENTIMENT_DISCLAIMER = (
    "Automated sentiment and emotion indicators use NLP polarity and lexicon heuristics "
    "when explicit labels are absent; predictions may be imperfect on sarcasm or domain slang."
)


def _normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    work = df.copy()

    for col in ("likes", "shares", "comments"):
        if col in work.columns:
            work[col] = pd.to_numeric(work[col], errors="coerce").fillna(0).clip(lower=0).astype(int)
        else:
            work[col] = 0
    work["total_engagement"] = work["likes"] + work["shares"] + work["comments"]

    if "post_id" not in work.columns:
        work["post_id"] = [f"POST_{i + 1:05d}" for i in range(len(work))]
    else:
        work["post_id"] = work["post_id"].fillna("").astype(str)

    if "post_content" not in work.columns:
        work["post_content"] = ""
    else:
        work["post_content"] = work["post_content"].fillna("").astype(str)

    if "char_length" not in work.columns:
        work["char_length"] = work["post_content"].str.len()

    for col, fallback in (
        ("platform", "Unknown"),
        ("author", "Unknown"),
        ("topic", "Uncategorized"),
    ):
        if col not in work.columns:
            work[col] = fallback
        else:
            work[col] = (
                work[col]
                .fillna(fallback)
                .astype(str)
                .str.strip()
                .replace({"": fallback, "nan": fallback, "None": fallback})
            )

    if "hashtags" not in work.columns:
        work["hashtags"] = ""
    else:
        work["hashtags"] = work["hashtags"].astype("string").fillna("")

    work["_tags_list"] = [
        extract_hashtags_from_row(h, c)
        for h, c in zip(work["hashtags"], work["post_content"])
    ]
    work["hashtag_count"] = [len(tags) for tags in work["_tags_list"]]

    if "timestamp" in work.columns:
        work["timestamp"] = pd.to_datetime(work["timestamp"], errors="coerce")

    if "impressions" in work.columns:
        work["impressions"] = (
            pd.to_numeric(work["impressions"], errors="coerce").fillna(0).clip(lower=0)
        )

    if "sentiment_polarity" not in work.columns or "detected_emotion" not in work.columns:
        work = enrich_sentiment_columns(work)
    else:
        work["sentiment"] = work["sentiment"].fillna("Neutral").astype(str)
        work["sentiment_polarity"] = pd.to_numeric(
            work["sentiment_polarity"], errors="coerce"
        ).fillna(0.0)
        work["detected_emotion"] = work["detected_emotion"].fillna("Neutral / Informative").astype(str)
        if "sentiment_source" not in work.columns:
            work["sentiment_source"] = "dataset_label"

    return work


def load_active_dataframe_with_record(
    db: Session | None = None,
    dataset_id: int | None = None,
    user_id: int | None = None,
) -> tuple[pd.DataFrame, DatasetRecord | None]:
    own_session = False
    if db is None:
        db = SessionLocal()
        own_session = True

    try:
        record = get_active_dataset_record(db, dataset_id=dataset_id, user_id=user_id)
        if record is not None:
            raw_df = get_cleaned_dataframe(record)
            return _normalize_dataframe(raw_df), record
        if DATASET_PATH.exists():
            return _normalize_dataframe(pd.read_csv(DATASET_PATH)), None
        return pd.DataFrame(), None
    finally:
        if own_session:
            db.close()


def load_active_dataframe(
    db: Session | None = None,
    dataset_id: int | None = None,
    user_id: int | None = None,
) -> pd.DataFrame:
    df, _ = load_active_dataframe_with_record(db=db, dataset_id=dataset_id, user_id=user_id)
    return df


def apply_filters(
    df: pd.DataFrame,
    *,
    platform: str | None = None,
    sentiment: str | None = None,
    topic: str | None = None,
    hashtag: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    search: str | None = None,
) -> pd.DataFrame:
    if df.empty:
        return df

    filtered = df.copy()

    if platform and platform.strip() and platform.strip().lower() != "all":
        selected = {p.strip().lower() for p in platform.split(",") if p.strip()}
        if selected:
            filtered = filtered[filtered["platform"].str.lower().isin(selected)]

    if sentiment and sentiment.strip() and sentiment.strip().lower() != "all":
        selected = {s.strip().lower() for s in sentiment.split(",") if s.strip()}
        if selected:
            filtered = filtered[filtered["sentiment"].str.lower().isin(selected)]

    if topic and topic.strip() and topic.strip().lower() != "all":
        selected = {t.strip().lower() for t in topic.split(",") if t.strip()}
        if selected:
            filtered = filtered[filtered["topic"].str.lower().isin(selected)]

    if hashtag and hashtag.strip():
        target = hashtag.strip().lower()
        if not target.startswith("#"):
            target = f"#{target}"
        filtered = filtered[filtered["_tags_list"].apply(lambda tags: target in tags)]

    if (start_date or end_date) and "timestamp" in filtered.columns:
        ts_dates = filtered["timestamp"].dt.date
        if start_date:
            try:
                start_d = pd.to_datetime(start_date).date()
                filtered = filtered[ts_dates.notna() & (ts_dates >= start_d)]
                ts_dates = filtered["timestamp"].dt.date
            except Exception:
                pass
        if end_date:
            try:
                end_d = pd.to_datetime(end_date).date()
                filtered = filtered[ts_dates.notna() & (ts_dates <= end_d)]
            except Exception:
                pass

    if search and search.strip():
        q = search.strip().lower()
        mask = (
            filtered["post_content"].str.lower().str.contains(q, regex=False, na=False)
            | filtered["topic"].str.lower().str.contains(q, regex=False, na=False)
            | filtered["hashtags"].str.lower().str.contains(q, regex=False, na=False)
            | filtered["platform"].str.lower().str.contains(q, regex=False, na=False)
            | filtered["author"].str.lower().str.contains(q, regex=False, na=False)
        )
        filtered = filtered[mask]

    return filtered


def _build_meta(
    full_df: pd.DataFrame,
    filtered_df: pd.DataFrame,
    record: DatasetRecord | None,
) -> dict[str, Any]:
    date_min = None
    date_max = None
    if not full_df.empty and "timestamp" in full_df.columns:
        valid_ts = full_df["timestamp"].dropna()
        if not valid_ts.empty:
            date_min = str(valid_ts.min().date())
            date_max = str(valid_ts.max().date())

    has_denom = bool(
        not full_df.empty
        and "impressions" in full_df.columns
        and (full_df["impressions"] > 0).any()
    )

    return {
        "dataset_id": record.id if record else None,
        "dataset_name": record.name if record else "SocialPulse Benchmark Dataset",
        "total_rows_unfiltered": int(len(full_df)),
        "filtered_rows": int(len(filtered_df)),
        "date_min": date_min,
        "date_max": date_max,
        "available_platforms": sorted(full_df["platform"].dropna().unique().tolist())
        if not full_df.empty
        else [],
        "available_topics": sorted(full_df["topic"].dropna().unique().tolist())
        if not full_df.empty
        else [],
        "has_engagement_denominator": has_denom,
        "engagement_rate_basis": "Total engagement / impressions (%)" if has_denom else None,
        "sentiment_disclaimer": SENTIMENT_DISCLAIMER,
    }


def _compute_hashtag_stats(df: pd.DataFrame) -> list[dict[str, Any]]:
    if df.empty:
        return []

    tag_records: dict[str, dict[str, Any]] = {}
    cooccurrence: dict[str, Counter[str]] = {}

    for _, row in df.iterrows():
        tags = row["_tags_list"]
        if not tags:
            continue
        eng = int(row["total_engagement"])
        likes = int(row["likes"])
        shares = int(row["shares"])
        comments = int(row["comments"])
        sent = str(row["sentiment"])
        plat = str(row["platform"])

        for tag in tags:
            entry = tag_records.setdefault(
                tag,
                {
                    "name": tag,
                    "count": 0,
                    "engagement": 0,
                    "likes": 0,
                    "shares": 0,
                    "comments": 0,
                    "Positive": 0,
                    "Negative": 0,
                    "Neutral": 0,
                    "platforms": Counter(),
                },
            )
            entry["count"] += 1
            entry["engagement"] += eng
            entry["likes"] += likes
            entry["shares"] += shares
            entry["comments"] += comments
            if sent in ("Positive", "Negative", "Neutral"):
                entry[sent] += 1
            entry["platforms"][plat] += 1

            co = cooccurrence.setdefault(tag, Counter())
            for other in tags:
                if other != tag:
                    co[other] += 1

    rows = []
    for tag, item in tag_records.items():
        cnt = item["count"] or 1
        top_plat = item["platforms"].most_common(1)[0][0] if item["platforms"] else "Unknown"
        related = [
            {"name": rel_tag, "co_occurrences": rel_cnt}
            for rel_tag, rel_cnt in cooccurrence.get(tag, Counter()).most_common(6)
        ]
        rows.append(
            {
                "name": tag,
                "count": int(item["count"]),
                "engagement": int(item["engagement"]),
                "avg_engagement": round(item["engagement"] / cnt, 1),
                "likes": int(item["likes"]),
                "shares": int(item["shares"]),
                "comments": int(item["comments"]),
                "positive_pct": round(item["Positive"] / cnt * 100, 1),
                "negative_pct": round(item["Negative"] / cnt * 100, 1),
                "neutral_pct": round(item["Neutral"] / cnt * 100, 1),
                "top_platform": top_plat,
                "related_hashtags": related,
            }
        )

    return sorted(rows, key=lambda x: (x["count"], x["engagement"]), reverse=True)


def _compute_topic_growth(df: pd.DataFrame) -> tuple[dict[str, float | None], bool]:
    if df.empty or "timestamp" not in df.columns:
        return {}, True
    valid = df.dropna(subset=["timestamp"]).sort_values("timestamp")
    if len(valid) < 10 or valid["timestamp"].dt.date.nunique() < 2:
        return {}, True

    midpoint = valid["timestamp"].min() + (valid["timestamp"].max() - valid["timestamp"].min()) / 2
    first_half = valid[valid["timestamp"] <= midpoint]
    second_half = valid[valid["timestamp"] > midpoint]
    if first_half.empty or second_half.empty:
        return {}, True

    c1 = first_half["topic"].value_counts()
    c2 = second_half["topic"].value_counts()
    growth: dict[str, float | None] = {}
    for topic in valid["topic"].unique():
        prev = int(c1.get(topic, 0))
        curr = int(c2.get(topic, 0))
        if prev == 0 and curr == 0:
            growth[str(topic)] = 0.0
        elif prev == 0:
            growth[str(topic)] = 100.0
        else:
            growth[str(topic)] = round((curr - prev) / prev * 100, 1)
    return growth, False


def _serialize_post_row(row: pd.Series) -> dict[str, Any]:
    ts = row.get("timestamp")
    ts_str = str(ts) if pd.notna(ts) else None
    return {
        "post_id": str(row.get("post_id", "")),
        "author": str(row.get("author", "Unknown")),
        "platform": str(row.get("platform", "Unknown")),
        "content": str(row.get("post_content", "")),
        "topic": str(row.get("topic", "Uncategorized")),
        "hashtags": row.get("_tags_list", []),
        "likes": int(row.get("likes", 0)),
        "shares": int(row.get("shares", 0)),
        "comments": int(row.get("comments", 0)),
        "engagement": int(row.get("total_engagement", 0)),
        "sentiment": str(row.get("sentiment", "Neutral")),
        "sentiment_polarity": float(row.get("sentiment_polarity", 0.0)),
        "detected_emotion": str(row.get("detected_emotion", "Neutral / Informative")),
        "sentiment_source": str(row.get("sentiment_source", "automated_nlp")),
        "char_length": int(row.get("char_length", 0)),
        "timestamp": ts_str,
    }


def overview(
    db: Session | None = None,
    *,
    dataset_id: int | None = None,
    user_id: int | None = None,
    platform: str | None = None,
    sentiment: str | None = None,
    topic: str | None = None,
    hashtag: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    search: str | None = None,
) -> dict[str, Any]:
    full_df, record = load_active_dataframe_with_record(db=db, dataset_id=dataset_id, user_id=user_id)
    df = apply_filters(
        full_df,
        platform=platform,
        sentiment=sentiment,
        topic=topic,
        hashtag=hashtag,
        start_date=start_date,
        end_date=end_date,
        search=search,
    )
    meta = _build_meta(full_df, df, record)

    if df.empty:
        return {
            "kpis": {
                "total_posts": 0,
                "total_engagement": 0,
                "total_likes": 0,
                "total_comments": 0,
                "total_shares": 0,
                "avg_engagement": 0,
                "median_engagement": 0,
                "engagement_rate": None,
                "engagement_rate_basis": meta["engagement_rate_basis"],
                "positive_sentiment": 0,
                "negative_sentiment": 0,
                "neutral_sentiment": 0,
                "top_platform": "N/A",
                "top_topic": "N/A",
                "top_hashtag": "N/A",
            },
            "activity": [],
            "platforms": [],
            "topics": [],
            "hashtags": [],
            "sentiment": [],
            "content_engagement": [],
            "meta": meta,
        }

    sentiment_counts = df["sentiment"].value_counts().to_dict()
    sentiment_total = sum(sentiment_counts.values()) or 1

    activity = []
    if "timestamp" in df.columns:
        ts_df = df.dropna(subset=["timestamp"]).copy()
        if not ts_df.empty:
            ts_df["date_only"] = ts_df["timestamp"].dt.date
            dates = (
                ts_df.groupby("date_only")
                .agg(
                    posts=("post_id", "size"),
                    engagement=("total_engagement", "sum"),
                    likes=("likes", "sum"),
                    shares=("shares", "sum"),
                    comments=("comments", "sum"),
                )
                .reset_index()
                .sort_values("date_only")
            )
            activity = [
                {
                    "date": str(row.date_only),
                    "posts": int(row.posts),
                    "engagement": int(row.engagement),
                    "likes": int(row.likes),
                    "shares": int(row.shares),
                    "comments": int(row.comments),
                }
                for _, row in dates.iterrows()
            ]

    platform_df = (
        df.groupby("platform")
        .agg(
            posts=("post_id", "size"),
            engagement=("total_engagement", "sum"),
            avg_engagement=("total_engagement", "mean"),
            likes=("likes", "sum"),
            shares=("shares", "sum"),
            comments=("comments", "sum"),
        )
        .reset_index()
        .sort_values("engagement", ascending=False)
    )
    platforms = []
    for _, row in platform_df.iterrows():
        sub = df[df["platform"] == row["platform"]]
        sub_sent = sub["sentiment"].value_counts()
        sub_tot = len(sub) or 1
        platforms.append(
            {
                "name": str(row["platform"]),
                "posts": int(row["posts"]),
                "engagement": int(row["engagement"]),
                "avg_engagement": round(float(row["avg_engagement"]), 1),
                "likes": int(row["likes"]),
                "shares": int(row["shares"]),
                "comments": int(row["comments"]),
                "positive_pct": round(sub_sent.get("Positive", 0) / sub_tot * 100, 1),
                "negative_pct": round(sub_sent.get("Negative", 0) / sub_tot * 100, 1),
                "neutral_pct": round(sub_sent.get("Neutral", 0) / sub_tot * 100, 1),
            }
        )

    total_posts = len(df)
    topic_df = (
        df.groupby("topic")
        .agg(
            posts=("post_id", "size"),
            engagement=("total_engagement", "sum"),
            avg_engagement=("total_engagement", "mean"),
        )
        .reset_index()
        .sort_values("posts", ascending=False)
        .head(12)
    )
    topics = [
        {
            "name": str(row["topic"]),
            "posts": int(row["posts"]),
            "engagement": int(row["engagement"]),
            "avg_engagement": round(float(row["avg_engagement"]), 1),
            "share_pct": round(int(row["posts"]) / total_posts * 100, 1),
        }
        for _, row in topic_df.iterrows()
    ]

    hashtags = _compute_hashtag_stats(df)[:15]

    buckets = pd.cut(
        df["char_length"],
        bins=[-1, 80, 160, 240, 100000],
        labels=["Short (<80)", "Medium (80-160)", "Long (161-240)", "Extended (240+)"],
    )
    bucket_df = (
        df.assign(length_bucket=buckets)
        .groupby("length_bucket", observed=False)
        .agg(
            posts=("post_id", "size"),
            avg_engagement=("total_engagement", "mean"),
            total_engagement=("total_engagement", "sum"),
        )
        .reset_index()
    )
    content_engagement = [
        {
            "bucket": str(row["length_bucket"]),
            "posts": int(row["posts"]),
            "avg_engagement": round(float(row["avg_engagement"]), 1) if pd.notna(row["avg_engagement"]) else 0.0,
            "total_engagement": int(row["total_engagement"]) if pd.notna(row["total_engagement"]) else 0,
        }
        for _, row in bucket_df.iterrows()
    ]

    engagement_rate = None
    if meta["has_engagement_denominator"]:
        valid_impr = df[df["impressions"] > 0]
        if not valid_impr.empty:
            total_impr = float(valid_impr["impressions"].sum())
            if total_impr > 0:
                engagement_rate = round(
                    float(valid_impr["total_engagement"].sum()) / total_impr * 100, 2
                )

    top_platform = platforms[0]["name"] if platforms else "N/A"
    top_topic = topics[0]["name"] if topics else "N/A"
    top_hashtag = hashtags[0]["name"] if hashtags else "N/A"

    return {
        "kpis": {
            "total_posts": int(total_posts),
            "total_engagement": int(df["total_engagement"].sum()),
            "total_likes": int(df["likes"].sum()),
            "total_comments": int(df["comments"].sum()),
            "total_shares": int(df["shares"].sum()),
            "avg_engagement": round(float(df["total_engagement"].mean()), 2),
            "median_engagement": round(float(df["total_engagement"].median()), 2),
            "engagement_rate": engagement_rate,
            "engagement_rate_basis": meta["engagement_rate_basis"],
            "positive_sentiment": round(sentiment_counts.get("Positive", 0) / sentiment_total * 100, 1),
            "negative_sentiment": round(sentiment_counts.get("Negative", 0) / sentiment_total * 100, 1),
            "neutral_sentiment": round(sentiment_counts.get("Neutral", 0) / sentiment_total * 100, 1),
            "positive_count": int(sentiment_counts.get("Positive", 0)),
            "negative_count": int(sentiment_counts.get("Negative", 0)),
            "neutral_count": int(sentiment_counts.get("Neutral", 0)),
            "top_platform": top_platform,
            "top_topic": top_topic,
            "top_hashtag": top_hashtag,
        },
        "activity": activity,
        "platforms": platforms,
        "topics": topics,
        "hashtags": hashtags,
        "sentiment": [
            {
                "name": name,
                "value": int(sentiment_counts.get(name, 0)),
                "percentage": round(sentiment_counts.get(name, 0) / sentiment_total * 100, 1),
            }
            for name in ("Positive", "Negative", "Neutral")
            if sentiment_counts.get(name, 0) > 0
        ],
        "content_engagement": content_engagement,
        "meta": meta,
    }


def trends(
    db: Session | None = None,
    *,
    dataset_id: int | None = None,
    user_id: int | None = None,
    platform: str | None = None,
    sentiment: str | None = None,
    topic: str | None = None,
    hashtag: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    search: str | None = None,
) -> dict[str, Any]:
    full_df, record = load_active_dataframe_with_record(db=db, dataset_id=dataset_id, user_id=user_id)
    df = apply_filters(
        full_df,
        platform=platform,
        sentiment=sentiment,
        topic=topic,
        hashtag=hashtag,
        start_date=start_date,
        end_date=end_date,
        search=search,
    )
    meta = _build_meta(full_df, df, record)
    if df.empty:
        return {
            "topics": [],
            "emerging_topics": [],
            "hashtags": [],
            "topic_timeline": [],
            "keywords": [],
            "insufficient_time_data": True,
            "historical_note": "No matching records to compute trends.",
            "meta": meta,
        }

    growth_map, insufficient_time = _compute_topic_growth(df)
    total_posts = len(df)
    grouped = (
        df.groupby("topic")
        .agg(
            posts=("post_id", "size"),
            engagement=("total_engagement", "sum"),
            avg_engagement=("total_engagement", "mean"),
        )
        .reset_index()
        .sort_values("posts", ascending=False)
    )

    topics_list = []
    for _, row in grouped.iterrows():
        tname = str(row["topic"])
        sub = df[df["topic"] == tname]
        sc = sub["sentiment"].value_counts()
        sub_tot = len(sub) or 1
        top_plat = sub["platform"].mode().iloc[0] if not sub["platform"].empty else "Unknown"
        g = growth_map.get(tname)
        direction = "stable"
        if g is not None:
            if g >= 10:
                direction = "rising"
            elif g <= -10:
                direction = "declining"
        topics_list.append(
            {
                "name": tname,
                "posts": int(row["posts"]),
                "share_pct": round(int(row["posts"]) / total_posts * 100, 1),
                "engagement": int(row["engagement"]),
                "avg_engagement": round(float(row["avg_engagement"]), 1),
                "growth_pct": g,
                "trend_direction": direction,
                "top_platform": str(top_plat),
                "positive_pct": round(sc.get("Positive", 0) / sub_tot * 100, 1),
                "negative_pct": round(sc.get("Negative", 0) / sub_tot * 100, 1),
            }
        )

    emerging = sorted(
        [t for t in topics_list if t["growth_pct"] is not None],
        key=lambda x: (x["growth_pct"] or 0, x["avg_engagement"]),
        reverse=True,
    )

    topic_timeline = []
    if "timestamp" in df.columns:
        ts_df = df.dropna(subset=["timestamp"]).copy()
        if not ts_df.empty:
            top_names = [t["name"] for t in topics_list[:6]]
            ts_df["period"] = ts_df["timestamp"].dt.to_period("W").astype(str)
            filtered_ts = ts_df[ts_df["topic"].isin(top_names)]
            if not filtered_ts.empty:
                pivot = (
                    filtered_ts.groupby(["period", "topic"])
                    .size()
                    .unstack(fill_value=0)
                    .reset_index()
                    .sort_values("period")
                )
                topic_timeline = pivot.to_dict(orient="records")

    return {
        "topics": topics_list,
        "emerging_topics": emerging[:10],
        "hashtags": _compute_hashtag_stats(df)[:30],
        "topic_timeline": topic_timeline,
        "keywords": extract_top_keywords(df, top_n=25),
        "insufficient_time_data": insufficient_time,
        "historical_note": (
            "Growth rates measure historical change between the first half and second half of the selected date span. "
            "Historical growth does not guarantee future performance."
        ),
        "meta": meta,
    }


def sentiment(
    db: Session | None = None,
    *,
    dataset_id: int | None = None,
    user_id: int | None = None,
    platform: str | None = None,
    sentiment_filter: str | None = None,
    topic: str | None = None,
    hashtag: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    search: str | None = None,
) -> dict[str, Any]:
    full_df, record = load_active_dataframe_with_record(db=db, dataset_id=dataset_id, user_id=user_id)
    df = apply_filters(
        full_df,
        platform=platform,
        sentiment=sentiment_filter,
        topic=topic,
        hashtag=hashtag,
        start_date=start_date,
        end_date=end_date,
        search=search,
    )
    meta = _build_meta(full_df, df, record)
    if df.empty:
        return {
            "distribution": [],
            "summary": {},
            "over_time": [],
            "by_platform": [],
            "by_topic": [],
            "most_positive_topics": [],
            "most_negative_topics": [],
            "emotions": [],
            "emotional_words": {"positive": [], "negative": []},
            "disclaimer": SENTIMENT_DISCLAIMER,
            "meta": meta,
        }

    counts = df["sentiment"].value_counts().to_dict()
    total = len(df) or 1
    distribution = [
        {
            "name": name,
            "value": int(counts.get(name, 0)),
            "percentage": round(counts.get(name, 0) / total * 100, 1),
        }
        for name in ("Positive", "Negative", "Neutral")
    ]

    over_time = []
    if "timestamp" in df.columns:
        ts_df = df.dropna(subset=["timestamp"]).copy()
        if not ts_df.empty:
            ts_df["period"] = ts_df["timestamp"].dt.to_period("W").astype(str)
            piv = ts_df.groupby(["period", "sentiment"]).size().unstack(fill_value=0)
            for col in ("Positive", "Negative", "Neutral"):
                if col not in piv.columns:
                    piv[col] = 0
            piv["avg_polarity"] = ts_df.groupby("period")["sentiment_polarity"].mean().round(3)
            over_time = [
                {
                    "period": str(period),
                    "Positive": int(row["Positive"]),
                    "Negative": int(row["Negative"]),
                    "Neutral": int(row["Neutral"]),
                    "avg_polarity": float(row["avg_polarity"]),
                }
                for period, row in piv.sort_index().iterrows()
            ]

    by_platform = []
    for plat, sub in df.groupby("platform"):
        sc = sub["sentiment"].value_counts()
        tot = len(sub) or 1
        by_platform.append(
            {
                "name": str(plat),
                "total_posts": int(len(sub)),
                "Positive": round(sc.get("Positive", 0) / tot * 100, 1),
                "Negative": round(sc.get("Negative", 0) / tot * 100, 1),
                "Neutral": round(sc.get("Neutral", 0) / tot * 100, 1),
                "avg_polarity": round(float(sub["sentiment_polarity"].mean()), 3),
            }
        )

    by_topic = []
    for top_name, sub in df.groupby("topic"):
        sc = sub["sentiment"].value_counts()
        tot = len(sub) or 1
        by_topic.append(
            {
                "name": str(top_name),
                "total_posts": int(len(sub)),
                "Positive": round(sc.get("Positive", 0) / tot * 100, 1),
                "Negative": round(sc.get("Negative", 0) / tot * 100, 1),
                "Neutral": round(sc.get("Neutral", 0) / tot * 100, 1),
                "avg_polarity": round(float(sub["sentiment_polarity"].mean()), 3),
            }
        )

    most_positive_topics = sorted(by_topic, key=lambda x: x["Positive"], reverse=True)[:5]
    most_negative_topics = sorted(by_topic, key=lambda x: x["Negative"], reverse=True)[:5]

    emotions = [
        {"name": str(name), "count": int(cnt), "percentage": round(cnt / total * 100, 1)}
        for name, cnt in df["detected_emotion"].value_counts().items()
    ]

    def _top_words_for(label: str) -> list[dict[str, Any]]:
        sub = df[df["sentiment"] == label]
        counter: Counter[str] = Counter()
        for text in sub["post_content"].dropna():
            counter.update(tokenize_meaningful_words(str(text)))
        return [{"word": w, "count": int(c)} for w, c in counter.most_common(20)]

    src_counts = df["sentiment_source"].value_counts().to_dict()

    return {
        "distribution": distribution,
        "summary": {
            "total_posts": int(len(df)),
            "positive_pct": round(counts.get("Positive", 0) / total * 100, 1),
            "negative_pct": round(counts.get("Negative", 0) / total * 100, 1),
            "neutral_pct": round(counts.get("Neutral", 0) / total * 100, 1),
            "avg_polarity": round(float(df["sentiment_polarity"].mean()), 3),
            "source_breakdown": {str(k): int(v) for k, v in src_counts.items()},
        },
        "over_time": over_time,
        "by_platform": by_platform,
        "by_topic": by_topic,
        "most_positive_topics": most_positive_topics,
        "most_negative_topics": most_negative_topics,
        "emotions": emotions,
        "emotional_words": {
            "positive": _top_words_for("Positive"),
            "negative": _top_words_for("Negative"),
        },
        "disclaimer": SENTIMENT_DISCLAIMER,
        "meta": meta,
    }


def engagement(
    db: Session | None = None,
    *,
    dataset_id: int | None = None,
    user_id: int | None = None,
    platform: str | None = None,
    sentiment_filter: str | None = None,
    topic: str | None = None,
    hashtag: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    search: str | None = None,
    sort_by: str = "total_engagement",
    limit: int = 20,
) -> dict[str, Any]:
    full_df, record = load_active_dataframe_with_record(db=db, dataset_id=dataset_id, user_id=user_id)
    df = apply_filters(
        full_df,
        platform=platform,
        sentiment=sentiment_filter,
        topic=topic,
        hashtag=hashtag,
        start_date=start_date,
        end_date=end_date,
        search=search,
    )
    meta = _build_meta(full_df, df, record)
    if df.empty:
        return {
            "summary": {},
            "top_posts": [],
            "lowest_posts": [],
            "trends": [],
            "platforms": [],
            "topics": [],
            "correlation": [],
            "meta": meta,
        }

    valid_sort = sort_by if sort_by in {"total_engagement", "likes", "shares", "comments"} else "total_engagement"
    top_df = df.sort_values(valid_sort, ascending=False).head(limit)
    low_df = df.sort_values(valid_sort, ascending=True).head(min(10, len(df)))

    top_posts = [_serialize_post_row(row) for _, row in top_df.iterrows()]
    lowest_posts = [_serialize_post_row(row) for _, row in low_df.iterrows()]

    trends_series = []
    if "timestamp" in df.columns:
        ts_df = df.dropna(subset=["timestamp"]).copy()
        if not ts_df.empty:
            ts_df["date_only"] = ts_df["timestamp"].dt.date
            grp = (
                ts_df.groupby("date_only")
                .agg(
                    posts=("post_id", "size"),
                    likes=("likes", "sum"),
                    shares=("shares", "sum"),
                    comments=("comments", "sum"),
                    total_engagement=("total_engagement", "sum"),
                    avg_engagement=("total_engagement", "mean"),
                )
                .reset_index()
                .sort_values("date_only")
            )
            trends_series = [
                {
                    "date": str(row.date_only),
                    "posts": int(row.posts),
                    "likes": int(row.likes),
                    "shares": int(row.shares),
                    "comments": int(row.comments),
                    "total_engagement": int(row.total_engagement),
                    "avg_engagement": round(float(row.avg_engagement), 1),
                }
                for _, row in grp.iterrows()
            ]

    plat_table = (
        df.groupby("platform")
        .agg(
            posts=("post_id", "size"),
            average=("total_engagement", "mean"),
            median=("total_engagement", "median"),
            total=("total_engagement", "sum"),
            avg_likes=("likes", "mean"),
            avg_shares=("shares", "mean"),
            avg_comments=("comments", "mean"),
        )
        .reset_index()
        .sort_values("average", ascending=False)
    )
    platforms = [
        {
            "name": str(row["platform"]),
            "posts": int(row["posts"]),
            "average": round(float(row["average"]), 2),
            "median": round(float(row["median"]), 1),
            "total": int(row["total"]),
            "avg_likes": round(float(row["avg_likes"]), 1),
            "avg_shares": round(float(row["avg_shares"]), 1),
            "avg_comments": round(float(row["avg_comments"]), 1),
        }
        for _, row in plat_table.iterrows()
    ]

    topic_table = (
        df.groupby("topic")
        .agg(
            posts=("post_id", "size"),
            average=("total_engagement", "mean"),
            total=("total_engagement", "sum"),
        )
        .reset_index()
        .sort_values("average", ascending=False)
        .head(12)
    )
    topics = [
        {
            "name": str(row["topic"]),
            "posts": int(row["posts"]),
            "average": round(float(row["average"]), 2),
            "total": int(row["total"]),
        }
        for _, row in topic_table.iterrows()
    ]

    corr_cols = ["likes", "shares", "comments", "total_engagement", "char_length", "hashtag_count"]
    corr_df = df[corr_cols].corr().fillna(0).round(2)
    correlation = [
        {"metric": str(idx), **{col: float(corr_df.loc[idx, col]) for col in corr_cols}}
        for idx in corr_df.index
    ]

    eng_rate = None
    if meta["has_engagement_denominator"]:
        valid_impr = df[df["impressions"] > 0]
        if not valid_impr.empty and valid_impr["impressions"].sum() > 0:
            eng_rate = round(
                float(valid_impr["total_engagement"].sum()) / float(valid_impr["impressions"].sum()) * 100,
                2,
            )

    return {
        "summary": {
            "total_likes": int(df["likes"].sum()),
            "total_shares": int(df["shares"].sum()),
            "total_comments": int(df["comments"].sum()),
            "total_engagement": int(df["total_engagement"].sum()),
            "avg_engagement": round(float(df["total_engagement"].mean()), 2),
            "median_engagement": round(float(df["total_engagement"].median()), 1),
            "p90_engagement": round(float(df["total_engagement"].quantile(0.9)), 1),
            "engagement_rate": eng_rate,
            "engagement_rate_basis": meta["engagement_rate_basis"],
        },
        "top_posts": top_posts,
        "lowest_posts": lowest_posts,
        "trends": trends_series,
        "platforms": platforms,
        "topics": topics,
        "correlation": correlation,
        "meta": meta,
    }


def platforms_comparison(
    db: Session | None = None,
    *,
    dataset_id: int | None = None,
    user_id: int | None = None,
    selected_platforms: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    full_df, record = load_active_dataframe_with_record(db=db, dataset_id=dataset_id, user_id=user_id)
    df = apply_filters(
        full_df,
        platform=selected_platforms,
        start_date=start_date,
        end_date=end_date,
    )
    meta = _build_meta(full_df, df, record)
    if df.empty:
        return {"platforms": [], "meta": meta}

    total_posts = len(df) or 1
    results = []
    for plat_name, sub in df.groupby("platform"):
        sc = sub["sentiment"].value_counts()
        sub_tot = len(sub) or 1
        top_topics = [
            {"name": str(t), "count": int(c)}
            for t, c in sub["topic"].value_counts().head(5).items()
        ]
        top_hashtags = _compute_hashtag_stats(sub)[:5]
        best_row = sub.sort_values("total_engagement", ascending=False).iloc[0]
        results.append(
            {
                "name": str(plat_name),
                "posts": int(len(sub)),
                "post_share_pct": round(len(sub) / total_posts * 100, 1),
                "engagement": int(sub["total_engagement"].sum()),
                "avg_engagement": round(float(sub["total_engagement"].mean()), 1),
                "median_engagement": round(float(sub["total_engagement"].median()), 1),
                "likes": int(sub["likes"].sum()),
                "shares": int(sub["shares"].sum()),
                "comments": int(sub["comments"].sum()),
                "avg_likes": round(float(sub["likes"].mean()), 1),
                "avg_shares": round(float(sub["shares"].mean()), 1),
                "avg_comments": round(float(sub["comments"].mean()), 1),
                "sentiment": {
                    "Positive": round(sc.get("Positive", 0) / sub_tot * 100, 1),
                    "Negative": round(sc.get("Negative", 0) / sub_tot * 100, 1),
                    "Neutral": round(sc.get("Neutral", 0) / sub_tot * 100, 1),
                },
                "top_topics": top_topics,
                "top_hashtags": [{"name": h["name"], "count": h["count"]} for h in top_hashtags],
                "best_post": _serialize_post_row(best_row),
            }
        )

    results.sort(key=lambda item: item["engagement"], reverse=True)
    return {"platforms": results, "meta": meta}


def hashtags_intelligence(
    db: Session | None = None,
    *,
    dataset_id: int | None = None,
    user_id: int | None = None,
    platform: str | None = None,
    sentiment_filter: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    search: str | None = None,
    selected_tag: str | None = None,
) -> dict[str, Any]:
    full_df, record = load_active_dataframe_with_record(db=db, dataset_id=dataset_id, user_id=user_id)
    df = apply_filters(
        full_df,
        platform=platform,
        sentiment=sentiment_filter,
        start_date=start_date,
        end_date=end_date,
    )
    meta = _build_meta(full_df, df, record)
    all_tags = _compute_hashtag_stats(df)

    if search and search.strip():
        q = search.strip().lower()
        all_tags = [t for t in all_tags if q in t["name"].lower()]

    detail = None
    if selected_tag and selected_tag.strip():
        target = selected_tag.strip().lower()
        if not target.startswith("#"):
            target = f"#{target}"
        matching_df = df[df["_tags_list"].apply(lambda tags: target in tags)]
        summary_item = next((t for t in all_tags if t["name"].lower() == target), None)
        if not matching_df.empty:
            timeline = []
            if "timestamp" in matching_df.columns:
                ts_df = matching_df.dropna(subset=["timestamp"]).copy()
                if not ts_df.empty:
                    ts_df["date_only"] = ts_df["timestamp"].dt.date
                    grp = (
                        ts_df.groupby("date_only")
                        .agg(posts=("post_id", "size"), engagement=("total_engagement", "sum"))
                        .reset_index()
                        .sort_values("date_only")
                    )
                    timeline = [
                        {"date": str(r.date_only), "posts": int(r.posts), "engagement": int(r.engagement)}
                        for _, r in grp.iterrows()
                    ]

            detail = {
                "tag": target,
                "summary": summary_item,
                "timeline": timeline,
                "platforms": [
                    {"name": str(p), "posts": int(c)}
                    for p, c in matching_df["platform"].value_counts().items()
                ],
                "posts": [
                    _serialize_post_row(row)
                    for _, row in matching_df.sort_values("total_engagement", ascending=False).head(25).iterrows()
                ],
            }

    return {"hashtags": all_tags[:100], "detail": detail, "meta": meta}


def content_performance(
    db: Session | None = None,
    *,
    dataset_id: int | None = None,
    user_id: int | None = None,
    platform: str | None = None,
    sentiment_filter: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    search: str | None = None,
) -> dict[str, Any]:
    full_df, record = load_active_dataframe_with_record(db=db, dataset_id=dataset_id, user_id=user_id)
    df = apply_filters(
        full_df,
        platform=platform,
        sentiment=sentiment_filter,
        start_date=start_date,
        end_date=end_date,
        search=search,
    )
    meta = _build_meta(full_df, df, record)
    if df.empty:
        return {
            "best_posts": [],
            "lowest_posts": [],
            "length_analysis": [],
            "hashtag_count_analysis": [],
            "sentiment_engagement": [],
            "top_keywords": [],
            "meta": meta,
        }

    best_posts = [
        _serialize_post_row(row)
        for _, row in df.sort_values("total_engagement", ascending=False).head(12).iterrows()
    ]
    lowest_posts = [
        _serialize_post_row(row)
        for _, row in df.sort_values("total_engagement", ascending=True).head(10).iterrows()
    ]

    length_bins = pd.cut(
        df["char_length"],
        bins=[-1, 80, 160, 240, 100000],
        labels=["Short (<80)", "Medium (80-160)", "Long (161-240)", "Extended (240+)"],
    )
    length_analysis = [
        {
            "bucket": str(bucket),
            "posts": int(len(sub)),
            "avg_engagement": round(float(sub["total_engagement"].mean()), 1),
            "avg_likes": round(float(sub["likes"].mean()), 1),
            "avg_shares": round(float(sub["shares"].mean()), 1),
            "avg_comments": round(float(sub["comments"].mean()), 1),
        }
        for bucket, sub in df.groupby(length_bins, observed=False)
        if not sub.empty
    ]

    tag_bins = pd.cut(
        df["hashtag_count"],
        bins=[-1, 0, 2, 4, 100],
        labels=["0 hashtags", "1-2 hashtags", "3-4 hashtags", "5+ hashtags"],
    )
    hashtag_count_analysis = [
        {
            "bucket": str(bucket),
            "posts": int(len(sub)),
            "avg_engagement": round(float(sub["total_engagement"].mean()), 1),
            "avg_shares": round(float(sub["shares"].mean()), 1),
        }
        for bucket, sub in df.groupby(tag_bins, observed=False)
        if not sub.empty
    ]

    sentiment_engagement = [
        {
            "sentiment": str(sent),
            "posts": int(len(sub)),
            "avg_engagement": round(float(sub["total_engagement"].mean()), 1),
            "total_engagement": int(sub["total_engagement"].sum()),
        }
        for sent, sub in df.groupby("sentiment")
    ]

    top_quartile_threshold = df["total_engagement"].quantile(0.75)
    top_q_df = df[df["total_engagement"] >= top_quartile_threshold]
    top_keywords = extract_top_keywords(top_q_df, top_n=18)

    return {
        "best_posts": best_posts,
        "lowest_posts": lowest_posts,
        "length_analysis": length_analysis,
        "hashtag_count_analysis": hashtag_count_analysis,
        "sentiment_engagement": sentiment_engagement,
        "top_keywords": top_keywords,
        "meta": meta,
    }


def topics_clustering(
    db: Session | None = None,
    *,
    dataset_id: int | None = None,
    user_id: int | None = None,
    platform: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    full_df, record = load_active_dataframe_with_record(db=db, dataset_id=dataset_id, user_id=user_id)
    df = apply_filters(full_df, platform=platform, start_date=start_date, end_date=end_date)
    meta = _build_meta(full_df, df, record)
    clusters = compute_topic_clusters(df)
    return {
        "clusters": clusters,
        "algorithm": "TF-IDF (1-2 ngrams) + KMeans clustering",
        "meta": meta,
    }


def time_analysis(
    db: Session | None = None,
    *,
    dataset_id: int | None = None,
    user_id: int | None = None,
    platform: str | None = None,
    granularity: str = "daily",
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    full_df, record = load_active_dataframe_with_record(db=db, dataset_id=dataset_id, user_id=user_id)
    df = apply_filters(full_df, platform=platform, start_date=start_date, end_date=end_date)
    meta = _build_meta(full_df, df, record)
    if df.empty or "timestamp" not in df.columns:
        return {
            "has_timestamps": False,
            "series": [],
            "hourly_pattern": [],
            "weekday_pattern": [],
            "heatmap": [],
            "growth_summary": {},
            "historical_note": "No valid timestamp values are available in the active dataset.",
            "meta": meta,
        }

    ts_df = df.dropna(subset=["timestamp"]).copy()
    if ts_df.empty:
        return {
            "has_timestamps": False,
            "series": [],
            "hourly_pattern": [],
            "weekday_pattern": [],
            "heatmap": [],
            "growth_summary": {},
            "historical_note": "Timestamp column exists but contains no parseable dates.",
            "meta": meta,
        }

    if granularity == "monthly":
        ts_df["period"] = ts_df["timestamp"].dt.to_period("M").astype(str)
    elif granularity == "weekly":
        ts_df["period"] = ts_df["timestamp"].dt.to_period("W").astype(str)
    else:
        ts_df["period"] = ts_df["timestamp"].dt.date.astype(str)

    grouped = (
        ts_df.groupby("period")
        .agg(
            posts=("post_id", "size"),
            engagement=("total_engagement", "sum"),
            avg_engagement=("total_engagement", "mean"),
            likes=("likes", "sum"),
            shares=("shares", "sum"),
            comments=("comments", "sum"),
        )
        .reset_index()
        .sort_values("period")
    )
    sent_piv = ts_df.groupby(["period", "sentiment"]).size().unstack(fill_value=0)
    series = []
    for _, row in grouped.iterrows():
        p = row["period"]
        series.append(
            {
                "period": str(p),
                "posts": int(row["posts"]),
                "engagement": int(row["engagement"]),
                "avg_engagement": round(float(row["avg_engagement"]), 1),
                "likes": int(row["likes"]),
                "shares": int(row["shares"]),
                "comments": int(row["comments"]),
                "Positive": int(sent_piv.loc[p, "Positive"]) if "Positive" in sent_piv.columns and p in sent_piv.index else 0,
                "Negative": int(sent_piv.loc[p, "Negative"]) if "Negative" in sent_piv.columns and p in sent_piv.index else 0,
                "Neutral": int(sent_piv.loc[p, "Neutral"]) if "Neutral" in sent_piv.columns and p in sent_piv.index else 0,
            }
        )

    ts_df["hour"] = ts_df["timestamp"].dt.hour
    ts_df["weekday"] = ts_df["timestamp"].dt.day_name()
    weekday_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    hour_grp = (
        ts_df.groupby("hour")
        .agg(posts=("post_id", "size"), avg_engagement=("total_engagement", "mean"), engagement=("total_engagement", "sum"))
        .reindex(range(24), fill_value=0)
        .reset_index()
    )
    hourly_pattern = [
        {
            "hour": int(r["hour"]),
            "label": f"{int(r['hour']):02d}:00",
            "posts": int(r["posts"]),
            "avg_engagement": round(float(r["avg_engagement"]), 1),
            "engagement": int(r["engagement"]),
        }
        for _, r in hour_grp.iterrows()
    ]

    wd_grp = (
        ts_df.groupby("weekday")
        .agg(posts=("post_id", "size"), avg_engagement=("total_engagement", "mean"), engagement=("total_engagement", "sum"))
        .reindex(weekday_order)
        .fillna(0)
        .reset_index()
    )
    weekday_pattern = [
        {
            "day": str(r["weekday"]),
            "short_day": str(r["weekday"])[:3],
            "posts": int(r["posts"]),
            "avg_engagement": round(float(r["avg_engagement"]), 1),
            "engagement": int(r["engagement"]),
        }
        for _, r in wd_grp.iterrows()
    ]

    heat_grp = (
        ts_df.groupby(["weekday", "hour"])
        .agg(posts=("post_id", "size"), avg_engagement=("total_engagement", "mean"))
        .reset_index()
    )
    heatmap = [
        {
            "day": str(r["weekday"]),
            "hour": int(r["hour"]),
            "posts": int(r["posts"]),
            "avg_engagement": round(float(r["avg_engagement"]), 1),
        }
        for _, r in heat_grp.iterrows()
    ]

    best_hour = max(hourly_pattern, key=lambda x: x["avg_engagement"]) if hourly_pattern else None
    best_day = max(weekday_pattern, key=lambda x: x["avg_engagement"]) if weekday_pattern else None

    midpoint = ts_df["timestamp"].min() + (ts_df["timestamp"].max() - ts_df["timestamp"].min()) / 2
    first_half = ts_df[ts_df["timestamp"] <= midpoint]
    second_half = ts_df[ts_df["timestamp"] > midpoint]
    eng_growth = None
    if not first_half.empty and not second_half.empty and first_half["total_engagement"].sum() > 0:
        eng_growth = round(
            (second_half["total_engagement"].sum() - first_half["total_engagement"].sum())
            / first_half["total_engagement"].sum()
            * 100,
            1,
        )

    return {
        "has_timestamps": True,
        "granularity": granularity,
        "series": series,
        "hourly_pattern": hourly_pattern,
        "weekday_pattern": weekday_pattern,
        "heatmap": heatmap,
        "growth_summary": {
            "best_hour": best_hour,
            "best_day": best_day,
            "period_engagement_change_pct": eng_growth,
            "unique_days": int(ts_df["timestamp"].dt.date.nunique()),
        },
        "historical_note": (
            "Posting-time and period metrics reflect historical patterns observed in the active dataset. "
            "They are descriptive statistics, not live API forecasts."
        ),
        "meta": meta,
    }


def anomalies(
    db: Session | None = None,
    *,
    dataset_id: int | None = None,
    user_id: int | None = None,
    platform: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    full_df, record = load_active_dataframe_with_record(db=db, dataset_id=dataset_id, user_id=user_id)
    df = apply_filters(full_df, platform=platform, start_date=start_date, end_date=end_date)
    meta = _build_meta(full_df, df, record)
    if df.empty or len(df) < 5:
        return {
            "post_anomalies": [],
            "daily_anomalies": [],
            "stats": {},
            "method": "Z-score, IQR, and Isolation Forest anomaly detection",
            "meta": meta,
        }

    eng = df["total_engagement"].astype(float)
    mean_eng = float(eng.mean())
    std_eng = float(eng.std()) or 1.0
    median_eng = float(eng.median())
    q1 = float(eng.quantile(0.25))
    q3 = float(eng.quantile(0.75))
    iqr = q3 - q1
    upper_iqr = q3 + 1.5 * iqr

    work = df.copy()
    work["z_score"] = ((eng - mean_eng) / std_eng).round(2)

    iso_flags = pd.Series(1, index=work.index)
    if len(work) >= 20:
        try:
            iso = IsolationForest(contamination=0.04, random_state=42)
            preds = iso.fit_predict(work[["likes", "shares", "comments", "total_engagement"]])
            iso_flags = pd.Series(preds, index=work.index)
        except Exception:
            pass

    flagged_mask = (work["z_score"].abs() >= 2.2) | (work["total_engagement"] > upper_iqr) | (iso_flags == -1)
    flagged = work[flagged_mask].sort_values("total_engagement", ascending=False).head(20)

    post_anomalies = []
    for idx, row in flagged.iterrows():
        val = int(row["total_engagement"])
        ratio = round(val / max(median_eng, 1.0), 1)
        z = float(row["z_score"])
        reasons = []
        if abs(z) >= 2.2:
            reasons.append(f"Z-score {z:+.2f} SD from mean ({mean_eng:.0f})")
        if val > upper_iqr:
            reasons.append(f"Exceeds Tukey IQR fence ({upper_iqr:.0f})")
        if iso_flags.loc[idx] == -1:
            reasons.append("Flagged by Isolation Forest across likes/shares/comments ratio")

        dominant_driver = max(
            [("likes", int(row["likes"])), ("shares", int(row["shares"])), ("comments", int(row["comments"]))],
            key=lambda x: x[1],
        )[0]

        item = _serialize_post_row(row)
        item["z_score"] = z
        item["median_multiple"] = ratio
        item["reason"] = (
            f"{val:,} total engagement ({ratio}x dataset median of {median_eng:.0f}), driven primarily by "
            f"{dominant_driver}. " + "; ".join(reasons) + "."
        )
        post_anomalies.append(item)

    daily_anomalies = []
    if "timestamp" in work.columns:
        ts_df = work.dropna(subset=["timestamp"]).copy()
        if not ts_df.empty:
            ts_df["date_only"] = ts_df["timestamp"].dt.date
            daily = (
                ts_df.groupby("date_only")
                .agg(posts=("post_id", "size"), engagement=("total_engagement", "sum"))
                .reset_index()
                .sort_values("date_only")
            )
            if len(daily) >= 5:
                d_mean = float(daily["engagement"].mean())
                d_std = float(daily["engagement"].std()) or 1.0
                daily["z"] = (daily["engagement"] - d_mean) / d_std
                for _, drow in daily[daily["z"].abs() >= 1.8].sort_values("z", ascending=False).iterrows():
                    kind = "Spike" if drow["z"] > 0 else "Drop"
                    daily_anomalies.append(
                        {
                            "date": str(drow["date_only"]),
                            "type": kind,
                            "posts": int(drow["posts"]),
                            "engagement": int(drow["engagement"]),
                            "baseline_mean": round(d_mean, 1),
                            "z_score": round(float(drow["z"]), 2),
                            "explanation": (
                                f"Daily engagement of {int(drow['engagement']):,} across {int(drow['posts'])} posts "
                                f"was {abs(float(drow['z'])):.2f} SD {'above' if drow['z'] > 0 else 'below'} "
                                f"the daily mean ({d_mean:,.0f})."
                            ),
                        }
                    )

    return {
        "post_anomalies": post_anomalies,
        "daily_anomalies": daily_anomalies,
        "stats": {
            "mean_engagement": round(mean_eng, 1),
            "median_engagement": round(median_eng, 1),
            "std_engagement": round(std_eng, 1),
            "iqr_upper_threshold": round(upper_iqr, 1),
            "flagged_posts_count": int(flagged_mask.sum()),
            "flagged_days_count": int(len(daily_anomalies)),
        },
        "method": "Statistical Z-score (|z| >= 2.2), Tukey IQR (Q3 + 1.5*IQR), and Isolation Forest",
        "meta": meta,
    }


def posts_explorer(
    db: Session | None = None,
    *,
    dataset_id: int | None = None,
    user_id: int | None = None,
    platform: str | None = None,
    sentiment_filter: str | None = None,
    topic: str | None = None,
    hashtag: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    search: str | None = None,
    sort_by: str = "total_engagement",
    sort_dir: str = "desc",
    page: int = 1,
    page_size: int = 25,
) -> dict[str, Any]:
    full_df, record = load_active_dataframe_with_record(db=db, dataset_id=dataset_id, user_id=user_id)
    df = apply_filters(
        full_df,
        platform=platform,
        sentiment=sentiment_filter,
        topic=topic,
        hashtag=hashtag,
        start_date=start_date,
        end_date=end_date,
        search=search,
    )
    meta = _build_meta(full_df, df, record)

    sort_map = {
        "total_engagement": "total_engagement",
        "engagement": "total_engagement",
        "likes": "likes",
        "shares": "shares",
        "comments": "comments",
        "timestamp": "timestamp",
        "sentiment_polarity": "sentiment_polarity",
    }
    col = sort_map.get(sort_by, "total_engagement")
    ascending = sort_dir.lower() == "asc"

    if df.empty:
        return {
            "posts": [],
            "pagination": {"page": 1, "page_size": page_size, "total": 0, "total_pages": 1},
            "meta": meta,
        }

    if col in df.columns:
        sorted_df = df.sort_values(col, ascending=ascending, na_position="last")
    else:
        sorted_df = df

    total = len(sorted_df)
    total_pages = max(1, (total + page_size - 1) // page_size)
    safe_page = max(1, min(page, total_pages))
    start = (safe_page - 1) * page_size
    page_df = sorted_df.iloc[start : start + page_size]

    return {
        "posts": [_serialize_post_row(row) for _, row in page_df.iterrows()],
        "pagination": {
            "page": safe_page,
            "page_size": page_size,
            "total": int(total),
            "total_pages": int(total_pages),
        },
        "meta": meta,
    }


def post_detail(
    post_id: str,
    db: Session | None = None,
    *,
    dataset_id: int | None = None,
    user_id: int | None = None,
) -> dict[str, Any]:
    df, record = load_active_dataframe_with_record(db=db, dataset_id=dataset_id, user_id=user_id)
    if df.empty:
        raise HTTPException(status_code=404, detail="No active dataset available.")
    match = df[df["post_id"].astype(str) == str(post_id)]
    if match.empty:
        raise HTTPException(status_code=404, detail=f"Post '{post_id}' not found in active dataset.")

    row = match.iloc[0]
    post = _serialize_post_row(row)
    dataset_avg = round(float(df["total_engagement"].mean()), 1)
    plat_df = df[df["platform"] == row["platform"]]
    plat_avg = round(float(plat_df["total_engagement"].mean()), 1) if not plat_df.empty else dataset_avg
    percentile = round(float((df["total_engagement"] <= row["total_engagement"]).mean() * 100), 1)

    return {
        "post": post,
        "benchmarks": {
            "dataset_avg_engagement": dataset_avg,
            "platform_avg_engagement": plat_avg,
            "engagement_percentile": percentile,
            "vs_dataset_avg_pct": round((post["engagement"] - dataset_avg) / max(dataset_avg, 1.0) * 100, 1),
        },
        "meta": _build_meta(df, df, record),
    }


def insights(
    db: Session | None = None,
    *,
    dataset_id: int | None = None,
    user_id: int | None = None,
    platform: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    ov = overview(
        db=db,
        dataset_id=dataset_id,
        user_id=user_id,
        platform=platform,
        start_date=start_date,
        end_date=end_date,
    )
    tr = trends(
        db=db,
        dataset_id=dataset_id,
        user_id=user_id,
        platform=platform,
        start_date=start_date,
        end_date=end_date,
    )
    sent = sentiment(
        db=db,
        dataset_id=dataset_id,
        user_id=user_id,
        platform=platform,
        start_date=start_date,
        end_date=end_date,
    )
    anom = anomalies(
        db=db,
        dataset_id=dataset_id,
        user_id=user_id,
        platform=platform,
        start_date=start_date,
        end_date=end_date,
    )
    time_res = time_analysis(
        db=db,
        dataset_id=dataset_id,
        user_id=user_id,
        platform=platform,
        start_date=start_date,
        end_date=end_date,
    )

    kpis = ov["kpis"]
    structured: list[dict[str, str]] = []

    if ov["platforms"]:
        best_total_plat = max(ov["platforms"], key=lambda x: x["engagement"])
        best_avg_plat = max(ov["platforms"], key=lambda x: x["avg_engagement"])
        structured.append(
            {
                "id": "platform-leader",
                "title": f"{best_avg_plat['name']} leads per-post engagement",
                "category": "platform",
                "observation": (
                    f"{best_avg_plat['name']} averages {best_avg_plat['avg_engagement']} interactions per post, "
                    f"while {best_total_plat['name']} drives the highest total volume ({best_total_plat['engagement']:,} interactions across {best_total_plat['posts']:,} posts)."
                ),
                "evidence": (
                    f"Calculated across {kpis['total_posts']:,} active posts: {best_avg_plat['name']} avg={best_avg_plat['avg_engagement']} "
                    f"(likes/shares/comments sum={best_avg_plat['engagement']:,})."
                ),
                "recommendation": (
                    f"Prioritize high-engagement formats on {best_avg_plat['name']} while maintaining consistent publishing cadence on {best_total_plat['name']}."
                ),
                "confidence_note": "Observed dataset metric",
            }
        )

    if kpis.get("total_posts", 0) > 0:
        dom_sent = max(
            [
                ("Positive", kpis["positive_sentiment"]),
                ("Negative", kpis["negative_sentiment"]),
                ("Neutral", kpis["neutral_sentiment"]),
            ],
            key=lambda x: x[1],
        )
        neg_topic = sent["most_negative_topics"][0] if sent["most_negative_topics"] else None
        structured.append(
            {
                "id": "sentiment-balance",
                "title": f"{dom_sent[0]} sentiment is the dominant tone ({dom_sent[1]}%)",
                "category": "sentiment",
                "observation": (
                    f"Sentiment splits into {kpis['positive_sentiment']}% Positive, {kpis['negative_sentiment']}% Negative, "
                    f"and {kpis['neutral_sentiment']}% Neutral."
                    + (
                        f" '{neg_topic['name']}' carries the highest negative share at {neg_topic['Negative']}%."
                        if neg_topic
                        else ""
                    )
                ),
                "evidence": (
                    f"Counts: {kpis['positive_count']:,} positive, {kpis['negative_count']:,} negative, "
                    f"{kpis['neutral_count']:,} neutral posts (avg polarity {sent['summary'].get('avg_polarity', 0):+.3f})."
                ),
                "recommendation": (
                    f"Audit pain points in '{neg_topic['name']}' posts and address recurring audience objections with educational follow-ups."
                    if neg_topic
                    else "Track sentiment shifts across weekly cohorts."
                ),
                "confidence_note": "Dataset labels + automated NLP fallback",
            }
        )

    if tr["emerging_topics"]:
        fast = tr["emerging_topics"][0]
        structured.append(
            {
                "id": "emerging-topic",
                "title": f"Fastest historical topic growth: {fast['name']} ({fast['growth_pct']:+.1f}%)",
                "category": "trend",
                "observation": (
                    f"'{fast['name']}' changed by {fast['growth_pct']:+.1f}% between the first and second half of the dataset timeline, "
                    f"averaging {fast['avg_engagement']} interactions per post."
                ),
                "evidence": (
                    f"Topic volume: {fast['posts']:,} posts ({fast['share_pct']}% share), primary channel {fast['top_platform']}."
                ),
                "recommendation": f"Allocate upcoming editorial slots to '{fast['name']}' on {fast['top_platform']}.",
                "confidence_note": "Historical period-over-period comparison (not a future guarantee)",
            }
        )
    elif ov["topics"]:
        top_t = ov["topics"][0]
        structured.append(
            {
                "id": "top-topic",
                "title": f"Top discussed topic: {top_t['name']}",
                "category": "trend",
                "observation": f"'{top_t['name']}' accounts for {top_t['posts']:,} posts ({top_t['share_pct']}% of volume).",
                "evidence": f"Total engagement {top_t['engagement']:,}, average {top_t['avg_engagement']} per post.",
                "recommendation": f"Build deep-dive content clusters around '{top_t['name']}' sub-themes.",
                "confidence_note": "Observed dataset metric",
            }
        )

    if ov["hashtags"]:
        best_eng_tag = max(ov["hashtags"], key=lambda x: x["avg_engagement"])
        most_freq_tag = ov["hashtags"][0]
        structured.append(
            {
                "id": "hashtag-efficiency",
                "title": f"{best_eng_tag['name']} drives highest avg engagement per tag ({best_eng_tag['avg_engagement']})",
                "category": "hashtag",
                "observation": (
                    f"{most_freq_tag['name']} is used most often ({most_freq_tag['count']} posts), while "
                    f"{best_eng_tag['name']} delivers {best_eng_tag['avg_engagement']} average engagement across {best_eng_tag['count']} uses."
                ),
                "evidence": f"Top hashtag total engagement: {most_freq_tag['engagement']:,} interactions.",
                "recommendation": f"Pair broad reach tags like {most_freq_tag['name']} with high-efficiency tags like {best_eng_tag['name']}.",
                "confidence_note": "Observed dataset metric",
            }
        )

    if anom["post_anomalies"]:
        top_anom = anom["post_anomalies"][0]
        structured.append(
            {
                "id": "anomaly-highlight",
                "title": f"{anom['stats']['flagged_posts_count']} high-variance engagement outliers detected",
                "category": "anomaly",
                "observation": (
                    f"Top outlier post {top_anom['post_id']} on {top_anom['platform']} reached {top_anom['engagement']:,} interactions "
                    f"({top_anom['median_multiple']}x the dataset median)."
                ),
                "evidence": top_anom["reason"],
                "recommendation": "Replicate the hook, topic, and hashtag structure of flagged positive outliers.",
                "confidence_note": "Statistical Z-score / IQR / Isolation Forest flag",
            }
        )

    if time_res.get("has_timestamps") and time_res["growth_summary"].get("best_hour"):
        bh = time_res["growth_summary"]["best_hour"]
        bd = time_res["growth_summary"]["best_day"]
        structured.append(
            {
                "id": "timing-pattern",
                "title": f"Peak historical window: {bd['day']} around {bh['label']}",
                "category": "timing",
                "observation": (
                    f"Posts published on {bd['day']} average {bd['avg_engagement']} engagement, and the {bh['label']} hour slot "
                    f"records {bh['avg_engagement']} average engagement."
                ),
                "evidence": f"Analyzed across {time_res['growth_summary']['unique_days']} unique calendar days in the dataset.",
                "recommendation": f"Schedule priority posts during {bd['day']} {bh['label']} windows and run A/B checks.",
                "confidence_note": "Historical descriptive timing pattern",
            }
        )

    flat_insights = [f"{item['title']}: {item['observation']}" for item in structured]

    return {
        "insights": flat_insights,
        "structured_insights": structured,
        "data": ov,
    }
