# 👨‍💻 LogShield Developer Guide

This guide describes development workflows, testing practices, code quality standards, and extension points for contributing to LogShield.

---

## 1. Project Organization

```
Assignment2/
├── .env.example              # Environment variables template
├── docker-compose.yml        # Development Docker Compose (Dashboard + API)
├── docker-compose.cluster.yml# Hadoop + PySpark Cluster stack
├── docker-compose.streaming.yml # Kafka + KRaft + Kafka UI stack
├── pyproject.toml            # Project packaging & dependencies
├── requirements.txt          # Frozen dependency specifications
├── index.html                # LogShield Dashboard V2 UI
├── server.log                # Primary benchmark log dataset (200,000 records)
├── src/
│   └── logshield/
│       ├── __init__.py       # Package version & metadata
│       ├── __main__.py       # Entry point for python -m logshield
│       ├── config/           # Pydantic Settings & environment loader
│       ├── ingestion/        # Apache, Nginx, JSON parsers & validator
│       ├── spark/            # Session factory, Bronze, Silver, Gold ETL
│       ├── security/         # Threat detection, rules, risk calculator
│       ├── api/              # FastAPI REST endpoints & schemas
│       ├── streaming/        # Kafka producer, consumer, PySpark streaming
│       ├── cli/              # Unified CLI subcommands
│       └── utils/            # Logging and formatting utilities
├── scripts/
│   └── generate_logs.py      # Synthetic log generator
├── notebooks/                # Interactive exploratory notebooks
├── tests/
│   ├── fixtures/             # Sample fixture log files
│   ├── unit/                 # Unit tests (parsers, validators, security, API)
│   ├── integration/          # Ingestion and end-to-end integration tests
│   └── test_analysis.py      # Baseline legacy test suite (14 tests)
└── docs/                     # Comprehensive architecture and operations docs
```

---

## 2. Running the Test Suite

LogShield uses `pytest` for automated regression testing:

```bash
# Run all tests (unit, integration, legacy)
pytest -v

# Run only unit tests
pytest tests/unit -v

# Run legacy regression suite
pytest tests/test_analysis.py -v
```

---

## 3. Adding a New Log Parser

1. Create a parser module in `src/logshield/ingestion/` (e.g. `caddy_parser.py`).
2. Implement `parse_caddy_line(line: str) -> Optional[ParsedLogRecord]`.
3. Register the new parser inside `LogReader._parse_line` in `src/logshield/ingestion/log_reader.py`.
4. Add unit test coverage in `tests/unit/test_parsers.py`.

---

## 4. Adding a New Security Detection Rule

1. Open `src/logshield/security/rules.py`.
2. Add regex pattern or route match definition.
3. Update `RiskCalculator.evaluate_profile()` in `src/logshield/security/risk.py` with appropriate penalty weighting.
4. Add unit test in `tests/unit/test_security.py`.

---

## 5. Code Style & Linting

LogShield enforces clean, PEP 8-compliant Python code:
```bash
ruff check .
```
Fix auto-fixable issues:
```bash
ruff check --fix .
```
