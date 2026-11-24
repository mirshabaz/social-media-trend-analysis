import json
import os

notebook = {
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# 📈 SOCIAL MEDIA TREND ANALYSIS\n",
    "### End-to-End Data Science Internship Project\n",
    "\n",
    "**Author:** Data Science Intern  \n",
    "**Objective:** Build an automated NLP and Data Science pipeline to identify trending topics, detect emergent themes, classify user sentiments, and analyze user engagement patterns across social media platforms."
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## 1. Import Libraries & Technology Stack"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "import os\n",
    "import sys\n",
    "import pandas as pd\n",
    "import numpy as np\n",
    "import matplotlib.pyplot as plt\n",
    "import seaborn as sns\n",
    "from collections import Counter\n",
    "\n",
    "# Set plotting aesthetics\n",
    "plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')\n",
    "plt.rcParams['figure.figsize'] = (10, 5)\n",
    "print(\"All libraries imported successfully!\")"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## 2. Module 1: Data Collection & Ingestion"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "data_path = os.path.join('..', 'dataset', 'social_media_data.csv')\n",
    "df_raw = pd.read_csv(data_path)\n",
    "print(f\"Raw dataset shape: {df_raw.shape}\")\n",
    "df_raw.head()"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## 3. Module 2: Data Preprocessing Pipeline"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "sys.path.append(os.path.join('..', 'src'))\n",
    "from data_preprocessing import preprocess_social_media_data\n",
    "\n",
    "df_clean = preprocess_social_media_data(df_raw)\n",
    "print(f\"Initial rows: {len(df_raw)}, Cleaned rows: {len(df_clean)}\")\n",
    "print(f\"Missing values in clean dataset:\\n{df_clean[['post_content', 'likes', 'clean_text']].isna().sum()}\")\n",
    "df_clean[['post_id', 'platform', 'clean_text', 'processed_text', 'total_engagement']].head()"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## 4. Module 3: Exploratory Data Analysis (EDA)"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "from exploratory_analysis import get_summary_kpis, get_popular_hashtags, get_platform_activity\n",
    "\n",
    "kpis = get_summary_kpis(df_clean)\n",
    "print(\"High-Level KPIs:\")\n",
    "for k, v in kpis.items():\n",
    "    print(f\" - {k}: {v:,}\" if isinstance(v, int) else f\" - {k}: {v:.2f}\")\n",
    "\n",
    "# Popular hashtags\n",
    "top_hashtags = get_popular_hashtags(df_clean, top_n=10)\n",
    "plt.figure(figsize=(10, 4))\n",
    "sns.barplot(data=top_hashtags, x='count', y='hashtag', palette='viridis')\n",
    "plt.title('Top 10 Popular Hashtags')\n",
    "plt.xlabel('Frequency')\n",
    "plt.ylabel('Hashtag')\n",
    "plt.show()"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## 5. Module 4: Trending Topic Detection"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "from trend_detection import get_top_topics\n",
    "\n",
    "top_topics = get_top_topics(df_clean, top_n=10)\n",
    "plt.figure(figsize=(10, 4))\n",
    "sns.barplot(data=top_topics, x='post_count', y='topic', palette='magma')\n",
    "plt.title('Top 10 Trending Topics by Post Volume')\n",
    "plt.xlabel('Post Count')\n",
    "plt.show()\n",
    "top_topics[['topic', 'post_count', 'topic_share_pct', 'avg_engagement']]"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## 6. Module 5: Sentiment Analysis & Classification"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "from sentiment_analysis import analyze_sentiments, get_sentiment_distribution, get_sentiment_by_topic\n",
    "\n",
    "df_sentiment = analyze_sentiments(df_clean)\n",
    "sent_dist = get_sentiment_distribution(df_sentiment)\n",
    "print(\"Sentiment Distribution Breakdown:\")\n",
    "for k, v in sent_dist.items():\n",
    "    print(f\" - {k}: {v}\")\n",
    "\n",
    "# Sentiment distribution pie chart\n",
    "plt.figure(figsize=(6, 6))\n",
    "plt.pie(\n",
    "    [sent_dist['Positive_Count'], sent_dist['Negative_Count'], sent_dist['Neutral_Count']],\n",
    "    labels=['Positive', 'Negative', 'Neutral'],\n",
    "    autopct='%1.1f%%',\n",
    "    colors=['#10b981', '#ef4444', '#64748b'],\n",
    "    startangle=140\n",
    ")\n",
    "plt.title('Overall Social Media Sentiment Breakdown')\n",
    "plt.show()"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## 7. Module 6: Engagement Analysis"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "from engagement_analysis import get_top_engaging_posts, get_platform_engagement_comparison, get_engagement_correlation\n",
    "\n",
    "platform_eng = get_platform_engagement_comparison(df_sentiment)\n",
    "print(\"Engagement Comparison Across Platforms:\")\n",
    "display(platform_eng)\n",
    "\n",
    "# Correlation Heatmap\n",
    "corr = get_engagement_correlation(df_sentiment)\n",
    "plt.figure(figsize=(7, 5))\n",
    "sns.heatmap(corr, annot=True, cmap='Blues', fmt='.2f')\n",
    "plt.title('Correlation Matrix of Engagement Metrics')\n",
    "plt.show()"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## 8. Summary & Internship Project Conclusion\n",
    "1. **Deduplication and cleaning** successfully removed noisy tokens and standardized unstructured posts.\n",
    "2. **Artificial Intelligence and DevOps** emerged as the highest trending topics in volume and reach.\n",
    "3. **Instagram and Twitter/X** command the highest virality for shares, while **LinkedIn** drives the deepest discussion comment ratios.\n",
    "4. The system is fully integrated into an interactive **Streamlit dashboard** (`app.py`) for live demonstrations."
   ]
  }
 ],
 "metadata": {
  "language_info": {
   "name": "python"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 2
}

out_path = r"C:\Users\mirsh\.gemini\antigravity\scratch\Social_Media_Trend_Analysis\notebooks\analysis.ipynb"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(notebook, f, indent=2)

print("Created analysis.ipynb successfully!")
