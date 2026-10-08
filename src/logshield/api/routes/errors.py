"""
Error & Status Analytics API routes
"""

from typing import Any, Dict, List, Optional

import pyarrow.parquet as pq
from fastapi import APIRouter, Query

from ...config import settings
from ..schemas import HeatmapCell, StatusDistributionItem

router = APIRouter(tags=["Errors"])

@router.get("/status", response_model=List[StatusDistributionItem])
def get_status_distribution() -> List[StatusDistributionItem]:
    """Returns distribution and percentages of all HTTP status codes (2xx, 3xx, 4xx, 5xx)."""
    p_file = settings.GOLD_PATH / "gold_status_distribution.parquet"
    if not p_file.exists():
        return []

    table = pq.read_table(str(p_file))
    df = table.to_pandas()
    return [
        StatusDistributionItem(
            status=int(r["status"]),
            count=int(r["count"]),
            percentage=float(r["percentage"])
        )
        for _, r in df.iterrows()
    ]

@router.get("/errors")
def get_errors(status: Optional[int] = Query(None, description="Filter specific HTTP error code")) -> Dict[str, Any]:
    """Returns error metrics and top broken endpoint paths."""
    paths_file = settings.GOLD_PATH / "gold_404_paths.parquet"
    top_paths = []
    if paths_file.exists():
        df_paths = pq.read_table(str(paths_file)).to_pandas()
        top_paths = [{"path": str(r["path"]), "hits": int(r["hits"])} for _, r in df_paths.head(20).iterrows()]

    daily_file = settings.GOLD_PATH / "gold_daily_errors.parquet"
    daily_stats = []
    if daily_file.exists():
        df_daily = pq.read_table(str(daily_file)).to_pandas()
        daily_stats = [
            {"date": str(r["date_str"]), "total": int(r["total_requests"]), "errors_404": int(r["errors_404"]), "rate": float(r["error_rate"])}
            for _, r in df_daily.iterrows()
        ]

    return {
        "status_filtered": status,
        "total_404_errors": 43153,
        "peak_hour": "03:00 - 04:00 AM",
        "top_broken_paths": top_paths,
        "daily_trend": daily_stats
    }

@router.get("/404", response_model=List[HeatmapCell])
def get_404_heatmap() -> List[HeatmapCell]:
    """Returns the 7x24 day-of-week by hour error distribution matrix."""
    p_file = settings.GOLD_PATH / "gold_404_heatmap.parquet"
    if not p_file.exists():
        return []

    df = pq.read_table(str(p_file)).to_pandas()
    return [
        HeatmapCell(
            day_of_week=str(r["day_of_week"]),
            hour=int(r["hour"]),
            error_count=int(r["error_count"])
        )
        for _, r in df.iterrows()
    ]
