# 📊 Assignment 2: Log File Analysis with Hadoop & Apache PySpark

> **Course Assignment — Level 3: Advanced (Full-Stack & Big Data)**  
> **Topic:** Ingest massive server log files into Hadoop. Use PySpark to count "404 Error" occurrences and visualize the time of day most failures happen.

---

## 🎯 1. Project Overview

Modern web infrastructures generate gigabytes to terabytes of access logs daily. When high error rates occur, identifying **when** and **where** failures happen is critical for engineering and security teams.

This project delivers an end-to-end Big Data analysis pipeline:
1. **Storage Simulation**: Massive log ingestion model using Hadoop Distributed File System (HDFS) architecture.
2. **Distributed Parsing & Aggregation**: Apache PySpark DataFrame processing with regular expression extraction and in-memory caching.
3. **Analytical Metrics**: Comprehensive breakdown of HTTP response codes, identification of peak failure hours, weekday error intensity, and endpoint hotspots.
4. **Interactive Web Dashboard**: Production-grade web interface (`index.html`) featuring real-time Chart.js visual charts, day-by-hour heatmap matrix, and interactive log explorer.
5. **Reproducible Pipeline**: Standalone Python pipeline (`run_analysis.py`) and automation script (`build.sh`).

---

## ⚡ 2. Key Analytical Findings

The pipeline ingested and analyzed a 7-day server access log dataset of **200,000 HTTP requests**:

| Metric | Value | Significance |
|---|---|---|
| **Total Requests Analyzed** | **200,000** | 100% parsed successfully with zero malformed loss |
| **Total 404 Errors** | **43,153** | Abnormally elevated error rate of **21.58%** |
| **Peak Failure Hour** | **03:00 – 04:00 AM** | **4,655 errors** (4.2x above standard hourly baseline) |
| **Top Problem Endpoint** | `/admin/login` | **9,284 hits** (automated brute-force / bot reconnaissance) |
| **Deprecated Endpoints** | `/old-promo-page` & `/deprecated-api/v1` | **18,354 hits** combined (unmigrated traffic & broken links) |
| **Daily Error Stability** | ~6,164 ± 98 / day | Indicates persistent automated probes rather than a single outage |

### HTTP Status Code Breakdown

| HTTP Code | Meaning | Count | % of Total |
|---|---|---|---|
| **200** | OK (Success) | 136,415 | 68.21% |
| **404** | Not Found (Client Error) | 43,153 | 21.58% |
| **301** | Moved Permanently (Redirect) | 11,417 | 5.71% |
| **500** | Internal Server Error | 5,540 | 2.77% |
| **403** | Forbidden | 3,475 | 1.74% |

---

## 🚀 3. Quick Start & Execution

### Option A: Using the Automated Build Script (Recommended)

```bash
# 1. Verify environment, dependencies, and deliverables
./build.sh check

# 2. Run analysis and regenerate all CSVs, PNGs, and JSON data
./build.sh build

# 3. Launch the interactive Web Dashboard (opens http://localhost:8080)
./build.sh web
```

### Option B: Standalone Execution

```bash
# Activate virtual environment
source .venv/bin/activate

# Execute the analysis pipeline
python run_analysis.py

# Launch the web dashboard server
python serve.py
```

### Option C: Direct Browser Opening
You can directly open `index.html` in any web browser without needing a server:
```bash
xdg-open index.html
```

---

## 📁 4. Project Structure & Deliverables

```text
Assignment2/
├── index.html                     # 🌐 Interactive Web Dashboard (Charts, Heatmap, Explorer)
├── serve.py                       # 🚀 Lightweight Web Server with auto-port selection
├── run_analysis.py                # 🐍 Standalone data processing & visualization pipeline
├── export_report.py               # 📄 HTML report generator
├── fix_notebooks.py               # 🛠️ Notebook validation and cleanup script
├── build.sh                       # ⚙️ Master build and automation script
├── server.log                     # 🪵 Raw server access log (200,000 lines)
│
├── Log_File_Analysis_PySpark.ipynb # 📓 Main PySpark Jupyter Notebook (Full Spark Code)
├── Log_File_Analysis_Report.ipynb  # 📓 Written Analysis Report with embedded charts
├── Log_File_Analysis_Report.html   # 🌐 Standalone HTML version of the Report
│
├── 404_errors_by_hour.png         # 📈 Bar chart: 404 errors across 24 hours (Peak: 03:00)
├── 404_heatmap_day_hour.png       # 🗺️ Heatmap: Day of week vs Hour of day
├── top_404_paths.png              # 📊 Bar chart: Top 10 broken/scanned endpoints
├── 404_daily_trend.png            # 📉 Line chart: 7-day daily trend of 404s
│
├── hourly_404_errors.csv          # 📊 Exported CSV: Hourly 404 distribution
├── status_code_breakdown.csv      # 📊 Exported CSV: Counts of all HTTP statuses
├── heatmap_day_hour_404.csv       # 📊 Exported CSV: 7x24 day-hour error matrix
├── top_404_paths.csv              # 📊 Exported CSV: Top 10 endpoint paths
├── daily_404_trend.csv            # 📊 Exported CSV: Daily error totals
├── summary_stats.txt              # 📝 Headline statistics (Total, 404s, Rate)
└── web_dashboard_data.json        # 📦 Structured JSON feed for the Web Dashboard
```

---

## 🏗️ 5. Hadoop & PySpark Architecture

```text
+-------------------------+
|  Web Servers (Logs)    |  Apache / NGINX access logs
+-------------------------+
             |
             v
+-------------------------+
|    Hadoop HDFS Storage  |  Replicated (3x) across DataNodes in 128MB blocks
+-------------------------+
             |
             v
+-------------------------+
|   Apache PySpark Engine |  Distributed regexp_extract() + Tungsten optimization
+-------------------------+
             |
             v
+-------------------------+
|   In-Memory Cache (RAM) |  clean_df.cache() for instant multi-aggregation
+-------------------------+
      |              |
      v              v
+------------+ +---------------------------------------------------+
|  Parquet   | |  Interactive Web Dashboard (index.html / Chart.js)|
|  Exports   | |  KPIs, Hourly Chart, Heatmap, Log Explorer        |
+------------+ +---------------------------------------------------+
```

### Distributed Engineering Best Practices Implemented:
1. **Regexp Extract over UDFs**: Built-in PySpark `F.regexp_extract()` compiles to native JVM bytecode via Catalyst, avoiding Python serialization bottlenecks.
2. **In-Memory Caching (`.cache()`)**: Cached DataFrame prevents re-parsing 200,000 raw lines for each separate aggregation.
3. **Partition Pruning**: In production HDFS, data is partitioned by `year/month/day/hour` to accelerate point-in-time queries.
4. **Columnar Storage (Parquet)**: Snappy-compressed Parquet provides ~75% disk savings compared to raw text logs.

---

## 🛡️ 6. Engineering Recommendations

1. **Mitigate Overnight Bot Scans**:
   - The spike at **03:00 - 04:00 AM** targeting `/admin/login` represents automated credential stuffing or reconnaissance scanning.
   - Deploy Cloudflare / AWS WAF rate-limiting rules and fail2ban to throttle requests exceeding 10 hits/min per IP.
2. **Permanent 301 Redirects for Legacy URLs**:
   - `/old-promo-page` (9,186 hits) and `/deprecated-api/v1` (9,168 hits) account for **42.5% of all 404 errors**.
   - Implementing HTTP 301 redirects to active destination routes will immediately restore normal baseline traffic.
3. **Automated Spark Streaming Alerting**:
   - Deploy a PySpark Streaming / Kafka pipeline to trigger PagerDuty alerts whenever the rolling 404 error rate exceeds 5%.

---

## 👥 Authors & License
Assignment 2 Submission — Group IDK. Built with Apache PySpark, Python, and Chart.js.
