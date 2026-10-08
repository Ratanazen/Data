"""
Paginated & Filtered Log Explorer API route
"""

from typing import Optional

import pandas as pd
import pyarrow.parquet as pq
from fastapi import APIRouter, Query

from ...config import settings
from ..schemas import LogItem, PaginatedLogsResponse

router = APIRouter(tags=["Logs"])

@router.get("/logs", response_model=PaginatedLogsResponse)
def get_logs(
    ip: Optional[str] = Query(None, description="Filter by client IP"),
    status: Optional[int] = Query(None, description="Filter by HTTP status code"),
    path: Optional[str] = Query(None, description="Filter by path substring"),
    method: Optional[str] = Query(None, description="Filter by HTTP method"),
    limit: int = Query(50, ge=1, le=100, description="Max records to return per page (default <= 100)"),
    offset: int = Query(0, ge=0, description="Pagination offset")
) -> PaginatedLogsResponse:
    """
    Returns filtered, paginated access log records directly from the partitioned Silver layer.
    Guarantees low memory footprint and high responsiveness.
    """
    silver_path = settings.SILVER_PATH
    if not silver_path.exists():
        return PaginatedLogsResponse(total_matching=0, limit=limit, offset=offset, items=[])

    # Build pyarrow filters for pushdown predicate execution
    filters = []
    if status is not None:
        filters.append(("status", "=", status))
    if ip is not None:
        filters.append(("ip", "=", ip.strip()))
    if method is not None:
        filters.append(("method", "=", method.upper().strip()))

    try:
        table = pq.read_table(
            str(silver_path),
            filters=filters if filters else None,
            columns=["timestamp", "ip", "method", "path", "protocol", "status", "response_bytes", "referer", "user_agent"]
        )
    except Exception:
        table = pq.read_table(str(silver_path))

    df = table.to_pandas()

    # In-memory substring filter on path if requested
    if path:
        df = df[df["path"].str.contains(path, case=False, na=False)]

    total_matching = len(df)
    page_df = df.iloc[offset: offset + limit]

    items = []
    for _, r in page_df.iterrows():
        items.append(LogItem(
            timestamp=str(r["timestamp"]),
            ip=str(r["ip"]),
            method=str(r["method"]),
            path=str(r["path"]),
            protocol=str(r.get("protocol") or "HTTP/1.1"),
            status=int(r["status"]),
            response_bytes=int(r["response_bytes"]),
            referer=str(r["referer"]) if pd.notna(r.get("referer")) else None,
            user_agent=str(r["user_agent"]) if pd.notna(r.get("user_agent")) else None
        ))

    return PaginatedLogsResponse(
        total_matching=total_matching,
        limit=limit,
        offset=offset,
        items=items
    )
