"""
Module 6: Engagement Analysis
Social Media Trend Analysis
"""

import pandas as pd
import numpy as np


def get_top_engaging_posts(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """
    Retrieves the top N posts with the highest total engagement (likes + shares + comments).
    """
    cols_to_show = [
        'post_id', 'platform', 'author', 'post_content',
        'likes', 'shares', 'comments', 'total_engagement'
    ]
    available_cols = [c for c in cols_to_show if c in df.columns]
    
    top_posts = df.sort_values(by='total_engagement', ascending=False).head(top_n)
    return top_posts[available_cols]


def get_platform_engagement_comparison(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compares average and median engagement metrics across platforms.
    """
    if 'platform' not in df.columns:
        return pd.DataFrame()
        
    summary = df.groupby('platform').agg(
        post_count=('post_id', 'count'),
        total_likes=('likes', 'sum'),
        total_shares=('shares', 'sum'),
        total_comments=('comments', 'sum'),
        total_engagement=('total_engagement', 'sum'),
        avg_likes=('likes', 'mean'),
        avg_shares=('shares', 'mean'),
        avg_comments=('comments', 'mean'),
        avg_total_engagement=('total_engagement', 'mean'),
        median_engagement=('total_engagement', 'median')
    ).reset_index()

    return summary.sort_values(by='avg_total_engagement', ascending=False)


def get_most_engaging_hashtags(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """
    Computes total and average engagement per hashtag.
    """
    hashtag_engagement = []
    
    for _, row in df.iterrows():
        tags = row.get('extracted_hashtags', [])
        engagement = row.get('total_engagement', 0)
        likes = row.get('likes', 0)
        shares = row.get('shares', 0)
        comments = row.get('comments', 0)
        
        if isinstance(tags, list):
            for t in tags:
                hashtag_engagement.append({
                    'hashtag': f"#{t}",
                    'engagement': engagement,
                    'likes': likes,
                    'shares': shares,
                    'comments': comments
                })

    if not hashtag_engagement:
        return pd.DataFrame()
        
    tag_df = pd.DataFrame(hashtag_engagement)
    summary = tag_df.groupby('hashtag').agg(
        occurrence=('engagement', 'count'),
        total_engagement=('engagement', 'sum'),
        avg_engagement=('engagement', 'mean'),
        avg_likes=('likes', 'mean')
    ).reset_index()
    
    # Filter hashtags with at least 5 mentions for statistical relevance
    filtered = summary[summary['occurrence'] >= 5]
    if len(filtered) < top_n:
        filtered = summary
        
    return filtered.sort_values(by='total_engagement', ascending=False).head(top_n)


def get_engagement_correlation(df: pd.DataFrame) -> pd.DataFrame:
    """Computes correlation matrix among likes, shares, comments, and character length."""
    num_cols = ['likes', 'shares', 'comments', 'total_engagement']
    if 'char_length' in df.columns:
        num_cols.append('char_length')
        
    return df[num_cols].corr().round(2)
