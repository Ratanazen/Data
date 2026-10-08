"""Integration tests for LogShield ingestion and parsing pipeline."""

from pathlib import Path

from src.logshield.ingestion.log_reader import LogReader


def test_fixture_ingestion(tmp_path):
    fixture_path = Path(__file__).resolve().parent.parent / "fixtures" / "sample.log"
    assert fixture_path.is_file()

    reader = LogReader(quarantine_dir=tmp_path / "quarantine")
    valid_records = list(reader.read_file(fixture_path))

    assert len(valid_records) == 10
    assert reader.stats["records_invalid"] == 0

    ips = [r.ip for r in valid_records]
    assert "10.0.12.45" in ips
    assert "10.0.11.83" in ips

    statuses = [r.status for r in valid_records]
    assert 404 in statuses
    assert 200 in statuses
    assert 403 in statuses
    assert 500 in statuses
