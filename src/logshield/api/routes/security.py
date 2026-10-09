"""
Security & Threat Analytics API routes
"""

from typing import List, Optional

import pyarrow.parquet as pq
from fastapi import APIRouter, Query

from ...config import settings
from ..schemas import SecurityEventItem, TopIpItem, TopUrlItem

router = APIRouter(tags=["Security"])

@router.get("/security", response_model=List[SecurityEventItem])
@router.get("/security/events", response_model=List[SecurityEventItem])
def get_security_events(
    severity: Optional[str] = Query(None, description="Filter by severity: LOW, MEDIUM, HIGH, CRITICAL"),
    ip: Optional[str] = Query(None, description="Filter events for specific client IP"),
    limit: int = Query(50, ge=1, le=500, description="Maximum number of events returned")
) -> List[SecurityEventItem]:
    """Returns detected security events with risk scores, forensic evidence, and remediation advice."""
    p_file = settings.GOLD_PATH / "gold_security_events.parquet"
    if not p_file.exists():
        return []

    df = pq.read_table(str(p_file)).to_pandas()

    if severity:
        df = df[df["severity"].str.upper() == severity.upper()]
    if ip:
        df = df[df["ip"] == ip.strip()]

    df = df.sort_values(by="risk_score", ascending=False).head(limit)

    items = []
    for _, r in df.iterrows():
        items.append(SecurityEventItem(
            event_id=str(r["event_id"]),
            timestamp=str(r["timestamp"]),
            ip=str(r["ip"]),
            event_type=str(r["event_type"]),
            severity=str(r["severity"]),
            risk_score=int(r["risk_score"]),
            evidence=str(r["evidence"]),
            request_count=int(r["request_count"]),
            recommendation=str(r["recommendation"]) if r.get("recommendation") else None
        ))
    return items

@router.get("/anomalies")
def get_anomalies() -> List[dict]:
    """Returns detected statistical deviations and volume anomalies."""
    p_file = settings.GOLD_PATH / "gold_anomalies.parquet"
    if not p_file.exists():
        return []

    df = pq.read_table(str(p_file)).to_pandas()
    return df.to_dict(orient="records")

@router.get("/top-ips", response_model=List[TopIpItem])
def get_top_ips(
    limit: int = Query(50, ge=1, le=200, description="Number of top IPs to return")
) -> List[TopIpItem]:
    """Returns top active client IPs with threat risk scores and failure breakdowns."""
    p_file = settings.GOLD_PATH / "gold_top_ips.parquet"
    if not p_file.exists():
        return []

    df = pq.read_table(str(p_file)).to_pandas().head(limit)
    return [
        TopIpItem(
            ip=str(r["ip"]),
            total_requests=int(r["total_requests"]),
            errors_404=int(r["errors_404"]),
            errors_403=int(r["errors_403"]),
            errors_500=int(r["errors_500"]),
            login_failures=int(r.get("login_failures", 0)),
            risk_score=int(r.get("risk_score", 0)),
            severity=str(r.get("severity", "LOW"))
        )
        for _, r in df.iterrows()
    ]

@router.get("/top-urls", response_model=List[TopUrlItem])
def get_top_urls(
    limit: int = Query(25, ge=1, le=100, description="Number of top URLs to return")
) -> List[TopUrlItem]:
    """Returns most requested URLs along with 404 error frequency and rate."""
    p_file = settings.GOLD_PATH / "gold_top_urls.parquet"
    if not p_file.exists():
        return []

    df = pq.read_table(str(p_file)).to_pandas().head(limit)
    return [
        TopUrlItem(
            path=str(r["path"]),
            hits=int(r["hits"]),
            errors_404=int(r["errors_404"]),
            error_rate=float(r["error_rate"])
        )
        for _, r in df.iterrows()
    ]
