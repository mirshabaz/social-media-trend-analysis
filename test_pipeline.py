"""
Automated Test & Artifact Generation Pipeline
Social Media Trend Analysis
"""

import os
import sys
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(BASE_DIR, "src")
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")
os.makedirs(OUTPUTS_DIR, exist_ok=True)

sys.path.append(SRC_DIR)

from data_preprocessing import preprocess_social_media_data
from exploratory_analysis import (
    get_summary_kpis,
    get_popular_hashtags,
    get_platform_activity,
    get_frequent_words
)
from trend_detection import get_top_topics, get_topic_trends_over_time
from sentiment_analysis import analyze_sentiments, get_sentiment_distribution, get_sentiment_by_topic
from engagement_analysis import get_top_engaging_posts, get_platform_engagement_comparison, get_engagement_correlation

def run_pipeline():
    print("=" * 60)
    print("RUNNING END-TO-END SOCIAL MEDIA TREND ANALYSIS PIPELINE")
    print("=" * 60)
    
    # 1. Load Data
    csv_path = os.path.join(BASE_DIR, "dataset", "social_media_data.csv")
    assert os.path.exists(csv_path), f"Dataset not found at {csv_path}"
    df_raw = pd.read_csv(csv_path)
    print(f"[✓] Step 1: Raw data loaded successfully. Total rows: {len(df_raw)}")
    
    # 2. Preprocessing
    df_clean = preprocess_social_media_data(df_raw)
    print(f"[✓] Step 2: Data Preprocessed. Clean rows: {len(df_clean)}")
    
    # 3. Exploratory Analysis
    kpis = get_summary_kpis(df_clean)
    print(f"[✓] Step 3: KPIs generated -> Posts: {kpis['total_posts']}, Total Interactions: {kpis['total_engagement']}")
    
    # 4. Trending Topics
    top_topics = get_top_topics(df_clean, top_n=10)
    print(f"[✓] Step 4: Top 10 Trending Topics Detected. #1: {top_topics.iloc[0]['topic']}")
    
    # 5. Sentiment Analysis
    df_sentiment = analyze_sentiments(df_clean)
    dist = get_sentiment_distribution(df_sentiment)
    print(f"[✓] Step 5: Sentiment Breakdown -> Pos: {dist['Positive_Pct']}%, Neg: {dist['Negative_Pct']}%, Neu: {dist['Neutral_Pct']}%")
    
    # 6. Engagement Analysis
    top_posts = get_top_engaging_posts(df_sentiment, top_n=5)
    print(f"[✓] Step 6: Most Engaging Post ID: {top_posts.iloc[0]['post_id']} ({top_posts.iloc[0]['total_engagement']} interactions)")
    
    # 7. Generate & Save Visualizations
    plt.style.use('default')
    
    # Plot 1: Sentiment Distribution
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.pie(
        [dist['Positive_Count'], dist['Negative_Count'], dist['Neutral_Count']],
        labels=['Positive', 'Negative', 'Neutral'],
        autopct='%1.1f%%',
        colors=['#10b981', '#ef4444', '#64748b'],
        startangle=140
    )
    ax.set_title("Overall Sentiment Distribution")
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUTS_DIR, "sentiment_distribution.png"), dpi=200)
    plt.close()
    
    # Plot 2: Top Trending Topics
    fig, ax = plt.subplots(figsize=(10, 5))
    sns.barplot(data=top_topics, x='post_count', y='topic', palette='viridis', ax=ax)
    ax.set_title("Top 10 Trending Topics by Post Count")
    ax.set_xlabel("Number of Posts")
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUTS_DIR, "trending_topics.png"), dpi=200)
    plt.close()

    # Plot 3: Engagement Correlation
    corr = get_engagement_correlation(df_sentiment)
    fig, ax = plt.subplots(figsize=(7, 5))
    sns.heatmap(corr, annot=True, cmap='Blues', fmt='.2f', ax=ax)
    ax.set_title("Correlation Heatmap of Engagement Metrics")
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUTS_DIR, "engagement_correlation.png"), dpi=200)
    plt.close()
    
    print(f"[✓] Step 7: Saved sample figures to {OUTPUTS_DIR}")
    print("=" * 60)
    print("ALL MODULES TESTED AND OPERATIONAL!")
    print("=" * 60)

if __name__ == "__main__":
    run_pipeline()
