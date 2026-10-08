# 📡 LogShield REST API Documentation

The LogShield REST API is an asynchronous backend powered by **FastAPI**. It serves analytical metrics, telemetry aggregations, detected security incidents, and live log exploration.

---

## 1. Quick Start

### Start the API Server:
```bash
python -m logshield serve api --host 0.0.0.0 --port 8000
```

### Interactive Documentation:
* **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
* **ReDoc UI**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 2. API Endpoints Reference

### Core & Health
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Platform identity & status check |
| `GET` | `/api/health` | Healthcheck (Spark, Storage, API version) |

#### Example: `GET /api/health`
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2026-10-08T08:30:00Z",
  "storage_backend": "Hadoop HDFS / Parquet",
  "active_partitions": 7
}
```

---

### Analytics & Telemetry
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/stats` | Executive KPI summary (requests, 404s, error rate) |
| `GET` | `/api/traffic` | 24-hour traffic volume and error distribution |
| `GET` | `/api/status` | HTTP status code breakdown (2xx, 3xx, 4xx, 5xx) |
| `GET` | `/api/errors` | Summary of 404 broken routes & daily trajectories |
| `GET` | `/api/404` | 7x24 Day-of-week by hour failure matrix |

#### Example: `GET /api/stats`
```json
{
  "total_requests": 200000,
  "total_404": 43153,
  "error_rate": 21.58,
  "peak_failure_hour": 3,
  "peak_failure_count": 4655,
  "unique_ips": 495,
  "unique_paths": 14,
  "total_200": 136413,
  "total_403": 3475,
  "total_500": 5540,
  "total_301": 11417,
  "suspicious_ips_count": 50,
  "security_events_count": 494
}
```

---

### Threat Intelligence & Security
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/security` | Detected security incidents with risk scores & WAF actions |
| `GET` | `/api/anomalies` | Statistical volume anomalies |
| `GET` | `/api/top-ips` | Top client IPs with behavioral risk scores |
| `GET` | `/api/top-urls` | Top requested endpoints & error frequencies |

#### Example: `GET /api/security?limit=2&severity=HIGH`
```json
[
  {
    "event_id": "SEC-001",
    "timestamp": "2026-09-07T03:45:00Z",
    "ip": "10.0.15.95",
    "event_type": "Sensitive Admin Route Probing",
    "severity": "HIGH",
    "risk_score": 75,
    "evidence": "Admin hits: 64, 404s: 86, 403s: 6",
    "request_count": 394,
    "recommendation": "Enforce WAF drop / fail2ban rate-limit on IP 10.0.15.95"
  }
]
```

---

### Live Log Explorer
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/logs` | Searchable log records with pagination and status filters |

Query parameters for `/api/logs`:
* `status` (integer, e.g. `404`)
* `ip` (string)
* `search` (string text search across paths)
* `page` (integer, default `1`)
* `page_size` (integer, default `50`)
