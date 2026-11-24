"""
Module 4: Trending Topic Detection
Social Media Trend Analysis
"""

import pandas as pd
import numpy as np
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer


def get_top_topics(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """
    Identifies top discussed topics by post volume, total engagement, and average engagement.
    """
    if 'topic' in df.columns:
        topic_summary = df.groupby('topic').agg(
            post_count=('post_id', 'count'),
            total_engagement=('total_engagement', 'sum'),
            avg_engagement=('total_engagement', 'mean'),
            total_likes=('likes', 'sum'),
            total_shares=('shares', 'sum'),
            total_comments=('comments', 'sum')
        ).reset_index()
        
        topic_summary['topic_share_pct'] = (
            topic_summary['post_count'] / topic_summary['post_count'].sum() * 100
        ).round(2)
        
        return topic_summary.sort_values(by='post_count', ascending=False).head(top_n)
    else:
        # Fallback to TF-IDF keyphrase extraction if topic column does not exist
        return extract_key_phrases(df, top_n=top_n)


def extract_key_phrases(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """Extracts top trending n-grams using TF-IDF."""
    texts = df['processed_text'].dropna().tolist()
    if not texts:
        return pd.DataFrame()
        
    tfidf = TfidfVectorizer(ngram_range=(1, 2), max_features=top_n, stop_words='english')
    X = tfidf.fit_transform(texts)
    scores = np.asarray(X.sum(axis=0)).ravel()
    features = tfidf.get_feature_names_out()
    
    phrase_df = pd.DataFrame({'topic': features, 'post_count': scores.round(1)})
    phrase_df['total_engagement'] = phrase_df['post_count'] * 100
    phrase_df['avg_engagement'] = phrase_df['total_engagement'] / (phrase_df['post_count'] + 1)
    phrase_df['topic_share_pct'] = (phrase_df['post_count'] / phrase_df['post_count'].sum() * 100).round(2)
    return phrase_df.sort_values(by='post_count', ascending=False)


def get_topic_trends_over_time(df: pd.DataFrame, top_topics: list = None) -> pd.DataFrame:
    """
    Tracks how the top trending topics evolve week-over-week.
    """
    if 'timestamp' not in df.columns or 'topic' not in df.columns:
        return pd.DataFrame()
        
    temp_df = df.copy()
    temp_df['timestamp'] = pd.to_datetime(temp_df['timestamp'])
    temp_df['week'] = temp_df['timestamp'].dt.to_period('W').astype(str)
    
    if top_topics is None:
        top_topics = temp_df['topic'].value_counts().head(5).index.tolist()
        
    filtered = temp_df[temp_df['topic'].isin(top_topics)]
    pivot_df = filtered.groupby(['week', 'topic']).size().unstack(fill_value=0).reset_index()
    return pivot_df
