"""
Schema definitions for raw and parsed log records in LogShield
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ParsedLogRecord(BaseModel):
    """Normalized schema representation of an HTTP access log record."""
    timestamp: datetime = Field(..., description="Normalized UTC ISO-8601 timestamp")
    ip: str = Field(..., description="Client IP address (IPv4 or IPv6)")
    method: str = Field(..., description="HTTP Method (GET, POST, PUT, DELETE, etc.)")
    path: str = Field(..., description="Requested URI path")
    protocol: str = Field(default="HTTP/1.1", description="HTTP protocol version")
    status: int = Field(..., description="HTTP response status code (e.g. 200, 404, 500)")
    response_bytes: int = Field(default=0, ge=0, description="Payload size in bytes")
    referer: Optional[str] = Field(default="-", description="Referrer URL if present")
    user_agent: Optional[str] = Field(default="-", description="Client User-Agent string")
    host: Optional[str] = Field(default="localhost", description="Target host or virtual host")
    source_file: str = Field(default="server.log", description="Originating filename or stream source")
    ingestion_time: datetime = Field(default_factory=datetime.utcnow, description="Timestamp of ingestion")

    # Derived partition fields
    date: Optional[str] = Field(default=None, description="Partition date YYYY-MM-DD")
    hour: Optional[int] = Field(default=None, description="Partition hour 0-23")

    def model_post_init(self, __context) -> None:
        """Automatically computes partition attributes if missing."""
        if self.timestamp:
            if not self.date:
                self.date = self.timestamp.strftime("%Y-%m-%d")
            if self.hour is None:
                self.hour = self.timestamp.hour

class QuarantineRecord(BaseModel):
    """Schema for corrupted or non-compliant records routed to data/quarantine."""
    raw_line: str = Field(..., description="Original unparsed string")
    source_file: str = Field(..., description="File where error occurred")
    line_number: int = Field(..., description="1-indexed line position in source")
    error_reason: str = Field(..., description="Validation failure explanation")
    quarantine_time: datetime = Field(default_factory=datetime.utcnow, description="Time quarantined")
