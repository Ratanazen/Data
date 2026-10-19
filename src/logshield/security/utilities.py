"""
Defensive Security Utilities
============================
1. File Integrity Checker: Cryptographic SHA-256 and MD5 checksum computation and baseline audit.
2. Log Sanitizer: Redacts passwords, API keys, bearer tokens, and session secrets for safe sharing.
3. Safe File Analyzer: Validates uploaded log files, preventing path traversal, binary injection, and oversized payloads.
"""

import hashlib
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Generator, List, Optional, Tuple, Union

from .models import FileIntegrityRecord

# Regex patterns for sanitizing sensitive credentials in logs
CREDENTIAL_PATTERNS = [
    (re.compile(r'(password|passwd|pwd)=([^&\s]+)', re.IGNORECASE), r'\1=[REDACTED]'),
    (re.compile(r'(bearer\s+)[a-zA-Z0-9_\-\.]{15,}', re.IGNORECASE), r'\1[REDACTED_TOKEN]'),
    (re.compile(r'(api[_\-]?key|apikey|secret)=([^&\s]+)', re.IGNORECASE), r'\1=[REDACTED_KEY]'),
    (re.compile(r'(access_token|refresh_token)=([^&\s]+)', re.IGNORECASE), r'\1=[REDACTED_TOKEN]'),
    (re.compile(r'Authorization:\s*(Basic|Bearer)\s+[^\r\n]+', re.IGNORECASE), r'Authorization: \1 [REDACTED_AUTH]'),
    (re.compile(r'PHPSESSID=[a-zA-Z0-9]+', re.IGNORECASE), r'PHPSESSID=[REDACTED_SESSION]'),
]


class FileIntegrityChecker:
    """
    Computes cryptographic hashes and performs baseline verification for files.
    """

    @staticmethod
    def hash_file(file_path: Union[str, Path]) -> Tuple[str, str, int, str]:
        """
        Computes SHA-256 and MD5 hashes, file size, and modification time for a file.
        Returns: (sha256, md5, size_bytes, modified_iso)
        """
        p = Path(file_path)
        if not p.is_file():
            raise FileNotFoundError(f"File not found: {file_path}")

        sha256 = hashlib.sha256()
        md5 = hashlib.md5()
        total_size = 0

        with open(p, "rb") as f:
            while chunk := f.read(65536):
                sha256.update(chunk)
                md5.update(chunk)
                total_size += len(chunk)

        mtime = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc).isoformat()
        return sha256.hexdigest(), md5.hexdigest(), total_size, mtime

    @classmethod
    def audit_file(
        cls,
        file_path: Union[str, Path],
        expected_sha256: Optional[str] = None
    ) -> FileIntegrityRecord:
        """
        Audits a single file against expected SHA-256 baseline.
        """
        p = Path(file_path)
        try:
            sha256, md5, size_bytes, mtime = cls.hash_file(p)
            if expected_sha256 is None:
                status = "VERIFIED"
            elif sha256.lower() == expected_sha256.lower().strip():
                status = "VERIFIED"
            else:
                status = "MODIFIED"

            return FileIntegrityRecord(
                file_path=str(p.name),
                sha256=sha256,
                md5=md5,
                size_bytes=size_bytes,
                modified_time=mtime,
                status=status
            )
        except Exception:
            return FileIntegrityRecord(
                file_path=str(p.name),
                sha256="",
                md5="",
                size_bytes=0,
                modified_time="",
                status="UNREADABLE"
            )

    @classmethod
    def audit_manifest(
        cls,
        manifest: Dict[str, str],
        base_dir: Union[str, Path] = "."
    ) -> List[FileIntegrityRecord]:
        """
        Audits a manifest mapping {relative_filename: expected_sha256}.
        """
        base = Path(base_dir)
        results: List[FileIntegrityRecord] = []
        for rel_name, expected_hash in manifest.items():
            full_path = base / rel_name
            results.append(cls.audit_file(full_path, expected_sha256=expected_hash))
        return results


class LogSanitizer:
    """
    Sanitizes log text or records by scrubbing confidential credentials and tokens.
    """

    @staticmethod
    def sanitize_line(line: str) -> str:
        """Removes or masks sensitive tokens, passwords, and authorization headers."""
        if not line or not isinstance(line, str):
            return line
        clean = line
        for pattern, replacement in CREDENTIAL_PATTERNS:
            clean = pattern.sub(replacement, clean)
        return clean

    @classmethod
    def sanitize_content(cls, content: str) -> str:
        """Sanitizes multiline string content."""
        if not content:
            return ""
        return "\n".join(cls.sanitize_line(line) for line in content.splitlines())


class SafeFileAnalyzer:
    """
    Safely inspects and processes uploaded log files.
    Enforces size restrictions, checks for binary injection, and neutralizes path traversal.
    """

    ALLOWED_EXTENSIONS = {".log", ".txt", ".csv", ".json", ".log.1"}
    MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB

    @classmethod
    def validate_filename(cls, filename: str) -> str:
        """Neutralizes path traversal attempts in filenames and returns clean basename."""
        safe_name = os.path.basename(filename).strip()
        # Remove dangerous control characters or null bytes
        safe_name = re.sub(r'[\x00-\x1f\x7f]', '', safe_name)
        if not safe_name:
            safe_name = "uploaded_log.log"
        return safe_name

    @classmethod
    def is_safe_log_file(cls, file_path: Union[str, Path]) -> Tuple[bool, Optional[str]]:
        """
        Validates whether a file is safe for analysis:
        - Must exist and be a regular file
        - File size <= 50MB
        - Must not contain null bytes (not a binary executable)
        - Allowed file extension
        """
        p = Path(file_path)
        if not p.is_file():
            return False, "File does not exist or is not a regular file"

        size = p.stat().st_size
        if size == 0:
            return True, None
        if size > cls.MAX_FILE_SIZE_BYTES:
            return False, f"File size exceeds safety limit of {cls.MAX_FILE_SIZE_BYTES / (1024*1024):.0f}MB"

        suffix = p.suffix.lower()
        if suffix not in cls.ALLOWED_EXTENSIONS and not p.name.endswith(".log"):
            return False, f"Unsupported file extension '{suffix}'. Allowed: {', '.join(sorted(cls.ALLOWED_EXTENSIONS))}"

        # Inspect first 4KB for binary/null bytes
        try:
            with open(p, "rb") as f:
                header = f.read(4096)
                if b"\x00" in header:
                    return False, "Binary file detected; plain-text or UTF-8 log required"
        except Exception as e:
            return False, f"Could not inspect file: {e}"

        return True, None
