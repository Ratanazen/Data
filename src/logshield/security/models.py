"""
Security Analytics Data Models
"""

import uuid
from datetime import datetime
from typing import Dict, Literal, Optional

from pydantic import BaseModel, Field

SeverityLevel = Literal["INFORMATIONAL", "LOW", "MEDIUM", "HIGH", "CRITICAL"]

class SecurityEvent(BaseModel):
    """Normalized security event representation for SIEM / Incident Response."""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8], description="Unique event identifier")
    timestamp: datetime = Field(..., description="Timestamp of the detected incident")
    ip: str = Field(..., description="Target source IP address")
    event_type: str = Field(..., description="Classification category (e.g. 'Brute Force Login', 'Path Traversal')")
    severity: SeverityLevel = Field(..., description="Calculated threat severity (INFORMATIONAL, LOW, MEDIUM, HIGH, CRITICAL)")
    risk_score: int = Field(..., ge=0, le=100, description="Heuristic threat risk score (0-100)")
    evidence: str = Field(..., description="Empirical indicators and forensic justification")
    request_count: int = Field(default=0, ge=0, description="Number of requests associated with this pattern")
    status_count: Dict[str, int] = Field(default_factory=dict, description="Distribution of response codes")
    recommendation: Optional[str] = Field(default="Monitor IP and enforce WAF rate limits", description="Incident mitigation action")
    is_confirmed_incident: bool = Field(default=False, description="Distinguishes detected pattern from confirmed security incident")

class AnomalyRecord(BaseModel):
    """Statistical anomaly metric detection record."""
    metric_name: str = Field(..., description="Observed system or traffic metric")
    timestamp: datetime = Field(..., description="Window timestamp")
    observed_value: float = Field(..., description="Actual measured value")
    baseline_value: float = Field(..., description="Historical baseline average")
    deviation_pct: float = Field(..., description="Percentage deviation from baseline")
    severity: SeverityLevel = Field(..., description="Statistical anomaly severity")
    message: str = Field(..., description="Human-readable explanation of anomaly")

class DetectionRule(BaseModel):
    """Configurable, explainable security detection rule definition."""
    rule_id: str = Field(..., description="Unique rule identifier (e.g. RULE-AUTH-001)")
    name: str = Field(..., description="Human-readable rule name")
    description: str = Field(..., description="Detailed description of detection logic")
    category: str = Field(default="Authentication", description="Threat category: Authentication, Reconnaissance, Privilege, Integrity")
    severity: SeverityLevel = Field(default="MEDIUM", description="Default incident severity level")
    threshold: int = Field(default=5, ge=1, description="Triggering threshold count")
    window_seconds: int = Field(default=120, ge=1, description="Sliding time window duration in seconds")
    enabled: bool = Field(default=True, description="Rule active state")
    trigger_count: int = Field(default=0, ge=0, description="Number of times rule has fired")

class AuthLogRecord(BaseModel):
    """Parsed authentication and system security event record."""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8], description="Unique event identifier")
    timestamp: datetime = Field(..., description="Timestamp of the authentication or privilege event")
    source_ip: Optional[str] = Field(default=None, description="Originating client IP address")
    user: Optional[str] = Field(default=None, description="Target username or account")
    event_type: str = Field(..., description="Categorization: failed_login, accepted_login, privilege_escalation, invalid_user, account_locked")
    severity: SeverityLevel = Field(..., description="Event severity rating")
    details: str = Field(..., description="Human-readable event summary")
    raw_message: str = Field(..., description="Preserved original unparsed log line")

class FileIntegrityRecord(BaseModel):
    """Cryptographic file integrity audit record."""
    file_path: str = Field(..., description="Target file path")
    sha256: str = Field(..., description="Cryptographic SHA-256 hex digest")
    md5: str = Field(..., description="Cryptographic MD5 hex digest")
    size_bytes: int = Field(..., ge=0, description="File size in bytes")
    modified_time: str = Field(..., description="Last modification timestamp")
    status: Literal["VERIFIED", "MODIFIED", "NEW", "UNREADABLE"] = Field(default="VERIFIED", description="Integrity audit status")
