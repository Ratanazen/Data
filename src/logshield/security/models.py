"""
Security Analytics Data Models
"""

import uuid
from datetime import datetime
from typing import Dict, Literal, Optional

from pydantic import BaseModel, Field

SeverityLevel = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]

class SecurityEvent(BaseModel):
    """Normalized security event representation for SIEM / Incident Response."""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8], description="Unique event identifier")
    timestamp: datetime = Field(..., description="Timestamp of the detected incident")
    ip: str = Field(..., description="Target source IP address")
    event_type: str = Field(..., description="Classification category (e.g. 'Brute Force Login', 'Path Traversal')")
    severity: SeverityLevel = Field(..., description="Calculated threat severity (LOW, MEDIUM, HIGH, CRITICAL)")
    risk_score: int = Field(..., ge=0, le=100, description="Heuristic threat risk score (0-100)")
    evidence: str = Field(..., description="Empirical indicators and forensic justification")
    request_count: int = Field(default=0, ge=0, description="Number of requests associated with this pattern")
    status_count: Dict[str, int] = Field(default_factory=dict, description="Distribution of response codes")
    recommendation: Optional[str] = Field(default="Monitor IP and enforce WAF rate limits", description="Incident mitigation action")

class AnomalyRecord(BaseModel):
    """Statistical anomaly metric detection record."""
    metric_name: str = Field(..., description="Observed system or traffic metric")
    timestamp: datetime = Field(..., description="Window timestamp")
    observed_value: float = Field(..., description="Actual measured value")
    baseline_value: float = Field(..., description="Historical baseline average")
    deviation_pct: float = Field(..., description="Percentage deviation from baseline")
    severity: SeverityLevel = Field(..., description="Statistical anomaly severity")
    message: str = Field(..., description="Human-readable explanation of anomaly")
