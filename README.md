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
├── Nasa.csv            # 🚀 NASA server log test dataset (1,000 records)
├── app.py              # 🛡️ Complete single-file Python web application & engine
├── requirements.txt    # 📦 Minimal external dependencies (Flask)
├── run.bat             # 🪟 Windows 1-click launcher (CMD / Explorer)
├── run.ps1             # 🪟 Windows PowerShell 1-click launcher
├── run.sh              # 🍎🐧 Linux & macOS 1-click launcher
├── .gitignore          # 🚫 Git ignore rules for virtual environments & caches
└── README.md           # 📖 Project documentation & verification report
```

---

## ⚡ Cross-Platform Quick Start (Windows, macOS, Linux)

### 🪟 Windows (10 / 11)

#### Option A: 1-Click Launcher (Easiest)
Simply **double-click** [`run.bat`](file:///home/reny/Documents/Assignment2/run.bat) in Windows File Explorer. It automatically detects Python, sets up `.venv`, installs requirements, and launches the dashboard!

#### Option B: Windows Command Prompt (CMD)
```cmd
REM 1. Clone & enter repository
git clone https://github.com/Ratanazen/Data.git
cd Data

REM 2. Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate.bat

REM 3. Install requirements
pip install -r requirements.txt

REM 4. Launch application (All-in-one run)
python app.py --open
```

#### Option C: Windows PowerShell
```powershell
# Run the PowerShell launcher directly
.\run.ps1 -open

# Or manual launch:
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py --open
```

---

### 🍎 macOS (Apple Silicon M1/M2/M3 & Intel)

#### Option A: 1-Click Launcher
```bash
chmod +x run.sh
./run.sh --open
```

#### Option B: macOS Terminal
```bash
# 1. Clone & enter repository
git clone https://github.com/Ratanazen/Data.git
cd Data

# 2. Setup virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Launch application
python3 app.py --open
```

---

### 🐧 Linux (Ubuntu, Debian, Fedora, Arch, CentOS)

#### Option A: 1-Click Launcher
```bash
chmod +x run.sh
./run.sh --open
```

#### Option B: Linux Terminal
```bash
# 1. Clone & enter repository
git clone https://github.com/Ratanazen/Data.git
cd Data

# 2. Setup virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Launch application
python3 app.py --open
```

---

### 🌐 Accessing the Dashboard

Once started, open your web browser at:
**[http://127.0.0.1:8080](http://127.0.0.1:8080)**

### ⚙️ Command Line Arguments (All Platforms)

| Flag | Purpose | Example |
| :--- | :--- | :--- |
| *(default)* | All-in-one: self-tests + PySpark auto-init + web server | `python app.py` |
| `--open` | Automatically open default browser on launch | `python app.py --open` |
| `--port <N>` | Specify custom port (auto-switches if port is busy) | `python app.py --port 5000` |
| `--host <IP>` | Specify host address | `python app.py --host 0.0.0.0` |
| `--test` | Run 21-point test suite and exit | `python app.py --test` |
| `--no-test` | Skip startup self-tests and start server immediately | `python app.py --no-test` |
| `--no-spark` | Force local in-memory engine (disable PySpark) | `python app.py --no-spark` |
| `--hdfs <URI>` | Connect to remote Hadoop HDFS NameNode | `python app.py --hdfs hdfs://nn:9000` |

---

## 🧪 Built-In Automated Verification

Run the built-in automated test suite directly from `app.py`:

```bash
python app.py --test
```

### Automated Test Coverage (21/21 Passed • 100%)

| Test Case | Scenario / Requirement | Verification | Result |
| :--- | :--- | :--- | :---: |
| `01_valid_csv` | Valid CSV upload | Computes total requests, status counts, 404 count | PASSED |
| `02_clf_logs` | Apache & Nginx access log parsing | Standard CLF regex parses IP, date, method, path, status | PASSED |
| `03_empty_csv` | Empty CSV file rejection | 0-byte file rejected with HTTP 400 Bad Request | PASSED |
| `04_malformed_rows` | Ragged/malformed rows handling | Excluded rows safely accounted for in `excluded_records` | PASSED |
| `05_missing_timestamp` | Missing timestamp column | Handled gracefully without crash (`timeline_available: false`) | PASSED |
| `06_missing_status` | Missing status-code column | Handled gracefully (`status_available: false`, rate = 0.0%) | PASSED |
| `07_invalid_timestamp`| Unparseable timestamp values | Non-date values fall back safely to unindexed timeline | PASSED |
| `08_mixed_statuses` | Mixed HTTP status codes | Verifies counts for 200, 301, 400, 403, 404, 500 & categories | PASSED |
| `09_404_percentage` | Exact 404 rate formula | $(\text{404 count} / \text{total valid requests}) \times 100$ | PASSED |
| `10_hourly_aggregation`| 24-hour UTC aggregation | Correct counts per hour, highlights peak failure window | PASSED |
| `11_timezone_offsets` | Timezone normalization | Offsets (`-0500`, `+0700`, `Z`) normalized to UTC | PASSED |
| `12_oversized_upload` | Oversized payload rejection | File exceeding limit rejected with HTTP 413 | PASSED |
| `13_csv_injection` | CSV spreadsheet formula defense | Values starting with `=+-@\t\r` prepended with `'` | PASSED |
| `14_spark_fallback` | PySpark optional engine fallback | Automatic fallback to local in-memory engine | PASSED |
| `15_hdfs_connection` | HDFS NameNode connection failure | Graceful connection test without service crash | PASSED |
| `16_route_errors` | Flask route & parameter errors | Returns 404 on invalid route/dataset, 400 on `.exe` | PASSED |
| `17_ui_render_health` | UI rendering & service health | GET `/` renders Dark Navy/Cyan UI, `/health` reports 200 OK | PASSED |
| `18_sample_generator` | Assignment 2 sample generator | 1,200 records generated with 03:00 AM peak spike | PASSED |
| `19_data_explorer` | Live pagination, search & filter | Column sorting, status filter, 10/25/50/100 pagination | PASSED |
| `20_session_clear` | Session clear & upload cleanup | POST `/api/clear` flushes memory and temporary files | PASSED |
| `21_spark_dataframe` | PySpark DataFrame distributed ETL | Real PySpark DataFrame 404 filter and group-by aggregation | PASSED |

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
