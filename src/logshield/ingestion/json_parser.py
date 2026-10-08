"""
JSON Access Log Parser for structured log streams
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from dateutil import parser as date_parser

from .schema import ParsedLogRecord


def parse_json_line(line: str, source_file: str = "app.log.json") -> Optional[ParsedLogRecord]:
    """Parses a single JSON line into a ParsedLogRecord."""
    line = line.strip()
    if not line:
        return None

    try:
        data: Dict[str, Any] = json.loads(line)
    except Exception:
        return None

    # Flexible key extraction
    raw_ts = data.get("timestamp") or data.get("time") or data.get("@timestamp")
    if not raw_ts:
        return None

    try:
        if isinstance(raw_ts, (int, float)):
            # Epoch timestamp
            ts = datetime.fromtimestamp(raw_ts, tz=timezone.utc).replace(tzinfo=None)
        else:
            ts = date_parser.parse(str(raw_ts))
            if ts.tzinfo is not None:
                ts = ts.astimezone(timezone.utc).replace(tzinfo=None)
    except Exception:
        return None

    ip = str(data.get("ip") or data.get("client_ip") or data.get("remote_addr") or "")
    method = str(data.get("method") or data.get("http_method") or "GET").upper()
    path = str(data.get("path") or data.get("uri") or data.get("request_uri") or "/")
    status = int(data.get("status") or data.get("status_code") or 200)
    response_bytes = int(data.get("response_bytes") or data.get("bytes_sent") or data.get("body_bytes_sent") or 0)
    protocol = str(data.get("protocol") or data.get("server_protocol") or "HTTP/1.1")
    referer = data.get("referer") or data.get("http_referer")
    user_agent = data.get("user_agent") or data.get("http_user_agent")
    host = data.get("host") or data.get("http_host")

    return ParsedLogRecord(
        timestamp=ts,
        ip=ip,
        method=method,
        path=path,
        protocol=protocol,
        status=status,
        response_bytes=max(0, response_bytes),
        referer=str(referer) if referer and referer != "-" else None,
        user_agent=str(user_agent) if user_agent and user_agent != "-" else None,
        host=str(host) if host else None,
        source_file=source_file
    )
