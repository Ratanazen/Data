"""Unit tests for Linux auth.log, secure, and SSH syslog parser."""

from src.logshield.ingestion.syslog_auth_parser import (
    parse_auth_line,
    parse_auth_log_file,
    parse_syslog_timestamp,
)


def test_parse_ssh_failed_password():
    line = "Sep 01 03:14:22 web01 sshd[4912]: Failed password for invalid user admin from 192.168.1.100 port 45212 ssh2"
    rec = parse_auth_line(line)
    assert rec is not None
    assert rec.event_type == "failed_login"
    assert rec.source_ip == "192.168.1.100"
    assert rec.user == "admin"
    assert rec.severity == "HIGH"
    assert "admin" in rec.details


def test_parse_ssh_accepted_password():
    line = "Sep 01 03:16:45 web01 sshd[5011]: Accepted publickey for secops from 10.0.5.2 port 51234 ssh2"
    rec = parse_auth_line(line)
    assert rec is not None
    assert rec.event_type == "accepted_login"
    assert rec.source_ip == "10.0.5.2"
    assert rec.user == "secops"
    assert rec.severity == "INFORMATIONAL"


def test_parse_invalid_user_probe():
    line = "Sep 01 03:18:10 web01 sshd[5100]: Invalid user testuser from 203.0.113.88 port 33412"
    rec = parse_auth_line(line)
    assert rec is not None
    assert rec.event_type == "invalid_user"
    assert rec.user == "testuser"
    assert rec.source_ip == "203.0.113.88"
    assert rec.severity == "HIGH"


def test_parse_sudo_privilege_escalation():
    line = "Sep 01 03:20:00 web01 sudo:   analyst : TTY=pts/2 ; PWD=/home/analyst ; USER=root ; COMMAND=/bin/bash"
    rec = parse_auth_line(line)
    assert rec is not None
    assert rec.event_type == "privilege_escalation"
    assert rec.user == "analyst"
    assert rec.severity == "HIGH"
    assert "/bin/bash" in rec.details


def test_parse_account_locked():
    line = "Sep 01 03:25:00 web01 login[6012]: account locked due to 10 failed logins"
    rec = parse_auth_line(line)
    assert rec is not None
    assert rec.event_type == "account_locked"
    assert rec.severity == "CRITICAL"


def test_parse_pam_failure():
    line = "Sep 01 03:28:15 web01 sshd[6120]: pam_unix(sshd:auth): authentication failure; logname= uid=0 euid=0 tty=ssh ruser= rhost=198.51.100.99 user=root"
    rec = parse_auth_line(line)
    assert rec is not None
    assert rec.event_type == "failed_login"
    assert rec.user == "root"
    assert rec.source_ip == "198.51.100.99"
    assert rec.severity == "HIGH"


def test_safe_parsing_on_malformed_input():
    # Empty string
    assert parse_auth_line("") is None
    # Comment line
    assert parse_auth_line("# This is a comment") is None
    # None input
    assert parse_auth_line(None) is None  # type: ignore
    # Random unformatted line
    assert parse_auth_line("random unformatted system message without match") is None


def test_parse_syslog_timestamp():
    dt = parse_syslog_timestamp("Sep 01 03:14:22", default_year=2026)
    assert dt.year == 2026
    assert dt.month == 9
    assert dt.day == 1
    assert dt.hour == 3
    assert dt.minute == 14
    assert dt.second == 22
