# 🗄️ LogShield Data Model & Parquet Lakehouse Schemas

LogShield stores all analytical datasets in **Apache Parquet** format with **Snappy** compression.

---

## 1. Medallion Table Schemas

### 🥉 Bronze Layer: `data/bronze/`
*Partitioned by: `date` (e.g., `date=2026-09-01`)*

| Column | Data Type | Nullable | Description |
|---|---|---|---|
| `timestamp` | `timestamp` | No | Extracted UTC event timestamp |
| `ip` | `string` | No | Client IP address |
| `method` | `string` | No | HTTP request verb (GET, POST, etc.) |
| `path` | `string` | No | Requested URL path |
| `protocol` | `string` | Yes | HTTP protocol version |
| `status` | `integer` | No | HTTP response code (RFC range) |
| `response_bytes`| `long` | No | Payload size in bytes |
| `source_file` | `string` | No | Originating source file |
| `ingestion_time`| `timestamp` | No | System timestamp when record was parsed |
| `date` | `string` | No | Partition key (YYYY-MM-DD) |

---

### 🥈 Silver Layer: `data/silver/`
*Dual partitioned by: `date`, `hour` (e.g., `date=2026-09-01/hour=3`)*

| Column | Data Type | Nullable | Description |
|---|---|---|---|
| `timestamp` | `timestamp` | No | Normalized UTC timestamp |
| `ip` | `string` | No | Validated IP address |
| `method` | `string` | No | Cleaned uppercase HTTP method |
| `path` | `string` | No | Normalized URI path |
| `protocol` | `string` | No | Defaulted HTTP protocol |
| `status` | `integer` | No | Validated status code (100–599) |
| `response_bytes`| `long` | No | Sanitized response byte count |
| `source_file` | `string` | No | Originating source file |
| `ingestion_time`| `timestamp` | No | Ingestion timestamp |
| `date` | `string` | No | Partition key (YYYY-MM-DD) |
| `hour` | `integer` | No | Partition key (0–23) |

---

### 🥇 Gold Layer: `data/gold/`

#### 1. `gold_hourly_traffic.parquet`
Columns: `hour` (int), `total_requests` (long), `errors_404` (long), `errors_403` (long), `errors_500` (long), `successes_200` (long), `redirects_301` (long), `error_rate` (double).

#### 2. `gold_status_distribution.parquet`
Columns: `status` (int), `count` (long), `percentage` (double).

#### 3. `gold_404_paths.parquet`
Columns: `path` (string), `hits` (long).

#### 4. `gold_daily_errors.parquet`
Columns: `date_str` (string), `total_requests` (long), `errors_404` (long), `error_rate` (double).

#### 5. `gold_404_heatmap.parquet`
Columns: `day_of_week` (string), `hour` (int), `error_count` (long).

#### 6. `gold_top_ips.parquet`
Columns: `ip` (string), `total_requests` (long), `errors_404` (long), `errors_403` (long), `errors_500` (long), `login_failures` (long), `risk_score` (int), `severity` (string).

#### 7. `gold_top_urls.parquet`
Columns: `path` (string), `hits` (long), `errors_404` (long), `error_rate` (double).

#### 8. `gold_security_events.parquet`
Columns: `event_id` (string), `timestamp` (string), `ip` (string), `event_type` (string), `severity` (string), `risk_score` (int), `evidence` (string), `request_count` (int), `recommendation` (string).

---

## 2. Storage Efficiency & Compression Benchmarks

| Metric | Raw Text (`server.log`) | Snappy Parquet (Lakehouse) | Savings |
|---|---|---|---|
| **File Size** | 15.63 MB | ~3.82 MB | **75.5% Compression** |
| **Row Count** | 200,000 | 200,000 | 100% Integrity |
| **Query Latency** | ~450 ms (full scan) | ~18 ms (columnar projection) | **25× Faster** |
