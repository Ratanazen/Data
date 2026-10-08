"""
Streaming-Friendly Multi-Format Log Ingestion Reader
"""

from collections.abc import Generator
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from ..config import settings
from .apache_parser import parse_apache_line
from .json_parser import parse_json_line
from .nginx_parser import parse_nginx_line
from .schema import ParsedLogRecord, QuarantineRecord
from .validator import validate_record


class LogReader:
    """
    Streaming reader capable of parsing Apache, Nginx, and JSON log streams,
    validating data quality, tracking metrics, and isolating corrupt lines to quarantine.
    """

    def __init__(self, quarantine_dir: Optional[Path] = None):
        self.quarantine_dir = quarantine_dir or settings.QUARANTINE_PATH
        self.quarantine_dir.mkdir(parents=True, exist_ok=True)
        self.stats = {
            "records_total": 0,
            "records_valid": 0,
            "records_invalid": 0,
            "duplicates": 0,
            "missing_timestamps": 0,
            "invalid_ips": 0,
        }
        self._seen_signatures = set()

    def _quarantine(self, raw_line: str, source_file: str, line_no: int, reason: str) -> None:
        """Writes non-compliant records to date-partitioned JSONL quarantine log."""
        self.stats["records_invalid"] += 1
        if "timestamp" in reason.lower():
            self.stats["missing_timestamps"] += 1
        if "ip" in reason.lower():
            self.stats["invalid_ips"] += 1

        today_str = datetime.utcnow().strftime("%Y-%m-%d")
        q_file = self.quarantine_dir / f"quarantine_{today_str}.jsonl"

        rec = QuarantineRecord(
            raw_line=raw_line.rstrip("\r\n"),
            source_file=source_file,
            line_number=line_no,
            error_reason=reason
        )
        with open(q_file, "a", encoding="utf-8") as f:
            f.write(rec.model_dump_json() + "\n")

    def _parse_line(self, line: str, source_file: str, format_hint: str) -> Optional[ParsedLogRecord]:
        """Dispatches line to appropriate parser based on format hint or content sniffing."""
        line_stripped = line.strip()
        if not line_stripped:
            return None

        if format_hint == "json" or line_stripped.startswith("{"):
            parsed = parse_json_line(line_stripped, source_file=source_file)
            if parsed:
                return parsed

        if format_hint == "nginx":
            parsed = parse_nginx_line(line_stripped, source_file=source_file)
            if parsed:
                return parsed

        # Default is Apache (Common or Combined)
        return parse_apache_line(line_stripped, source_file=source_file)

    def read_file(
        self,
        file_path: Path,
        format_hint: str = "auto",
        deduplicate: bool = True
    ) -> Generator[ParsedLogRecord, None, None]:
        """
        Stream-reads a log file line by line with fault-tolerant error recovery.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Log file does not exist: {path}")

        source_name = path.name
        # Fallback encodings for dirty enterprise access logs
        encodings = ["utf-8", "latin-1", "cp1252"]

        for enc in encodings:
            try:
                with open(path, "r", encoding=enc, errors="replace") as f:
                    for line_no, line in enumerate(f, start=1):
                        self.stats["records_total"] += 1

                        if not line.strip() or line.strip().startswith("#"):
                            continue

                        parsed = self._parse_line(line, source_name, format_hint)
                        if not parsed:
                            self._quarantine(line, source_name, line_no, "Failed regex pattern match")
                            continue

                        is_valid, reason = validate_record(parsed)
                        if not is_valid:
                            self._quarantine(line, source_name, line_no, reason)
                            continue

                        if deduplicate:
                            sig = (parsed.timestamp.isoformat(), parsed.ip, parsed.method, parsed.path, parsed.status)
                            if sig in self._seen_signatures:
                                self.stats["duplicates"] += 1
                                continue
                            self._seen_signatures.add(sig)

                        self.stats["records_valid"] += 1
                        yield parsed
                break
            except UnicodeDecodeError:
                continue

    def get_quality_report(self) -> Dict[str, Any]:
        """Returns comprehensive data quality metrics."""
        total = self.stats["records_total"]
        valid = self.stats["records_valid"]
        valid_rate = (valid / total * 100.0) if total > 0 else 0.0
        return {
            **self.stats,
            "data_quality_pct": round(valid_rate, 2),
            "quarantine_directory": str(self.quarantine_dir)
        }
