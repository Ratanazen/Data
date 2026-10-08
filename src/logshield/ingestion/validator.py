"""
Validation engine for raw and parsed log records
"""

import ipaddress
from typing import Optional, Tuple

from .schema import ParsedLogRecord

VALID_METHODS = {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS", "CONNECT", "TRACE"}

def is_valid_ip(ip_str: str) -> bool:
    """Checks if a string is a valid IPv4 or IPv6 address."""
    if not ip_str or not isinstance(ip_str, str):
        return False
    try:
        ipaddress.ip_address(ip_str.strip())
        return True
    except ValueError:
        return False

def is_valid_status_code(code: int) -> bool:
    """Checks if an HTTP status code is in standard RFC range (100-599)."""
    return isinstance(code, int) and 100 <= code <= 599

def validate_record(record: ParsedLogRecord) -> Tuple[bool, Optional[str]]:
    """
    Performs comprehensive data quality validation.
    Returns:
        (True, None) if record is valid
        (False, failure_reason) if record is invalid
    """
    if record.timestamp is None:
        return False, "Null timestamp"

    if not is_valid_ip(record.ip):
        return False, f"Invalid IP address: '{record.ip}'"

    if not record.path or len(record.path.strip()) == 0:
        return False, "Empty or missing requested path"

    if not is_valid_status_code(record.status):
        return False, f"Invalid HTTP status code: {record.status}"

    if record.response_bytes < 0:
        return False, f"Negative response bytes: {record.response_bytes}"

    clean_method = record.method.upper().strip()
    if clean_method not in VALID_METHODS:
        return False, f"Unrecognized HTTP method: '{record.method}'"

    return True, None
