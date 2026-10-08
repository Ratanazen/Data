# ⚙️ LogShield Installation & Setup Guide

This guide provides step-by-step instructions for installing and running LogShield on Linux, macOS, and Windows.

---

## 1. System Requirements

* **Python**: 3.9+ (Python 3.11 recommended)
* **Java Runtime**: OpenJDK 11 or 17 (Required for Apache Spark / PySpark)
* **Memory**: Minimum 4 GB RAM (8 GB+ recommended for Spark batch operations)
* **Storage**: 1 GB free disk space
* **Optional**: Docker & Docker Compose (for containerized Hadoop cluster and Kafka streaming)

Verify Java installation:
```bash
java -version
```
If Java is not installed:
* **Ubuntu/Debian**: `sudo apt install -y default-jre`
* **macOS**: `brew install openjdk@17`
* **Windows**: Download OpenJDK from [Adoptium](https://adoptium.net/).

---

## 2. Clone and Setup Environment

### Clone the Repository:
```bash
git clone https://github.com/Ratanazen/Data.git logshield
cd logshield
```

### Create and Activate Virtual Environment:
```bash
# On Linux / macOS:
python3 -m venv .venv
source .venv/bin/activate

# On Windows (cmd.exe):
python -m venv .venv
.venv\Scripts\activate.bat

# On Windows (PowerShell):
.venv\Scripts\Activate.ps1
```

### Install Dependencies:
```bash
pip install -r requirements.txt
```

### Configure Environment Variables:
Copy the template configuration:
```bash
cp .env.example .env
```
Default parameters in `.env`:
```ini
APP_ENV=development
MODE=local
LOG_LEVEL=INFO
RAW_LOG_PATH=server.log
DATA_ROOT=data
API_HOST=0.0.0.0
API_PORT=8000
DASHBOARD_PORT=8080
```

---

## 3. Verify Installation

Run the automated test suite:
```bash
pytest
```
Expected output:
```
37 passed in 1.2s
```

Test the unified CLI:
```bash
python -m logshield --help
python -m logshield --version
```

---

## 4. Run the Pipeline in 10 Seconds

Execute the full batch Lakehouse processing pipeline:
```bash
python -m logshield batch
```
This generates:
- `data/bronze/` (Raw partitioned Parquet)
- `data/silver/` (Cleaned partitioned Parquet)
- `data/gold/` (7 Analytical Gold tables + KPIs)
- `data/gold/gold_security_events.parquet` (Security incidents)

Start the Web Dashboard & API:
```bash
# Terminal 1: FastAPI REST API
python -m logshield serve api --port 8000

# Terminal 2: Web Dashboard
python -m logshield serve dashboard --port 8080
```
Open your browser to:
- **Interactive Dashboard**: `http://localhost:8080/`
- **FastAPI Interactive Docs**: `http://localhost:8000/docs`
