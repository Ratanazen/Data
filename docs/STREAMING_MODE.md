# ⚡ LogShield Real-Time Streaming Mode

LogShield provides real-time distributed stream ingestion and sliding-window anomaly detection powered by **Apache Kafka** and **PySpark Structured Streaming**.

---

## 1. Streaming Architecture

```
  ┌──────────────┐         ┌────────────────────────┐         ┌────────────────────────┐
  │ LogProducer  │ ──────> │ Apache Kafka (KRaft)   │ ──────> │ PySpark Streaming      │
  │ (File/Stream)│         │ Topic: 'server-logs'   │         │ Catalyst Parsing       │
  └──────────────┘         └───────────┬────────────┘         └───────────┬────────────┘
                                       │                                  │
                                       ▼                                  ▼
                            ┌──────────────────────┐           ┌──────────────────────┐
                            │ Kafka UI             │           │ Tumbling & Sliding   │
                            │ Port 8085            │           │ Window Aggregations  │
                            └──────────────────────┘           └──────────┬───────────┘
                                                                          │
                                                                          ▼
                                                               ┌──────────────────────┐
                                                               │ Live Sink: Parquet / │
                                                               │ Real-Time Security   │
                                                               └──────────────────────┘
```

---

## 2. Launching Kafka Stack with Docker

Start the streaming cluster (Kafka KRaft broker + Kafka UI + Streaming Worker):
```bash
docker compose -f docker-compose.streaming.yml up -d
```

### Web Interfaces:
* **Kafka UI Dashboard**: `http://localhost:8085`

---

## 3. Streaming Records into Kafka

Use the LogShield CLI or Python module to stream server log events:

### High-Speed Log Producer:
```bash
python -m logshield stream --mode producer --file server.log --rate 250 --limit 5000
```
Parameters:
* `--rate`: Messages streamed per second (e.g., 250 msgs/sec).
* `--topic`: Target Kafka topic (default: `server-logs`).
* `--limit`: Number of records to stream before finishing.
* `--simulate`: Offline simulation without connecting to a live broker.

---

## 4. Running PySpark Structured Streaming Job

Start the streaming analytics job:
```bash
python -m logshield stream --mode job --bootstrap localhost:9092 --topic server-logs
```

### Stateful Windowing Configurations:
* **Tumbling Window**: 5-minute fixed windows tracking overall error rate with a 10-minute watermark.
* **Sliding Window**: 10-minute window sliding every 2 minutes tracking IP-level request frequency to flag automated scanners.

### Graceful Fallback:
If Kafka is offline, `LogShield` automatically engages **micro-batch simulation mode**, ensuring tests and local validations succeed without network failures.
