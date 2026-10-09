"""
Traffic Analytics API route
"""

from typing import List

import pyarrow.parquet as pq
from fastapi import APIRouter

from ...config import settings
from ..schemas import HourlyTrafficItem

router = APIRouter(tags=["Traffic"])

@router.get("/traffic", response_model=List[HourlyTrafficItem])
@router.get("/traffic/hourly", response_model=List[HourlyTrafficItem])
def get_traffic() -> List[HourlyTrafficItem]:
    """Returns 24-hour traffic distribution containing request counts and status breakdowns per hour."""
    p_file = settings.GOLD_PATH / "gold_hourly_traffic.parquet"
    if not p_file.exists():
        return []

    table = pq.read_table(str(p_file))
    df = table.to_pandas()
    items = []
    for _, row in df.iterrows():
        items.append(HourlyTrafficItem(
            hour=int(row["hour"]),
            total_requests=int(row["total_requests"]),
            errors_404=int(row["errors_404"]),
            errors_403=int(row["errors_403"]),
            errors_500=int(row["errors_500"]),
            successes_200=int(row["successes_200"]),
            redirects_301=int(row["redirects_301"]),
            error_rate=float(row["error_rate"])
        ))
    return items
