"""
Pydantic API Schemas for LogShield REST Endpoints
"""

from typing import List, Optional

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    version: str
    mode: str
    environment: str
    storage_status: str
    kafka_status: str
    timestamp: str

class StatsKPIs(BaseModel):
    total_requests: int
    total_404: int
    error_rate: float
    peak_failure_hour: int
    peak_failure_count: int
    unique_ips: int
    unique_paths: int
    total_200: int
    total_403: int
    total_500: int
    total_301: int
    suspicious_ips_count: int
    security_events_count: int

class HourlyTrafficItem(BaseModel):
    hour: int
    total_requests: int
    errors_404: int
    errors_403: int
    errors_500: int
    successes_200: int
    redirects_301: int
    error_rate: float

class StatusDistributionItem(BaseModel):
    status: int
    count: int
    percentage: float

class TopUrlItem(BaseModel):
    path: str
    hits: int
    errors_404: int
    error_rate: float

class TopIpItem(BaseModel):
    ip: str
    total_requests: int
    errors_404: int
    errors_403: int
    errors_500: int
    login_failures: int
    risk_score: int
    severity: str

class SecurityEventItem(BaseModel):
    event_id: str
    timestamp: str
    ip: str
    event_type: str
    severity: str
    risk_score: int
    evidence: str
    request_count: int
    recommendation: Optional[str] = None

class HeatmapCell(BaseModel):
    day_of_week: str
    hour: int
    error_count: int

class LogItem(BaseModel):
    timestamp: str
    ip: str
    method: str
    path: str
    protocol: Optional[str] = "HTTP/1.1"
    status: int
    response_bytes: int
    referer: Optional[str] = None
    user_agent: Optional[str] = None

class PaginatedLogsResponse(BaseModel):
    total_matching: int
    limit: int
    offset: int
    items: List[LogItem]
