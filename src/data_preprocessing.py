"""
Module 2: Data Preprocessing
Social Media Trend Analysis
Author: Data Science Intern
"""

import re
import string
import pandas as pd
import numpy as np

# Robust built-in stopwords list to ensure smooth execution even if NLTK corpus download is delayed
DEFAULT_STOPWORDS = set([
    'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you', "you're", "you've",
    "you'll", "you'd", 'your', 'yours', 'yourself', 'yourselves', 'he', 'him', 'his', 'himself',
    'she', "she's", 'her', 'hers', 'herself', 'it', "it's", 'its', 'itself', 'they', 'them',
    'their', 'theirs', 'themselves', 'what', 'which', 'who', 'whom', 'this', 'that', "that'll",
    'these', 'those', 'am', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has',
    'had', 'having', 'do', 'does', 'did', 'doing', 'a', 'an', 'the', 'and', 'but', 'if', 'or',
    'because', 'as', 'until', 'while', 'of', 'at', 'by', 'for', 'with', 'about', 'against',
    'between', 'into', 'through', 'during', 'before', 'after', 'above', 'below', 'to', 'from',
    'up', 'down', 'in', 'out', 'on', 'off', 'over', 'under', 'again', 'further', 'then', 'once',
    'here', 'there', 'when', 'where', 'why', 'how', 'all', 'any', 'both', 'each', 'few', 'more',
    'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than',
    'too', 'very', 's', 't', 'can', 'will', 'just', 'don', "don't", 'should', "should've",
    'now', 'd', 'll', 'm', 'o', 're', 've', 'y', 'ain', 'aren', "aren't", 'couldn', "couldn't",
    'didn', "didn't", 'doesn', "doesn't", 'hadn', "hadn't", 'hasn', "hasn't", 'haven', "haven't",
    'isn', "isn't", 'ma', 'mightn', "mightn't", 'mustn', "mustn't", 'needn', "needn't", 'shan',
    "shan't", 'shouldn', "shouldn't", 'wasn', "wasn't", 'weren', "weren't", 'won', "won't",
    'wouldn', "wouldn't", 'today', 'also', 'get', 'got', 'like', 'one', 'new'
])

try:
    import nltk
    from nltk.corpus import stopwords
    nltk.download('stopwords', quiet=True)
    nltk.download('punkt', quiet=True)
    nltk_stopwords = set(stopwords.words('english'))
    STOPWORDS = DEFAULT_STOPWORDS.union(nltk_stopwords)
except Exception:
    STOPWORDS = DEFAULT_STOPWORDS


def clean_text(text: str) -> str:
    """
    Cleans raw social media post text:
    - Lowercase conversion
    - URL removal
    - Mention removal (@user)
    - Punctuation & special character removal (retaining words)
    - Multiple whitespace normalization
    """
    if not isinstance(text, str):
        return ""

    # Convert to lowercase
    text = text.lower()

    # Remove URLs (http, https, www)
    text = re.sub(r'https?://\S+|www\.\S+', '', text)

    # Remove user mentions (@username)
    text = re.sub(r'@\w+', '', text)

    # Remove HTML tags if any
    text = re.sub(r'<.*?>', '', text)

    # Remove emojis and non-ascii characters
    text = text.encode('ascii', 'ignore').decode('ascii')

    # Remove punctuation
    text = text.translate(str.maketrans('', '', string.punctuation))

    # Remove standalone numbers
    text = re.sub(r'\b\d+\b', '', text)

    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    return text


def remove_stopwords(text: str) -> str:
    """Removes common stopwords from the cleaned text."""
    words = text.split()
    filtered_words = [w for w in words if w not in STOPWORDS and len(w) > 2]
    return " ".join(filtered_words)


def extract_hashtags(text: str) -> list:
    """Extracts hashtag list from post text or hashtag column."""
    if not isinstance(text, str):
        return []
    tags = re.findall(r'#(\w+)', text)
    return [t.lower() for t in tags]


def preprocess_social_media_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Complete preprocessing pipeline for social media dataset:
    1. Removes duplicate posts
    2. Handles missing values
    3. Formats timestamps
    4. Cleans text content
    5. Removes stopwords
    6. Computes token length and total engagement
    """
    df = df.copy()

    # 1. Deduplication
    initial_count = len(df)
    df = df.drop_duplicates(subset=['post_content'])
    df = df.drop_duplicates(subset=['post_id'])

    # 2. Missing Value Imputation
    df['post_content'] = df['post_content'].fillna("")
    df['platform'] = df['platform'].fillna("Unknown")
    df['author'] = df['author'].fillna("anonymous_user")
    df['hashtags'] = df['hashtags'].fillna("")
    
    # Fill numeric missing values
    for col in ['likes', 'shares', 'comments']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

    # 3. Timestamp parsing
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        # Fill invalid dates with default current or median date
        df['timestamp'] = df['timestamp'].fillna(pd.Timestamp.now())
        df['date'] = df['timestamp'].dt.date
        df['hour'] = df['timestamp'].dt.hour
        df['day_name'] = df['timestamp'].dt.day_name()
        df['month_year'] = df['timestamp'].dt.to_period('M').astype(str)

    # 4. Text cleaning
    df['clean_text'] = df['post_content'].apply(clean_text)

    # 5. Stopwords removal
    df['processed_text'] = df['clean_text'].apply(remove_stopwords)

    # 6. Extract clean hashtags list
    if 'extracted_hashtags' not in df.columns:
        df['extracted_hashtags'] = df['post_content'].apply(extract_hashtags)

    # 7. Post character and word length
    df['char_length'] = df['post_content'].apply(len)
    df['word_count'] = df['processed_text'].apply(lambda x: len(x.split()))

    # 8. Total engagement calculation
    df['total_engagement'] = df['likes'] + df['shares'] + df['comments']
    df['engagement_rate'] = (
        (df['likes'] * 1.0) + (df['comments'] * 2.0) + (df['shares'] * 3.0)
    ).astype(float)

    return df


if __name__ == "__main__":
    import os
    dataset_path = os.path.join(os.path.dirname(__file__), "..", "dataset", "social_media_data.csv")
    if os.path.exists(dataset_path):
        raw_df = pd.read_csv(dataset_path)
        print(f"Loaded raw dataset with {len(raw_df)} rows.")
        clean_df = preprocess_social_media_data(raw_df)
        print(f"Preprocessed dataset has {len(clean_df)} clean rows.")
        print(clean_df[['post_id', 'platform', 'clean_text', 'total_engagement']].head(3))
