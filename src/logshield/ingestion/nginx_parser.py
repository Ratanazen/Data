"""
Nginx Access Log Parser
"""

from typing import Optional

from .apache_parser import COMBINED_PATTERN, COMMON_PATTERN, parse_apache_timestamp
from .schema import ParsedLogRecord

NGINX_STANDARD_PATTERN = COMBINED_PATTERN

def parse_nginx_line(line: str, source_file: str = "nginx.log") -> Optional[ParsedLogRecord]:
    """Parses standard Nginx access log lines (Combined or Common)."""
    line = line.strip()
    if not line or line.startswith("#"):
        return None

    m = NGINX_STANDARD_PATTERN.match(line)
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

