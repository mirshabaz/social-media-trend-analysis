from datetime import datetime
from typing import Any

from pydantic import BaseModel


class DatasetSummary(BaseModel):
    id: int
    name: str
    original_filename: str
    row_count: int
    cleaned_row_count: int
    column_count: int
    duplicate_count: int
    missing_value_count: int
    column_mapping: dict[str, str]
    is_active: bool
    created_at: datetime


class DatasetPreview(BaseModel):
    id: int
    name: str
    columns: list[str]
    rows: list[dict[str, Any]]
    row_count: int
    cleaned_row_count: int
    missing_values: dict[str, int]
    duplicate_count: int
    column_mapping: dict[str, str]
