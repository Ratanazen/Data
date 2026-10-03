# ==============================================================================
# Makefile for Assignment 2: Log File Analysis (Hadoop & PySpark)
# ==============================================================================

SHELL := /bin/bash
PYTHON := $(shell if [ -f .venv/bin/python ]; then echo .venv/bin/python; elif command -v python3 >/dev/null 2>&1; then echo python3; else echo python; fi)
PORT ?= 8080

.DEFAULT_GOAL := help

.PHONY: help
help: ## Show this interactive help screen
	@echo "======================================================================"
	@echo "  📊 LOG FILE ANALYSIS PIPELINE (HADOOP & PYSPARK) — MAKEFILE"
	@echo "======================================================================"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'
	@echo "======================================================================"

.PHONY: install
install: ## Create virtualenv and install dependencies
	@echo "[*] Setting up virtual environment and packages..."
	@if command -v uv >/dev/null 2>&1; then \
		uv venv --python 3.11 .venv && uv pip install --python .venv/bin/python -r requirements.txt; \
	else \
		python3 -m venv .venv && .venv/bin/pip install -r requirements.txt; \
	fi
	@echo "[✓] Environment configured."

.PHONY: check
check: ## Verify environment, dependencies, log file integrity, and deliverables
	@./build.sh check

.PHONY: run build
run: build
build: ## Execute data pipeline, regenerate CSVs, charts, and web feed
	@echo "[*] Running analysis pipeline..."
	@$(PYTHON) run_analysis.py
	@$(PYTHON) export_report.py
	@echo "[✓] Build complete."

.PHONY: web serve
web: serve
serve: ## Launch the interactive Web Dashboard (default port: 8080)
	@$(PYTHON) serve.py $(PORT)

.PHONY: report
report: ## Regenerate standalone HTML report
	@$(PYTHON) export_report.py
	@echo "[✓] Log_File_Analysis_Report.html regenerated."

.PHONY: test
test: ## Run automated unit tests suite
	@$(PYTHON) -m unittest discover -s tests -p "test_*.py"

.PHONY: clean
clean: ## Safely remove caches, temporary files, and checkpoints
	@echo "[*] Cleaning temporary files and caches..."
	@rm -rf __pycache__ tests/__pycache__ .pytest_cache *.pyc
	@echo "[✓] Clean completed."

.PHONY: docker-build
docker-build: ## Build Docker container image
	@docker build -t log-analytics-dashboard:latest .

.PHONY: docker-run
docker-run: ## Run dashboard inside Docker container
	@docker run --rm -p $(PORT):8080 --name log-analytics-dashboard log-analytics-dashboard:latest

.PHONY: docker-stop
docker-stop: ## Stop Docker container
	@docker stop log-analytics-dashboard || true

.PHONY: all
all: clean check test build ## Run full sequence: clean, check, test, and build
	@echo "[✓] All pipeline stages verified successfully!"
