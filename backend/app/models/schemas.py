"""Pydantic models for request/response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class DatasetInfo(BaseModel):
    """Metadata about an uploaded dataset."""

    id: str
    filename: str
    rows: int
    columns: int
    column_names: list[str]
    column_types: dict[str, str]
    missing_values: dict[str, int]
    duplicate_rows: int
    file_size: int
    uploaded_at: datetime


class AnalysisRequest(BaseModel):
    """Incoming question + context for analysis."""

    question: str
    dataset_ids: list[str] = Field(default_factory=list)
    conversation_history: list[dict[str, Any]] = Field(default_factory=list)


class AnalysisResponse(BaseModel):
    """Full analysis result returned to the frontend."""

    answer: str
    data: Optional[dict[str, Any] | list[Any]] = None
    chart_config: Optional[dict[str, Any]] = None
    sql_code: Optional[str] = None
    pandas_code: Optional[str] = None
    anomalies: Optional[list[dict[str, Any]]] = None
    insights: Optional[list[dict[str, Any]]] = None
    error: Optional[str] = None


class InsightsRequest(BaseModel):
    """Request automated insights for a dataset."""

    dataset_id: str


class InsightsResponse(BaseModel):
    """Automated insights generated from a dataset."""

    kpis: list[dict[str, Any]] = Field(default_factory=list)
    top_performers: list[Any] = Field(default_factory=list)
    trends: list[Any] = Field(default_factory=list)
    anomalies: list[Any] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class DataPreviewResponse(BaseModel):
    """Preview of dataset rows + schema information."""

    columns: list[str]
    dtypes: dict[str, str]
    preview_data: list[dict[str, Any]]
    total_rows: int
    missing_summary: dict[str, int]
    duplicate_count: int
