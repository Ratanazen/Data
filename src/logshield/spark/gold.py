"""
Gold Layer Pipeline: Generates analytics-ready aggregate tables in Parquet
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from ..config import settings
from ..utils import logger


def run_gold_aggregation(
    silver_dir: Optional[Path] = None,
    output_dir: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Reads normalized Silver records, performs multi-dimensional aggregations,
    and writes production-ready Gold Parquet tables.
    """
    silver_path = Path(silver_dir or settings.SILVER_PATH)
    gold_path = Path(output_dir or settings.GOLD_PATH)
    gold_path.mkdir(parents=True, exist_ok=True)

    logger.info(f"[*] Gold Aggregation starting: {silver_path} -> {gold_path}")

    # Read Silver dataset
    table = pq.read_table(str(silver_path))
    df = table.to_pandas()

    if df.empty:
        raise ValueError(f"Silver dataset is empty in {silver_path}")

    total_requests = len(df)
    errors_404_df = df[df["status"] == 404]
    total_404 = len(errors_404_df)
    error_rate = (total_404 / total_requests * 100.0) if total_requests > 0 else 0.0

    # 1. Hourly Traffic & 404 breakdown (00:00 - 23:00)
    hourly_records = []
    for h in range(24):
        h_df = df[df["hour"] == h]
        h_total = len(h_df)
        h_404 = len(h_df[h_df["status"] == 404])
        h_403 = len(h_df[h_df["status"] == 403])
        h_500 = len(h_df[h_df["status"] == 500])
        h_200 = len(h_df[h_df["status"] == 200])
        h_301 = len(h_df[h_df["status"] == 301])
        h_err_rate = (h_404 / h_total * 100.0) if h_total > 0 else 0.0
        hourly_records.append({
            "hour": h,
            "total_requests": h_total,
            "errors_404": h_404,
            "errors_403": h_403,
            "errors_500": h_500,
            "successes_200": h_200,
            "redirects_301": h_301,
            "error_rate": round(h_err_rate, 2)
        })
    df_hourly = pd.DataFrame(hourly_records)
    pq.write_table(pa.Table.from_pandas(df_hourly), gold_path / "gold_hourly_traffic.parquet")

    # Determine peak failure hour
    peak_row = df_hourly.sort_values(by="errors_404", ascending=False).iloc[0]
    peak_hour = int(peak_row["hour"])
    peak_count = int(peak_row["errors_404"])

    # 2. HTTP Status Code Breakdown
    status_counts = df["status"].value_counts().reset_index()
    status_counts.columns = ["status", "count"]
    status_counts["percentage"] = (status_counts["count"] / total_requests * 100.0).round(2)
    pq.write_table(pa.Table.from_pandas(status_counts), gold_path / "gold_status_distribution.parquet")

    # 3. Top 404 Paths
    top_404 = errors_404_df["path"].value_counts().head(50).reset_index()
    top_404.columns = ["path", "hits"]
    pq.write_table(pa.Table.from_pandas(top_404), gold_path / "gold_404_paths.parquet")

    # 4. Top URLs (All status codes)
    top_urls = df["path"].value_counts().head(50).reset_index()
    top_urls.columns = ["path", "hits"]
    url_404_counts = errors_404_df["path"].value_counts().to_dict()
    top_urls["errors_404"] = top_urls["path"].map(lambda p: url_404_counts.get(p, 0))
    top_urls["error_rate"] = ((top_urls["errors_404"] / top_urls["hits"]) * 100.0).round(2)
    pq.write_table(pa.Table.from_pandas(top_urls), gold_path / "gold_top_urls.parquet")

    # 5. Top IPs & Client Traffic
    ip_stats = df.groupby("ip").agg(
        total_requests=("status", "count"),
        errors_404=("status", lambda s: (s == 404).sum()),
        errors_403=("status", lambda s: (s == 403).sum()),
        errors_500=("status", lambda s: (s == 500).sum())
    ).reset_index()
    ip_stats = ip_stats.sort_values(by="total_requests", ascending=False).head(100)
    pq.write_table(pa.Table.from_pandas(ip_stats), gold_path / "gold_top_ips.parquet")

    # 6. Daily Error Trend
    df["date_str"] = df["date"]
    daily_stats = df.groupby("date_str").agg(
        total_requests=("status", "count"),
        errors_404=("status", lambda s: (s == 404).sum())
    ).reset_index()
    daily_stats["error_rate"] = ((daily_stats["errors_404"] / daily_stats["total_requests"]) * 100.0).round(2)
    pq.write_table(pa.Table.from_pandas(daily_stats), gold_path / "gold_daily_errors.parquet")

    # 7. Day-Hour 7x24 Matrix
    # Compute day of week index (0=Monday ... 6=Sunday)
    if "timestamp" in df.columns:
        df["day_of_week"] = pd.to_datetime(df["timestamp"]).dt.day_name()
        df["day_index"] = pd.to_datetime(df["timestamp"]).dt.dayofweek
    else:
        df["day_of_week"] = "Monday"
        df["day_index"] = 0

    heatmap_records = []
    days_ordered = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    for day in days_ordered:
        d_sub = df[(df["day_of_week"] == day) & (df["status"] == 404)]
        hour_counts = d_sub["hour"].value_counts().to_dict()
        for h in range(24):
            heatmap_records.append({
                "day_of_week": day,
                "hour": h,
                "error_count": hour_counts.get(h, 0)
            })
    df_heatmap = pd.DataFrame(heatmap_records)
    pq.write_table(pa.Table.from_pandas(df_heatmap), gold_path / "gold_404_heatmap.parquet")

    # 8. High-Level KPI Summary (JSON)
    kpis = {
        "total_requests": int(total_requests),
        "total_404": int(total_404),
        "error_rate": round(error_rate, 2),
        "peak_failure_hour": peak_hour,
        "peak_failure_count": peak_count,
        "unique_ips": int(df["ip"].nunique()),
        "unique_paths": int(df["path"].nunique()),
        "total_200": int((df["status"] == 200).sum()),
        "total_403": int((df["status"] == 403).sum()),
        "total_500": int((df["status"] == 500).sum()),
        "total_301": int((df["status"] == 301).sum()),
        "storage_format": "Parquet (Snappy Compressed)",
        "generated_at": pd.Timestamp.utcnow().isoformat()
    }
    with open(gold_path / "gold_kpis.json", "w", encoding="utf-8") as f:
        json.dump(kpis, f, indent=2)

    logger.info(f"[+] Gold Layer complete: {len(df_hourly)} hourly rows, peak {peak_hour:02d}:00 ({peak_count:,} errors).")
    return {
        "status": "success",
        "layer": "gold",
        "output_directory": str(gold_path),
        "kpis": kpis
    }
