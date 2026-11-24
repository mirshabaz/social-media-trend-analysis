import pandas as pd
from fastapi import HTTPException

from app.services.dataset_service import clean_dataframe, detect_column_mapping


def test_flexible_column_mapping():
    mapping = detect_column_mapping(
        ["Post ID", "Network", "Tweet", "Like Count", "Retweets", "Reply Count"]
    )

    assert mapping["post_id"] == "Post ID"
    assert mapping["platform"] == "Network"
    assert mapping["post_content"] == "Tweet"
    assert mapping["likes"] == "Like Count"
    assert mapping["shares"] == "Retweets"
    assert mapping["comments"] == "Reply Count"


def test_clean_dataframe_calculates_engagement_and_removes_empty_text():
    df = pd.DataFrame(
        {
            "post_id": ["P1", "P2", "P3"],
            "post_content": ["Great AI update!", "   ", "A useful post"],
            "likes": [10, 4, "3"],
            "shares": [2, 1, None],
            "comments": [1, 0, 2],
        }
    )

    cleaned = clean_dataframe(df, detect_column_mapping(list(df.columns)))

    assert len(cleaned) == 2
    assert cleaned["total_engagement"].tolist() == [13, 5]
    assert cleaned["platform"].tolist() == ["Unknown", "Unknown"]
    assert cleaned["author"].tolist() == ["Unknown", "Unknown"]


def test_clean_dataframe_rejects_missing_text_column():
    df = pd.DataFrame({"id": [1, 2], "likes": [10, 20]})

    try:
        clean_dataframe(df, detect_column_mapping(list(df.columns)))
        raise AssertionError("Expected missing-text validation to fail")
    except HTTPException as exc:
        assert exc.status_code == 422
