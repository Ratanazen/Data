#!/usr/bin/env python3
"""
Log File Analysis with PySpark & Python
=======================================
Project: Log File Analysis (Hadoop + PySpark)
Objective: Ingest massive server log files, count "404 Error" occurrences,
           and visualize the time of day most failures happen.

This script executes the complete data pipeline:
  1. Ingests or verifies server.log (Common Log Format)
  2. Parses fields with regular expressions
  3. Computes 404 error counts, error rates, and peak failure hours
  4. Generates aggregation CSV files
  5. Produces high-resolution chart images (.png)
  6. Exports structured JSON data for the interactive Web Dashboard
"""

import os
import sys
import re
import json
from datetime import datetime
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

LOG_FILE = "server.log"
LOG_PATTERN = re.compile(
    r'^(\S+) \S+ \S+ \[(\d{2}/\w{3}/\d{4}:\d{2}:\d{2}:\d{2}) [^\]]+\] "(\S+) (\S+) [^"]*" (\d{3}) (\d+)'
)

def parse_logs(log_path):
    print(f"[*] Ingesting and parsing log file: {log_path}...")
    if not os.path.exists(log_path):
        raise FileNotFoundError(f"Log file not found: {log_path}")

    records = []
    malformed = 0
    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            m = LOG_PATTERN.match(line)
            if m:
                records.append({
                    'ip': m.group(1),
                    'timestamp_str': m.group(2),
                    'method': m.group(3),
                    'path': m.group(4),
                    'status': int(m.group(5)),
                    'size': int(m.group(6))
                })
            else:
                malformed += 1

    print(f"[+] Total lines processed: {len(records) + malformed:,}")
    print(f"[+] Clean records parsed:  {len(records):,}")
    if malformed > 0:
        print(f"[!] Malformed lines dropped: {malformed:,}")

    df = pd.DataFrame(records)
    df['timestamp'] = pd.to_datetime(df['timestamp_str'], format='%d/%b/%Y:%H:%M:%S')
    df['hour'] = df['timestamp'].dt.hour
    df['date'] = df['timestamp'].dt.strftime('%Y-%m-%d')
    df['day_of_week'] = df['timestamp'].dt.day_name()
    return df

def analyze_and_export(df):
    print("\n[*] Performing aggregations and generating deliverables...")
    total_requests = len(df)
    error_404_df = df[df['status'] == 404]
    total_404 = len(error_404_df)
    error_rate = (total_404 / total_requests) * 100

    print(f"    - Total Requests : {total_requests:,}")
    print(f"    - Total 404 Errors: {total_404:,}")
    print(f"    - 404 Error Rate  : {error_rate:.2f}%")

    # 1. Summary stats text
    with open("summary_stats.txt", "w") as f:
        f.write(f"total_requests={total_requests}\n")
        f.write(f"total_404={total_404}\n")
        f.write(f"error_rate={error_rate:.2f}\n")
    print("[+] Saved: summary_stats.txt")

    # 2. HTTP Status Code Breakdown
    status_breakdown = df['status'].value_counts().reset_index()
    status_breakdown.columns = ['status', 'count']
    status_breakdown.to_csv("status_code_breakdown.csv", index=False)
    print("[+] Saved: status_code_breakdown.csv")

    # 3. Hourly 404 distribution
    hourly_counts = error_404_df['hour'].value_counts().reindex(range(24), fill_value=0).reset_index()
    hourly_counts.columns = ['hour', 'error_count']
    hourly_counts.to_csv("hourly_404_errors.csv", index=False)
    peak_row = hourly_counts.loc[hourly_counts['error_count'].idxmax()]
    peak_hour = int(peak_row['hour'])
    peak_count = int(peak_row['error_count'])
    print(f"[+] Peak failure hour: {peak_hour:02d}:00 - {peak_hour+1:02d}:00 ({peak_count:,} errors)")
    print("[+] Saved: hourly_404_errors.csv")

    # 4. Day of Week x Hour Heatmap
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    heatmap_df = error_404_df.groupby(['day_of_week', 'hour']).size().unstack(fill_value=0)
    heatmap_df = heatmap_df.reindex(day_order)
    heatmap_df.to_csv("heatmap_day_hour_404.csv")
    print("[+] Saved: heatmap_day_hour_404.csv")

    # 5. Top 10 Endpoints causing 404
    top_paths = error_404_df['path'].value_counts().head(10).reset_index()
    top_paths.columns = ['path', 'hits']
    top_paths.to_csv("top_404_paths.csv", index=False)
    print("[+] Saved: top_404_paths.csv")

    # 6. Daily Trend
    daily_trend = error_404_df['date'].value_counts().sort_index().reset_index()
    daily_trend.columns = ['date', 'error_count']
    daily_trend.to_csv("daily_404_trend.csv", index=False)
    print("[+] Saved: daily_404_trend.csv")

    # Generate Chart Visualizations
    print("\n[*] Generating high-resolution chart images (.png)...")
    sns.set_theme(style="whitegrid", font="sans-serif")

    # Chart 1: Hourly 404 Errors Bar Chart
    plt.figure(figsize=(13, 6))
    colors = ['#dc2626' if h == peak_hour else '#2563eb' for h in hourly_counts['hour']]
    bars = plt.bar(hourly_counts['hour'], hourly_counts['error_count'], color=colors, edgecolor='#1e293b', linewidth=0.8)
    plt.title(f"404 Errors by Hour of Day (Peak Hour: {peak_hour:02d}:00 with {peak_count:,} Errors)",
              fontsize=14, fontweight='bold', pad=15)
    plt.xlabel("Hour of Day (00:00 - 23:00)", fontsize=11, fontweight='semibold')
    plt.ylabel("Number of 404 Errors", fontsize=11, fontweight='semibold')
    plt.xticks(range(24))
    for bar, count in zip(bars, hourly_counts['error_count']):
        if count == peak_count:
            plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 50,
                     f"PEAK\n{count:,}", ha='center', va='bottom', fontsize=9, fontweight='bold', color='#dc2626')
    plt.tight_layout()
    plt.savefig("404_errors_by_hour.png", dpi=200)
    plt.close()
    print("[+] Generated: 404_errors_by_hour.png")

    # Chart 2: Heatmap Day of Week vs Hour
    plt.figure(figsize=(15, 6))
    sns.heatmap(heatmap_df, cmap="YlOrRd", linewidths=0.5, linecolor='#e2e8f0',
                cbar_kws={'label': '404 Error Count'})
    plt.title("404 Error Heatmap: Day of Week vs Hour of Day", fontsize=14, fontweight='bold', pad=15)
    plt.xlabel("Hour of Day (00:00 - 23:00)", fontsize=11, fontweight='semibold')
    plt.ylabel("Day of Week", fontsize=11, fontweight='semibold')
    plt.tight_layout()
    plt.savefig("404_heatmap_day_hour.png", dpi=200)
    plt.close()
    print("[+] Generated: 404_heatmap_day_hour.png")

    # Chart 3: Top 10 Paths Bar Chart
    plt.figure(figsize=(11, 6))
    palette = sns.color_palette("Reds_r", n_colors=len(top_paths))
    barplot = sns.barplot(data=top_paths, y='path', x='hits', hue='path', palette=palette, legend=False)
    plt.title("Top 10 Endpoints Causing 404 Errors", fontsize=14, fontweight='bold', pad=15)
    plt.xlabel("404 Hit Count", fontsize=11, fontweight='semibold')
    plt.ylabel("Endpoint Path", fontsize=11, fontweight='semibold')
    for p in barplot.patches:
        val = int(p.get_width())
        barplot.annotate(f"{val:,}", (p.get_width() + 100, p.get_y() + p.get_height() / 2),
                         va='center', fontsize=9, fontweight='semibold')
    plt.xlim(0, max(top_paths['hits']) * 1.15)
    plt.tight_layout()
    plt.savefig("top_404_paths.png", dpi=200)
    plt.close()
    print("[+] Generated: top_404_paths.png")

    # Chart 4: Daily Trend Line Chart
    plt.figure(figsize=(12, 5))
    plt.plot(daily_trend['date'], daily_trend['error_count'], marker='o', color='#dc2626',
             linewidth=2.5, markersize=8, markerfacecolor='#991b1b')
    plt.title("404 Errors Over Time (Daily Trend across 7 Days)", fontsize=14, fontweight='bold', pad=15)
    plt.xlabel("Date", fontsize=11, fontweight='semibold')
    plt.ylabel("404 Error Count", fontsize=11, fontweight='semibold')
    plt.ylim(min(daily_trend['error_count']) * 0.9, max(daily_trend['error_count']) * 1.1)
    for _, row in daily_trend.iterrows():
        plt.annotate(f"{row['error_count']:,}", (row['date'], row['error_count'] + 40),
                     ha='center', fontsize=9, fontweight='bold')
    plt.xticks(rotation=30)
    plt.tight_layout()
    plt.savefig("404_daily_trend.png", dpi=200)
    plt.close()
    print("[+] Generated: 404_daily_trend.png")

    # 7. Export structured JSON for the Web Dashboard
    print("\n[*] Exporting JSON data feed for the Web Dashboard...")
    sample_records = df.head(150)[['timestamp_str', 'ip', 'method', 'path', 'status', 'size']].to_dict(orient='records')
    
    # Heatmap matrix as list of dicts for Chart.js / Matrix
    heatmap_matrix = []
    for day in day_order:
        row_vals = heatmap_df.loc[day].tolist()
        heatmap_matrix.append({'day': day, 'hours': row_vals})

    dashboard_data = {
        'metadata': {
            'generated_at': datetime.now().isoformat(),
            'dataset_name': "Server Access Logs (Apache/NGINX Common Log Format)",
            'storage_engine': "Hadoop Distributed File System (HDFS)",
            'processing_engine': "Apache PySpark DataFrame API",
            'total_requests': int(total_requests),
            'total_404': int(total_404),
            'error_rate': round(float(error_rate), 2),
            'peak_hour': int(peak_hour),
            'peak_hour_formatted': f"{peak_hour:02d}:00 - {peak_hour+1:02d}:00",
            'peak_count': int(peak_count)
        },
        'status_breakdown': status_breakdown.to_dict(orient='records'),
        'hourly_distribution': hourly_counts.to_dict(orient='records'),
        'top_endpoints': top_paths.to_dict(orient='records'),
        'daily_trend': daily_trend.to_dict(orient='records'),
        'heatmap_matrix': heatmap_matrix,
        'sample_logs': sample_records
    }

    with open("web_dashboard_data.json", "w", encoding='utf-8') as f:
        json.dump(dashboard_data, f, indent=2)
    print("[+] Saved: web_dashboard_data.json")

    print("\n[✓] All pipeline deliverables generated successfully!")

if __name__ == '__main__':
    df = parse_logs(LOG_FILE)
    analyze_and_export(df)
