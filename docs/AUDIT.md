# LogShield — Repository Audit Report (Phase 0)

**Date**: 2026-10-08  
**Repository**: [https://github.com/Ratanazen/Data](https://github.com/Ratanazen/Data)  
**Project**: LogShield (Upgrading Project #19 "Log File Analysis")  
**Scope**: Ingestion, PySpark ETL, Data Architecture, Security Analytics, API, Dashboard, Docker, CI/CD  

---

## 1. Executive Summary

This audit assesses the state of the existing repository prior to undertaking the **LogShield** architectural upgrade. The repository currently implements a self-contained, working assignment pipeline for server access log analysis (`server.log`, 200,000 Common Log Format records) focused on isolating HTTP 404 "Not Found" error spikes at 03:00–04:00 AM, visualizing findings via Chart.js on an interactive web dashboard (`index.html`), simulating Hadoop HDFS cluster configurations, and running cross-platform CI matrix builds.

The objective of the LogShield upgrade is to elevate this baseline into a **production-style Distributed Log Analytics & Security Detection Platform** without discarding working features, breaking backwards compatibility, or introducing synthetic placeholders.

---

## 2. Existing Architecture & Components

```text
                           [ server.log (200k records) ]
                                         │
                                         ▼
                                [ run_analysis.py ]
                     (Regex parsing, aggregations, figures)
                                         │
     ┌────────────────────┬──────────────┴──────────────┬────────────────────┐
     ▼                    ▼                             ▼                    ▼
[ CSVS / TXT ]    [ PNG Charts (4x) ]       [ web_dashboard_data.json ] [ cluster-configs/ ]
- hourly_404      - 404_errors_by_hour      - KPIs, hourly trend        - spark-defaults.conf
- status_code     - 404_heatmap_day_hour    - 7x24 heatmap matrix       - core-site.xml
- top_404_paths   - top_404_paths           - top broken endpoints      - hdfs-site.xml
- daily_trend     - 404_daily_trend         - sizing & telemetry specs  - yarn-site.xml
- summary_stats                                         │
                                                        ▼
                                             [ serve.py (port 8080) ]
                                                        │
                                                        ▼
                                            [ index.html Dashboard ]
                                       - Chart.js visualizers
                                       - 7x24 day-hour heatmap
                                       - Interactive Log Explorer
                                       - Log Deep-Dive Inspector
                                       - Cluster Hardware Tuner
```

### Component Inventory:
1. **Data Ingestion & Processing (`run_analysis.py`)**:
   - Monolithic script (566 lines) handling log creation, regex parsing (`Apache Common Log Format`), pandas aggregations, Matplotlib chart generation, `cluster_sizing` math, and XML/conf writing.
2. **Web Server (`serve.py`)**:
   - Custom Python `http.server.SimpleHTTPRequestHandler` with explicit MIME mappings for SVG, JSON, and JS.
3. **Interactive Dashboard (`index.html`)**:
   - Single-page application styled with Tailwind CSS, Chart.js, Lucide icons.
   - Features: Hero stats, 4 responsive charts, 7x24 Day-Hour heatmap, interactive Log Explorer, Log Entry Deep-Dive Inspector modal (with RFC status decoder and WAF `deny` rule generator), Chart Presentation Zoom modal, multi-format exporter (CSV, JSON, Markdown, Clipboard), Cluster Resource Tuner with live topology cards, and System Settings modal (OLED/Obsidian cyberpunk themes, Web Audio chimes).
4. **Report Generator (`export_report.py`)**:
   - Compiles markdown and figures from `Log_File_Analysis_Report.ipynb` into a standalone executive HTML report (`Log_File_Analysis_Report.html`).
5. **Notebooks**:
   - `Log_File_Analysis_PySpark.ipynb`: Educational PySpark notebook demonstrating HDFS block chunking, regex parsing, Catalyst query optimization, caching (`.cache()`), and aggregations.
   - `Log_File_Analysis_Report.ipynb`: Written technical and executive presentation notebook.
6. **Docker Orchestration**:
   - `Dockerfile`: Python 3.11-slim container running `run_analysis.py` and `serve.py 8080`.
   - `docker-compose.yml`: Standalone dashboard container.
   - `docker-compose.cluster.yml`: 5-service stack (`namenode`, `datanode`, `spark-master`, `spark-worker`, `dashboard`).
7. **Automation & Cross-Platform Scripts**:
   - `Makefile` (POSIX), `build.sh` (macOS/Linux), `build.bat` (Windows cmd), `build.ps1` (PowerShell), `run.bat` (1-click Windows launcher).
8. **Automated Test Suite (`tests/test_analysis.py`)**:
   - 14 test cases verifying file presence, regex parsing, summary statistics, hourly rows, status code counts, top endpoints, PNG outputs, JSON schemas, MIME mappings, cluster sizing math, XML config output, Docker compose definitions, and dashboard DOM IDs.
9. **CI/CD Pipeline (`.github/workflows/ci.yml`)**:
   - Cross-platform matrix test running on `ubuntu-latest`, `macos-latest`, and `windows-latest` across Python 3.10, 3.11, and 3.12 (9 total matrix jobs, all currently passing).

---

## 3. Data Flow & Baseline Metrics

The pipeline analyzes a baseline dataset of **200,000 HTTP requests** generated over 7 consecutive days (01/Sep/2026 – 07/Sep/2026):
- **Total Requests**: 200,000 (100% clean parsing, 0 dropped).
- **Total 404 Errors**: 43,153 (elevated error rate of **21.58%**).
- **Peak Failure Window**: **03:00 – 04:00 AM** with **4,655 errors** (4.2x above average).
- **Top Broken/Probed Endpoint**: `/admin/login` (9,284 hits; credential reconnaissance).
- **Legacy Deprecated Routes**: `/old-promo-page` (9,186 hits) + `/deprecated-api/v1` (9,168 hits) accounting for 42.5% of all 404s.
- **HTTP Status Code Breakdown**:
  - `200 OK`: 136,415 (68.21%)
  - `404 Not Found`: 43,153 (21.58%)
  - `301 Redirect`: 11,417 (5.71%)
  - `500 Internal Server Error`: 5,540 (2.77%)
  - `403 Forbidden`: 3,475 (1.74%)

---

## 4. Problems & Limitations Identified

| Category | Problem Identified | Technical Impact |
| :--- | :--- | :--- |
| **Architecture** | Monolithic codebase in `run_analysis.py` | ETL, clustering, and visualization logic are tightly coupled in one script. Lacks modular package boundaries. |
| **Data Lakehouse** | Absence of Bronze/Silver/Gold layers | Raw logs are converted directly to summary CSVs. No partitioned Parquet lakehouse storage exists (`data/bronze`, `data/silver`, `data/gold`). |
| **Log Ingestion** | Single-format rigid parsing | Only Apache Common Log Format is supported. Lacks support for Nginx custom formats, JSON logs, or CSV logs. Corrupt records are dropped without quarantine tracking. |
| **API Layer** | Static file serving via `serve.py` | Dashboard fetches a static 160KB `web_dashboard_data.json`. No dynamic REST API (FastAPI) with query filters, date slicing, IP lookups, or pagination. |
| **Security Analytics** | Heuristic limited to 404 endpoint flags | No structured security event schema, risk score calculator (0–100), brute-force detection, suspicious scanning identification, or alert event model. |
| **Streaming** | No live streaming pipeline | Real-time Kafka + PySpark Structured Streaming modules are absent. |
| **CLI** | Limited CLI flags | Script only supports basic argparse options for cluster sizing. No unified `python -m logshield` command suite (`ingest`, `process`, `analyze`, `security`, `serve`, `stream`, etc.). |
| **Testing** | Monolithic `unittest` file | 14 tests in a single file without pytest fixtures, unit vs integration test separation, API mock tests, or security rule tests. |
| **Documentation** | No dedicated `docs/` architecture manual | Documentation was confined to `README.md` and `QUICKSTART.md`. No dedicated architectural blueprints, API documentation, or runbook guides existed. |

---

## 5. Non-Destructive Migration Strategy

To follow the Non-Destructive Update Rule:
1. **Preserve Legacy Assets**:
   - Retain `run_analysis.py`, `serve.py`, `export_report.py`, `index.html`, and `tests/test_analysis.py` as working baseline fallbacks.
   - Retain `server.log`, existing CSV exports, PNG figures, and notebooks (`Log_File_Analysis_PySpark.ipynb`, `Log_File_Analysis_Report.ipynb`).
2. **Implement Modular Package (`src/logshield/`)**:
   - `src/logshield/config/`: Configuration management, environment variable loading (`.env`), and runtime modes (`local`, `hadoop`, `streaming`).
   - `src/logshield/ingestion/`: Ingestion readers, Apache/Nginx/JSON parsers, validation, and quarantine storage (`data/quarantine/`).
   - `src/logshield/spark/`: PySpark & local engine for Bronze, Silver, and Gold Parquet generation.
   - `src/logshield/security/`: Security rule engine, anomaly detectors, risk scoring (0–100), and event models.
   - `src/logshield/api/`: FastAPI REST backend exposing analytics and security endpoints.
   - `src/logshield/streaming/`: Kafka producer, consumer, PySpark Structured Streaming windowed processor.
   - `src/logshield/cli/`: Unified command-line interface `python -m logshield`.
3. **Upgrade Dashboard V2**:
   - Connect `index.html` to query FastAPI endpoints (`/api/stats`, `/api/traffic`, `/api/errors`, `/api/security`, `/api/logs`) while preserving standalone demo fallback if the API is offline.
4. **Expand Testing & Documentation**:
   - Provide comprehensive pytest suite in `tests/unit/` and `tests/integration/` while maintaining the existing 14 tests in `tests/test_analysis.py`.
   - Author complete documentation suite in `docs/`.
