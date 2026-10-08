# 💻 LogShield Local Developer Mode

LogShield is designed with a **zero-dependency local development workflow**. You do not need a running Hadoop cluster or Kafka broker to run full batch analytics, evaluate threat vectors, or test the REST API.

---

## 1. Architecture in Local Mode

In Local Mode (`MODE=local`):
* **Execution Engine**: Local PySpark session initialized with `master("local[*]")`.
* **Storage**: Local filesystem at `./data/` using standard Apache Parquet with Snappy compression.
* **Metadata**: JSON KPI summaries stored directly at `data/gold/gold_kpis.json`.
* **Quarantine**: Faulty/corrupted records isolated to `data/quarantine/`.

---

## 2. Step-by-Step Execution Workflow

### Step 1: Ingest Raw Logs into Bronze Layer
Read `server.log` (200,000 records) and write partitioned Bronze Parquet:
```bash
python -m logshield ingest --input server.log
```
*Output*: `data/bronze/date=YYYY-MM-DD/*.parquet`

### Step 2: Normalize and Clean into Silver Layer
Filter RFC status codes, normalize timestamps, and generate `date` + `hour` partitions:
```bash
python -m logshield process
```
*Output*: `data/silver/date=YYYY-MM-DD/hour=H/*.parquet`

### Step 3: Compute Gold Analytics
Generate the 7 Gold analytical tables and KPI metadata:
```bash
python -m logshield analyze
```
*Output*:
- `data/gold/gold_hourly_traffic.parquet`
- `data/gold/gold_status_distribution.parquet`
- `data/gold/gold_404_paths.parquet`
- `data/gold/gold_daily_errors.parquet`
- `data/gold/gold_404_heatmap.parquet`
- `data/gold/gold_top_ips.parquet`
- `data/gold/gold_top_urls.parquet`
- `data/gold/gold_kpis.json`

### Step 4: Run Threat Intelligence & Security Detection
Evaluate behavioral rules and risk scoring across all client IPs:
```bash
python -m logshield security
```
*Output*:
- `data/gold/gold_security_events.parquet`
- `data/gold/gold_anomalies.parquet`

### Step 5: (Or Run All Above via Single Batch Command)
```bash
python -m logshield batch
```

---

## 3. Serving & Visualizing Locally

Start the servers:
```bash
# Start FastAPI REST API on port 8000
python -m logshield serve api --port 8000

# Start Dashboard on port 8080
python -m logshield serve dashboard --port 8080
```

When you visit `http://localhost:8080/`, the dashboard automatically checks for the FastAPI backend at `http://localhost:8000`. If active, it binds directly to the REST endpoints. If offline, it reads `web_dashboard_data.json` or embedded datasets with zero errors.
