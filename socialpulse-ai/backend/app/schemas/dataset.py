from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class DatasetSummary(BaseModel):
    id: int
    name: str
    original_filename: str
    row_count: int
    cleaned_row_count: int
    column_count: int
    duplicate_count: int
    missing_value_count: int
    invalid_record_count: int = 0
    status: str = "ready"
    column_mapping: dict[str, str]
    cleaning_summary: dict[str, Any] = {}
    is_bundled: bool = False
    is_active: bool
    owner_id: int | None = None
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
    invalid_record_count: int = 0
    column_mapping: dict[str, str]
    cleaning_summary: dict[str, Any] = {}


class UserRegisterRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not any(char.isdigit() for char in value):
            raise ValueError("Password must contain at least one number.")
        if not any(char.isalpha() for char in value):
            raise ValueError("Password must contain at least one letter.")
        return value
    full_name: str = Field(..., min_length=2, max_length=120)
    role: str = Field(default="Social Media Analyst", max_length=120)
    organization: str = Field(default="", max_length=255)


class UserLoginRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=1, max_length=128)


class UserProfileUpdateRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=120)
    role: str = Field(default="Social Media Analyst", max_length=120)
    organization: str = Field(default="", max_length=255)
    bio: str = Field(default="", max_length=1000)


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        if not any(char.isdigit() for char in value):
            raise ValueError("Password must contain at least one number.")
        if not any(char.isalpha() for char in value):
            raise ValueError("Password must contain at least one letter.")
        return value


class AssistantQueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    dataset_id: int | None = None
    history: list[dict[str, str]] = Field(default_factory=list)


class ReportGenerateRequest(BaseModel):
    report_type: str = Field(default="overall")
    format: str = Field(default="pdf")
    dataset_id: int | None = None
    platform: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    title: str | None = None
