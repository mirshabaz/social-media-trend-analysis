"""
Module 3: Exploratory Data Analysis (EDA)
Social Media Trend Analysis
"""

import pandas as pd
import numpy as np
from collections import Counter
import re


def get_summary_kpis(df: pd.DataFrame) -> dict:
    """Calculates overall high-level KPIs for posts, likes, shares, comments."""
    return {
        "total_posts": int(len(df)),
        "total_likes": int(df['likes'].sum() if 'likes' in df.columns else 0),
        "total_shares": int(df['shares'].sum() if 'shares' in df.columns else 0),
        "total_comments": int(df['comments'].sum() if 'comments' in df.columns else 0),
        "total_engagement": int(df['total_engagement'].sum() if 'total_engagement' in df.columns else 0),
        "avg_likes_per_post": float(df['likes'].mean() if 'likes' in df.columns else 0),
        "avg_shares_per_post": float(df['shares'].mean() if 'shares' in df.columns else 0),
        "avg_comments_per_post": float(df['comments'].mean() if 'comments' in df.columns else 0)
    }


def get_popular_hashtags(df: pd.DataFrame, top_n: int = 15) -> pd.DataFrame:
    """Extracts and counts the most frequent hashtags."""
    all_tags = []
    if 'extracted_hashtags' in df.columns:
        for tags in df['extracted_hashtags']:
            if isinstance(tags, list):
                all_tags.extend(tags)
    elif 'hashtags' in df.columns:
        for text in df['hashtags'].dropna():
            tags = re.findall(r'#?(\w+)', str(text))
            all_tags.extend([t.lower() for t in tags if t.strip()])

    counter = Counter(all_tags)
    tag_df = pd.DataFrame(counter.most_common(top_n), columns=['hashtag', 'count'])
    tag_df['hashtag'] = tag_df['hashtag'].apply(lambda x: f"#{x}" if not x.startswith('#') else x)
    return tag_df


def get_frequent_words(df: pd.DataFrame, top_n: int = 20) -> pd.DataFrame:
    """Extracts top occurring words in processed clean text."""
    words = []
    text_series = df['processed_text'] if 'processed_text' in df.columns else df['clean_text']
    for text in text_series.dropna():
        tokens = str(text).split()
        words.extend([w for w in tokens if len(w) > 3])
    
    counter = Counter(words)
    word_df = pd.DataFrame(counter.most_common(top_n), columns=['word', 'frequency'])
    return word_df


def get_platform_activity(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregates post counts and engagement metrics by platform."""
    if 'platform' not in df.columns:
        return pd.DataFrame()
    
    activity = df.groupby('platform').agg(
        total_posts=('post_id', 'count'),
        total_likes=('likes', 'sum'),
        total_shares=('shares', 'sum'),
        total_comments=('comments', 'sum'),
        total_engagement=('total_engagement', 'sum'),
        avg_likes=('likes', 'mean'),
        avg_shares=('shares', 'mean'),
        avg_comments=('comments', 'mean')
    ).reset_index()

    activity['post_share_pct'] = (activity['total_posts'] / activity['total_posts'].sum() * 100).round(2)
    return activity.sort_values(by='total_posts', ascending=False)


def get_temporal_activity(df: pd.DataFrame, freq: str = 'D') -> pd.DataFrame:
    """Analyzes posting activity over time."""
    if 'timestamp' not in df.columns:
        return pd.DataFrame()
    
    temp_df = df.copy()
    temp_df['timestamp'] = pd.to_datetime(temp_df['timestamp'])
    temp_df = temp_df.set_index('timestamp')
    
    resampled = temp_df.resample(freq).agg(
        post_count=('post_id', 'count'),
        likes=('likes', 'sum'),
        shares=('shares', 'sum'),
        comments=('comments', 'sum'),
        total_engagement=('total_engagement', 'sum')
    ).reset_index()

    return resampled
