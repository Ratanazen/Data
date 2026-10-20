# 🛡️ LogShield — Log File Analysis Web Application

> **Assignment 2: Big Data Analytics & PySpark Log Analysis (Project #19)**  
> *Ingest massive server log files into Hadoop. Use PySpark to count '404 Error' occurrences and visualize the time of day most failures happen.*

---

## 📋 Overview

**LogShield** is a single-file Python web application for ingesting, parsing, and analyzing web server logs and CSV files. Built with **Flask** and styled in an enterprise **Dark Navy (`#0b1120`) and Cyan (`#06b6d4`)** theme, it provides instant visibility into HTTP traffic health, 404 failure patterns, hourly anomaly distributions, and broken URL endpoints.

### ✨ Key Capabilities

- **🚀 Single-File Python Engine (`app.py`)**: Web server, analytical logic, parsing engine, and embedded dashboard UI consolidated into one file.
- **📂 Multi-Format Ingestion**:
  - Apache Common Log Format (CLF) and Combined Log Format
  - Nginx access logs
  - Tabular CSV / TSV files with auto-delimiter sniffing (`,`, `\t`, `;`, `|`)
  - Auto-detection of common column aliases (`status`, `url`/`path`, `ip`, `timestamp`, `method`, `size`)
  - Universal encoding support: UTF-8, UTF-8 with BOM (`utf-8-sig`), Latin-1 (`iso-8859-1`), and Windows CP1252
- **📊 HTTP 404 & Error Analytics**:
  - Exact 404 error rate formula: $\text{404 Percentage} = \left(\frac{\text{HTTP 404 Responses}}{\text{Total Valid HTTP Requests}}\right) \times 100$
  - Complete status code breakdown (200, 301, 400, 403, 404, 500, etc.)
  - Count of malformed/unparseable excluded rows clearly reported
- **🕒 24-Hour Failure Distribution (UTC Normalized)**:
  - Timestamps with timezone offsets (`+0000`, `-0500`, ISO 8601, epoch) are normalized consistently to UTC
  - Highlights the peak failure hour (e.g. 03:00 AM automated bot scan spike)
- **🔗 Top Endpoints & Client IPs**:
  - Ranked table of most frequently failing URL endpoints with individual failure percentages
  - Most active client IP addresses and request volumes
- **⚡ Optional Apache PySpark & Hadoop HDFS Integration**:
  - Configurable PySpark distributed processing (`--spark`)
  - Configurable Hadoop HDFS NameNode connection (`--hdfs <uri>`)
  - Automatic graceful fallback to local in-memory engine when Hadoop/Spark are not configured
  - Transparent processing status badge on the dashboard (`/api/status`)
- **🔎 Interactive Data Explorer & Sanitized Export**:
  - Live search across all log columns
  - Status code category filtering (All, 404 Only, 4xx Client, 5xx Server, 200 OK, 3xx Redirect)
  - Column sorting and pagination (10, 25, 50, 100 per page)
  - One-click CSV export with formula injection mitigation (values starting with `=`, `+`, `-`, `@` prepended with `'`)

---

## 📁 Repository Structure

```text
Data/
├── app.py              # 🚀 Complete single-file Python web application & engine
├── requirements.txt    # 📦 Minimal external dependencies (Flask)
├── .gitignore          # 🚫 Git ignore rules for virtual environments & caches
└── README.md           # 📖 Project documentation & verification report
```

---

## ⚡ Installation & Quick Start

### 1. Prerequisites

- Python 3.10+ (tested on Python 3.11, 3.12, 3.14)
- `pip` package manager

### 2. Setup Virtual Environment & Dependencies

```bash
# Clone the repository
git clone https://github.com/Ratanazen/Data.git
cd Data

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install minimal requirements
pip install -r requirements.txt
```

### 3. Launch the Application

```bash
# Run on default address (http://127.0.0.1:8080/)
python app.py

# Or specify custom host and port
python app.py --host 127.0.0.1 --port 8080
```

Open your browser at **[http://127.0.0.1:8080](http://127.0.0.1:8080)**.

### 4. Optional PySpark & Hadoop Modes

```bash
# Attempt distributed processing with PySpark (if pyspark is installed)
python app.py --spark

# Connect to a remote Hadoop HDFS NameNode
python app.py --hdfs hdfs://namenode:9000
```
*Note: If PySpark or Hadoop HDFS are unavailable, the application automatically operates in local in-memory mode without errors.*

---

## 🧪 Built-In Automated Verification

Run the built-in automated test suite directly from `app.py`:

```bash
python app.py --test
```

### Automated Test Coverage

| Test Case | Description | Result |
| :--- | :--- | :---: |
| `t1_root_render` | GET `/` renders Dark Navy (`#0b1120`) & Cyan dashboard | PASSED |
| `t2_health_status` | GET `/health` & `/api/status` report engine status | PASSED |
| `t3_sample_generator` | Built-in 1,200 record generator detects 03:00 AM failure peak | PASSED |
| `t4_csv_upload` | Valid CSV upload computes exact 404 percentage | PASSED |
| `t5_clf_log_upload` | Apache / Nginx Common Log Format parsing | PASSED |
| `t6_empty_file` | Empty upload rejection with 400 Bad Request | PASSED |
| `t7_invalid_extension`| Disallowed extension rejection (`.exe`) | PASSED |
| `t8_missing_columns` | Missing columns handled gracefully without crashing | PASSED |
| `t9_timezone_norm` | Timezone offsets (`-0500`, `+0000`) normalized to UTC | PASSED |
| `t10_encodings` | Auto-decodes UTF-8, UTF-8 with BOM, and Latin-1 | PASSED |
| `t11_api_query` | Live search, pagination, status filtering, and endpoints | PASSED |
| `t12_csv_injection` | CSV export sanitizes formula injection characters (`=`, `+`, `-`, `@`) | PASSED |
| `t13_spark_fallback` | PySpark and Hadoop HDFS fallback behavior | PASSED |
| `t14_session_clear` | Session clear and temporary dataset cleanup | PASSED |

---

## 🌐 API Route Specification

| Route | Method | Description |
| :--- | :---: | :--- |
| `/` | `GET` | Interactive Dark Navy & Cyan dashboard interface |
| `/upload` or `/api/upload` | `POST` | Upload and analyze a CSV or log file (`multipart/form-data`) |
| `/api/sample` | `POST` | Load the built-in realistic Apache log test dataset |
| `/api/stats` | `GET` | Summary metrics: total requests, 404 counts, failure rates, peak hour |
| `/api/hourly` | `GET` | 24-hour request and 404 failure counts (UTC normalized) |
| `/api/urls` | `GET` | Top 10 frequently failing URL endpoints |
| `/api/status` | `GET` | Application engine status (Local, PySpark, HDFS connectivity) |
| `/api/data` | `GET` | Paginated, searchable, sortable view of records |
| `/export` or `/api/export` | `GET` | Download filtered results as sanitized CSV |
| `/api/clear` | `POST` | Clear active session and flush temporary uploads |
| `/health` or `/api/health` | `GET` | Service health check endpoint |

---

## 🔒 Security & Defensive Engineering

1. **Upload Size Restrictions**: Enforces a strict `MAX_CONTENT_LENGTH` of 32MB. Oversized files are rejected with HTTP 413.
2. **File Validation**: Filenames are sanitized via `secure_filename`. Extensions are strictly restricted to `.csv`, `.log`, `.txt`, `.tsv`.
3. **CSV Formula Injection Mitigation**: Any exported cell value starting with spreadsheet execution triggers (`=`, `+`, `-`, `@`, `\t`, `\r`) is prepended with a single quote (`'`).
4. **XSS Protection**: All user-controlled text rendered to the DOM is entity-escaped.
5. **Safe Temporary Storage**: Uploads are stored in a dedicated temporary directory with a 2-hour TTL auto-cleanup mechanism. Uploaded content is never executed.
6. **Localhost Binding**: Binds to `127.0.0.1` by default with debug mode disabled.

---

## 📄 License & Attribution

Developed for **Project #19: Log File Analysis (Hadoop & PySpark)**.  
Repository: [https://github.com/Ratanazen/Data](https://github.com/Ratanazen/Data)
