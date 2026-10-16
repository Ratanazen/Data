"""Unit tests for LogShield CLI commands."""

import pytest

from src.logshield.cli.main import main


def test_cli_help(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
    captured = capsys.readouterr()
    assert "LogShield" in captured.out
    assert "Available subcommands" in captured.out


def test_cli_version(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    captured = capsys.readouterr()
    assert "LogShield v" in captured.out


def test_cli_no_args(capsys):
    code = main([])
    assert code == 0
    captured = capsys.readouterr()
    assert "LogShield" in captured.out


def test_cli_serve_help(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["serve", "--help"])
    assert exc.value.code == 0
    captured = capsys.readouterr()
    assert "usage: logshield serve" in captured.out
    assert "--open" in captured.out


def test_cli_batch_help(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["batch", "--help"])
    assert exc.value.code == 0
    captured = capsys.readouterr()
    assert "usage: logshield batch" in captured.out
    assert "--input" in captured.out


def test_module_aliases():
    from src.logshield.security.detectors import run_security_analysis, run_security_detection_pipeline
    from src.logshield.spark.bronze import run_bronze_ingestion, write_bronze_layer
    from src.logshield.spark.etl import run_full_etl_pipeline, run_pipeline
    from src.logshield.spark.gold import run_gold_aggregation, write_gold_layer
    from src.logshield.spark.silver import run_silver_transformation, write_silver_layer

    assert write_bronze_layer == run_bronze_ingestion
    assert write_silver_layer == run_silver_transformation
    assert write_gold_layer == run_gold_aggregation
    assert run_full_etl_pipeline == run_pipeline
    assert run_security_detection_pipeline == run_security_analysis
