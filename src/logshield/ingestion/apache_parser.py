"""
Apache Access Log Parser (Common and Combined formats)
"""

import re
from datetime import datetime, timezone
from typing import Optional

from .schema import ParsedLogRecord

# Apache Common Log Format regex
COMMON_PATTERN = re.compile(
    r'^(\S+)\s+\S+\s+\S+\s+\[([^\]]+)\]\s+"([A-Z]+)\s+([^"\s]+)\s*([^"]*)"\s+(\d{3})\s+(\S+)'
)

# Apache Combined Log Format regex (includes referer and user-agent)
COMBINED_PATTERN = re.compile(
    r'^(\S+)\s+\S+\s+\S+\s+\[([^\]]+)\]\s+"([A-Z]+)\s+([^"\s]+)\s*([^"]*)"\s+(\d{3})\s+(\S+)\s+"([^"]*)"\s+"([^"]*)"'
)

def parse_apache_timestamp(ts_str: str) -> datetime:
    """Parses Apache standard timestamp (e.g. '04/Sep/2026:03:27:23 +0000') into UTC datetime."""
    # Strip optional brackets if present
    ts_clean = ts_str.strip("[] ")
    try:
        dt = datetime.strptime(ts_clean, "%d/%b/%Y:%H:%M:%S %z")
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    except ValueError:
        # Fallback without timezone offset
        dt = datetime.strptime(ts_clean.split()[0], "%d/%b/%Y:%H:%M:%S")
        return dt

def parse_apache_line(line: str, source_file: str = "server.log") -> Optional[ParsedLogRecord]:
    """Parses a single line of Apache Common or Combined log format."""
    line = line.strip()
    if not line or line.startswith("#"):
        return None

    # First attempt Combined format
    m = COMBINED_PATTERN.match(line)
    if m:
        ip, ts_str, method, path, proto, status_str, bytes_str, referer, user_agent = m.groups()
        resp_bytes = int(bytes_str) if bytes_str.isdigit() else 0
        proto_clean = proto.strip() if proto.strip() else "HTTP/1.1"
        try:
            ts = parse_apache_timestamp(ts_str)
        except Exception:
            return None

        return ParsedLogRecord(
            timestamp=ts,
            ip=ip,
            method=method,
            path=path,
            protocol=proto_clean,
            status=int(status_str),
            response_bytes=resp_bytes,
            referer=referer if referer != "-" else None,
            user_agent=user_agent if user_agent != "-" else None,
            source_file=source_file
        )

    # Fallback to Common format
    m = COMMON_PATTERN.match(line)
    if m:
        ip, ts_str, method, path, proto, status_str, bytes_str = m.groups()
        resp_bytes = int(bytes_str) if bytes_str.isdigit() else 0
        proto_clean = proto.strip() if proto.strip() else "HTTP/1.1"
        try:
            ts = parse_apache_timestamp(ts_str)
        except Exception:
            return None

        return ParsedLogRecord(
            timestamp=ts,
            ip=ip,
            method=method,
            path=path,
            protocol=proto_clean,
            status=int(status_str),
            response_bytes=resp_bytes,
            source_file=source_file
        )

    return None
