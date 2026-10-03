# 📊 Assignment 2: Log File Analysis with Hadoop & Apache PySpark

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB?style=for-the-badge&logo=python&logoColor=white)
![OS](https://img.shields.io/badge/OS-Windows%20%7C%20macOS%20%7C%20Linux-0078D6?style=for-the-badge&logo=windows&logoColor=white)
![Hadoop](https://img.shields.io/badge/Hadoop-HDFS%20Distributed-FFC107?style=for-the-badge&logo=apachehadoop&logoColor=black)
![PySpark](https://img.shields.io/badge/Apache%20Spark-PySpark%20DataFrame-E25A1C?style=for-the-badge&logo=apachespark&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![CI Tests](https://img.shields.io/badge/CI%20Matrix-10%2F10%20Tests%20Passing-22C55E?style=for-the-badge&logo=githubactions&logoColor=white)

<br/>

### 🚀 Level 3: Advanced (Focus: Full-Stack & Big Data)
**Topic:** *Ingest massive server log files into Hadoop. Use PySpark to count "404 Error" occurrences and visualize the time of day most failures happen.*

[🌐 Live Interactive Web Dashboard](index.html) • [📄 Full Written HTML Report](Log_File_Analysis_Report.html) • [📓 Main PySpark Notebook](Log_File_Analysis_PySpark.ipynb) • [⚡ Quick Start Guide](QUICKSTART.md)

---

</div>

## 📥 How to Clone & Run Locally in 60 Seconds

### Step 1: Clone the Repo
```bash
git clone https://github.com/Ratanazen/Data.git
cd Data
```

### Step 2: Choose Your Platform

#### 🪟 Windows Users:
- **Easiest**: Simply **double-click** `run.bat` in File Explorer!
- **Or via Command Prompt**:
  ```cmd
  pip install -r requirements.txt
  build.bat all
  build.bat web
  ```
- **Or via PowerShell**:
  ```powershell
  pip install -r requirements.txt
  .\build.ps1 all
  .\build.ps1 web
  ```

#### 🍎 macOS Users:
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
./build.sh all
./build.sh web
```

#### 🐧 Linux Users:
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
./build.sh all
./build.sh web
```

#### 🐳 Docker Users (Zero Local Dependencies):
```bash
docker compose up --build
```

👉 Once running, open **[http://localhost:8080/](http://localhost:8080/)** in your browser!

---

## 📑 Table of Contents
- [🎯 1. Project Overview](#-1-project-overview)
- [⚡ 2. Key Analytical Findings](#-2-key-analytical-findings)
- [🏗️ 3. Big Data Architecture](#️-3-big-data-architecture)
- [💻 4. Comprehensive Execution Commands](#-4-comprehensive-execution-commands)
- [🧪 5. Automated Testing Suite](#-5-automated-testing-suite)
- [📁 6. Repository Layout & Deliverables](#-6-repository-layout--deliverables)
- [🛡️ 7. Tactical Incident Recommendations](#️-7-tactical-incident-recommendations)

---

## 🎯 1. Project Overview

Production server clusters generate gigabytes of telemetry every hour. When elevated error rates threaten user experience, identifying **when** failures spike, **which** endpoints trigger them, and **why** they happen is a core data engineering challenge.

This project delivers a complete, cross-platform Big Data analysis pipeline:
1. **Hadoop HDFS Storage Simulation**: Models distributed 128MB block chunking with 3x replica fault tolerance.
2. **PySpark DataFrame Engine**: Distributed regex parsing (`F.regexp_extract`) leveraging Catalyst query optimization and Tungsten JVM bytecode compilation.
3. **In-Memory Caching (`.cache()`)**: Persists cleaned DataFrames in executor RAM for instantaneous multi-dimensional aggregations.
4. **Interactive Web Dashboard**: Modern, responsive analytics dashboard (`index.html`) featuring real-time Chart.js visualizations, day-by-hour heatmap matrix, and log explorer.
5. **Full Cross-Platform Build Configuration**: Works seamlessly on **Windows**, **macOS**, and **Linux** with `Makefile`, `build.sh`, `build.bat`, `build.ps1`, `run.bat`, `pyproject.toml`, and `Dockerfile`.

---

## ⚡ 2. Key Analytical Findings

The pipeline ingested and analyzed a 7-day server access log dataset of **200,000 HTTP requests**:

| Metric | Value | Significance & Insights |
|---|---|---|
| **Total Requests Analyzed** | **200,000** | 100% parsed successfully with zero malformed loss |
| **Total 404 Errors** | **43,153** | Abnormally elevated error rate of **21.58%** |
| **Peak Failure Hour** | **03:00 – 04:00 AM** | **4,655 errors** (4.2x above standard hourly baseline) |
| **Top Problem Endpoint** | `/admin/login` | **9,284 hits** (automated brute-force / bot reconnaissance) |
| **Deprecated Endpoints** | `/old-promo-page` & `/deprecated-api/v1` | **18,354 hits** combined (unmigrated client traffic) |
| **Daily Error Variance** | **±1.6%** (~6,164 / day) | Proves continuous automated scans rather than transient outages |

### HTTP Status Code Breakdown

```text
  [200 OK]             ██████████████████████████████ 136,415 (68.21%)
  [404 Not Found]      █████████ 43,153 (21.58%)
  [301 Redirect]       ██ 11,417 (5.71%)
  [500 Server Error]   █ 5,540 (2.77%)
  [403 Forbidden]      ▌ 3,475 (1.74%)
```

---

## 🏗️ 3. Big Data Architecture

```text
+-----------------------+
|  Web Servers (Logs)   |  Raw Common Log Format (200,000 lines)
+-----------------------+
            |
            v
+-----------------------+
|  Hadoop HDFS Cluster  |  128MB Blocks • 3x Replica Fault-Tolerance
+-----------------------+
            |
            v
+-----------------------+
|  Apache PySpark 3.5+  |  Catalyst Optimizer • F.regexp_extract()
+-----------------------+
            |
            v
+-----------------------+
| In-Memory Cache (RAM) |  clean_df.cache() for parallel aggregations
+-----------------------+
      |            |
      v            v
+-----------+ +---------------------------------------------------------+
|  Parquet  | |  🌐 Interactive Web Dashboard (index.html)              |
|  Lakehouse| |  KPIs • 24h Bar Chart • 7x24 Heatmap • Log Explorer     |
+-----------+ +---------------------------------------------------------+
```

---

## 💻 4. Comprehensive Execution Commands

### Using `make` (macOS / Linux):
```bash
make help    # View colorized interactive help menu
make install # Create venv & install dependencies
make all     # Full pipeline: clean, check, test, build
make web     # Start local web server (http://localhost:8080)
make test    # Run all 10 automated unit tests
```

### Using `./build.sh` (macOS / Linux):
```bash
./build.sh check        # Audit environment and deliverables
./build.sh build        # Run pipeline and regenerate outputs
./build.sh web          # Launch web dashboard
./build.sh web --port=3000 # Specify custom port
./build.sh test         # Run unit tests
```

### Using `build.bat` (Windows):
```cmd
build.bat check
build.bat build
build.bat web
build.bat test
build.bat all
```

---

## 🧪 5. Automated Testing Suite

The repository includes an automated test suite in [`tests/test_analysis.py`](tests/test_analysis.py) and continuous integration across **Linux**, **macOS**, and **Windows** via GitHub Actions ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)).

```bash
python -m unittest tests/test_analysis.py -v
```

### Test Coverage (10 Test Cases):
- `test_01_server_log_exists`: Ensures `server.log` is present and intact (>1MB).
- `test_02_regex_pattern`: Verifies Common Log Format parser against sample lines.
- `test_03_summary_stats`: Verifies exact values in `summary_stats.txt` (200k total, 43,153 errors, 21.58%).
- `test_04_hourly_errors_csv`: Verifies 24 hourly rows and confirms peak hour = 3 (03:00 AM).
- `test_05_status_code_breakdown_csv`: Verifies distribution of 200, 404, 301, 500, and 403 codes.
- `test_06_top_endpoints_csv`: Validates top 10 endpoints and flags `/admin/login`.
- `test_07_chart_images_generated`: Verifies all 4 high-resolution `.png` figures are rendered (>10KB).
- `test_08_web_dashboard_data_json`: Validates schema and structure of the dashboard JSON feed.
- `test_09_web_dashboard_html`: Checks critical UI containers and SVG favicon in `index.html`.
- `test_10_serve_mime_types`: Ensures proper `.svg`, `.json`, `.js`, and `.css` MIME mappings on Windows/Mac.

---

## 📁 6. Repository Layout & Deliverables

```text
Assignment2/
├── index.html                     # 🌐 Interactive Web Dashboard (Chart.js, Heatmap, Explorer)
├── serve.py                       # 🚀 Cross-Platform Web Server with MIME mapping & auto-port
├── run_analysis.py                # 🐍 Standalone data processing & visualization pipeline
├── export_report.py               # 📄 HTML report generator with styled formatting
├── fix_notebooks.py               # 🛠️ Notebook validation and cell cleanup script
├── QUICKSTART.md                  # ⚡ 60-Second Clone & Run Guide
│
├── build.bat                      # 🪟 Windows Command Prompt build script
├── build.ps1                      # 🪟 Windows & Mac PowerShell automation script
├── run.bat                        # 🪟 Windows 1-Click desktop launcher
├── Makefile                       # ⚙️ Master POSIX build configuration
├── build.sh                       # 📜 Master Unix shell automation script
├── Dockerfile                     # 🐳 Container build specification
├── docker-compose.yml             # 🐳 Multi-service orchestration config
├── pyproject.toml                 # 📦 Modern Python project metadata & tool settings
├── requirements.txt               # 📋 Pinned dependencies list
├── .editorconfig                  # 📐 Code styling and formatting rules
│
├── .github/                       # 🤖 GitHub CI Workflows
│   └── workflows/ci.yml           # Cross-platform matrix test on Linux, Mac, & Windows
│
├── assets/                        # 🎨 Visual & SVG Assets
│   ├── favicon.svg                # 🌟 Glowing activity pulse favicon
│   ├── hadoop.svg                 # 🐘 Hadoop HDFS SVG icon
│   ├── spark.svg                  # 🔥 Apache Spark SVG flame icon
│   └── architecture.svg           # 🏗️ System architecture SVG diagram
│
├── tests/                         # 🧪 Automated Test Suite
│   └── test_analysis.py           # 10 unit tests verifying pipeline integrity
│
├── server.log                     # 🪵 200,000 raw server access records
├── Log_File_Analysis_PySpark.ipynb # 📓 Main PySpark Jupyter Notebook
├── Log_File_Analysis_Report.ipynb  # 📓 Written Analysis Report with embedded charts
├── Log_File_Analysis_Report.html   # 🌐 Standalone HTML version of the Report
│
├── 404_errors_by_hour.png         # 📈 Bar chart: 404 errors across 24 hours (Peak: 03:00)
├── 404_heatmap_day_hour.png       # 🗺️ Heatmap: Day of week vs Hour of day
├── top_404_paths.png              # 📊 Bar chart: Top 10 broken/scanned endpoints
├── 404_daily_trend.png            # 📉 Line chart: 7-day daily trend of 404s
│
├── hourly_404_errors.csv          # 📊 Exported CSV: Hourly 404 distribution
├── status_code_breakdown.csv      # 📊 Exported CSV: HTTP status code counts
├── heatmap_day_hour_404.csv       # 📊 Exported CSV: 7x24 day-hour error matrix
├── top_404_paths.csv              # 📊 Exported CSV: Top 10 endpoint paths
├── daily_404_trend.csv            # 📊 Exported CSV: Daily error totals
├── summary_stats.txt              # 📝 Headline statistics (Total, 404s, Rate)
└── web_dashboard_data.json        # 📦 Structured JSON feed for the Web Dashboard
```

---

## 🛡️ 7. Tactical Incident Recommendations

1. **Deploy WAF Rules for Overnight Automated Probes**:
   - The failure surge at **03:00 – 04:00 AM** targeting `/admin/login` indicates automated reconnaissance scanning.
   - Configure Web Application Firewall (WAF) rate limits and fail2ban rules to drop IPs exceeding 10 requests/min.
2. **Permanent 301 Redirects for Legacy URLs**:
   - `/old-promo-page` (9,186 hits) and `/deprecated-api/v1` (9,168 hits) represent **42.5% of all 404 errors**.
   - Implementing HTTP 301 redirects to active destination routes will immediately restore normal baseline traffic.
3. **Automate Real-Time Spark Streaming Alerts**:
   - Deploy a PySpark Streaming / Kafka pipeline to notify on-call engineers if rolling 404 error rates exceed 5%.
4. **Lakehouse Storage Migration**:
   - Store historical logs in snappy-compressed Parquet partitioned by `year/month/day/hour` to cut storage by 75%.

---

## 👥 Authors & License
Assignment 2 Submission — Group IDK. Built with Apache PySpark, Python, Chart.js, and Tailwind CSS.
