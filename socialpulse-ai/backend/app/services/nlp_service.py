import re
from collections import Counter

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer

try:
    from textblob import TextBlob

    HAS_TEXTBLOB = True
except Exception:
    HAS_TEXTBLOB = False


STOPWORDS = {
    "about", "above", "after", "again", "against", "almost", "alone", "along",
    "already", "also", "although", "always", "among", "another", "around", "because",
    "been", "before", "being", "below", "between", "both", "could", "does", "doing",
    "done", "down", "during", "each", "either", "enough", "even", "every", "from",
    "further", "getting", "going", "have", "having", "here", "hers", "herself",
    "himself", "into", "itself", "just", "keep", "know", "like", "likely", "made",
    "make", "many", "maybe", "more", "most", "much", "must", "myself", "neither",
    "never", "next", "none", "nothing", "once", "only", "other", "others", "ours",
    "ourselves", "over", "really", "same", "several", "should", "since", "some",
    "something", "still", "such", "than", "that", "their", "theirs", "them",
    "themselves", "then", "there", "these", "they", "thing", "things", "this",
    "those", "though", "through", "today", "together", "under", "until", "very",
    "want", "were", "what", "when", "where", "whether", "which", "while", "with",
    "within", "without", "would", "your", "yours", "yourself", "http", "https",
}

POSITIVE_LEXICON = {
    "great", "excellent", "good", "amazing", "love", "best", "breakthrough",
    "transform", "transformed", "win", "healthy", "rewarding", "growth", "boost",
    "promising", "supportive", "progress", "success", "successfully", "efficient",
    "efficiency", "excited", "innovative", "innovation", "solution", "relief",
    "gain", "gains", "vital", "grateful", "kudos", "better", "restored", "happy",
    "achieved", "authentic", "impressive", "reliable", "prevented", "saving",
    "democratizing", "life-saving", "zero-downtime", "surpassed",
}

NEGATIVE_LEXICON = {
    "bad", "terrible", "worst", "fail", "failed", "failing", "hate", "worry",
    "worried", "burnout", "nightmare", "attack", "severe", "pain", "crisis",
    "outage", "vulnerability", "vulnerabilities", "displacement", "hallucinations",
    "crackdown", "fraud", "fraudulent", "frustration", "exhausted", "loss", "poor",
    "phishing", "ransomware", "slashed", "critical", "miserably", "draining",
    "isolation", "unusable", "congestion", "volatility", "liquidations", "doubled",
    "greenwashing", "droughts", "stricter", "unexpected", "headache", "chronic",
}

NEGATIONS = {"not", "no", "never", "neither", "hardly", "barely", "without"}

EMOTION_LEXICONS = {
    "Joy / Enthusiasm": {
        "amazing", "excited", "win", "love", "grateful", "breakthrough", "kudos",
        "great", "excellent", "best", "achieved", "happy", "celebrated", "impressive",
        "boost", "success", "successfully", "growth", "better",
    },
    "Concern / Risk": {
        "worried", "worry", "critical", "phishing", "ransomware", "attack",
        "vulnerability", "vulnerabilities", "risk", "crisis", "privacy", "ethical",
        "displacement", "outage", "droughts", "volatility", "severe", "urgent",
    },
    "Frustration / Stress": {
        "nightmare", "exhausted", "burnout", "headache", "frustration", "pain",
        "miserably", "draining", "failing", "failed", "worst", "terrible",
        "unusable", "slashed", "isolation", "heart",
    },
    "Analytical / Curious": {
        "exploring", "comparing", "assessing", "analyzing", "reviewing", "pilot",
        "benchmark", "architecture", "protocol", "protocols", "strategy", "model",
        "models", "metrics", "data", "research", "study",
    },
}


def compute_text_sentiment(text: str) -> tuple[float, str, float, str]:
    """Return (polarity, label, confidence, emotion) computed from post text."""
    if not isinstance(text, str) or not text.strip():
        return 0.0, "Neutral", 0.5, "Neutral / Informative"

    tb_polarity = 0.0
    if HAS_TEXTBLOB:
        try:
            tb_polarity = float(TextBlob(text).sentiment.polarity)
        except Exception:
            tb_polarity = 0.0

    tokens = re.findall(r"[a-z0-9'-]+", text.lower())
    pos_score = 0.0
    neg_score = 0.0
    for idx, token in enumerate(tokens):
        negated = idx > 0 and tokens[idx - 1] in NEGATIONS
        if token in POSITIVE_LEXICON:
            if negated:
                neg_score += 1.0
            else:
                pos_score += 1.0
        elif token in NEGATIVE_LEXICON:
            if negated:
                pos_score += 0.6
            else:
                neg_score += 1.0

    lex_polarity = 0.0
    if pos_score or neg_score:
        lex_polarity = (pos_score - neg_score) / max(pos_score + neg_score, 1.0) * 0.65

    if tb_polarity != 0.0 and lex_polarity != 0.0:
        polarity = 0.6 * tb_polarity + 0.4 * lex_polarity
    elif tb_polarity != 0.0:
        polarity = tb_polarity
    else:
        polarity = lex_polarity

    polarity = float(max(-1.0, min(1.0, round(polarity, 3))))

    if polarity > 0.05:
        label = "Positive"
    elif polarity < -0.05:
        label = "Negative"
    else:
        label = "Neutral"

    confidence = round(min(0.98, 0.52 + abs(polarity) * 0.46), 2)

    token_set = set(tokens)
    emotion_scores = {
        emotion: len(token_set.intersection(words))
        for emotion, words in EMOTION_LEXICONS.items()
    }
    best_emotion = max(emotion_scores.items(), key=lambda item: item[1])
    if best_emotion[1] > 0:
        emotion = best_emotion[0]
    elif label == "Positive":
        emotion = "Joy / Enthusiasm"
    elif label == "Negative":
        emotion = "Concern / Risk"
    else:
        emotion = "Neutral / Informative"

    return polarity, label, confidence, emotion


def normalize_sentiment_label(value: object) -> str | None:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    raw = str(value).strip().lower()
    if not raw or raw in {"nan", "none", "null", "na", "n/a"}:
        return None
    if raw in {"positive", "pos", "1", "good", "bullish"}:
        return "Positive"
    if raw in {"negative", "neg", "-1", "bad", "bearish"}:
        return "Negative"
    if raw in {"neutral", "neu", "0", "mixed", "objective"}:
        return "Neutral"
    return None


def enrich_sentiment_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure sentiment, polarity, confidence, source, and emotion columns exist."""
    enriched = df.copy()
    texts = enriched["post_content"].fillna("").astype(str).tolist()
    computed = [compute_text_sentiment(text) for text in texts]

    enriched["sentiment_polarity"] = [item[0] for item in computed]
    enriched["predicted_sentiment"] = [item[1] for item in computed]
    enriched["sentiment_confidence"] = [item[2] for item in computed]
    enriched["detected_emotion"] = [item[3] for item in computed]

    if "sentiment" in enriched.columns:
        normalized = enriched["sentiment"].map(normalize_sentiment_label)
        has_label = normalized.notna()
        enriched["sentiment"] = normalized.where(has_label, enriched["predicted_sentiment"])
        enriched["sentiment_source"] = np.where(has_label, "dataset_label", "automated_nlp")
    else:
        enriched["sentiment"] = enriched["predicted_sentiment"]
        enriched["sentiment_source"] = "automated_nlp"

    return enriched


def extract_hashtags_from_row(hashtags_val: object, content_val: object) -> list[str]:
    tags: list[str] = []
    seen: set[str] = set()

    for source in (hashtags_val, content_val):
        if source is None or (isinstance(source, float) and np.isnan(source)):
            continue
        text = str(source)
        found = re.findall(r"#([A-Za-z0-9_]+)", text)
        if not found and source is hashtags_val:
            # Handle comma/space-separated tags without leading #
            found = [
                part.strip().lstrip("#")
                for part in re.split(r"[,\s]+", text)
                if part.strip() and re.match(r"^[A-Za-z0-9_]{2,}$", part.strip().lstrip("#"))
            ]
        for tag in found:
            normalized = f"#{tag.lower()}"
            if normalized not in seen:
                seen.add(normalized)
                tags.append(normalized)
    return tags


def tokenize_meaningful_words(text: str) -> list[str]:
    if not isinstance(text, str):
        return []
    cleaned = re.sub(r"https?://\S+|www\.\S+", " ", text.lower())
    cleaned = re.sub(r"@[A-Za-z0-9_]+|#[A-Za-z0-9_]+", " ", cleaned)
    tokens = re.findall(r"\b[a-z]{4,}\b", cleaned)
    return [token for token in tokens if token not in STOPWORDS]


def extract_top_keywords(df: pd.DataFrame, top_n: int = 25) -> list[dict]:
    if df.empty or "post_content" not in df.columns:
        return []

    texts = []
    engagements = []
    for _, row in df.iterrows():
        tokens = tokenize_meaningful_words(str(row.get("post_content", "")))
        if tokens:
            texts.append(" ".join(tokens))
            engagements.append(float(row.get("total_engagement", 0) or 0))

    if not texts:
        return []

    word_counts: Counter[str] = Counter()
    word_eng: dict[str, list[float]] = {}
    for text, eng in zip(texts, engagements):
        unique_tokens = set(text.split())
        for tok in text.split():
            word_counts[tok] += 1
        for tok in unique_tokens:
            word_eng.setdefault(tok, []).append(eng)

    tfidf_scores: dict[str, float] = {}
    try:
        vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            max_features=max(top_n * 3, 60),
            stop_words="english",
            min_df=1,
        )
        matrix = vectorizer.fit_transform(texts)
        totals = np.asarray(matrix.sum(axis=0)).ravel()
        for term, score in zip(vectorizer.get_feature_names_out(), totals):
            tfidf_scores[str(term)] = float(round(score, 3))
    except Exception:
        pass

    results = []
    if tfidf_scores:
        for term, score in sorted(tfidf_scores.items(), key=lambda x: x[1], reverse=True)[:top_n]:
            freq = word_counts.get(term, 0)
            if freq == 0:
                freq = sum(1 for text in texts if term in text)
            matching_eng = [
                eng for text, eng in zip(texts, engagements) if term in text
            ]
            results.append(
                {
                    "keyword": term,
                    "tfidf_score": score,
                    "frequency": int(freq),
                    "avg_engagement": round(float(np.mean(matching_eng)), 1)
                    if matching_eng
                    else 0.0,
                }
            )
    else:
        for term, freq in word_counts.most_common(top_n):
            results.append(
                {
                    "keyword": term,
                    "tfidf_score": float(freq),
                    "frequency": int(freq),
                    "avg_engagement": round(float(np.mean(word_eng.get(term, [0]))), 1),
                }
            )
    return results


def compute_topic_clusters(df: pd.DataFrame, max_clusters: int = 8) -> list[dict]:
    """Cluster posts using TF-IDF + KMeans into interpretable discussion themes."""
    if df.empty or "post_content" not in df.columns:
        return []

    work = df.copy().reset_index(drop=True)
    docs = [
        " ".join(tokenize_meaningful_words(str(val)))
        for val in work["post_content"].fillna("")
    ]
    valid_indices = [idx for idx, doc in enumerate(docs) if len(doc.strip()) > 0]
    if len(valid_indices) < 4:
        return [
            {
                "cluster_id": 0,
                "label": str(work["topic"].mode().iloc[0]) if "topic" in work.columns and not work["topic"].empty else "General Discussion",
                "keywords": [k["keyword"] for k in extract_top_keywords(work, top_n=5)],
                "post_count": int(len(work)),
                "share_pct": 100.0,
                "avg_engagement": round(float(work["total_engagement"].mean()), 1) if "total_engagement" in work.columns else 0.0,
                "dominant_sentiment": str(work["sentiment"].mode().iloc[0]) if "sentiment" in work.columns and not work["sentiment"].empty else "Neutral",
                "sample_posts": [
                    {
                        "post_id": str(row.get("post_id", "")),
                        "platform": str(row.get("platform", "Unknown")),
                        "content": str(row.get("post_content", ""))[:180],
                        "engagement": int(row.get("total_engagement", 0)),
                        "sentiment": str(row.get("sentiment", "Neutral")),
                    }
                    for _, row in work.sort_values("total_engagement", ascending=False).head(5).iterrows()
                ],
            }
        ]

    valid_docs = [docs[idx] for idx in valid_indices]
    n_clusters = min(max_clusters, max(2, min(len(valid_docs) // 12 or 2, 8)))
    if len(valid_docs) < n_clusters:
        n_clusters = max(2, len(valid_docs) // 2)

    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        max_features=400,
        stop_words="english",
        min_df=1,
    )
    X = vectorizer.fit_transform(valid_docs)
    terms = vectorizer.get_feature_names_out()

    model = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = model.fit_predict(X)
    centroids = model.cluster_centers_

    work["cluster_id"] = -1
    for pos, orig_idx in enumerate(valid_indices):
        work.at[orig_idx, "cluster_id"] = int(labels[pos])

    total_posts = len(work)
    clusters = []
    for cluster_idx in range(n_clusters):
        subset = work[work["cluster_id"] == cluster_idx]
        if subset.empty:
            continue
        top_term_indices = centroids[cluster_idx].argsort()[::-1][:6]
        keywords = [str(terms[i]) for i in top_term_indices if centroids[cluster_idx][i] > 0][:6]

        dominant_topic = None
        if "topic" in subset.columns:
            non_uncat = subset[subset["topic"] != "Uncategorized"]["topic"]
            if not non_uncat.empty:
                dominant_topic = str(non_uncat.mode().iloc[0])

        label = (
            dominant_topic
            if dominant_topic
            else " / ".join(word.title() for word in keywords[:3]) or f"Cluster {cluster_idx + 1}"
        )

        dom_sentiment = (
            str(subset["sentiment"].mode().iloc[0])
            if "sentiment" in subset.columns and not subset["sentiment"].empty
            else "Neutral"
        )
        avg_eng = (
            round(float(subset["total_engagement"].mean()), 1)
            if "total_engagement" in subset.columns
            else 0.0
        )

        sample_posts = [
            {
                "post_id": str(row.get("post_id", "")),
                "platform": str(row.get("platform", "Unknown")),
                "content": str(row.get("post_content", ""))[:180],
                "engagement": int(row.get("total_engagement", 0)),
                "sentiment": str(row.get("sentiment", "Neutral")),
            }
            for _, row in subset.sort_values("total_engagement", ascending=False).head(5).iterrows()
        ]

        clusters.append(
            {
                "cluster_id": int(cluster_idx),
                "label": label,
                "keywords": keywords,
                "post_count": int(len(subset)),
                "share_pct": round(len(subset) / total_posts * 100, 1),
                "avg_engagement": avg_eng,
                "dominant_sentiment": dom_sentiment,
                "sample_posts": sample_posts,
            }
        )

    return sorted(clusters, key=lambda item: item["post_count"], reverse=True)

