"""
Security Detector Engine: Analyzes log telemetry and outputs Security Events & Anomalies
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from ..config import settings
from ..utils import logger
from .models import AnomalyRecord, SecurityEvent
from .risk import RiskCalculator
from .rules import is_admin_or_sensitive_path, matches_suspicious_path_signature


def run_security_analysis(
    silver_dir: Optional[Path] = None,
    output_dir: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Performs deterministic rule-based security detection across Silver records,
    classifies malicious IP behaviors, calculates risk scores, and outputs
    Gold Security Parquet tables.
    """
    silver_path = Path(silver_dir or settings.SILVER_PATH)
    gold_path = Path(output_dir or settings.GOLD_PATH)
    gold_path.mkdir(parents=True, exist_ok=True)

    logger.info(f"[*] Security Analysis starting: analyzing {silver_path} -> {gold_path}")

    table = pq.read_table(str(silver_path))
    df = table.to_pandas()

    if df.empty:
        raise ValueError("Cannot run security analysis on empty Silver dataset")

    # Group requests by Client IP
    events: List[SecurityEvent] = []
    anomalies: List[AnomalyRecord] = []
    ip_profiles: List[Dict[str, Any]] = []

    ip_groups = df.groupby("ip")

    for ip, group in ip_groups:
        req_count = len(group)
        status_counts = group["status"].value_counts().to_dict()
        count_404 = status_counts.get(404, 0)
        count_403 = status_counts.get(403, 0)
        count_500 = status_counts.get(500, 0)
        count_200 = status_counts.get(200, 0)

        err_rate = ((count_404 + count_403 + count_500) / req_count * 100.0) if req_count > 0 else 0.0

        # Check for admin and brute-force indicators
        admin_hits = group[group["path"].apply(is_admin_or_sensitive_path)]
        admin_scan_count = len(admin_hits)

        # Login failure probing (e.g. status 404 or 403 or 401 on /admin/login)
        login_fails = len(admin_hits[admin_hits["status"] != 200])

        # Traversal attempts
        traversal_hits = len(group[group["path"].apply(matches_suspicious_path_signature)])

        # Calculate Risk Score & Evidence
        score, severity, evidence = RiskCalculator.evaluate_profile(
            request_count=req_count,
            count_404=count_404,
            count_403=count_403,
            count_500=count_500,
            login_failures=login_fails,
            admin_scan_count=admin_scan_count,
            traversal_attempts=traversal_hits,
            error_rate_pct=err_rate
        )

        ip_profiles.append({
            "ip": ip,
            "total_requests": req_count,
            "errors_404": count_404,
            "errors_403": count_403,
            "errors_500": count_500,
            "successes_200": count_200,
            "login_failures": login_fails,
            "admin_scan_count": admin_scan_count,
            "risk_score": score,
            "severity": severity
        })

        # Emit High/Critical/Medium Security Events
        if score >= 25:
            # Primary incident classification
            if login_fails >= 15:
                event_type = "Potential Brute-Force Login Probing"
                rec_action = f"Enforce WAF rate-limiting on {ip} and challenge with CAPTCHA/fail2ban"
            elif admin_scan_count >= 10:
                event_type = "Automated Admin Route Scanning"
                rec_action = f"Add {ip} to edge WAF drop list for sensitive administrative endpoints"
            elif count_404 >= 100:
                event_type = "Excessive 404 Reconnaissance Spike"
                rec_action = f"Block {ip} via IP subnet reputation filter"
            else:
                event_type = "Suspicious Client Traffic Anomaly"
                rec_action = f"Monitor traffic from {ip} for behavioral escalation"

            # Representative timestamp: latest request from this IP
            latest_ts = pd.to_datetime(group["timestamp"].max()).to_pydatetime()

            events.append(SecurityEvent(
                timestamp=latest_ts,
                ip=ip,
                event_type=event_type,
                severity=severity,
                risk_score=score,
                evidence="; ".join(evidence),
                request_count=req_count,
                status_count={str(k): int(v) for k, v in status_counts.items()},
                recommendation=rec_action
            ))

    # Detect Global Traffic Volume / Peak Hour Anomalies
    hourly_counts = df.groupby("hour").agg(
        total_req=("status", "count"),
        total_404=("status", lambda s: (s == 404).sum())
    ).reset_index()

    mean_hourly_404 = hourly_counts["total_404"].mean()
    std_hourly_404 = hourly_counts["total_404"].std() or 1.0

    for _, row in hourly_counts.iterrows():
        h = int(row["hour"])
        count_404 = int(row["total_404"])
        z_score = (count_404 - mean_hourly_404) / std_hourly_404

        if z_score >= 2.0:
            dev_pct = ((count_404 - mean_hourly_404) / mean_hourly_404) * 100.0
            anomalies.append(AnomalyRecord(
                metric_name="hourly_404_failure_rate",
                timestamp=datetime.utcnow(),
                observed_value=float(count_404),
                baseline_value=float(round(mean_hourly_404, 2)),
                deviation_pct=float(round(dev_pct, 2)),
                severity="CRITICAL" if z_score >= 3.0 else "HIGH",
                message=f"Hour {h:02d}:00 experienced {count_404:,} 404 errors ({z_score:.1f} standard deviations above mean baseline of {mean_hourly_404:.1f})"
            ))

    # Write Security Events Parquet
    events_data = [e.model_dump() for e in events]
    if events_data:
        df_events = pd.DataFrame(events_data)
        # Convert status_count dict to json string for parquet serialization
        df_events["status_count"] = df_events["status_count"].apply(json.dumps)
        pq.write_table(pa.Table.from_pandas(df_events), gold_path / "gold_security_events.parquet")
    else:
        df_events = pd.DataFrame(columns=["event_id", "timestamp", "ip", "event_type", "severity", "risk_score", "evidence", "request_count", "recommendation"])
        pq.write_table(pa.Table.from_pandas(df_events), gold_path / "gold_security_events.parquet")

    # Write Anomalies Parquet
    anom_data = [a.model_dump() for a in anomalies]
    if anom_data:
        df_anom = pd.DataFrame(anom_data)
        pq.write_table(pa.Table.from_pandas(df_anom), gold_path / "gold_anomalies.parquet")

    # Update gold_top_ips with security scores
    df_profiles = pd.DataFrame(ip_profiles).sort_values(by="risk_score", ascending=False)
    pq.write_table(pa.Table.from_pandas(df_profiles), gold_path / "gold_top_ips.parquet")

    logger.info(f"[+] Security Detection complete: {len(events)} security events, {len(anomalies)} anomalies identified.")

    return {
        "status": "success",
        "security_events_count": len(events),
        "anomalies_count": len(anomalies),
        "high_risk_ips": int((df_profiles["risk_score"] >= 50).sum()),
        "output_directory": str(gold_path)
    }
