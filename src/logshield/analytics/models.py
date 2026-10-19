"""
Pydantic Data Models for Data Analytics & Dataset Profiling
"""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class ColumnStats(BaseModel):
    name: str
    dtype: str
    total_count: int
    null_count: int
    null_percentage: float
    unique_count: int
    min_val: Optional[Union[float, int, str]] = None
    max_val: Optional[Union[float, int, str]] = None
    mean: Optional[float] = None
    std: Optional[float] = None
    p25: Optional[float] = None
    median: Optional[float] = None
    p75: Optional[float] = None
    top_values: List[Dict[str, Any]] = Field(default_factory=list)


class DatasetSummaryItem(BaseModel):
    id: str
    name: str
    file_path: str
    format: str
    rows: int
    columns: int
    size_bytes: int
    last_modified: str


class DatasetProfile(BaseModel):
    dataset_id: str
    dataset_name: str
    file_type: str
    total_rows: int
    total_columns: int
    columns: List[ColumnStats]
    duplicate_rows: int
    duplicate_percentage: float
    memory_size_bytes: int
    sample_rows: List[Dict[str, Any]] = Field(default_factory=list)
    quality_score: float


class InspectRequest(BaseModel):
    content: str
    format: str = "csv"
    name: Optional[str] = "custom_dataset"


class ExportRequest(BaseModel):
    dataset_id: str
    format: str = "csv"
    filter_column: Optional[str] = None
    filter_value: Optional[str] = None
    sort_column: Optional[str] = None
    sort_descending: bool = False
    limit: Optional[int] = 1000
