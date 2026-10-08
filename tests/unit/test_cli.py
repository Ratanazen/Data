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
