#!/usr/bin/env python3
"""
LogShield — Single-File Log File Analysis & Web Application
===========================================================
A self-contained Flask web application for log analysis, CSV inspection,
HTTP 404 error tracking, and hourly failure pattern detection.

Features:
  - Drag-and-drop CSV, Apache, and Nginx log upload with encoding auto-detection
  - Automatic column detection (status, url/path, ip, timestamp, method, size)
  - HTTP 404 error counting, 404 percentage calculation, and status breakdown
  - 24-hour timeline distribution with UTC timestamp normalization & peak failure hour
  - Top failing URLs and active client IP address tracking
  - Optional PySpark and Hadoop HDFS integration with local in-memory fallback
  - Interactive data table with search, status filtering, column sorting & pagination
  - Sanitized CSV export with CSV formula injection mitigation
  - Professional Dark Navy (#0b1120) and Cyan (#06b6d4) responsive dashboard with SVG icons

Usage:
  python app.py
  python app.py --host 127.0.0.1 --port 8080
  python app.py --test
"""

from __future__ import annotations

import argparse
import csv
import datetime
import html
import io
import json
import math
import os
import re
import secrets
import shutil
import sys
import tempfile
import threading
import time
import uuid
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from flask import (
    Flask,
    Response,
    abort,
    jsonify,
    render_template_string,
    request,
    send_file,
    session,
)
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename

# ==============================================================================
# CONFIGURATION & CONSTANTS
# ==============================================================================

MAX_UPLOAD_SIZE_MB = 32
MAX_CONTENT_LENGTH = MAX_UPLOAD_SIZE_MB * 1024 * 1024
ALLOWED_EXTENSIONS = {"csv", "log", "txt", "tsv"}
UPLOAD_DIR = Path(tempfile.gettempdir()) / "logshield_uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Common Log Format (CLF) / Apache / Nginx Combined Regex
# Matches: IP, identity, authuser, [timestamp], "METHOD /path HTTP/x.x", status, size
CLF_REGEX = re.compile(
    r'^(\S+)\s+\S+\s+\S+\s+\[([^\]]+)\]\s+"([A-Z]+)\s+([^"\s]+)[^"]*"\s+(\d{3})\s+(\d+|-)'
)

# Semantic column name aliases for CSV auto-detection
COLUMN_ALIASES: Dict[str, List[str]] = {
    "status": ["status", "status_code", "sc_status", "code", "response", "http_status", "statuscode"],
    "path": ["path", "url", "uri", "endpoint", "request", "request_uri", "cs_uri_stem", "target"],
    "ip": ["ip", "client_ip", "remote_addr", "host", "src_ip", "clientip", "c_ip", "remote_ip"],
    "timestamp": ["timestamp", "time", "datetime", "date", "timestamp_str", "time_local", "time_stamp"],
    "method": ["method", "verb", "http_method", "cs_method", "request_method"],
    "size": ["size", "bytes", "body_bytes_sent", "content_length", "sc_bytes", "length"],
    "user_agent": ["user_agent", "agent", "ua", "cs_user_agent", "http_user_agent"],
}

# In-memory storage for active sessions (session_id -> dataset dict)
DATASET_STORE: Dict[str, Dict[str, Any]] = {}
DATASET_LOCK = threading.Lock()
SESSION_TTL_SECONDS = 7200  # 2 hours

# Global Spark / Hadoop configuration holder
PROCESSING_CONFIG = {
    "engine": "Local In-Memory",
    "spark_available": False,
    "spark_initialized": False,
    "spark_session": None,
    "hdfs_uri": os.environ.get("HDFS_URI", ""),
    "hdfs_available": False,
    "status_message": "Local processing engine active (PySpark/HDFS on standby)",
}

# ==============================================================================
# HADOOP & PYSPARK INTEGRATION (OPTIONAL WITH LOCAL FALLBACK)
# ==============================================================================

class HadoopSparkManager:
    """Manages optional PySpark session and Hadoop HDFS integration with local fallback."""

    @classmethod
    def check_pyspark_available(cls) -> bool:
        """Check if pyspark package can be imported in the current environment."""
        try:
            import pyspark
            return True
        except ImportError:
            return False

    @classmethod
    def initialize_spark(cls, master: str = "local[*]", app_name: str = "LogShieldAnalytics") -> bool:
        """Attempt initializing a SparkSession. Returns True if successful, False on failure."""
        if not cls.check_pyspark_available():
            PROCESSING_CONFIG["spark_available"] = False
            PROCESSING_CONFIG["status_message"] = "PySpark not installed. Using local processing engine."
            return False

        try:
            from pyspark.sql import SparkSession
            spark = SparkSession.builder \
                .master(master) \
                .appName(app_name) \
                .config("spark.driver.memory", "1g") \
                .getOrCreate()
            PROCESSING_CONFIG["spark_available"] = True
            PROCESSING_CONFIG["spark_initialized"] = True
            PROCESSING_CONFIG["spark_session"] = spark
            PROCESSING_CONFIG["engine"] = "Apache PySpark (Distributed)"
            PROCESSING_CONFIG["status_message"] = f"PySpark active (Master: {master})"
            return True
        except Exception as e:
            PROCESSING_CONFIG["spark_available"] = False
            PROCESSING_CONFIG["spark_initialized"] = False
            PROCESSING_CONFIG["status_message"] = f"Spark init failed ({e!s}). Reverted to local engine."
            return False

    @classmethod
    def check_hdfs_connection(cls, hdfs_uri: str) -> bool:
        """Verify connectivity to Hadoop HDFS NameNode."""
        if not hdfs_uri:
            return False
        import urllib.request
        try:
            # Check WebHDFS / NameNode status endpoint
            check_url = hdfs_uri if hdfs_uri.startswith("http") else f"http://{hdfs_uri}:9870"
            req = urllib.request.Request(check_url, headers={"User-Agent": "LogShield"})
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                return resp.status in (200, 302, 401)
        except Exception:
            return False

    @classmethod
    def analyze_with_spark(cls, file_path_or_uri: str) -> Optional[Dict[str, Any]]:
        """
        Execute distributed log analysis using PySpark DataFrame API.
        Extracts status, timestamp, hour, path, ip, aggregates metrics,
        and returns a lightweight dictionary without loading raw records into Python memory.
        """
        if not PROCESSING_CONFIG["spark_initialized"] or not PROCESSING_CONFIG["spark_session"]:
            return None

        try:
            from pyspark.sql import functions as F
            spark = PROCESSING_CONFIG["spark_session"]

            # Read log file as text
            df = spark.read.text(file_path_or_uri)
            total_lines = df.count()
            if total_lines == 0:
                return None

            # Common Log Format regex pattern
            clf_pattern = r'^(\S+)\s+\S+\s+\S+\s+\[([^\]]+)\]\s+"([A-Z]+)\s+([^"\s]+)[^"]*"\s+(\d{3})\s+(\d+|-)'
            parsed = df.select(
                F.regexp_extract("value", clf_pattern, 1).alias("ip"),
                F.regexp_extract("value", clf_pattern, 2).alias("raw_time"),
                F.regexp_extract("value", clf_pattern, 3).alias("method"),
                F.regexp_extract("value", clf_pattern, 4).alias("path"),
                F.regexp_extract("value", clf_pattern, 5).alias("status"),
                F.regexp_extract("value", clf_pattern, 6).alias("size"),
            ).filter(F.col("status") != "")

            valid_count = parsed.count()
            if valid_count == 0:
                return None

            malformed_count = total_lines - valid_count

            # Status breakdown
            status_df = parsed.groupBy("status").count().orderBy(F.desc("count")).collect()
            status_counts = {row["status"]: row["count"] for row in status_df}
            total_404 = status_counts.get("404", 0)
            rate_404 = round((total_404 / valid_count * 100), 2) if valid_count > 0 else 0.0

            category_counts = {"2xx": 0, "3xx": 0, "4xx": 0, "5xx": 0, "other": 0}
            total_errors = 0
            for code, count in status_counts.items():
                if code.startswith("2"):
                    category_counts["2xx"] += count
                elif code.startswith("3"):
                    category_counts["3xx"] += count
                elif code.startswith("4"):
                    category_counts["4xx"] += count
                    total_errors += count
                elif code.startswith("5"):
                    category_counts["5xx"] += count
                    total_errors += count
                else:
                    category_counts["other"] += count

            error_rate = round((total_errors / valid_count * 100), 2) if valid_count > 0 else 0.0

            # Hourly distribution (regex extracts the hour part :HH:)
            hour_col = F.regexp_extract("raw_time", r':(\d{2}):\d{2}:\d{2}', 1).cast("int")
            hourly_df = parsed.withColumn("hour", hour_col)

            hourly_all = hourly_df.groupBy("hour").count().collect()
            hourly_404 = hourly_df.filter(F.col("status") == "404").groupBy("hour").count().collect()

            req_by_hour = {r["hour"]: r["count"] for r in hourly_all if r["hour"] is not None}
            err_by_hour = {r["hour"]: r["count"] for r in hourly_404 if r["hour"] is not None}

            peak_hour = None
            peak_hour_count = 0
            hourly_distribution = []
            for h in range(24):
                reqs = req_by_hour.get(h, 0)
                errs = err_by_hour.get(h, 0)
                if errs > peak_hour_count:
                    peak_hour_count = errs
                    peak_hour = h
                hourly_distribution.append({
                    "hour": h,
                    "label": f"{h:02d}:00",
                    "requests": reqs,
                    "errors_404": errs,
                })

            # Top 10 broken paths
            top_paths_df = parsed.filter(F.col("status") == "404").groupBy("path").count().orderBy(F.desc("count")).limit(10).collect()
            all_paths_counts = {
                r["path"]: r["count"]
                for r in parsed.filter(F.col("path").isin([r["path"] for r in top_paths_df])).groupBy("path").count().collect()
            }
            top_endpoints = []
            for r in top_paths_df:
                p = r["path"]
                errs = r["count"]
                tot = all_paths_counts.get(p, errs)
                fail_pct = round((errs / tot * 100), 1) if tot > 0 else 0.0
                top_endpoints.append({
                    "path": p,
                    "count": tot,
                    "errors_404": errs,
                    "failure_pct": fail_pct,
                })

            # Top 10 client IPs
            top_ips_df = parsed.groupBy("ip").count().orderBy(F.desc("count")).limit(10).collect()
            top_ips_404 = {
                r["ip"]: r["count"]
                for r in parsed.filter((F.col("status") == "404") & F.col("ip").isin([r["ip"] for r in top_ips_df])).groupBy("ip").count().collect()
            }
            top_ips = []
            for r in top_ips_df:
                ip_addr = r["ip"]
                tot = r["count"]
                errs = top_ips_404.get(ip_addr, 0)
                err_pct = round((errs / tot * 100), 1) if tot > 0 else 0.0
                top_ips.append({
                    "ip": ip_addr,
                    "count": tot,
                    "errors_404": errs,
                    "error_pct": err_pct,
                })

            sorted_status = [
                {"code": code, "count": count, "pct": round(count / valid_count * 100, 2)}
                for code, count in sorted(status_counts.items(), key=lambda x: x[1], reverse=True)
            ]

            # Sample rows for the interactive table
            sample_rows = [
                r.asDict() for r in parsed.limit(100).collect()
            ]

            return {
                "analytics": {
                    "total_records": valid_count,
                    "total_valid_requests": valid_count,
                    "excluded_records": malformed_count,
                    "total_404": total_404,
                    "rate_404": rate_404,
                    "total_errors": total_errors,
                    "error_rate": error_rate,
                    "status_available": True,
                    "path_available": True,
                    "ip_available": True,
                    "timeline_available": True,
                    "timezone": "UTC (Normalized)",
                    "peak_hour": peak_hour,
                    "peak_hour_count": peak_hour_count,
                    "status_breakdown": sorted_status,
                    "category_counts": category_counts,
                    "top_endpoints": top_endpoints,
                    "top_ips": top_ips,
                    "hourly_distribution": hourly_distribution,
                    "daily_trend": [],
                    "column_mapping": {"status": "status", "path": "path", "ip": "ip", "timestamp": "timestamp", "method": "method"},
                    "headers": ["ip", "timestamp", "method", "path", "status", "size"],
                },
                "rows": sample_rows,
                "headers": ["ip", "timestamp", "method", "path", "status", "size"],
                "mapping": {"status": "status", "path": "path", "ip": "ip", "timestamp": "timestamp", "method": "method"},
            }
        except Exception:
            return None


# ==============================================================================
# FLASK APPLICATION SETUP
# ==============================================================================

app = Flask(__name__)
app.secret_key = secrets.token_hex(24)
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH


@app.errorhandler(RequestEntityTooLarge)
def handle_file_too_large(e):
    return (
        jsonify({
            "success": False,
            "error": f"Upload rejected: File exceeds the maximum allowed size of {MAX_UPLOAD_SIZE_MB}MB.",
        }),
        413,
    )


@app.errorhandler(500)
def handle_server_error(e):
    return jsonify({"success": False, "error": f"Internal server error: {e!s}"}), 500


# ==============================================================================
# STORAGE & CLEANUP UTILITIES
# ==============================================================================

def cleanup_expired_sessions() -> None:
    """Evict in-memory sessions and temporary files older than SESSION_TTL_SECONDS."""
    now = time.time()
    with DATASET_LOCK:
        expired = [sid for sid, d in DATASET_STORE.items() if now - d.get("created_at", 0) > SESSION_TTL_SECONDS]
        for sid in expired:
            DATASET_STORE.pop(sid, None)

    try:
        for f in UPLOAD_DIR.glob("*"):
            if f.is_file() and now - f.stat().st_mtime > SESSION_TTL_SECONDS:
                try:
                    f.unlink()
                except OSError:
                    pass
    except Exception:
        pass


def get_or_create_session_id() -> str:
    """Retrieve existing session ID from cookie or generate a new secure UUID."""
    if "sid" not in session:
        session["sid"] = str(uuid.uuid4())
    return session["sid"]


# ==============================================================================
# LOG & CSV PARSING ENGINE
# ==============================================================================

def decode_file_bytes(raw_bytes: bytes) -> Tuple[str, str]:
    """
    Attempt decoding raw bytes using common CSV encodings.
    Returns (decoded_text, encoding_used).
    """
    encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252", "iso-8859-1"]
    for enc in encodings:
        try:
            return raw_bytes.decode(enc), enc
        except UnicodeDecodeError:
            continue
    return raw_bytes.decode("utf-8", errors="replace"), "utf-8-replace"


def parse_normalized_datetime(ts_val: Any) -> Optional[datetime.datetime]:
    """
    Parse timestamp string and normalize consistently to UTC timezone.
    Supports CLF, ISO 8601, standard formats, and epoch timestamps.
    """
    if not ts_val:
        return None
    s = str(ts_val).strip()

    # Apache/Nginx CLF format: 01/Sep/2026:03:14:22 +0000 or [01/Sep/2026:03:14:22 -0500]
    clf_m = re.search(r'(\d{2}/\w{3}/\d{4}:\d{2}:\d{2}:\d{2})\s*([+-]\d{4})?', s)
    if clf_m:
        dt_str = clf_m.group(1)
        tz_str = clf_m.group(2) or "+0000"
        try:
            dt = datetime.datetime.strptime(f"{dt_str} {tz_str}", "%d/%b/%Y:%H:%M:%S %z")
            return dt.astimezone(datetime.timezone.utc)
        except Exception:
            pass

    # ISO 8601: 2026-09-01T03:14:22Z or 2026-09-01 03:14:22+00:00
    iso_clean = s.replace("Z", "+00:00")
    try:
        dt = datetime.datetime.fromisoformat(iso_clean)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt.astimezone(datetime.timezone.utc)
    except Exception:
        pass

    # Standard formats without timezone (assume UTC)
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S", "%d/%m/%Y %H:%M:%S", "%m/%d/%Y %H:%M:%S"):
        try:
            dt = datetime.datetime.strptime(s, fmt)
            return dt.replace(tzinfo=datetime.timezone.utc)
        except Exception:
            pass

    # Epoch timestamp: 10 digits (seconds) or 13 digits (milliseconds)
    if s.isdigit() and len(s) in (10, 13):
        try:
            secs = int(s) if len(s) == 10 else int(s) / 1000.0
            return datetime.datetime.fromtimestamp(secs, tz=datetime.timezone.utc)
        except Exception:
            pass

    return None


def detect_columns(headers: List[str]) -> Dict[str, Optional[str]]:
    """Map detected header names to standard semantic fields."""
    mapping: Dict[str, Optional[str]] = {k: None for k in COLUMN_ALIASES}
    lower_headers = {h.lower().replace("-", "_").replace(" ", "_"): h for h in headers}

    for semantic_name, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in lower_headers:
                mapping[semantic_name] = lower_headers[alias]
                break

    return mapping


def parse_raw_log_lines(text: str) -> Tuple[List[str], List[Dict[str, Any]], int]:
    """
    Parse raw Apache/Nginx CLF text lines into structured dictionaries.
    Returns (headers, valid_rows, malformed_count).
    """
    headers = ["ip", "timestamp", "method", "path", "status", "size"]
    rows: List[Dict[str, Any]] = []
    malformed_count = 0

    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = CLF_REGEX.match(line)
        if m:
            ip, ts, method, path, status, size = m.groups()
            rows.append({
                "ip": ip,
                "timestamp": ts,
                "method": method,
                "path": path,
                "status": int(status),
                "size": int(size) if size.isdigit() else 0,
            })
        else:
            malformed_count += 1

    return headers, rows, malformed_count


def parse_csv_content(text: str) -> Tuple[List[str], List[Dict[str, Any]], int]:
    """
    Parse CSV text using delimiter sniffing and DictReader.
    Returns (headers, list of row dicts, malformed_count).
    """
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return [], [], 0

    # Detect delimiter with csv.Sniffer or fallback
    sample = "\n".join(lines[:20])
    delimiter = ","
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",\t;|")
        delimiter = dialect.delimiter
    except Exception:
        first_line = lines[0]
        for candidate in [",", "\t", ";", "|"]:
            if candidate in first_line:
                delimiter = candidate
                break

    reader = csv.DictReader(lines, delimiter=delimiter)
    headers = [h.strip() for h in (reader.fieldnames or []) if h]
    rows: List[Dict[str, Any]] = []
    malformed_count = 0

    for raw_row in reader:
        if None in raw_row or any(v is None for v in raw_row.values()):
            malformed_count += 1
        cleaned_row: Dict[str, Any] = {}
        for k, v in raw_row.items():
            if k is not None:
                val = v.strip() if isinstance(v, str) else v
                cleaned_row[k.strip()] = val
        rows.append(cleaned_row)

    return headers, rows, malformed_count


# ==============================================================================
# LOG ANALYTICS & HOURLY 404 CALCULATIONS
# ==============================================================================

def compute_analytics(rows: List[Dict[str, Any]], headers: List[str], mapping: Dict[str, Optional[str]], malformed_count: int = 0) -> Dict[str, Any]:
    """
    Calculate metrics from actual uploaded data:
      - Total valid requests
      - HTTP 404 count and percentage formula: (404 count / total valid requests) * 100
      - Counts for 200, 301, 400, 403, 404, 500, and other observed status codes
      - Hourly 404 counts for all 24 hours normalized to UTC
      - Peak failure hour with highest 404 count
      - Most frequently failing URLs
      - Most active client IP addresses
      - Date-based error trends
      - Count of excluded/malformed records
    Never fabricates statistics. Handles missing columns gracefully.
    """
    total_valid = len(rows)
    status_col = mapping.get("status")
    path_col = mapping.get("path")
    ip_col = mapping.get("ip")
    time_col = mapping.get("timestamp")

    status_counts: Counter[str] = Counter()
    category_counts: Dict[str, int] = {"2xx": 0, "3xx": 0, "4xx": 0, "5xx": 0, "other": 0}
    total_404 = 0
    total_errors = 0

    if status_col:
        for r in rows:
            val = str(r.get(status_col, "")).strip()
            # Clean numeric status e.g. "404.0" -> "404"
            if re.match(r'^\d+(\.0+)?$', val):
                val = str(int(float(val)))
            if val:
                status_counts[val] += 1
                if val == "404":
                    total_404 += 1
                if val.startswith("2"):
                    category_counts["2xx"] += 1
                elif val.startswith("3"):
                    category_counts["3xx"] += 1
                elif val.startswith("4"):
                    category_counts["4xx"] += 1
                    total_errors += 1
                elif val.startswith("5"):
                    category_counts["5xx"] += 1
                    total_errors += 1
                else:
                    category_counts["other"] += 1

    # Exact required formula: (number of HTTP 404 responses / total valid HTTP requests) * 100
    rate_404 = round((total_404 / total_valid * 100), 2) if total_valid > 0 else 0.0
    error_rate = round((total_errors / total_valid * 100), 2) if total_valid > 0 else 0.0

    # Top failing URLs / endpoints
    top_endpoints: List[Dict[str, Any]] = []
    if path_col:
        path_counter: Counter[str] = Counter()
        path_404_counter: Counter[str] = Counter()
        for r in rows:
            p = str(r.get(path_col, "")).strip()
            if p:
                path_counter[p] += 1
                if status_col and str(r.get(status_col, "")).strip() in ("404", "404.0"):
                    path_404_counter[p] += 1

        for path_name, count in path_counter.most_common(10):
            errs = path_404_counter[path_name]
            fail_pct = round((errs / count * 100), 1) if count > 0 else 0.0
            top_endpoints.append({
                "path": path_name,
                "count": count,
                "errors_404": errs,
                "failure_pct": fail_pct,
            })

    # Most active client IPs (neutral reporting without assuming malicious activity)
    top_ips: List[Dict[str, Any]] = []
    if ip_col:
        ip_counter: Counter[str] = Counter()
        ip_404_counter: Counter[str] = Counter()

        for r in rows:
            ip_addr = str(r.get(ip_col, "")).strip()
            if ip_addr:
                ip_counter[ip_addr] += 1
                if status_col and str(r.get(status_col, "")).strip() in ("404", "404.0"):
                    ip_404_counter[ip_addr] += 1

        for ip_addr, count in ip_counter.most_common(10):
            errs = ip_404_counter[ip_addr]
            err_pct = round((errs / count * 100), 1) if count > 0 else 0.0
            top_ips.append({
                "ip": ip_addr,
                "count": count,
                "errors_404": errs,
                "error_pct": err_pct,
            })

    # Hourly 404 timeline (all 24 hours 00:00 to 23:00 UTC)
    hourly_distribution: List[Dict[str, Any]] = []
    date_trends: Dict[str, Dict[str, int]] = defaultdict(lambda: {"total": 0, "errors_404": 0})
    peak_hour = None
    peak_hour_count = 0

    if time_col:
        hourly_req_counter: Counter[int] = Counter()
        hourly_404_counter: Counter[int] = Counter()

        for r in rows:
            dt = parse_normalized_datetime(r.get(time_col))
            if dt is not None:
                h = dt.hour
                d_str = dt.strftime("%Y-%m-%d")
                hourly_req_counter[h] += 1
                date_trends[d_str]["total"] += 1
                if status_col and str(r.get(status_col, "")).strip() in ("404", "404.0"):
                    hourly_404_counter[h] += 1
                    date_trends[d_str]["errors_404"] += 1

        for hour in range(24):
            reqs = hourly_req_counter[hour]
            errs = hourly_404_counter[hour]
            if errs > peak_hour_count:
                peak_hour_count = errs
                peak_hour = hour
            hourly_distribution.append({
                "hour": hour,
                "label": f"{hour:02d}:00",
                "requests": reqs,
                "errors_404": errs,
            })

    # Sort status codes descending
    sorted_status = [
        {"code": code, "count": count, "pct": round(count / total_valid * 100, 2)}
        for code, count in status_counts.most_common()
    ]

    # Convert date trends to sorted list
    daily_trend = [
        {"date": d, "total": vals["total"], "errors_404": vals["errors_404"]}
        for d, vals in sorted(date_trends.items())
    ]

    return {
        "total_records": total_valid,
        "total_valid_requests": total_valid,
        "excluded_records": malformed_count,
        "total_404": total_404,
        "rate_404": rate_404,
        "total_errors": total_errors,
        "error_rate": error_rate,
        "status_available": bool(status_col),
        "path_available": bool(path_col),
        "ip_available": bool(ip_col),
        "timeline_available": bool(time_col) and any(d["requests"] > 0 for d in hourly_distribution),
        "timezone": "UTC (Normalized)",
        "peak_hour": peak_hour,
        "peak_hour_count": peak_hour_count,
        "status_breakdown": sorted_status,
        "category_counts": category_counts,
        "top_endpoints": top_endpoints,
        "top_ips": top_ips,
        "hourly_distribution": hourly_distribution,
        "daily_trend": daily_trend,
        "column_mapping": mapping,
        "headers": headers,
    }


# ==============================================================================
# SAMPLE DATASET GENERATOR
# ==============================================================================

def generate_sample_dataset() -> Tuple[List[str], List[Dict[str, Any]], int]:
    """
    Generate a realistic baseline log dataset (1,200 records) modeled on the
    Assignment 2 PySpark 200,000 log distribution:
      - 03:00 AM peak failure spike
      - Broken endpoints: /old-promo-page, /deprecated-api/v1, /admin/login
      - Realistic status codes: 200, 301, 404, 403, 500
    """
    import random
    random.seed(42)

    headers = ["ip", "timestamp", "method", "path", "status", "size"]
    rows: List[Dict[str, Any]] = []

    normal_paths = [
        "/index.html", "/home", "/about", "/api/users", "/api/orders",
        "/checkout", "/product/123", "/product/456", "/images/logo.png",
    ]
    error_paths = ["/old-promo-page", "/deprecated-api/v1", "/admin/login", "/product/999"]
    ips = [f"192.168.1.{i}" for i in range(10, 35)] + ["10.0.12.45", "172.16.0.88", "198.51.100.14"]
    active_ips = ["198.51.100.14", "10.0.12.45"]

    base_time = datetime.datetime(2026, 9, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)

    for i in range(1200):
        # 30% of records in 03:00 AM failure window
        if random.random() < 0.32:
            hour = 3
            minute = random.randint(0, 59)
            second = random.randint(0, 59)
            ip_val = random.choice(active_ips) if random.random() < 0.75 else random.choice(ips)
            path_val = random.choice(error_paths) if random.random() < 0.85 else random.choice(normal_paths)
            status_val = random.choices([404, 500, 403], weights=[85, 10, 5])[0]
        else:
            hour = random.choice([9, 10, 11, 14, 15, 16, 20, 21, random.randint(0, 23)])
            minute = random.randint(0, 59)
            second = random.randint(0, 59)
            ip_val = random.choice(ips)
            if random.random() < 0.85:
                path_val = random.choice(normal_paths)
                status_val = random.choices([200, 301, 404], weights=[90, 8, 2])[0]
            else:
                path_val = random.choice(error_paths)
                status_val = random.choices([404, 200, 403], weights=[70, 20, 10])[0]

        record_time = base_time + datetime.timedelta(days=random.randint(0, 6), hours=hour, minutes=minute, seconds=second)
        ts_str = record_time.strftime("%d/%b/%Y:%H:%M:%S +0000")
        method_val = random.choice(["GET", "GET", "GET", "POST", "PUT"])
        size_val = random.randint(200, 4500) if status_val == 200 else random.randint(150, 450)

        rows.append({
            "ip": ip_val,
            "timestamp": ts_str,
            "method": method_val,
            "path": path_val,
            "status": status_val,
            "size": size_val,
        })

    return headers, rows, 0


# ==============================================================================
# FLASK ROUTE HANDLERS
# ==============================================================================

@app.route("/")
def index():
    """Render the dashboard UI."""
    return render_template_string(HTML_TEMPLATE)


@app.route("/health")
@app.route("/api/health")
def health():
    """Healthcheck endpoint."""
    return jsonify({
        "status": "healthy",
        "service": "LogShield Analytics",
        "engine": PROCESSING_CONFIG["engine"],
        "timestamp": time.time(),
    })


@app.route("/api/status")
def api_status():
    """Return application and processing engine status (Local, PySpark, Hadoop HDFS)."""
    sid = get_or_create_session_id()
    with DATASET_LOCK:
        has_dataset = sid in DATASET_STORE

    return jsonify({
        "engine": PROCESSING_CONFIG["engine"],
        "spark_available": PROCESSING_CONFIG["spark_available"],
        "spark_initialized": PROCESSING_CONFIG["spark_initialized"],
        "hdfs_uri": PROCESSING_CONFIG["hdfs_uri"] or None,
        "hdfs_available": PROCESSING_CONFIG["hdfs_available"],
        "status_message": PROCESSING_CONFIG["status_message"],
        "max_upload_size_mb": MAX_UPLOAD_SIZE_MB,
        "has_active_dataset": has_dataset,
    })


@app.route("/upload", methods=["POST"])
@app.route("/api/upload", methods=["POST"])
def upload_file():
    """
    Handle CSV, Apache, or Nginx log file upload:
      - Validates file presence, filename, and extension
      - Decodes encoding safely (UTF-8, Latin-1, CP1252)
      - Automatically detects delimiter and semantic columns
      - Computes real-time metrics and reports excluded/malformed records
      - Caches parsed rows in session store for fast pagination & export
    """
    cleanup_expired_sessions()

    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file uploaded. Please select a CSV or log file."}), 400

    file = request.files["file"]
    if not file or not file.filename:
        return jsonify({"success": False, "error": "Empty filename provided."}), 400

    filename = secure_filename(file.filename)
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({
            "success": False,
            "error": f"Invalid file extension '.{ext}'. Allowed formats: .csv, .log, .txt, .tsv",
        }), 400

    raw_bytes = file.read()
    if len(raw_bytes) == 0:
        return jsonify({"success": False, "error": "Uploaded file is completely empty (0 bytes)."}), 400

    decoded_text, used_enc = decode_file_bytes(raw_bytes)

    first_lines = [l.strip() for l in decoded_text.splitlines() if l.strip()][:5]
    if not first_lines:
        return jsonify({"success": False, "error": "File does not contain any readable text rows."}), 400

    sid = get_or_create_session_id()

    # Optional PySpark distributed analysis for large log/csv datasets
    if PROCESSING_CONFIG["spark_initialized"]:
        temp_file = UPLOAD_DIR / f"spark_{sid}_{filename}"
        try:
            temp_file.write_bytes(raw_bytes)
            spark_result = HadoopSparkManager.analyze_with_spark(str(temp_file))
            if spark_result:
                analytics = spark_result["analytics"]
                headers = spark_result["headers"]
                rows = spark_result["rows"]
                mapping = spark_result["mapping"]
                with DATASET_LOCK:
                    DATASET_STORE[sid] = {
                        "filename": filename,
                        "headers": headers,
                        "mapping": mapping,
                        "rows": rows,
                        "analytics": analytics,
                        "encoding": used_enc,
                        "created_at": time.time(),
                        "engine": "Apache PySpark (Distributed)",
                    }
                return jsonify({
                    "success": True,
                    "filename": filename,
                    "encoding": used_enc,
                    "analytics": analytics,
                    "message": f"Successfully parsed {analytics['total_valid_requests']:,} records via Apache PySpark DataFrame engine.",
                    "engine": "Apache PySpark (Distributed)",
                })
        except Exception:
            pass
        finally:
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except OSError:
                    pass

    # Local processing path (default & reliable fallback)
    # Determine whether to parse as raw Apache/Nginx CLF or tabular CSV
    malformed_count = 0
    if ext in ("log", "txt") and CLF_REGEX.match(first_lines[0]):
        headers, rows, malformed_count = parse_raw_log_lines(decoded_text)
    else:
        headers, rows, malformed_count = parse_csv_content(decoded_text)
        if (len(headers) <= 1 and rows) and CLF_REGEX.match(first_lines[0]):
            headers, rows, malformed_count = parse_raw_log_lines(decoded_text)

    if not rows:
        return jsonify({
            "success": False,
            "error": "Could not extract valid records from this file. Check file formatting or delimiter.",
        }), 400

    mapping = detect_columns(headers)
    analytics = compute_analytics(rows, headers, mapping, malformed_count=malformed_count)

    with DATASET_LOCK:
        DATASET_STORE[sid] = {
            "filename": filename,
            "headers": headers,
            "mapping": mapping,
            "rows": rows,
            "analytics": analytics,
            "encoding": used_enc,
            "created_at": time.time(),
            "engine": "Local In-Memory",
        }

    return jsonify({
        "success": True,
        "filename": filename,
        "encoding": used_enc,
        "analytics": analytics,
        "message": f"Successfully parsed {len(rows):,} records with {len(headers)} columns.",
    })


@app.route("/api/sample", methods=["POST", "GET"])
def load_sample():
    """Load the realistic built-in Assignment 2 log dataset."""
    cleanup_expired_sessions()
    headers, rows, malformed = generate_sample_dataset()
    mapping = detect_columns(headers)
    analytics = compute_analytics(rows, headers, mapping, malformed_count=malformed)

    sid = get_or_create_session_id()
    with DATASET_LOCK:
        DATASET_STORE[sid] = {
            "filename": "sample_apache_server.log",
            "headers": headers,
            "mapping": mapping,
            "rows": rows,
            "analytics": analytics,
            "encoding": "utf-8",
            "created_at": time.time(),
        }

    return jsonify({
        "success": True,
        "filename": "sample_apache_server.log",
        "encoding": "utf-8",
        "analytics": analytics,
        "message": "Loaded sample Apache log dataset (1,200 records with 03:00 AM peak failures).",
    })


@app.route("/api/stats")
def api_stats():
    """Return analysis statistics for the active dataset."""
    sid = get_or_create_session_id()
    with DATASET_LOCK:
        session_data = DATASET_STORE.get(sid)

    if not session_data:
        return jsonify({"error": "No active dataset loaded. Please upload a file."}), 404

    a = session_data["analytics"]
    return jsonify({
        "filename": session_data["filename"],
        "total_requests": a["total_records"],
        "total_valid_requests": a["total_valid_requests"],
        "excluded_records": a["excluded_records"],
        "total_404": a["total_404"],
        "rate_404": a["rate_404"],
        "total_errors": a["total_errors"],
        "error_rate": a["error_rate"],
        "peak_hour": a["peak_hour"],
        "peak_hour_count": a["peak_hour_count"],
        "status_breakdown": a["status_breakdown"],
        "category_counts": a["category_counts"],
        "timezone": a["timezone"],
    })


@app.route("/api/hourly")
def api_hourly():
    """Return hourly 404 counts and total request distribution for all 24 hours."""
    sid = get_or_create_session_id()
    with DATASET_LOCK:
        session_data = DATASET_STORE.get(sid)

    if not session_data:
        return jsonify({"error": "No active dataset loaded."}), 404

    a = session_data["analytics"]
    return jsonify({
        "hourly_distribution": a["hourly_distribution"],
        "peak_hour": a["peak_hour"],
        "peak_hour_count": a["peak_hour_count"],
        "timezone": a["timezone"],
    })


@app.route("/api/urls")
def api_urls():
    """Return URL statistics and failure counts for top failing endpoints."""
    sid = get_or_create_session_id()
    with DATASET_LOCK:
        session_data = DATASET_STORE.get(sid)

    if not session_data:
        return jsonify({"error": "No active dataset loaded."}), 404

    return jsonify({
        "top_endpoints": session_data["analytics"]["top_endpoints"],
    })


@app.route("/api/data")
def get_data():
    """
    Paginated, searchable, filterable, and sortable view of the active dataset.
    Query parameters:
      - page: 1-indexed page number (default: 1)
      - page_size: records per page (default: 25, max: 100)
      - search: string search across all columns
      - status_filter: 'all', '404', '4xx', '5xx', '2xx', '3xx', or specific status code
      - sort_col: header name to sort by
      - sort_dir: 'asc' or 'desc'
    """
    sid = get_or_create_session_id()
    with DATASET_LOCK:
        session_data = DATASET_STORE.get(sid)

    if not session_data:
        return jsonify({"rows": [], "total_rows": 0, "page": 1, "total_pages": 1, "columns": []})

    rows: List[Dict[str, Any]] = session_data["rows"]
    headers: List[str] = session_data["headers"]
    mapping: Dict[str, Optional[str]] = session_data["mapping"]
    status_col = mapping.get("status")

    # 1. Filter by status
    status_filter = request.args.get("status_filter", "all").strip().lower()
    filtered = rows
    if status_col and status_filter and status_filter != "all":
        if status_filter == "404":
            filtered = [r for r in filtered if str(r.get(status_col, "")).startswith("404")]
        elif status_filter == "4xx":
            filtered = [r for r in filtered if str(r.get(status_col, "")).startswith("4")]
        elif status_filter == "5xx":
            filtered = [r for r in filtered if str(r.get(status_col, "")).startswith("5")]
        elif status_filter == "2xx":
            filtered = [r for r in filtered if str(r.get(status_col, "")).startswith("2")]
        elif status_filter == "3xx":
            filtered = [r for r in filtered if str(r.get(status_col, "")).startswith("3")]
        else:
            filtered = [r for r in filtered if str(r.get(status_col, "")) == status_filter]

    # 2. Search query filter
    search_q = request.args.get("search", "").strip().lower()
    if search_q:
        filtered = [
            r for r in filtered
            if any(search_q in str(v).lower() for v in r.values())
        ]

    # 3. Sorting
    sort_col = request.args.get("sort_col", "")
    sort_dir = request.args.get("sort_dir", "asc").lower()
    if sort_col and sort_col in headers:
        reverse = (sort_dir == "desc")
        try:
            filtered = sorted(
                filtered,
                key=lambda x: float(re.sub(r'[^0-9.]', '', str(x.get(sort_col, 0))) or 0),
                reverse=reverse,
            )
        except Exception:
            filtered = sorted(filtered, key=lambda x: str(x.get(sort_col, "")).lower(), reverse=reverse)

    # 4. Pagination
    try:
        page = max(1, int(request.args.get("page", 1)))
        page_size = min(100, max(5, int(request.args.get("page_size", 25))))
    except ValueError:
        page = 1
        page_size = 25

    total_filtered = len(filtered)
    total_pages = max(1, math.ceil(total_filtered / page_size))
    if page > total_pages:
        page = total_pages

    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    page_rows = filtered[start_idx:end_idx]

    return jsonify({
        "rows": page_rows,
        "total_rows": total_filtered,
        "total_unfiltered": len(rows),
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "columns": headers,
        "mapping": mapping,
    })


@app.route("/export")
@app.route("/api/export")
def export_csv():
    """
    Export currently filtered results as a downloadable CSV.
    Implements CSV Formula Injection defense by sanitizing sensitive characters.
    """
    sid = get_or_create_session_id()
    with DATASET_LOCK:
        session_data = DATASET_STORE.get(sid)

    if not session_data or not session_data.get("rows"):
        return jsonify({"error": "No active dataset to export."}), 400

    rows: List[Dict[str, Any]] = session_data["rows"]
    headers: List[str] = session_data["headers"]
    mapping: Dict[str, Optional[str]] = session_data["mapping"]
    status_col = mapping.get("status")

    status_filter = request.args.get("status_filter", "all").strip().lower()
    filtered = rows
    if status_col and status_filter and status_filter != "all":
        if status_filter == "404":
            filtered = [r for r in filtered if str(r.get(status_col, "")).startswith("404")]
        elif status_filter == "4xx":
            filtered = [r for r in filtered if str(r.get(status_col, "")).startswith("4")]
        elif status_filter == "5xx":
            filtered = [r for r in filtered if str(r.get(status_col, "")).startswith("5")]
        elif status_filter == "2xx":
            filtered = [r for r in filtered if str(r.get(status_col, "")).startswith("2")]
        elif status_filter == "3xx":
            filtered = [r for r in filtered if str(r.get(status_col, "")).startswith("3")]
        else:
            filtered = [r for r in filtered if str(r.get(status_col, "")) == status_filter]

    search_q = request.args.get("search", "").strip().lower()
    if search_q:
        filtered = [
            r for r in filtered
            if any(search_q in str(v).lower() for v in r.values())
        ]

    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)
    writer.writerow(headers)

    for r in filtered:
        cleaned_row = []
        for h in headers:
            val = str(r.get(h, ""))
            if val and val[0] in ("=", "+", "-", "@", "\t", "\r"):
                val = f"'{val}"
            cleaned_row.append(val)
        writer.writerow(cleaned_row)

    csv_data = output.getvalue().encode("utf-8")
    return Response(
        csv_data,
        mimetype="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="logshield_filtered_export.csv"',
            "Content-Length": str(len(csv_data)),
        },
    )


@app.route("/api/clear", methods=["POST"])
def clear_data():
    """Clear active uploaded dataset and flush memory session."""
    sid = get_or_create_session_id()
    with DATASET_LOCK:
        DATASET_STORE.pop(sid, None)
    return jsonify({"success": True, "message": "Dataset cleared."})


# ==============================================================================
# EMBEDDED DASHBOARD USER INTERFACE (HTML + CSS + JAVASCRIPT)
# Professional SVG icons only — zero emoji characters used
# ==============================================================================

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>LogShield — Log File Analysis Dashboard</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg-base: #0b1120;
      --bg-surface: #0f172a;
      --bg-card: #1e293b;
      --bg-card-hover: #24344d;
      --border-subtle: #334155;
      --border-glow: #06b6d4;
      --cyan-400: #22d3ee;
      --cyan-500: #06b6d4;
      --cyan-600: #0891b2;
      --cyan-glow: rgba(6, 182, 212, 0.25);
      --text-main: #f8fafc;
      --text-muted: #94a3b8;
      --rose-500: #f43f5e;
      --emerald-500: #10b981;
      --amber-500: #f59e0b;
      --font-sans: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif;
      --font-mono: 'JetBrains Mono', monospace;
    }
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      background: radial-gradient(circle at 50% 0%, #172554 0%, var(--bg-base) 60%);
      color: var(--text-main);
      font-family: var(--font-sans);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      overflow-x: hidden;
    }
    header {
      background: rgba(15, 23, 42, 0.85);
      backdrop-filter: blur(12px);
      border-bottom: 1px solid var(--border-subtle);
      position: sticky;
      top: 0;
      z-index: 50;
    }
    .header-inner {
      max-width: 1440px;
      margin: 0 auto;
      padding: 0.85rem 1.5rem;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 1rem;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      text-decoration: none;
      color: inherit;
    }
    .brand-icon {
      width: 38px;
      height: 38px;
      background: linear-gradient(135deg, #06b6d4, #3b82f6);
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 0 16px var(--cyan-glow);
    }
    .brand-title {
      font-weight: 800;
      font-size: 1.25rem;
      letter-spacing: -0.02em;
      background: linear-gradient(135deg, #ffffff 40%, #22d3ee);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }
    .badge-chip {
      background: rgba(6, 182, 212, 0.12);
      border: 1px solid rgba(6, 182, 212, 0.3);
      color: var(--cyan-400);
      font-family: var(--font-mono);
      font-size: 0.75rem;
      padding: 0.25rem 0.6rem;
      border-radius: 9999px;
      font-weight: 600;
      display: inline-flex;
      align-items: center;
      gap: 0.35rem;
    }
    .header-actions {
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }
    .btn {
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.5rem 1rem;
      border-radius: 8px;
      font-size: 0.875rem;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s ease;
      text-decoration: none;
      border: none;
    }
    .btn svg { width: 16px; height: 16px; }
    .btn-primary {
      background: linear-gradient(135deg, #06b6d4, #0891b2);
      color: #042f2e;
      box-shadow: 0 4px 14px rgba(6, 182, 212, 0.3);
    }
    .btn-primary:hover {
      background: linear-gradient(135deg, #22d3ee, #06b6d4);
      transform: translateY(-1px);
    }
    .btn-secondary {
      background: rgba(30, 41, 59, 0.8);
      color: var(--text-main);
      border: 1px solid var(--border-subtle);
    }
    .btn-secondary:hover {
      background: var(--bg-card-hover);
      border-color: var(--cyan-500);
    }
    .btn-danger {
      background: rgba(244, 63, 94, 0.15);
      color: #fda4af;
      border: 1px solid rgba(244, 63, 94, 0.3);
    }
    .btn-danger:hover {
      background: rgba(244, 63, 94, 0.25);
    }
    main {
      flex: 1;
      max-width: 1440px;
      width: 100%;
      margin: 0 auto;
      padding: 2rem 1.5rem;
      display: flex;
      flex-direction: column;
      gap: 2rem;
    }
    .upload-container {
      background: var(--bg-surface);
      border: 2px dashed var(--border-subtle);
      border-radius: 16px;
      padding: 2.5rem 1.5rem;
      text-align: center;
      transition: all 0.25s ease;
      cursor: pointer;
      position: relative;
    }
    .upload-container:hover, .upload-container.dragover {
      border-color: var(--cyan-500);
      background: rgba(6, 182, 212, 0.04);
      box-shadow: 0 0 25px var(--cyan-glow);
    }
    .upload-icon {
      width: 56px;
      height: 56px;
      margin: 0 auto 1rem;
      background: rgba(6, 182, 212, 0.15);
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      color: var(--cyan-400);
    }
    .upload-title {
      font-size: 1.25rem;
      font-weight: 700;
      margin-bottom: 0.4rem;
    }
    .upload-subtitle {
      color: var(--text-muted);
      font-size: 0.9rem;
      margin-bottom: 1.2rem;
    }
    .upload-actions {
      display: flex;
      justify-content: center;
      align-items: center;
      gap: 1rem;
      flex-wrap: wrap;
    }
    #fileInput { display: none; }
    .alert {
      padding: 1rem 1.25rem;
      border-radius: 10px;
      font-size: 0.9rem;
      display: none;
      align-items: center;
      gap: 0.75rem;
      animation: fadeIn 0.3s ease;
    }
    .alert-error {
      background: rgba(244, 63, 94, 0.12);
      border: 1px solid rgba(244, 63, 94, 0.3);
      color: #fecdd3;
    }
    .alert-success {
      background: rgba(16, 185, 129, 0.12);
      border: 1px solid rgba(16, 185, 129, 0.3);
      color: #a7f3d0;
    }
    .metrics-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 1.25rem;
    }
    .metric-card {
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      border-radius: 12px;
      padding: 1.25rem;
      position: relative;
      overflow: hidden;
      transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .metric-card:hover {
      transform: translateY(-2px);
      border-color: rgba(6, 182, 212, 0.4);
    }
    .metric-card::after {
      content: '';
      position: absolute;
      top: 0; left: 0; right: 0;
      height: 3px;
      background: linear-gradient(90deg, var(--cyan-500), transparent);
    }
    .metric-card.rose::after { background: linear-gradient(90deg, var(--rose-500), transparent); }
    .metric-card.amber::after { background: linear-gradient(90deg, var(--amber-500), transparent); }
    .metric-card.emerald::after { background: linear-gradient(90deg, var(--emerald-500), transparent); }
    .metric-label {
      font-size: 0.8rem;
      text-transform: uppercase;
      font-weight: 700;
      letter-spacing: 0.05em;
      color: var(--text-muted);
      margin-bottom: 0.5rem;
    }
    .metric-value {
      font-size: 2rem;
      font-weight: 800;
      color: var(--text-main);
      font-family: var(--font-mono);
      line-height: 1.1;
    }
    .metric-subtext {
      margin-top: 0.5rem;
      font-size: 0.8rem;
      color: var(--text-muted);
    }
    .charts-grid {
      display: grid;
      grid-template-columns: 2fr 1fr;
      gap: 1.5rem;
    }
    @media (max-width: 1024px) {
      .charts-grid { grid-template-columns: 1fr; }
    }
    .card {
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      border-radius: 14px;
      padding: 1.5rem;
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }
    .card-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-bottom: 1px solid var(--border-subtle);
      padding-bottom: 0.75rem;
    }
    .card-title {
      font-size: 1.05rem;
      font-weight: 700;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }
    .card-title svg { width: 18px; height: 18px; color: var(--cyan-400); }
    .timeline-chart-container {
      height: 220px;
      display: flex;
      align-items: flex-end;
      gap: 6px;
      padding-top: 1rem;
      position: relative;
    }
    .chart-bar-col {
      flex: 1;
      height: 100%;
      display: flex;
      flex-direction: column;
      justify-content: flex-end;
      align-items: center;
      gap: 4px;
      position: relative;
    }
    .chart-bar {
      width: 100%;
      background: var(--cyan-600);
      border-radius: 4px 4px 0 0;
      transition: height 0.4s ease, background 0.2s ease;
      min-height: 2px;
      position: relative;
    }
    .chart-bar.peak {
      background: var(--rose-500);
      box-shadow: 0 0 12px rgba(244, 63, 94, 0.4);
    }
    .chart-bar:hover {
      background: var(--cyan-400);
    }
    .chart-label {
      font-size: 0.65rem;
      font-family: var(--font-mono);
      color: var(--text-muted);
    }
    .tooltip {
      position: absolute;
      bottom: calc(100% + 8px);
      left: 50%;
      transform: translateX(-50%);
      background: #020617;
      border: 1px solid var(--border-subtle);
      color: white;
      padding: 0.25rem 0.5rem;
      border-radius: 6px;
      font-size: 0.7rem;
      font-family: var(--font-mono);
      white-space: nowrap;
      pointer-events: none;
      display: none;
      z-index: 10;
    }
    .chart-bar-col:hover .tooltip { display: block; }
    .ranked-list {
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
    }
    .ranked-item {
      display: flex;
      flex-direction: column;
      gap: 0.25rem;
      font-size: 0.85rem;
    }
    .ranked-meta {
      display: flex;
      justify-content: space-between;
      font-family: var(--font-mono);
      font-size: 0.8rem;
    }
    .bar-bg {
      background: rgba(51, 65, 85, 0.5);
      border-radius: 9999px;
      height: 7px;
      overflow: hidden;
    }
    .bar-fill {
      height: 100%;
      background: linear-gradient(90deg, #06b6d4, #22d3ee);
      border-radius: 9999px;
      transition: width 0.4s ease;
    }
    .bar-fill.rose { background: linear-gradient(90deg, #f43f5e, #fda4af); }
    .table-controls {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 1rem;
      margin-bottom: 0.75rem;
    }
    .search-box {
      flex: 1;
      min-width: 260px;
      position: relative;
    }
    .search-input {
      width: 100%;
      background: var(--bg-card);
      border: 1px solid var(--border-subtle);
      color: var(--text-main);
      padding: 0.5rem 1rem 0.5rem 2.2rem;
      border-radius: 8px;
      font-family: var(--font-sans);
      font-size: 0.875rem;
      outline: none;
    }
    .search-input:focus { border-color: var(--cyan-500); box-shadow: 0 0 10px var(--cyan-glow); }
    .search-icon {
      position: absolute;
      left: 0.75rem;
      top: 50%;
      transform: translateY(-50%);
      color: var(--text-muted);
      width: 16px;
      height: 16px;
    }
    .filter-select {
      background: var(--bg-card);
      border: 1px solid var(--border-subtle);
      color: var(--text-main);
      padding: 0.5rem 1rem;
      border-radius: 8px;
      font-size: 0.875rem;
      outline: none;
      cursor: pointer;
    }
    .table-container {
      overflow-x: auto;
      border-radius: 10px;
      border: 1px solid var(--border-subtle);
    }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.85rem;
      text-align: left;
    }
    thead {
      background: #111c33;
      border-bottom: 1px solid var(--border-subtle);
    }
    th {
      padding: 0.75rem 1rem;
      font-weight: 700;
      color: var(--text-muted);
      cursor: pointer;
      user-select: none;
      white-space: nowrap;
    }
    th:hover { color: var(--cyan-400); }
    td {
      padding: 0.65rem 1rem;
      border-bottom: 1px solid rgba(51, 65, 85, 0.4);
      white-space: nowrap;
      font-family: var(--font-mono);
      font-size: 0.8rem;
    }
    tbody tr:hover { background: rgba(30, 41, 59, 0.5); }
    .status-badge {
      display: inline-block;
      padding: 0.2rem 0.5rem;
      border-radius: 6px;
      font-weight: 700;
      font-size: 0.75rem;
    }
    .status-2xx { background: rgba(16, 185, 129, 0.15); color: #34d399; }
    .status-3xx { background: rgba(59, 130, 246, 0.15); color: #60a5fa; }
    .status-4xx { background: rgba(245, 158, 11, 0.15); color: #fbbf24; }
    .status-404 { background: rgba(244, 63, 94, 0.2); color: #fda4af; font-weight: 800; border: 1px solid rgba(244, 63, 94, 0.4); }
    .status-5xx { background: rgba(225, 29, 72, 0.25); color: #f43f5e; }
    .pagination {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 1rem;
      margin-top: 1rem;
      font-size: 0.85rem;
      color: var(--text-muted);
    }
    .pagination-actions {
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }
    footer {
      border-top: 1px solid var(--border-subtle);
      padding: 1.5rem;
      text-align: center;
      font-size: 0.8rem;
      color: var(--text-muted);
      background: var(--bg-surface);
    }
    @keyframes fadeIn { from { opacity: 0; transform: translateY(-4px); } to { opacity: 1; transform: translateY(0); } }
  </style>
</head>
<body>

  <!-- HEADER -->
  <header>
    <div class="header-inner">
      <a href="/" class="brand">
        <div class="brand-icon">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#042f2e" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
          </svg>
        </div>
        <div>
          <span class="brand-title">LogShield</span>
          <span class="badge-chip">Log Analytics Dashboard</span>
        </div>
      </a>
      <div class="header-actions">
        <span id="engineBadge" class="badge-chip">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="3"/>
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
          </svg>
          Engine: Local In-Memory
        </span>
        <button id="btnSample" class="btn btn-secondary">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
          </svg>
          Load Sample Data
        </button>
        <button id="btnExport" class="btn btn-primary" style="display:none;">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="7 10 12 15 17 10"/>
            <line x1="12" y1="15" x2="12" y2="3"/>
          </svg>
          Export CSV
        </button>
        <button id="btnClear" class="btn btn-danger" style="display:none;">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="3 6 5 6 21 6"/>
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
          </svg>
          Clear
        </button>
      </div>
    </div>
  </header>

  <!-- MAIN BODY -->
  <main>
    <div id="alertBox" class="alert"></div>

    <!-- UPLOAD ZONE -->
    <div id="dropZone" class="upload-container">
      <div class="upload-icon">
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
          <polyline points="17 8 12 3 7 8"/>
          <line x1="12" y1="3" x2="12" y2="15"/>
        </svg>
      </div>
      <h2 class="upload-title">Drop your Server Log or CSV file here</h2>
      <p class="upload-subtitle">Supports Apache CLF, Nginx access logs, and CSV files (UTF-8, Latin-1, CP1252 &bull; Max 32MB)</p>
      <div class="upload-actions">
        <button type="button" class="btn btn-primary" onclick="document.getElementById('fileInput').click()">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
          </svg>
          Select File from Computer
        </button>
        <input type="file" id="fileInput" accept=".csv,.log,.txt,.tsv">
      </div>
    </div>

    <!-- DASHBOARD CONTENT (Hidden until dataset loaded) -->
    <div id="dashboardSection" style="display:none; display:flex; flex-direction:column; gap:2rem;">
      
      <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:1rem;">
        <div>
          <h2 id="activeFileName" style="font-size:1.4rem; font-weight:800; color:var(--text-main);"></h2>
          <p id="activeFileMeta" style="color:var(--text-muted); font-size:0.85rem; margin-top:0.25rem;"></p>
        </div>
        <div id="detectedBadges" style="display:flex; gap:0.5rem; flex-wrap:wrap;"></div>
      </div>

      <!-- KPI METRICS GRID -->
      <div class="metrics-grid">
        <div class="metric-card">
          <div class="metric-label">Total HTTP Requests</div>
          <div class="metric-value" id="kpiTotal">0</div>
          <div class="metric-subtext" id="kpiExcluded">0 unparseable rows excluded</div>
        </div>
        <div class="metric-card rose">
          <div class="metric-label">Total 404 Errors</div>
          <div class="metric-value" id="kpi404">0</div>
          <div class="metric-subtext" id="kpi404Rate">0.00% failure rate</div>
        </div>
        <div class="metric-card amber">
          <div class="metric-label">Total Error Rate (4xx + 5xx)</div>
          <div class="metric-value" id="kpiErrorRate">0.00%</div>
          <div class="metric-subtext" id="kpiErrorCounts">0 total errors</div>
        </div>
        <div class="metric-card emerald">
          <div class="metric-label">Peak Failure Window</div>
          <div class="metric-value" id="kpiPeakHour">--</div>
          <div class="metric-subtext" id="kpiPeakCount">0 errors recorded</div>
        </div>
      </div>

      <!-- CHARTS SECTION -->
      <div class="charts-grid">
        <!-- 24-HOUR TIMELINE CHART -->
        <div class="card">
          <div class="card-header">
            <div class="card-title">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="20" x2="18" y2="10"/>
                <line x1="12" y1="20" x2="12" y2="4"/>
                <line x1="6" y1="20" x2="6" y2="14"/>
              </svg>
              24-Hour Failure &amp; Request Timeline (UTC Normalized)
            </div>
            <span class="badge-chip" id="timelineBadge">Hourly 404 Counts</span>
          </div>
          <div id="timelineContainer" class="timeline-chart-container"></div>
        </div>

        <!-- STATUS CODE DISTRIBUTION -->
        <div class="card">
          <div class="card-header">
            <div class="card-title">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"/>
                <line x1="12" y1="8" x2="12" y2="12"/>
                <line x1="12" y1="16" x2="12.01" y2="16"/>
              </svg>
              HTTP Status Breakdown
            </div>
          </div>
          <div id="statusList" class="ranked-list"></div>
        </div>
      </div>

      <!-- TOP BROKEN URLS & ACTIVE CLIENT IPS -->
      <div class="charts-grid">
        <!-- TOP BROKEN URLS -->
        <div class="card">
          <div class="card-header">
            <div class="card-title">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/>
                <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>
              </svg>
              Frequently Failing URLs (Top 404 Endpoints)
            </div>
          </div>
          <div id="topEndpointsList" class="ranked-list"></div>
        </div>

        <!-- ACTIVE CLIENT IPS -->
        <div class="card">
          <div class="card-header">
            <div class="card-title">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="2" y="2" width="20" height="8" rx="2" ry="2"/>
                <rect x="2" y="14" width="20" height="8" rx="2" ry="2"/>
                <line x1="6" y1="6" x2="6.01" y2="6"/>
                <line x1="6" y1="18" x2="6.01" y2="18"/>
              </svg>
              Most Active Client IP Addresses
            </div>
          </div>
          <div id="topIpsList" class="ranked-list"></div>
        </div>
      </div>

      <!-- DATA EXPLORER TABLE -->
      <div class="card">
        <div class="card-header">
          <div class="card-title">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
              <line x1="16" y1="13" x2="8" y2="13"/>
              <line x1="16" y1="17" x2="8" y2="17"/>
              <polyline points="10 9 9 9 8 9"/>
            </svg>
            Interactive Log Data Explorer
          </div>
          <span id="recordCountChip" class="badge-chip">0 records</span>
        </div>

        <!-- CONTROLS -->
        <div class="table-controls">
          <div class="search-box">
            <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="11" cy="11" r="8"/>
              <line x1="21" y1="21" x2="16.65" y2="16.65"/>
            </svg>
            <input type="text" id="tableSearch" class="search-input" placeholder="Search across path, IP, status code...">
          </div>
          <div style="display:flex; gap:0.5rem; align-items:center;">
            <select id="statusFilter" class="filter-select">
              <option value="all">All Status Codes</option>
              <option value="404">404 Not Found Only</option>
              <option value="4xx">4xx Client Errors</option>
              <option value="5xx">5xx Server Errors</option>
              <option value="2xx">200 OK Requests</option>
              <option value="3xx">3xx Redirects</option>
            </select>
            <select id="pageSizeSelect" class="filter-select">
              <option value="10">10 / page</option>
              <option value="25" selected>25 / page</option>
              <option value="50">50 / page</option>
              <option value="100">100 / page</option>
            </select>
          </div>
        </div>

        <!-- TABLE -->
        <div class="table-container">
          <table id="dataTable">
            <thead id="tableHead"></thead>
            <tbody id="tableBody"></tbody>
          </table>
        </div>

        <!-- PAGINATION -->
        <div class="pagination">
          <div id="paginationInfo">Showing 0 to 0 of 0 entries</div>
          <div class="pagination-actions">
            <button id="btnPrevPage" class="btn btn-secondary" style="padding:0.4rem 0.8rem;">&larr; Previous</button>
            <span id="pageIndicator" style="font-family:var(--font-mono); font-weight:700;">Page 1 of 1</span>
            <button id="btnNextPage" class="btn btn-secondary" style="padding:0.4rem 0.8rem;">Next &rarr;</button>
          </div>
        </div>
      </div>

    </div>
  </main>

  <!-- FOOTER -->
  <footer>
    LogShield Log File Analysis Platform &bull; Clean Single-File Architecture &bull; Assignment 2: Hadoop &amp; PySpark Project #19
  </footer>

  <script>
    let activeData = null;
    let currentPage = 1;
    let totalPages = 1;
    let currentSortCol = '';
    let currentSortDir = 'asc';

    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const alertBox = document.getElementById('alertBox');
    const dashboardSection = document.getElementById('dashboardSection');
    const btnSample = document.getElementById('btnSample');
    const btnExport = document.getElementById('btnExport');
    const btnClear = document.getElementById('btnClear');
    const tableSearch = document.getElementById('tableSearch');
    const statusFilter = document.getElementById('statusFilter');
    const pageSizeSelect = document.getElementById('pageSizeSelect');
    const btnPrevPage = document.getElementById('btnPrevPage');
    const btnNextPage = document.getElementById('btnNextPage');
    const engineBadge = document.getElementById('engineBadge');

    // Fetch engine status
    async function updateEngineStatus() {
      try {
        const resp = await fetch('/api/status');
        const data = await resp.json();
        engineBadge.textContent = `Engine: ${data.engine}`;
      } catch (err) {}
    }
    updateEngineStatus();

    dropZone.addEventListener('dragover', (e) => {
      e.preventDefault();
      dropZone.classList.add('dragover');
    });
    dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
    dropZone.addEventListener('drop', (e) => {
      e.preventDefault();
      dropZone.classList.remove('dragover');
      if (e.dataTransfer.files.length > 0) {
        uploadFile(e.dataTransfer.files[0]);
      }
    });
    fileInput.addEventListener('change', () => {
      if (fileInput.files.length > 0) {
        uploadFile(fileInput.files[0]);
      }
    });

    function showAlert(msg, isError = true) {
      alertBox.textContent = msg;
      alertBox.className = 'alert ' + (isError ? 'alert-error' : 'alert-success');
      alertBox.style.display = 'flex';
      setTimeout(() => { alertBox.style.display = 'none'; }, 6000);
    }

    async function uploadFile(file) {
      const formData = new FormData();
      formData.append('file', file);
      showAlert(`Uploading and analyzing ${file.name}...`, false);

      try {
        const resp = await fetch('/upload', { method: 'POST', body: formData });
        const data = await resp.json();
        if (!resp.ok || !data.success) {
          showAlert(data.error || 'Failed to parse file.', true);
          return;
        }
        showAlert(data.message, false);
        renderDashboard(data.filename, data.encoding, data.analytics);
      } catch (err) {
        showAlert(`Upload error: ${err.message}`, true);
      }
    }

    btnSample.addEventListener('click', async () => {
      try {
        showAlert('Loading sample Apache log dataset...', false);
        const resp = await fetch('/api/sample', { method: 'POST' });
        const data = await resp.json();
        if (data.success) {
          showAlert(data.message, false);
          renderDashboard(data.filename, data.encoding, data.analytics);
        } else {
          showAlert(data.error, true);
        }
      } catch (err) {
        showAlert(`Sample load failed: ${err.message}`, true);
      }
    });

    btnClear.addEventListener('click', async () => {
      await fetch('/api/clear', { method: 'POST' });
      activeData = null;
      dashboardSection.style.display = 'none';
      btnExport.style.display = 'none';
      btnClear.style.display = 'none';
      showAlert('Dataset cleared.', false);
    });

    btnExport.addEventListener('click', () => {
      const filter = statusFilter.value;
      const search = encodeURIComponent(tableSearch.value.trim());
      window.location.href = `/export?status_filter=${filter}&search=${search}`;
    });

    function renderDashboard(filename, encoding, a) {
      activeData = a;
      dashboardSection.style.display = 'flex';
      btnExport.style.display = 'inline-flex';
      btnClear.style.display = 'inline-flex';

      document.getElementById('activeFileName').textContent = filename;
      document.getElementById('activeFileMeta').textContent = `Encoding: ${encoding} • Valid Requests: ${a.total_valid_requests.toLocaleString()} • Excluded Rows: ${a.excluded_records}`;

      const badgeBox = document.getElementById('detectedBadges');
      badgeBox.innerHTML = '';
      for (const [key, val] of Object.entries(a.column_mapping)) {
        if (val) {
          const badge = document.createElement('span');
          badge.className = 'badge-chip';
          badge.textContent = `${key.toUpperCase()}: ${val}`;
          badgeBox.appendChild(badge);
        }
      }

      document.getElementById('kpiTotal').textContent = a.total_records.toLocaleString();
      document.getElementById('kpiExcluded').textContent = `${a.excluded_records} malformed records excluded`;
      document.getElementById('kpi404').textContent = a.total_404.toLocaleString();
      document.getElementById('kpi404Rate').textContent = `${a.rate_404}% of valid requests`;
      document.getElementById('kpiErrorRate').textContent = `${a.error_rate}%`;
      document.getElementById('kpiErrorCounts').textContent = `${a.total_errors.toLocaleString()} client & server errors`;

      if (a.peak_hour !== null) {
        document.getElementById('kpiPeakHour').textContent = `${String(a.peak_hour).padStart(2, '0')}:00 UTC`;
        document.getElementById('kpiPeakCount').textContent = `${a.peak_hour_count.toLocaleString()} failures recorded`;
      } else {
        document.getElementById('kpiPeakHour').textContent = 'N/A';
        document.getElementById('kpiPeakCount').textContent = 'No timestamp column detected';
      }

      renderTimeline(a.hourly_distribution, a.peak_hour);
      renderStatusBreakdown(a.status_breakdown, a.total_records);
      renderTopEndpoints(a.top_endpoints);
      renderTopIps(a.top_ips);

      currentPage = 1;
      fetchTableData();
    }

    function renderTimeline(distribution, peakHour) {
      const container = document.getElementById('timelineContainer');
      container.innerHTML = '';

      if (!distribution || distribution.length === 0) {
        container.innerHTML = '<div style="margin:auto; color:var(--text-muted); font-size:0.9rem;">No timestamp distribution available.</div>';
        return;
      }

      const maxVal = Math.max(...distribution.map(d => d.requests), 1);

      distribution.forEach(d => {
        const col = document.createElement('div');
        col.className = 'chart-bar-col';

        const isPeak = (d.hour === peakHour && d.errors_404 > 0);
        const heightPct = Math.max(4, Math.round((d.requests / maxVal) * 100));

        col.innerHTML = `
          <div class="tooltip">${d.label} UTC<br>Total Requests: ${d.requests.toLocaleString()}<br>404 Failures: ${d.errors_404.toLocaleString()}</div>
          <div class="chart-bar ${isPeak ? 'peak' : ''}" style="height:${heightPct}%;"></div>
          <span class="chart-label">${d.label.slice(0, 2)}</span>
        `;
        container.appendChild(col);
      });
    }

    function renderStatusBreakdown(statusList, totalRecords) {
      const list = document.getElementById('statusList');
      list.innerHTML = '';

      if (!statusList || statusList.length === 0) {
        list.innerHTML = '<div style="color:var(--text-muted); font-size:0.85rem;">No status code column detected in CSV.</div>';
        return;
      }

      statusList.slice(0, 6).forEach(s => {
        const item = document.createElement('div');
        item.className = 'ranked-item';
        const is404 = (s.code === '404');
        item.innerHTML = `
          <div class="ranked-meta">
            <span class="status-badge ${is404 ? 'status-404' : (s.code.startsWith('2') ? 'status-2xx' : 'status-5xx')}">HTTP ${s.code}</span>
            <span>${s.count.toLocaleString()} (${s.pct}%)</span>
          </div>
          <div class="bar-bg">
            <div class="bar-fill ${is404 ? 'rose' : ''}" style="width:${s.pct}%;"></div>
          </div>
        `;
        list.appendChild(item);
      });
    }

    function renderTopEndpoints(endpoints) {
      const list = document.getElementById('topEndpointsList');
      list.innerHTML = '';

      if (!endpoints || endpoints.length === 0) {
        list.innerHTML = '<div style="color:var(--text-muted); font-size:0.85rem;">No path / URL column detected in CSV.</div>';
        return;
      }

      const maxCount = Math.max(...endpoints.map(e => e.count), 1);

      endpoints.forEach(e => {
        const item = document.createElement('div');
        item.className = 'ranked-item';
        const pct = Math.round((e.count / maxCount) * 100);
        item.innerHTML = `
          <div class="ranked-meta">
            <span style="font-weight:600; text-overflow:ellipsis; overflow:hidden; max-width:240px;">${escapeHtml(e.path)}</span>
            <span>${e.count.toLocaleString()} hits <span style="color:var(--rose-500); font-weight:700;">(${e.errors_404} 404s)</span></span>
          </div>
          <div class="bar-bg">
            <div class="bar-fill ${e.errors_404 > 0 ? 'rose' : ''}" style="width:${pct}%;"></div>
          </div>
        `;
        list.appendChild(item);
      });
    }

    function renderTopIps(ips) {
      const list = document.getElementById('topIpsList');
      list.innerHTML = '';

      if (!ips || ips.length === 0) {
        list.innerHTML = '<div style="color:var(--text-muted); font-size:0.85rem;">No client IP column detected in CSV.</div>';
        return;
      }

      const maxCount = Math.max(...ips.map(i => i.count), 1);

      ips.forEach(i => {
        const item = document.createElement('div');
        item.className = 'ranked-item';
        const pct = Math.round((i.count / maxCount) * 100);
        item.innerHTML = `
          <div class="ranked-meta">
            <span><strong>${escapeHtml(i.ip)}</strong></span>
            <span>${i.count.toLocaleString()} reqs (${i.errors_404} 404s &bull; ${i.error_pct}%)</span>
          </div>
          <div class="bar-bg">
            <div class="bar-fill ${i.errors_404 > 0 ? 'rose' : ''}" style="width:${pct}%;"></div>
          </div>
        `;
        list.appendChild(item);
      });
    }

    async function fetchTableData() {
      const pageSize = pageSizeSelect.value;
      const search = encodeURIComponent(tableSearch.value.trim());
      const filter = statusFilter.value;
      const sortParam = currentSortCol ? `&sort_col=${encodeURIComponent(currentSortCol)}&sort_dir=${currentSortDir}` : '';

      const url = `/api/data?page=${currentPage}&page_size=${pageSize}&status_filter=${filter}&search=${search}${sortParam}`;
      try {
        const resp = await fetch(url);
        const data = await resp.json();

        totalPages = data.total_pages;
        currentPage = data.page;

        renderTable(data.columns, data.rows, data.mapping);
        updatePagination(data.page, data.total_pages, data.total_rows, data.page_size, data.total_unfiltered);
      } catch (err) {
        console.error('Error fetching table data:', err);
      }
    }

    function renderTable(columns, rows, mapping) {
      const head = document.getElementById('tableHead');
      const body = document.getElementById('tableBody');

      head.innerHTML = '<tr>' + columns.map(col => {
        const isSorted = (currentSortCol === col);
        const arrow = isSorted ? (currentSortDir === 'asc' ? ' ↑' : ' ↓') : '';
        return `<th onclick="sortTable('${escapeHtml(col)}')">${escapeHtml(col)}${arrow}</th>`;
      }).join('') + '</tr>';

      if (!rows || rows.length === 0) {
        body.innerHTML = `<tr><td colspan="${columns.length}" style="text-align:center; padding:2rem; color:var(--text-muted);">No matching log records found.</td></tr>`;
        return;
      }

      const statusCol = mapping.status;
      body.innerHTML = rows.map(r => {
        return '<tr>' + columns.map(col => {
          const val = r[col] !== undefined ? String(r[col]) : '';
          if (col === statusCol) {
            let cls = 'status-badge ';
            if (val.startsWith('2')) cls += 'status-2xx';
            else if (val === '404') cls += 'status-404';
            else if (val.startsWith('4')) cls += 'status-4xx';
            else if (val.startsWith('5')) cls += 'status-5xx';
            else cls += 'status-3xx';
            return `<td><span class="${cls}">${escapeHtml(val)}</span></td>`;
          }
          return `<td>${escapeHtml(val)}</td>`;
        }).join('') + '</tr>';
      }).join('');
    }

    function sortTable(col) {
      if (currentSortCol === col) {
        currentSortDir = (currentSortDir === 'asc') ? 'desc' : 'asc';
      } else {
        currentSortCol = col;
        currentSortDir = 'asc';
      }
      fetchTableData();
    }

    function updatePagination(page, pages, totalFiltered, pageSize, totalUnfiltered) {
      document.getElementById('pageIndicator').textContent = `Page ${page} of ${pages}`;
      document.getElementById('paginationInfo').textContent = `Showing ${(page-1)*pageSize + 1} to ${Math.min(page*pageSize, totalFiltered)} of ${totalFiltered.toLocaleString()} entries ${totalFiltered !== totalUnfiltered ? `(filtered from ${totalUnfiltered.toLocaleString()} total)` : ''}`;
      document.getElementById('recordCountChip').textContent = `${totalFiltered.toLocaleString()} records`;

      btnPrevPage.disabled = (page <= 1);
      btnNextPage.disabled = (page >= pages);
    }

    let searchTimeout = null;
    tableSearch.addEventListener('input', () => {
      clearTimeout(searchTimeout);
      searchTimeout = setTimeout(() => {
        currentPage = 1;
        fetchTableData();
      }, 250);
    });

    statusFilter.addEventListener('change', () => {
      currentPage = 1;
      fetchTableData();
    });

    pageSizeSelect.addEventListener('change', () => {
      currentPage = 1;
      fetchTableData();
    });

    btnPrevPage.addEventListener('click', () => {
      if (currentPage > 1) {
        currentPage--;
        fetchTableData();
      }
    });

    btnNextPage.addEventListener('click', () => {
      if (currentPage < totalPages) {
        currentPage++;
        fetchTableData();
      }
    });

    function escapeHtml(str) {
      if (!str) return '';
      return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
    }
  </script>
</body>
</html>
"""


# ==============================================================================
# CLI ENTRYPOINT & BUILT-IN VERIFICATION TESTS
# ==============================================================================

def run_self_tests() -> int:
    """Execute built-in self-test suite covering routes, uploads, encodings, and analytics."""
    print("=" * 70)
    print("  LOGSHIELD — RUNNING BUILT-IN VERIFICATION TEST SUITE")
    print("=" * 70)
    app.config["TESTING"] = True
    client = app.test_client()
    passed = 0
    failed = 0

    def test(name, fn):
        nonlocal passed, failed
        try:
            fn()
            print(f"  [✓] PASSED: {name}")
            passed += 1
        except Exception as e:
            print(f"  [✗] FAILED: {name} ({e})")
            failed += 1

    # 1. Valid CSV upload
    def t01():
        csv_c = "ip,timestamp,method,path,status,size\n1.1.1.1,01/Sep/2026:03:00:00 +0000,GET,/p,404,100\n1.1.1.1,01/Sep/2026:03:05:00 +0000,GET,/p,200,200\n"
        data = {"file": (io.BytesIO(csv_c.encode()), "test.csv")}
        resp = client.post("/upload", data=data, content_type="multipart/form-data")
        assert resp.status_code == 200
        a = resp.get_json()["analytics"]
        assert a["total_records"] == 2
        assert a["total_404"] == 1
        assert a["rate_404"] == 50.0
    test("1. Valid CSV upload and metrics calculation", t01)

    # 2. Apache and Nginx access log parsing
    def t02():
        log_c = (
            '10.0.12.45 - - [01/Sep/2026:03:14:22 +0000] "GET /admin/login HTTP/1.1" 404 342\n'
            '192.168.1.5 - - [01/Sep/2026:09:20:11 +0000] "GET /index.html HTTP/1.1" 200 4500\n'
        )
        data = {"file": (io.BytesIO(log_c.encode()), "access.log")}
        resp = client.post("/upload", data=data, content_type="multipart/form-data")
        assert resp.status_code == 200
        a = resp.get_json()["analytics"]
        assert a["total_records"] == 2
        assert a["total_404"] == 1
    test("2. Apache & Nginx access log parsing", t02)

    # 3. Empty CSV file rejection
    def t03():
        data = {"file": (io.BytesIO(b""), "empty.csv")}
        resp = client.post("/upload", data=data, content_type="multipart/form-data")
        assert resp.status_code == 400
        assert "empty" in resp.get_json()["error"].lower()
    test("3. Empty CSV file rejection (0 bytes)", t03)

    # 4. Malformed rows handling
    def t04():
        raw_csv = "ip,timestamp,method,path,status,size\n1.1.1.1,01/Sep/2026:03:00:00 +0000,GET,/p,404,100\nmalformed_line_missing_columns\n2.2.2.2,01/Sep/2026:04:00:00 +0000,GET,/ok,200,200\n"
        data = {"file": (io.BytesIO(raw_csv.encode()), "ragged.csv")}
        resp = client.post("/upload", data=data, content_type="multipart/form-data")
        assert resp.status_code == 200
        a = resp.get_json()["analytics"]
        assert a["total_records"] >= 2
        assert a["excluded_records"] >= 1
    test("4. Malformed rows handled and reported in excluded_records", t04)

    # 5. Missing timestamp column
    def t05():
        csv_no_time = "ip,method,path,status\n1.1.1.1,GET,/items,404\n"
        data = {"file": (io.BytesIO(csv_no_time.encode()), "no_time.csv")}
        resp = client.post("/upload", data=data, content_type="multipart/form-data")
        assert resp.status_code == 200
        a = resp.get_json()["analytics"]
        assert a["timeline_available"] is False
        assert a["total_404"] == 1
    test("5. Missing timestamp column handled gracefully", t05)

    # 6. Missing status-code column
    def t06():
        csv_no_status = "ip,timestamp,method,path\n1.1.1.1,01/Sep/2026:03:00:00 +0000,GET,/page\n"
        data = {"file": (io.BytesIO(csv_no_status.encode()), "no_status.csv")}
        resp = client.post("/upload", data=data, content_type="multipart/form-data")
        assert resp.status_code == 200
        a = resp.get_json()["analytics"]
        assert a["status_available"] is False
        assert a["total_404"] == 0
        assert a["rate_404"] == 0.0
    test("6. Missing status-code column handled gracefully", t06)

    # 7. Invalid timestamp handling
    def t07():
        csv_bad_ts = "ip,timestamp,status,path\n1.1.1.1,not-a-valid-timestamp,404,/fail\n"
        data = {"file": (io.BytesIO(csv_bad_ts.encode()), "bad_ts.csv")}
        resp = client.post("/upload", data=data, content_type="multipart/form-data")
        assert resp.status_code == 200
        a = resp.get_json()["analytics"]
        assert a["total_records"] == 1
        assert a["total_404"] == 1
        assert a["timeline_available"] is False
    test("7. Invalid timestamp strings fall back gracefully", t07)

    # 8. Mixed HTTP status codes
    def t08():
        lines = [
            "ip,status,path",
            "1.1.1.1,200,/home",
            "1.1.1.2,301,/old",
            "1.1.1.3,400,/bad",
            "1.1.1.4,403,/secret",
            "1.1.1.5,404,/missing",
            "1.1.1.6,404,/missing2",
            "1.1.1.7,500,/error",
        ]
        data = {"file": (io.BytesIO("\n".join(lines).encode()), "mixed.csv")}
        resp = client.post("/upload", data=data, content_type="multipart/form-data")
        assert resp.status_code == 200
        a = resp.get_json()["analytics"]
        breakdown = {item["code"]: item["count"] for item in a["status_breakdown"]}
        assert breakdown.get("200") == 1
        assert breakdown.get("301") == 1
        assert breakdown.get("400") == 1
        assert breakdown.get("403") == 1
        assert breakdown.get("404") == 2
        assert breakdown.get("500") == 1
        assert a["category_counts"]["4xx"] == 4
        assert a["category_counts"]["5xx"] == 1
    test("8. Mixed HTTP status codes (200, 301, 400, 403, 404, 500)", t08)

    # 9. Correct 404 percentage formula
    def t09():
        lines = ["status"] + ["404"] * 3 + ["200"] * 7
        data = {"file": (io.BytesIO("\n".join(lines).encode()), "pct.csv")}
        resp = client.post("/upload", data=data, content_type="multipart/form-data")
        assert resp.status_code == 200
        a = resp.get_json()["analytics"]
        assert a["total_records"] == 10
        assert a["total_404"] == 3
        assert a["rate_404"] == 30.0
    test("9. Exact 404 percentage formula validation", t09)

    # 10. Correct hourly aggregation
    def t10():
        lines = [
            "timestamp,status",
            "01/Sep/2026:03:10:00 +0000,404",
            "01/Sep/2026:03:25:00 +0000,404",
            "01/Sep/2026:14:00:00 +0000,404",
            "01/Sep/2026:14:15:00 +0000,200",
        ]
        data = {"file": (io.BytesIO("\n".join(lines).encode()), "hourly.csv")}
        resp = client.post("/upload", data=data, content_type="multipart/form-data")
        assert resp.status_code == 200
        a = resp.get_json()["analytics"]
        hourly = {item["hour"]: item for item in a["hourly_distribution"]}
        assert hourly[3]["errors_404"] == 2
        assert hourly[14]["errors_404"] == 1
        assert hourly[14]["requests"] == 2
        assert a["peak_hour"] == 3
    test("10. Correct 24-hour aggregation & peak failure detection", t10)

    # 11. Different timezone offsets normalized to UTC
    def t11():
        dt1 = parse_normalized_datetime("01/Sep/2026:22:15:00 -0500")
        assert dt1 is not None and dt1.hour == 3
        dt2 = parse_normalized_datetime("01/Sep/2026:10:15:00 +0700")
        assert dt2 is not None and dt2.hour == 3
        dt3 = parse_normalized_datetime("2026-09-01T15:30:00Z")
        assert dt3 is not None and dt3.hour == 15
    test("11. Timezone offsets (-0500, +0700, Z) normalized to UTC", t11)

    # 12. Oversized upload rejection (HTTP 413)
    def t12():
        orig_max = app.config.get("MAX_CONTENT_LENGTH")
        try:
            app.config["MAX_CONTENT_LENGTH"] = 200
            big_data = {"file": (io.BytesIO(b"A" * 600), "big.csv")}
            resp = client.post("/upload", data=big_data, content_type="multipart/form-data")
            assert resp.status_code == 413
        finally:
            app.config["MAX_CONTENT_LENGTH"] = orig_max
    test("12. Oversized upload rejection with HTTP 413", t12)

    # 13. CSV export and formula injection defense
    def t13():
        mal_c = 'ip,status,path\n1.1.1.1,200,"=SUM(A1:A10)"\n1.1.1.1,200,"-5+5"\n'
        data = {"file": (io.BytesIO(mal_c.encode()), "mal.csv")}
        client.post("/upload", data=data, content_type="multipart/form-data")
        resp = client.get("/export")
        assert resp.status_code == 200
        body = resp.data.decode("utf-8")
        assert "'=SUM" in body
        assert "'-5+5" in body
    test("13. CSV export & spreadsheet formula injection mitigation", t13)

    # 14. Spark unavailable fallback behavior
    def t14():
        assert PROCESSING_CONFIG["engine"] in ("Local In-Memory", "Apache PySpark (Distributed)")
        assert HadoopSparkManager.check_hdfs_connection("") is False
    test("14. PySpark optional fallback to local in-memory engine", t14)

    # 15. HDFS connection failure handling
    def t15():
        conn = HadoopSparkManager.check_hdfs_connection("invalid.hdfs.node:9000")
        assert conn is False
    test("15. HDFS connection failure handled gracefully without crash", t15)

    # 16. Flask route error handling
    def t16():
        assert client.get("/invalid-nonexistent-endpoint-xyz").status_code == 404
        client.post("/api/clear")
        assert client.get("/api/stats").status_code == 404
        bad_ext = {"file": (io.BytesIO(b"hello"), "malicious.sh")}
        resp = client.post("/upload", data=bad_ext, content_type="multipart/form-data")
        assert resp.status_code == 400
        assert "Invalid file extension" in resp.get_json()["error"]
    test("16. Flask route errors (404 route, 404 stats, 400 extension)", t16)

    # 17. UI Dashboard rendering & service health check
    def t17():
        resp = client.get("/")
        assert resp.status_code == 200
        assert b"LogShield" in resp.data
        assert b"#0b1120" in resp.data
        resp2 = client.get("/health")
        assert resp2.status_code == 200
        assert resp2.get_json()["status"] == "healthy"
    test("17. UI Dashboard rendering & service health check", t17)

    # 18. Built-in 1,200 record sample dataset generator
    def t18():
        resp = client.post("/api/sample")
        assert resp.status_code == 200
        d = resp.get_json()
        assert d["success"] is True
        assert d["analytics"]["total_records"] == 1200
        assert d["analytics"]["peak_hour"] == 3
    test("18. Built-in 1,200 record sample dataset generator", t18)

    # 19. Data Explorer live pagination, search, and filtering
    def t19():
        client.post("/api/sample")
        resp = client.get("/api/data?page=1&page_size=10")
        assert resp.status_code == 200
        assert len(resp.get_json()["rows"]) == 10
        resp_404 = client.get("/api/data?status_filter=404")
        assert resp_404.status_code == 200
        assert client.get("/api/hourly").status_code == 200
        assert client.get("/api/urls").status_code == 200
    test("19. Data Explorer live pagination, search, and filtering", t19)

    # 20. Session clear and temporary dataset flush
    def t20():
        resp = client.post("/api/clear")
        assert resp.status_code == 200
        resp_data = client.get("/api/data")
        assert resp_data.get_json()["total_rows"] == 0
    test("20. Session clear and temporary dataset flush", t20)

    # 21. Real PySpark DataFrame distributed analysis (when PySpark is available)
    def t21():
        if HadoopSparkManager.check_pyspark_available():
            HadoopSparkManager.initialize_spark()
            with tempfile.NamedTemporaryFile("w", suffix=".log", delete=False) as f:
                f.write('1.1.1.1 - - [01/Sep/2026:03:00:00 +0000] "GET /admin/login HTTP/1.1" 404 100\n')
                f.write('2.2.2.2 - - [01/Sep/2026:03:15:00 +0000] "GET /admin/login HTTP/1.1" 404 100\n')
                f.write('3.3.3.3 - - [01/Sep/2026:14:00:00 +0000] "GET /index.html HTTP/1.1" 200 200\n')
                t_path = f.name
            try:
                res = HadoopSparkManager.analyze_with_spark(t_path)
                assert res is not None
                assert res["analytics"]["total_valid_requests"] == 3
                assert res["analytics"]["total_404"] == 2
                assert res["analytics"]["peak_hour"] == 3
                assert res["analytics"]["rate_404"] == 66.67
            finally:
                if os.path.exists(t_path):
                    os.unlink(t_path)
    test("21. PySpark DataFrame distributed aggregation verification", t21)

    print("=" * 70)
    print(f"  ALL TESTS COMPLETE: {passed} passed, {failed} failed")
    print("=" * 70)
    with DATASET_LOCK:
        DATASET_STORE.clear()
    app.config["TESTING"] = False
    return 0 if failed == 0 else 1


def is_port_available(port: int, host: str = "127.0.0.1") -> bool:
    """Check if socket can bind to port."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        try:
            s.bind((host, port))
            return True
        except OSError:
            return False


def find_available_port(start_port: int, host: str = "127.0.0.1") -> int:
    """Find the next available port starting from start_port."""
    port = start_port
    while port < start_port + 100:
        if is_port_available(port, host):
            return port
        port += 1
    return start_port


def main() -> None:
    """
    All-in-One CLI runner:
      - Automatically runs built-in self-tests verification
      - Automatically detects & initializes PySpark distributed engine if available
      - Automatically connects to Hadoop HDFS if configured
      - Automatically detects open ports and launches the Web Application dashboard
    """
    parser = argparse.ArgumentParser(
        description="LogShield — All-in-One Single-File Python Log Analytics & CSV Web Application",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python app.py                       # All-in-one run: self-tests + PySpark auto-init + web dashboard
  python app.py --port 8080           # Custom port (auto-switches if port is busy)
  python app.py --host 0.0.0.0        # Listen on external interfaces
  python app.py --test                # Run test suite only and exit
  python app.py --no-test             # Launch server immediately without running startup tests
  python app.py --no-spark            # Disable PySpark auto-detection and use local engine only
  python app.py --hdfs hdfs://nn:9000 # Connect to Hadoop HDFS NameNode
        """
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host address to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8080, help="Port to listen on (default: 8080)")
    parser.add_argument("--debug", action="store_true", help="Enable Flask debug mode")
    parser.add_argument("--test", "--test-only", dest="test_only", action="store_true", help="Run automated test suite and exit")
    parser.add_argument("--no-test", action="store_true", help="Skip startup automated self-tests")
    parser.add_argument("--open", action="store_true", help="Automatically open web browser on startup (Windows, macOS, Linux)")
    parser.add_argument("--spark", action="store_true", help="Force initializing PySpark distributed engine")
    parser.add_argument("--no-spark", action="store_true", help="Disable PySpark and force local engine")
    parser.add_argument("--hdfs", default=os.environ.get("HDFS_URI", ""), help="Hadoop HDFS NameNode URI (e.g. hdfs://namenode:9000)")

    args = parser.parse_args()

    # If --test or --test-only is explicitly requested, run tests and exit
    if args.test_only:
        sys.exit(run_self_tests())

    # Step 1: Run automated self-tests verification on startup (unless --no-test)
    if not args.no_test:
        test_exit_code = run_self_tests()
        if test_exit_code != 0:
            print("  [!] Self-tests encountered failures. Aborting startup.")
            sys.exit(test_exit_code)

    # Step 2: Auto-detect and initialize Apache PySpark if available (unless --no-spark)
    if not args.no_spark:
        if args.spark or HadoopSparkManager.check_pyspark_available():
            HadoopSparkManager.initialize_spark()

    # Step 3: Configure optional Hadoop HDFS if specified or found in HDFS_URI
    if args.hdfs:
        PROCESSING_CONFIG["hdfs_uri"] = args.hdfs
        if HadoopSparkManager.check_hdfs_connection(args.hdfs):
            PROCESSING_CONFIG["hdfs_available"] = True
            print(f"  [✓] Connected to Hadoop HDFS: {args.hdfs}")
        else:
            PROCESSING_CONFIG["hdfs_available"] = False
            print(f"  [!] Hadoop HDFS unreachable at {args.hdfs}. Operating in local storage mode.")

    # Step 4: Auto-detect available port if requested port is in use
    target_port = args.port
    if not is_port_available(target_port, args.host):
        alt_port = find_available_port(target_port + 1, args.host)
        print(f"  [!] Port {target_port} is already in use. Auto-switching to available port {alt_port}.")
        target_port = alt_port

    # Step 5: Display full startup banner and launch dashboard
    print("=" * 70)
    print("  LOGSHIELD — ALL-IN-ONE LOG ANALYTICS & CSV DASHBOARD")
    print("=" * 70)
    print(f"  Web Dashboard : http://{args.host}:{target_port}/")
    print(f"  Processing    : {PROCESSING_CONFIG['engine']}")
    print(f"  HDFS Storage  : {PROCESSING_CONFIG['hdfs_uri'] or 'Local Filesystem'}")
    print(f"  Max File Size : {MAX_UPLOAD_SIZE_MB} MB")
    print(f"  Upload Folder : {UPLOAD_DIR}")
    print(f"  Architecture  : Single-File Python Flask Application (app.py)")
    print("  Press Ctrl+C to stop the server.")
    print("=" * 70)

    # Auto-open browser across Windows, macOS, Linux
    if args.open:
        import webbrowser
        threading.Timer(1.2, lambda: webbrowser.open(f"http://{args.host}:{target_port}/")).start()

    try:
        app.run(host=args.host, port=target_port, debug=args.debug)
    except KeyboardInterrupt:
        print("\n[*] LogShield server stopped gracefully.")
        sys.exit(0)


if __name__ == "__main__":
    main()
