"""
Data Analytics & Dataset Profiling REST API Routes
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse

from ...analytics import (
    ColumnStats,
    DatasetAnalyzer,
    DatasetProfile,
    DatasetSummaryItem,
    ExportRequest,
    InspectRequest,
)

router = APIRouter(tags=["Analytics"])
analyzer = DatasetAnalyzer()


@router.get("/analytics/datasets", response_model=List[DatasetSummaryItem])
def list_datasets() -> List[DatasetSummaryItem]:
    """Returns a list of all available project datasets with row counts, column counts, and sizes."""
    try:
        return analyzer.discover_datasets()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to scan datasets: {str(e)}")


@router.get("/analytics/profile", response_model=DatasetProfile)
def get_dataset_profile(
    dataset_id: str = Query("hourly_404_errors", description="Dataset identifier or relative file path"),
    sample_limit: int = Query(50, ge=5, le=500, description="Maximum sample rows to include")
) -> DatasetProfile:
    """Returns detailed statistical profile, missing value counts, and quality score for a dataset."""
    try:
        return analyzer.profile_dataset(dataset_id=dataset_id, max_sample_rows=sample_limit)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Profiling failed: {str(e)}")


@router.post("/analytics/inspect", response_model=DatasetProfile)
def inspect_dataset_in_memory(request: InspectRequest) -> DatasetProfile:
    """Performs in-memory schema validation, missing-value audits, and statistical summary on submitted CSV/JSON."""
    try:
        return analyzer.inspect_in_memory(
            content=request.content,
            format=request.format,
            name=request.name or "custom_dataset"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inspection failed: {str(e)}")


@router.post("/analytics/export", response_class=PlainTextResponse)
def export_dataset_content(request: ExportRequest) -> str:
    """Exports dataset with optional filtering and sorting as CSV, JSON, or Markdown."""
    try:
        content = analyzer.export_dataset(
            dataset_id=request.dataset_id,
            format=request.format,
            filter_column=request.filter_column,
            filter_value=request.filter_value,
            sort_column=request.sort_column,
            sort_descending=request.sort_descending,
            limit=request.limit or 1000
        )
        return content
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")
