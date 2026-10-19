"""Unit tests for defensive security utilities (file integrity, log sanitizer, safe file analyzer)."""

import hashlib
import tempfile
from pathlib import Path

from src.logshield.security.utilities import (
    FileIntegrityChecker,
    LogSanitizer,
    SafeFileAnalyzer,
)


def test_file_integrity_checker_verified():
    with tempfile.NamedTemporaryFile("w+", delete=False) as f:
        f.write("LogShield system configuration test payload\n")
        f.flush()
        fpath = Path(f.name)

    try:
        # Calculate actual hash
        sha256 = hashlib.sha256(fpath.read_bytes()).hexdigest()
        md5 = hashlib.md5(fpath.read_bytes()).hexdigest()

        rec = FileIntegrityChecker.audit_file(fpath, expected_sha256=sha256)
        assert rec.status == "VERIFIED"
        assert rec.sha256 == sha256
        assert rec.md5 == md5
        assert rec.size_bytes > 0
    finally:
        fpath.unlink(missing_ok=True)


def test_file_integrity_checker_modified():
    with tempfile.NamedTemporaryFile("w+", delete=False) as f:
        f.write("Original content\n")
        f.flush()
        fpath = Path(f.name)

    try:
        rec = FileIntegrityChecker.audit_file(fpath, expected_sha256="0000000000000000000000000000000000000000000000000000000000000000")
        assert rec.status == "MODIFIED"
    finally:
        fpath.unlink(missing_ok=True)


def test_file_integrity_checker_unreadable():
    rec = FileIntegrityChecker.audit_file("/non/existent/path/for/sure/log.txt")
    assert rec.status == "UNREADABLE"


def test_log_sanitizer_redacts_credentials():
    dirty_log = '10.0.1.1 - - [01/Sep/2026:03:00:00 +0000] "POST /login?password=SuperSecretPassword123&user=admin HTTP/1.1" 200 450'
    clean_log = LogSanitizer.sanitize_line(dirty_log)
    assert "SuperSecretPassword123" not in clean_log
    assert "password=[REDACTED]" in clean_log


def test_log_sanitizer_redacts_bearer_and_api_keys():
    bearer_log = 'GET /api/v1/data HTTP/1.1 Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xyz.secret'
    clean_bearer = LogSanitizer.sanitize_line(bearer_log)
    assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xyz.secret" not in clean_bearer
    assert "Bearer [REDACTED_AUTH]" in clean_bearer

    api_key_log = 'curl https://api.example.com/v1?api_key=AIzaSyD-RandomKeySecretValue123'
    clean_api = LogSanitizer.sanitize_line(api_key_log)
    assert "AIzaSyD-RandomKeySecretValue123" not in clean_api
    assert "api_key=[REDACTED_KEY]" in clean_api


def test_safe_file_analyzer_filename_sanitization():
    unsafe_name = "../../etc/passwd"
    clean_name = SafeFileAnalyzer.validate_filename(unsafe_name)
    assert clean_name == "passwd"
    assert ".." not in clean_name

    unsafe_null = "test\x00malicious.log"
    clean_null = SafeFileAnalyzer.validate_filename(unsafe_null)
    assert "\x00" not in clean_null


def test_safe_file_analyzer_binary_rejection():
    with tempfile.NamedTemporaryFile("wb", delete=False, suffix=".log") as f:
        # Write binary file containing null bytes
        f.write(b"\x7fELF\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00")
        f.flush()
        fpath = Path(f.name)

    try:
        is_safe, reason = SafeFileAnalyzer.is_safe_log_file(fpath)
        assert is_safe is False
        assert "Binary file detected" in str(reason)
    finally:
        fpath.unlink(missing_ok=True)
