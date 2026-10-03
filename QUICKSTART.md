# ⚡ Quick Start: Clone & Run Guide

Get the **Hadoop & PySpark 404 Log File Analytics** running on your local machine in under 60 seconds!

---

## 📥 Step 1: Clone the Repository

Open your terminal or command prompt:

```bash
git clone https://github.com/Ratanazen/Data.git
cd Data
```

---

## 🚀 Step 2: Run by Operating System

### 🪟 Windows Users

#### Option 1: 1-Click Double Click (Easiest)
In File Explorer, simply **double-click** [`run.bat`](run.bat).  
It will automatically test the environment, build all data deliverables, and launch the Web Dashboard in your browser!

#### Option 2: Command Prompt (`cmd`)
```cmd
REM Install dependencies (first time only)
pip install -r requirements.txt

REM Run full verification & build pipeline
build.bat all

REM Start the Web Dashboard on http://localhost:8080/
build.bat web
```

#### Option 3: PowerShell
```powershell
# Install dependencies
pip install -r requirements.txt

# Run full pipeline & launch dashboard
.\build.ps1 all
.\build.ps1 web
```

---

### 🍎 macOS Users

Open Terminal inside the cloned repository folder:

```bash
# 1. Setup virtual environment & dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Run full check, tests, and build
./build.sh all

# 3. Launch the Web Dashboard
./build.sh web
```

*Or simply use `make`:*
```bash
make install
make all
make web
```

---

### 🐧 Linux Users

```bash
# 1. Setup virtual environment & dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Run full pipeline
./build.sh all

# 3. Launch Web Dashboard
./build.sh web
```

---

### 🐳 Docker (Zero Setup on Any System)

If you have Docker installed, you don't even need Python installed locally:

```bash
docker compose up --build
```
Open **[http://localhost:8080/](http://localhost:8080/)** in your browser!

---

## 🧪 Step 3: Run Automated Tests

To verify that all 10 unit tests pass on your machine:

```bash
# Cross-platform test command
python -m unittest tests/test_analysis.py -v
```

---

## 🌐 Deliverables Overview

Once started, open **[http://localhost:8080/](http://localhost:8080/)** to access:
- **📊 24-Hour Failure Distribution Chart** (Highlighting 03:00 AM peak)
- **🗺️ 7×24 Day vs. Hour Heatmap** (With interactive cell hover inspector)
- **🎯 Top 10 Broken Endpoints Bar Chart**
- **🔎 Live Log Explorer** (Instant search, quick filter chips, and CSV export)
- **📄 Written Executive Report**: View via `http://localhost:8080/Log_File_Analysis_Report.html`
