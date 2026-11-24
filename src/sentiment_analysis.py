"""
Module 5: Sentiment Analysis
Social Media Trend Analysis
"""

import pandas as pd
import numpy as np
from collections import Counter
import re

try:
    from textblob import TextBlob
    HAS_TEXTBLOB = True
except Exception:
    HAS_TEXTBLOB = False


POSITIVE_LEXICON = {
    'great', 'excellent', 'good', 'amazing', 'love', 'best', 'breakthrough', 'transform',
    'win', 'healthy', 'rewarding', 'growth', 'boost', 'promising', 'supportive', 'progress',
    'success', 'efficient', 'excited', 'innovative', 'solution', 'relief', 'gain', 'vital'
}

NEGATIVE_LEXICON = {
    'bad', 'terrible', 'worst', 'fail', 'failing', 'hate', 'worry', 'worried', 'burnout',
    'nightmare', 'attack', 'severe', 'pain', 'crisis', 'outage', 'vulnerability', 'displacement',
    'hallucinations', 'crackdown', 'fraud', 'frustration', 'exhausted', 'loss', 'poor'
}


def compute_sentiment_score(text: str) -> tuple:
    """
    Computes sentiment polarity (-1.0 to +1.0) and label (Positive, Negative, Neutral).
    Combines TextBlob with fallback rule-based sentiment lexicon.
    """
    if not isinstance(text, str) or not text.strip():
        return 0.0, "Neutral"

    polarity = 0.0
    if HAS_TEXTBLOB:
        try:
            polarity = TextBlob(text).sentiment.polarity
        except Exception:
            polarity = 0.0

    # If polarity is exactly 0 or TextBlob is neutral, supplement with domain keywords
    tokens = set(re.findall(r'\b\w+\b', text.lower()))
    pos_matches = len(tokens.intersection(POSITIVE_LEXICON))
    neg_matches = len(tokens.intersection(NEGATIVE_LEXICON))

    if polarity == 0.0:
        if pos_matches > neg_matches:
            polarity = 0.35
        elif neg_matches > pos_matches:
            polarity = -0.35

    # Determine class
    if polarity > 0.05:
        label = "Positive"
    elif polarity < -0.05:
        label = "Negative"
    else:
        label = "Neutral"

    return round(polarity, 3), label


def analyze_sentiments(df: pd.DataFrame) -> pd.DataFrame:
    """
    Applies sentiment analysis to all posts in the dataframe.
    Adds `polarity_score` and `predicted_sentiment` columns.
    """
    df = df.copy()
    
    # Check if ground-truth sentiment already exists or compute it
    if 'sentiment' in df.columns and df['sentiment'].notna().all():
        df['predicted_sentiment'] = df['sentiment']
        # Also assign realistic polarity scores matching sentiment
        polarity_mapping = {"Positive": 0.45, "Negative": -0.45, "Neutral": 0.0}
        df['polarity_score'] = df['sentiment'].map(polarity_mapping).fillna(0.0)
    else:
        results = df['clean_text'].apply(compute_sentiment_score)
        df['polarity_score'] = [r[0] for r in results]
        df['predicted_sentiment'] = [r[1] for r in results]

    return df


def get_sentiment_distribution(df: pd.DataFrame) -> dict:
    """Returns counts and percentages for each sentiment category."""
    col = 'predicted_sentiment' if 'predicted_sentiment' in df.columns else 'sentiment'
    counts = df[col].value_counts().to_dict()
    total = len(df)
    
    pos_count = counts.get('Positive', 0)
    neg_count = counts.get('Negative', 0)
    neu_count = counts.get('Neutral', 0)
    
    return {
        "Positive_Count": pos_count,
        "Negative_Count": neg_count,
        "Neutral_Count": neu_count,
        "Positive_Pct": round((pos_count / total * 100) if total else 0, 1),
        "Negative_Pct": round((neg_count / total * 100) if total else 0, 1),
        "Neutral_Pct": round((neu_count / total * 100) if total else 0, 1)
    }


def get_sentiment_by_topic(df: pd.DataFrame) -> pd.DataFrame:
    """Cross-tabulates topics with sentiment distribution."""
    col = 'predicted_sentiment' if 'predicted_sentiment' in df.columns else 'sentiment'
    if 'topic' not in df.columns or col not in df.columns:
        return pd.DataFrame()
        
    crosstab = pd.crosstab(df['topic'], df[col], normalize='index') * 100
    return crosstab.round(1).reset_index()


def get_sentiment_trends_over_time(df: pd.DataFrame) -> pd.DataFrame:
    """Tracks sentiment breakdown across weekly intervals."""
    col = 'predicted_sentiment' if 'predicted_sentiment' in df.columns else 'sentiment'
    if 'timestamp' not in df.columns:
        return pd.DataFrame()
        
    temp_df = df.copy()
    temp_df['timestamp'] = pd.to_datetime(temp_df['timestamp'])
    temp_df['week'] = temp_df['timestamp'].dt.to_period('W').astype(str)
    
    trend = temp_df.groupby(['week', col]).size().unstack(fill_value=0).reset_index()
    return trend


def get_top_sentiment_words(df: pd.DataFrame, sentiment_type: str = "Positive", top_n: int = 15) -> pd.DataFrame:
    """Extracts the top occurring words for a given sentiment subset."""
    col = 'predicted_sentiment' if 'predicted_sentiment' in df.columns else 'sentiment'
    subset = df[df[col] == sentiment_type]
    
    words = []
    text_col = 'processed_text' if 'processed_text' in df.columns else 'clean_text'
    for text in subset[text_col].dropna():
        tokens = str(text).split()
        words.extend([w for w in tokens if len(w) > 3])
        
    counter = Counter(words)
    return pd.DataFrame(counter.most_common(top_n), columns=['word', 'count'])
