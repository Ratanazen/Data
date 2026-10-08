# 🛠️ LogShield Troubleshooting Guide

This document lists common operational issues, diagnostics, and resolutions.

---

## 1. PyArrow Legacy Dataset Parameter Error

### Symptom:
```
TypeError: ParquetDataset.__init__() got an unexpected keyword argument 'use_legacy_dataset'
```

### Cause:
PyArrow version 15.0+ and 25.0+ completely deprecated and removed the `use_legacy_dataset` argument.

### Resolution:
Replace `pq.ParquetDataset(path, use_legacy_dataset=False)` with direct table reads:
```python
import pyarrow.parquet as pq
table = pq.read_table(str(file_or_dir_path))
df = table.to_pandas()
```
LogShield codebase has already been modernized to use `pq.read_table()`.

---

## 2. Java / PySpark Gateway Error

### Symptom:
```
py4j.protocol.Py4JNetworkError: An error occurred while trying to connect to the Java server (127.0.0.1:...)
```

### Cause:
Java is missing from system `$PATH`, or Java version is incompatible (Java 8 vs 17).

### Resolution:
1. Verify Java is installed:
   ```bash
   java -version
   ```
2. Set `JAVA_HOME`:
   ```bash
   # Linux (Ubuntu)
   export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
   export PATH=$JAVA_HOME/bin:$PATH
   ```

---

## 3. Windows Terminal Character Encoding (cp1252)

### Symptom:
```
UnicodeEncodeError: 'charmap' codec can't encode characters in position ...: character maps to <undefined>
```

### Cause:
Windows console output defaults to code page 1252 instead of UTF-8 when printing unicode icons (e.g. `✓`, `🚀`).

### Resolution:
Set the Windows console output encoding in your script or shell:
```bash
set PYTHONIOENCODING=utf-8
chcp 65001
```
Or in Python:
```python
import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
```
LogShield scripts include this auto-reconfiguration.

---

## 4. Port Conflict on 8000 or 8080

### Symptom:
```
OSError: [Errno 98] Address already in use
```

### Resolution:
Identify and terminate the occupying process, or use another port:
```bash
# Check what is listening on 8080:
lsof -i :8080
kill -9 <PID>

# Or start on alternative ports:
python -m logshield serve api --port 8001
python -m logshield serve dashboard --port 8081
```

---

## 5. Corrupt / Malformed Log Records

### Symptom:
Certain dirty access logs fail standard regex matching.

### Resolution:
LogShield features an automatic fault-tolerant quarantine mechanism. Corrupted lines are written to `data/quarantine/quarantine_YYYYMMDD.jsonl` with exact file name, line number, and rejection reason, allowing the primary lakehouse pipeline to continue uninterrupted.
