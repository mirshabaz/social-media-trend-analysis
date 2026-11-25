import json
import re
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.analytics.dataset_analytics import (
    anomalies,
    engagement,
    hashtags_intelligence,
    insights,
    load_active_dataframe_with_record,
    overview,
    platforms_comparison,
    sentiment,
    time_analysis,
    trends,
)
from app.core.config import settings


def _extract_limit(question: str, default: int = 5) -> int:
    match = re.search(r"\b(\d{1,2})\b", question)
    if match:
        val = int(match.group(1))
        return max(1, min(val, 20))
    word_map = {"three": 3, "five": 5, "ten": 10, "top": default}
    lower = question.lower()
    for word, num in word_map.items():
        if word in lower and word != "top":
            return num
    return default


def _solve_deterministic(
    question: str,
    db: Session,
    *,
    dataset_id: int | None = None,
    user_id: int | None = None,
) -> dict[str, Any]:
    q = question.strip()
    lower = q.lower()

    full_df, record = load_active_dataframe_with_record(
        db=db, dataset_id=dataset_id, user_id=user_id
    )
    dataset_name = record.name if record else "SocialPulse Benchmark Dataset"

    if full_df.empty:
        return {
            "answer": "No records are currently loaded in the active dataset. Upload or activate a CSV dataset in Dataset Explorer to analyze.",
            "metrics": [],
            "suggested_followups": ["Upload a CSV dataset"],
            "mode": "deterministic_analytics",
            "dataset_name": dataset_name,
        }

    ov = overview(db=db, dataset_id=dataset_id, user_id=user_id)
    kpis = ov["kpis"]
    plat_names = [p["name"] for p in ov["platforms"]]
    matched_platforms = [p for p in plat_names if p.lower() in lower or p.split("/")[0].lower() in lower]

    # 1. Explicit platform comparison (e.g. "Compare Instagram and LinkedIn")
    if ("compare" in lower or " vs " in lower or "versus" in lower) and len(matched_platforms) >= 2:
        comp = platforms_comparison(
            db=db,
            dataset_id=dataset_id,
            user_id=user_id,
            selected_platforms=",".join(matched_platforms),
        )["platforms"]
        lines = [
            f"Comparison across **{', '.join(p['name'] for p in comp)}** in **{dataset_name}** ({kpis['total_posts']:,} total posts):"
        ]
        metrics = []
        for p in comp:
            lines.append(
                f"- **{p['name']}**: {p['posts']:,} posts ({p['post_share_pct']}% share), "
                f"{p['engagement']:,} total engagement (avg {p['avg_engagement']}/post), "
                f"Sentiment: {p['sentiment']['Positive']}% Positive / {p['sentiment']['Negative']}% Negative."
            )
            metrics.append(
                {
                    "label": p["name"],
                    "value": f"{p['avg_engagement']} avg eng",
                    "detail": f"{p['posts']:,} posts • {p['engagement']:,} total",
                }
            )
        winner = max(comp, key=lambda x: x["avg_engagement"])
        lines.append(
            f"\n**Summary**: **{winner['name']}** leads in average engagement per post ({winner['avg_engagement']})."
        )
        return {
            "answer": "\n".join(lines),
            "metrics": metrics,
            "suggested_followups": [
                f"What are the top hashtags on {winner['name']}?",
                "Which topic is trending overall?",
                "Give me recommendations based on my dataset.",
            ],
            "mode": "deterministic_analytics",
            "dataset_name": dataset_name,
        }

    # 2. Hashtags intent
    if "hashtag" in lower or "#" in lower:
        n = _extract_limit(lower, default=5)
        tags_data = hashtags_intelligence(db=db, dataset_id=dataset_id, user_id=user_id)["hashtags"][:n]
        if not tags_data:
            return {
                "answer": f"No hashtags were found in **{dataset_name}**.",
                "metrics": [],
                "suggested_followups": ["Which topic is trending?", "What is the overall sentiment?"],
                "mode": "deterministic_analytics",
                "dataset_name": dataset_name,
            }
        lines = [f"Top **{len(tags_data)} hashtags** in **{dataset_name}** by frequency and engagement:"]
        metrics = []
        for idx, tag in enumerate(tags_data, start=1):
            lines.append(
                f"{idx}. **{tag['name']}** — {tag['count']:,} posts, {tag['engagement']:,} total engagement "
                f"(avg {tag['avg_engagement']}/post, {tag['positive_pct']}% positive)."
            )
            metrics.append(
                {
                    "label": tag["name"],
                    "value": f"{tag['count']} uses",
                    "detail": f"Avg {tag['avg_engagement']} eng • {tag['top_platform']}",
                }
            )
        return {
            "answer": "\n".join(lines),
            "metrics": metrics,
            "suggested_followups": [
                "Which platform has the highest engagement?",
                "Give me recommendations based on my dataset.",
            ],
            "mode": "deterministic_analytics",
            "dataset_name": dataset_name,
        }

    # 3. Sentiment / negative trends intent
    if "sentiment" in lower or "positive" in lower or "negative" in lower or "emotion" in lower or "opinion" in lower:
        sent_data = sentiment(db=db, dataset_id=dataset_id, user_id=user_id)
        neg_topics = sent_data["most_negative_topics"][:3]
        pos_topics = sent_data["most_positive_topics"][:3]
        neg_words = [w["word"] for w in sent_data["emotional_words"]["negative"][:6]]

        lines = [
            f"Overall sentiment across **{kpis['total_posts']:,} posts** in **{dataset_name}**:",
            f"- **Positive**: {kpis['positive_sentiment']}% ({kpis['positive_count']:,} posts)",
            f"- **Negative**: {kpis['negative_sentiment']}% ({kpis['negative_count']:,} posts)",
            f"- **Neutral**: {kpis['neutral_sentiment']}% ({kpis['neutral_count']:,} posts)",
        ]
        if neg_topics:
            lines.append(
                "\n**Highest Negative Sentiment Topics**: "
                + ", ".join(f"{t['name']} ({t['Negative']}% negative)" for t in neg_topics)
                + "."
            )
        if pos_topics:
            lines.append(
                "**Most Positive Topics**: "
                + ", ".join(f"{t['name']} ({t['Positive']}% positive)" for t in pos_topics)
                + "."
            )
        if neg_words:
            lines.append(f"**Frequent Negative Vocabulary**: {', '.join(neg_words)}.")
        lines.append("\n_Note: Automated sentiment classifications may be imperfect when dataset labels are absent or text contains sarcasm._")

        return {
            "answer": "\n".join(lines),
            "metrics": [
                {"label": "Positive", "value": f"{kpis['positive_sentiment']}%", "detail": f"{kpis['positive_count']:,} posts"},
                {"label": "Negative", "value": f"{kpis['negative_sentiment']}%", "detail": f"{kpis['negative_count']:,} posts"},
                {"label": "Neutral", "value": f"{kpis['neutral_sentiment']}%", "detail": f"{kpis['neutral_count']:,} posts"},
            ],
            "suggested_followups": [
                "Which topic is trending?",
                "Which platform has the highest engagement?",
            ],
            "mode": "deterministic_analytics",
            "dataset_name": dataset_name,
        }

    # 4. Recommendations / Insights intent
    if "recommend" in lower or "action" in lower or "should" in lower or "strategy" in lower or "insight" in lower:
        ins = insights(db=db, dataset_id=dataset_id, user_id=user_id)["structured_insights"]
        lines = [f"Actionable recommendations grounded in **{dataset_name}**:"]
        for idx, item in enumerate(ins, start=1):
            lines.append(f"{idx}. **{item['title']}**\n   - *Data*: {item['observation']}\n   - *Action*: {item['recommendation']}")
        return {
            "answer": "\n".join(lines),
            "metrics": [
                {"label": "Top Platform", "value": str(kpis["top_platform"]), "detail": "Highest volume"},
                {"label": "Top Topic", "value": str(kpis["top_topic"]), "detail": "Most discussed"},
                {"label": "Avg Engagement", "value": str(kpis["avg_engagement"]), "detail": "Per post"},
            ],
            "suggested_followups": [
                "What are the negative sentiment trends?",
                "Which posts received the most engagement?",
            ],
            "mode": "deterministic_analytics",
            "dataset_name": dataset_name,
        }

    # 5. Best/Top Posts intent
    if "post" in lower and ("most" in lower or "top" in lower or "best" in lower or "viral" in lower or "highest" in lower):
        n = _extract_limit(lower, default=5)
        eng_data = engagement(db=db, dataset_id=dataset_id, user_id=user_id, limit=n)
        top_posts = eng_data["top_posts"]
        lines = [f"Top **{len(top_posts)} posts** by total engagement (likes + shares + comments) in **{dataset_name}**:"]
        metrics = []
        for idx, post in enumerate(top_posts, start=1):
            snippet = post["content"][:110] + ("..." if len(post["content"]) > 110 else "")
            lines.append(
                f"{idx}. **[{post['post_id']}] {post['platform']}** — **{post['engagement']:,}** interactions "
                f"({post['likes']:,} likes, {post['shares']:,} shares, {post['comments']:,} comments): \"{snippet}\""
            )
            metrics.append(
                {"label": post["post_id"], "value": f"{post['engagement']:,}", "detail": post["platform"]}
            )
        return {
            "answer": "\n".join(lines),
            "metrics": metrics[:4],
            "suggested_followups": [
                "Are there engagement anomalies in the dataset?",
                "Compare Instagram and LinkedIn",
            ],
            "mode": "deterministic_analytics",
            "dataset_name": dataset_name,
        }

    # 6. Platform engagement intent
    if "platform" in lower or "channel" in lower or len(matched_platforms) == 1:
        plats = platforms_comparison(db=db, dataset_id=dataset_id, user_id=user_id)["platforms"]
        by_total = sorted(plats, key=lambda x: x["engagement"], reverse=True)
        by_avg = sorted(plats, key=lambda x: x["avg_engagement"], reverse=True)
        lines = [
            f"Platform engagement breakdown in **{dataset_name}**:",
            f"- **Highest Total Engagement**: **{by_total[0]['name']}** ({by_total[0]['engagement']:,} total across {by_total[0]['posts']:,} posts)" if by_total else "",
            f"- **Highest Average Engagement / Post**: **{by_avg[0]['name']}** ({by_avg[0]['avg_engagement']} avg per post)" if by_avg else "",
            "\n**All Channels**:",
        ]
        metrics = []
        for p in by_total:
            lines.append(
                f"- **{p['name']}**: {p['posts']:,} posts, {p['engagement']:,} total ({p['avg_engagement']} avg/post, {p['sentiment']['Positive']}% positive)"
            )
            metrics.append(
                {"label": p["name"], "value": f"{p['engagement']:,}", "detail": f"{p['avg_engagement']} avg • {p['posts']} posts"}
            )
        return {
            "answer": "\n".join(line for line in lines if line),
            "metrics": metrics,
            "suggested_followups": [
                "Compare Instagram and LinkedIn",
                "What are the top 5 hashtags?",
            ],
            "mode": "deterministic_analytics",
            "dataset_name": dataset_name,
        }

    # 7. Trending / Emerging Topics intent
    if "topic" in lower or "trend" in lower or "emerging" in lower or "growing" in lower:
        tr = trends(db=db, dataset_id=dataset_id, user_id=user_id)
        top_topics = tr["topics"][:5]
        emerging = tr["emerging_topics"][:3]
        lines = [f"Top trending topics by post volume in **{dataset_name}**:"]
        for idx, t in enumerate(top_topics, start=1):
            g_str = f", historical change {t['growth_pct']:+.1f}%" if t["growth_pct"] is not None else ""
            lines.append(
                f"{idx}. **{t['name']}** — {t['posts']:,} posts ({t['share_pct']}% share), avg {t['avg_engagement']} engagement{g_str}."
            )
        if emerging:
            lines.append(
                "\n**Fastest Historical Growth**: "
                + ", ".join(f"{e['name']} ({e['growth_pct']:+.1f}%)" for e in emerging)
                + "."
            )
        return {
            "answer": "\n".join(lines),
            "metrics": [
                {"label": t["name"], "value": f"{t['posts']} posts", "detail": f"Avg {t['avg_engagement']} eng"}
                for t in top_topics[:4]
            ],
            "suggested_followups": [
                "What is the overall sentiment?",
                "What are the top 5 hashtags?",
            ],
            "mode": "deterministic_analytics",
            "dataset_name": dataset_name,
        }

    # 8. Posting time / Anomalies intent
    if "time" in lower or "hour" in lower or "day" in lower or "when" in lower:
        ta = time_analysis(db=db, dataset_id=dataset_id, user_id=user_id)
        if not ta["has_timestamps"]:
            return {
                "answer": f"**{dataset_name}** does not contain parseable timestamps to analyze posting times.",
                "metrics": [],
                "suggested_followups": ["Which topic is trending?"],
                "mode": "deterministic_analytics",
                "dataset_name": dataset_name,
            }
        bh = ta["growth_summary"]["best_hour"]
        bd = ta["growth_summary"]["best_day"]
        return {
            "answer": (
                f"Historical timing analysis for **{dataset_name}** ({ta['growth_summary']['unique_days']} unique days):\n"
                f"- **Best Day**: **{bd['day']}** (avg {bd['avg_engagement']} engagement across {bd['posts']} posts)\n"
                f"- **Best Hour**: **{bh['label']}** (avg {bh['avg_engagement']} engagement across {bh['posts']} posts)\n\n"
                f"_{ta['historical_note']}_"
            ),
            "metrics": [
                {"label": "Peak Day", "value": bd["day"], "detail": f"{bd['avg_engagement']} avg eng"},
                {"label": "Peak Hour", "value": bh["label"], "detail": f"{bh['avg_engagement']} avg eng"},
            ],
            "suggested_followups": ["Give me recommendations based on my dataset."],
            "mode": "deterministic_analytics",
            "dataset_name": dataset_name,
        }

    if "anomal" in lower or "outlier" in lower or "spike" in lower or "unusual" in lower:
        anom = anomalies(db=db, dataset_id=dataset_id, user_id=user_id)
        stats = anom["stats"]
        top_a = anom["post_anomalies"][:3]
        lines = [
            f"Anomaly scan on **{dataset_name}** ({anom['method']}):",
            f"- **Flagged Outlier Posts**: {stats.get('flagged_posts_count', 0)} posts (IQR upper fence {stats.get('iqr_upper_threshold', 0):,.0f})",
            f"- **Flagged Daily Spikes/Drops**: {stats.get('flagged_days_count', 0)} days",
        ]
        for a in top_a:
            lines.append(f"- **{a['post_id']} ({a['platform']})**: {a['reason']}")
        return {
            "answer": "\n".join(lines),
            "metrics": [
                {"label": "Outlier Posts", "value": str(stats.get("flagged_posts_count", 0)), "detail": "Statistical flags"},
                {"label": "Dataset Median", "value": str(stats.get("median_engagement", 0)), "detail": "Baseline engagement"},
            ],
            "suggested_followups": ["Which posts received the most engagement?"],
            "mode": "deterministic_analytics",
            "dataset_name": dataset_name,
        }

    # 9. General overview / keyword fallback
    # Check if user asked about a specific keyword present in dataset
    words = [w for w in re.findall(r"[a-zA-Z0-9_#-]{3,}", lower) if w not in {"what", "which", "about", "with", "from", "have", "your", "dataset", "show", "tell", "does", "that", "this"}]
    if words:
        probe = words[-1]
        sub = overview(db=db, dataset_id=dataset_id, user_id=user_id, search=probe)
        if 0 < sub["kpis"]["total_posts"] < kpis["total_posts"]:
            sk = sub["kpis"]
            return {
                "answer": (
                    f"Found **{sk['total_posts']:,} posts** matching **\"{probe}\"** in **{dataset_name}**:\n"
                    f"- **Total Engagement**: {sk['total_engagement']:,} (avg {sk['avg_engagement']}/post)\n"
                    f"- **Sentiment**: {sk['positive_sentiment']}% Positive, {sk['negative_sentiment']}% Negative, {sk['neutral_sentiment']}% Neutral\n"
                    f"- **Leading Platform**: {sk['top_platform']}"
                ),
                "metrics": [
                    {"label": "Matching Posts", "value": f"{sk['total_posts']:,}", "detail": f"Filter: {probe}"},
                    {"label": "Avg Engagement", "value": str(sk["avg_engagement"]), "detail": f"{sk['total_engagement']:,} total"},
                ],
                "suggested_followups": ["Which platform has the highest engagement?", "What is the overall sentiment?"],
                "mode": "deterministic_analytics",
                "dataset_name": dataset_name,
            }

    return {
        "answer": (
            f"Summary of **{dataset_name}** ({kpis['total_posts']:,} cleaned posts):\n"
            f"- **Total Engagement**: {kpis['total_engagement']:,} ({kpis['total_likes']:,} likes, {kpis['total_shares']:,} shares, {kpis['total_comments']:,} comments)\n"
            f"- **Top Platform**: {kpis['top_platform']} | **Top Topic**: {kpis['top_topic']} | **Top Hashtag**: {kpis['top_hashtag']}\n"
            f"- **Sentiment Mix**: {kpis['positive_sentiment']}% Positive, {kpis['negative_sentiment']}% Negative, {kpis['neutral_sentiment']}% Neutral"
        ),
        "metrics": [
            {"label": "Posts", "value": f"{kpis['total_posts']:,}", "detail": dataset_name},
            {"label": "Interactions", "value": f"{kpis['total_engagement']:,}", "detail": f"Avg {kpis['avg_engagement']}"},
            {"label": "Top Topic", "value": str(kpis["top_topic"]), "detail": str(kpis["top_platform"])},
        ],
        "suggested_followups": [
            "Which platform has the highest engagement?",
            "What are the top 5 hashtags?",
            "What are the negative sentiment trends?",
            "Give me recommendations based on my dataset.",
        ],
        "mode": "deterministic_analytics",
        "dataset_name": dataset_name,
    }


async def answer_assistant_query(
    question: str,
    db: Session,
    *,
    dataset_id: int | None = None,
    user_id: int | None = None,
) -> dict[str, Any]:
    baseline = _solve_deterministic(question, db, dataset_id=dataset_id, user_id=user_id)

    # Optional LLM polish strictly grounded in computed deterministic output if backend key is configured
    if settings.openai_api_key:
        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                resp = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                    json={
                        "model": settings.openai_model,
                        "temperature": 0.2,
                        "messages": [
                            {
                                "role": "system",
                                "content": (
                                    "You are SOCIALPULSE AI Analytics Assistant. Refine the computed analytics answer concisely. "
                                    "ONLY cite numbers and facts present in the computed_context JSON. Never invent metrics."
                                ),
                            },
                            {
                                "role": "user",
                                "content": json.dumps(
                                    {"question": question, "computed_context": baseline}
                                ),
                            },
                        ],
                    },
                )
                if resp.status_code == 200:
                    content = resp.json()["choices"][0]["message"]["content"]
                    if content:
                        baseline["answer"] = content.strip()
                        baseline["mode"] = "llm_grounded"
        except Exception:
            pass

    return baseline

