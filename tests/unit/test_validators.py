"""Unit tests for LogShield record validators."""

from datetime import datetime

from src.logshield.ingestion.schema import ParsedLogRecord
from src.logshield.ingestion.validator import (
    is_valid_ip,
    is_valid_status_code,
    validate_record,
)


def test_ip_validation():
    assert is_valid_ip("10.0.12.45") is True
    assert is_valid_ip("192.168.1.1") is True
    assert is_valid_ip("256.0.0.1") is False
    assert is_valid_ip("invalid-ip") is False
    assert is_valid_ip("") is False


def test_status_validation():
    assert is_valid_status_code(200) is True
    assert is_valid_status_code(404) is True
    assert is_valid_status_code(500) is True
    assert is_valid_status_code(99) is False
    assert is_valid_status_code(600) is False
    assert is_valid_status_code("not-int") is False


def test_validate_record():
    valid_rec = ParsedLogRecord(
        ip="10.0.12.45",
        timestamp=datetime(2026, 9, 1, 3, 14, 22),
        method="GET",
        path="/admin/login",
        protocol="HTTP/1.1",
        status=404,
        response_bytes=342,
        date="2026-09-01",
        hour=3,
        source_file="server.log",
        line_number=1,
    )
    is_valid, reason = validate_record(valid_rec)
    assert is_valid is True
    assert reason is None

    # Invalid record with bad IP
    bad_rec = ParsedLogRecord(
        ip="not.an.ip",
        timestamp=datetime(2026, 9, 1, 3, 14, 22),
        method="GET",
        path="/admin/login",
        protocol="HTTP/1.1",
        status=404,
        response_bytes=342,
        date="2026-09-01",
        hour=3,
        source_file="server.log",
        line_number=1,
    )
    is_valid, reason = validate_record(bad_rec)
    assert is_valid is False
    assert "Invalid IP" in reason
