# 🐘 LogShield Hadoop HDFS & Spark Cluster Mode

For large-scale enterprise deployments, LogShield integrates with Apache Hadoop HDFS and Apache Spark standalone or YARN clusters.

---

## 1. Cluster Architecture

```
                    ┌───────────────────────────┐
                    │  HDFS NameNode (Port 9870)│
                    │  RPC FileSystem: 9000     │
                    └─────────────┬─────────────┘
                                  │
                 ┌────────────────┴────────────────┐
                 ▼                                 ▼
    ┌──────────────────────────┐     ┌──────────────────────────┐
    │ HDFS DataNode 1 (9864)   │     │ HDFS DataNode 2 (9864)   │
    │ Block Storage: 128 MB    │     │ Block Storage: 128 MB    │
    └──────────────────────────┘     └──────────────────────────┘
                 ▲                                 ▲
                 └────────────────┬────────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │  Spark Master (Port 8080) │
                    │  Driver RPC: 7077         │
                    └─────────────┬─────────────┘
                                  │
                 ┌────────────────┴────────────────┐
                 ▼                                 ▼
    ┌──────────────────────────┐     ┌──────────────────────────┐
    │ Spark Worker 1 (Port 8081)│     │ Spark Worker 2 (Port 8081)│
    │ Cores: 4, RAM: 8 GB      │     │ Cores: 4, RAM: 8 GB      │
    └──────────────────────────┘     └──────────────────────────┘
```

---

## 2. Starting the Cluster Stack with Docker

Use the pre-configured multi-container stack:
```bash
docker compose -f docker-compose.cluster.yml up -d
```

Verify service status:
```bash
docker compose -f docker-compose.cluster.yml ps
```

### Cluster Web Interfaces:
* **Hadoop HDFS NameNode Web UI**: `http://localhost:9870`
* **Hadoop HDFS DataNode Web UI**: `http://localhost:9864`
* **Spark Master UI**: `http://localhost:8081` (or `8080`)
* **Spark Worker UI**: `http://localhost:8082`

---

## 3. Ingesting Data into HDFS

Upload the access logs into the distributed filesystem:
```bash
# Create log directory inside HDFS
docker exec -it hadoop-namenode hdfs dfs -mkdir -p /logs/raw

# Copy server.log from local host to HDFS
docker cp server.log hadoop-namenode:/tmp/server.log
docker exec -it hadoop-namenode hdfs dfs -put /tmp/server.log /logs/raw/server.log

# Verify block placement and replication
docker exec -it hadoop-namenode hdfs dfs -ls -h /logs/raw/
docker exec -it hadoop-namenode hdfs fsck /logs/raw/server.log -files -blocks -locations
```

---

## 4. Submitting PySpark Batch Jobs to the Cluster

Submit the LogShield Lakehouse ETL to the Spark Master:
```bash
docker exec -it spark-master /spark/bin/spark-submit \
  --master spark://spark-master:7077 \
  --conf spark.executor.memory=2g \
  --conf spark.driver.memory=2g \
  /app/src/logshield/spark/etl.py
```

Results are stored back to HDFS in Parquet format at `/logs/lakehouse/gold/`.

---

## 5. Production Sizing Guide (4-Node Cluster Baseline)

For processing high-volume daily server logs:
* **Hardware Profile**: 4 Nodes × (8 CPU cores, 32 GB RAM, 2 TB Storage).
* **Usable Cores**: 7 per node (28 total cluster vcores).
* **Usable RAM**: 30 GB per node (120 GB total cluster memory).
* **Spark Executors**: 3 Worker Executors + 1 Driver Executor.
* **Per-Executor Memory**: 27 GB RAM + 2.7 GB overhead (`spark.yarn.executor.memoryOverhead`).
* **Shuffle Partitions**: 45 (`spark.sql.shuffle.partitions`).
