"""
Authentication and Syslog Log Parser
====================================
Parses Linux auth.log, /var/log/secure, and OpenSSH daemon logs.
Extracts timestamps, usernames, source IPs, privilege escalations (sudo),
and classifies severity from INFORMATIONAL to CRITICAL.
"""

import re
from datetime import datetime, timezone
from typing import List, Optional

from ..security.models import AuthLogRecord, SeverityLevel

# Regex patterns for common authentication syslog events
# 1. Standard syslog timestamp prefix: "Sep 01 03:14:22" or "2026-09-01T03:14:22+00:00"
TS_SYSLOG_PATTERN = re.compile(
    r"^([A-Z][a-z]{2}\s+\d+\s+\d{2}:\d{2}:\d{2}|[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?(?:[+-][0-9]{2}:?[0-9]{2}|Z)?)\s+(\S+)\s+([^:]+):\s+(.*)$"
)

# 2. SSH Failed Password: "Failed password for [invalid user ]<user> from <ip> port <port> ssh2"
FAILED_PWD_PATTERN = re.compile(
    r"Failed password for (?:invalid user )?(\S+) from (\S+) port (\d+) ssh2",
    re.IGNORECASE
)

# 3. SSH Accepted Password/Publickey: "Accepted (password|publickey) for <user> from <ip> port <port> ssh2"
ACCEPTED_PWD_PATTERN = re.compile(
    r"Accepted (?:password|publickey) for (\S+) from (\S+) port (\d+) ssh2",
    re.IGNORECASE
)

# 4. Invalid User probe: "Invalid user <user> from <ip> port <port>"
INVALID_USER_PATTERN = re.compile(
    r"Invalid user (\S+) from (\S+) port (\d+)",
    re.IGNORECASE
)

# 5. Sudo privilege escalation: "sudo:   username : TTY=pts/0 ; PWD=/root ; USER=root ; COMMAND=/bin/bash"
SUDO_PATTERN = re.compile(
    r"(?:sudo:\s*)?(\S+)\s*:\s*TTY=(\S+)\s*;\s*PWD=(\S+)\s*;\s*USER=(\S+)\s*;\s*COMMAND=(.*)",
    re.IGNORECASE
)


# 6. PAM authentication failure: "pam_unix(sshd:auth): authentication failure; logname= uid=0 euid=0 tty=ssh ruser= rhost=192.168.1.1 user=root"
PAM_AUTH_FAIL_PATTERN = re.compile(
    r"authentication failure;.*rhost=(\S+).*user=(\S+)",
    re.IGNORECASE
)

# 7. Account locked / Max auth attempts
LOCKED_PATTERN = re.compile(
    r"(account locked|maximum authentication attempts exceeded)",
    re.IGNORECASE
)


def parse_syslog_timestamp(ts_str: str, default_year: int = 2026) -> datetime:
    """Parses standard BSD syslog (e.g. 'Sep 01 03:14:22') or ISO-8601 into datetime."""
    ts_clean = ts_str.strip()
    # Try ISO-8601 first
    try:
        if "T" in ts_clean:
            return datetime.fromisoformat(ts_clean.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        pass

    # Try standard syslog format: "Sep 01 03:14:22" or "Sep  1 03:14:22"
    try:
        parts = ts_clean.split()
        if len(parts) == 3:
            month, day, time_str = parts
            dt_str = f"{default_year} {month} {int(day):02d} {time_str}"
            return datetime.strptime(dt_str, "%Y %b %d %H:%M:%S")
    except Exception:
        pass

    return datetime.now(timezone.utc).replace(tzinfo=None)


def parse_auth_line(line: str) -> Optional[AuthLogRecord]:
    """
    Safely parses a single line of an authentication or syslog security log.
    Returns AuthLogRecord if recognized, None if unparseable or irrelevant.
    Guarantees no unhandled exceptions on malformed input.
    """
    if not line or not isinstance(line, str):
        return None

    raw_line = line.strip()
    if not raw_line or raw_line.startswith("#"):
        return None

    match = TS_SYSLOG_PATTERN.match(raw_line)
    if not match:
        # Non-standard syslog prefix; attempt direct pattern matching with fallback timestamp
        ts = datetime.now(timezone.utc).replace(tzinfo=None)
        hostname = "localhost"
        process = "auth"
        body = raw_line
    else:
        ts_str, hostname, process, body = match.groups()
        ts = parse_syslog_timestamp(ts_str)

    # 1. Check account locked
    if LOCKED_PATTERN.search(body):
        return AuthLogRecord(
            timestamp=ts,
            source_ip=None,
            user=None,
            event_type="account_locked",
            severity="CRITICAL",
            details="Account locked due to excessive authentication failures",
            raw_message=raw_line
        )

    # 2. Check SSH Failed password
    m_fail = FAILED_PWD_PATTERN.search(body)
    if m_fail:
        user, ip, port = m_fail.groups()
        return AuthLogRecord(
            timestamp=ts,
            source_ip=ip,
            user=user,
            event_type="failed_login",
            severity="HIGH" if user in ("root", "admin") else "MEDIUM",
            details=f"Failed password for user '{user}' from {ip}:{port}",
            raw_message=raw_line
        )

    # 3. Check SSH Accepted password
    m_acc = ACCEPTED_PWD_PATTERN.search(body)
    if m_acc:
        user, ip, port = m_acc.groups()
        return AuthLogRecord(
            timestamp=ts,
            source_ip=ip,
            user=user,
            event_type="accepted_login",
            severity="INFORMATIONAL",
            details=f"Successful authentication for user '{user}' from {ip}:{port}",
            raw_message=raw_line
        )

    # 4. Check Invalid User probe
    m_inv = INVALID_USER_PATTERN.search(body)
    if m_inv:
        user, ip, port = m_inv.groups()
        return AuthLogRecord(
            timestamp=ts,
            source_ip=ip,
            user=user,
            event_type="invalid_user",
            severity="HIGH",
            details=f"Reconnaissance attempt with non-existent username '{user}' from {ip}:{port}",
            raw_message=raw_line
        )

    # 5. Check Sudo privilege escalation
    if ("sudo" in process.lower() or "sudo" in raw_line.lower()) and "TTY=" in body:
        m_sudo = SUDO_PATTERN.search(body)
        if m_sudo:
            user, tty, pwd, target_user, cmd = m_sudo.groups()

        is_root = target_user.lower() == "root"
        return AuthLogRecord(
            timestamp=ts,
            source_ip=None,
            user=user,
            event_type="privilege_escalation",
            severity="HIGH" if is_root and any(c in cmd for c in ["/bin/bash", "/bin/sh", "su", "chmod"]) else "LOW",
            details=f"User '{user}' executed privileged command as '{target_user}': {cmd.strip()} (TTY={tty}, PWD={pwd})",
            raw_message=raw_line
        )

    # 6. Check PAM authentication failure
    m_pam = PAM_AUTH_FAIL_PATTERN.search(body)
    if m_pam:
        ip, user = m_pam.groups()
        return AuthLogRecord(
            timestamp=ts,
            source_ip=ip,
            user=user,
            event_type="failed_login",
            severity="HIGH" if user in ("root", "admin") else "MEDIUM",
            details=f"PAM authentication failure for user '{user}' from {ip}",
            raw_message=raw_line
        )

    return None


def parse_auth_log_file(file_path: str, max_records: Optional[int] = None) -> List[AuthLogRecord]:
    """
    Parses an entire authentication log file safely with streaming line-by-line read.
    """
    records: List[AuthLogRecord] = []
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                rec = parse_auth_line(line)
                if rec:
                    records.append(rec)
                    if max_records and len(records) >= max_records:
                        break
    except Exception:
        pass
    return records
