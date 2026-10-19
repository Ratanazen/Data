# 🛡️ LogShield Security Analytics & Threat Detection

LogShield incorporates an empirical, deterministic threat detection engine that evaluates every client IP against known threat patterns.

---

## 1. Threat Detection Taxonomy

| Attack Vector | Indicator Pattern | Risk Penalty | Mitigation |
|---|---|---|---|
| **Brute-Force Login** | Rapid requests to `/admin/login`, `/wp-login.php`, etc. | +30 to +45 | Rate limit or temporary IP ban |
| **Directory Traversal** | Path containing `../`, `/etc/passwd`, `/boot.ini` | +50 | Immediate WAF Drop rule |
| **Sensitive File Probing** | Access to `/.env`, `/.git`, `/config.json`, `/actuator` | +35 | Block IP & audit perimeter ACLs |
| **Vulnerability Scanning** | User-Agents matching `sqlmap`, `nikto`, `masscan` | +30 | Blacklist User-Agent / Drop IP |
| **High Error Ratio** | Client 4xx error rate > 30% of their total volume | +15 to +25 | Captcha challenge / rate throttle |
| **Volume Spikes** | Request frequency > 3.0× baseline standard deviation | +20 | Nginx `limit_req` connection burst |

---

## 2. Risk Scoring Algorithm

Risk scores are strictly bounded between **0 and 100**:
$$\text{Risk Score} = \min\left(100, \sum \text{Penalties}\right)$$

### Operational Severity Bands:
* **CRITICAL (75 – 100)**: Active malicious exploitation (traversal, high-volume brute-force, account locking). Requires immediate firewall isolation.
* **HIGH (50 – 74)**: Persistent scanning of protected admin routes, SSH password failure spikes, unauthorized sudo privilege elevation.
* **MEDIUM (25 – 49)**: Suspicious error spikes, unmapped route probing, repeated invalid username checks.
* **LOW (1 – 24)**: Standard benign client traffic, occasional 404 broken link hits, authorized routine sudo usage.
* **INFORMATIONAL (0)**: Routine successful authentication (`accepted_login`), health probes, standard telemetry records.

---

## 3. Configurable & Explainable Detection Rules Engine

LogShield features an empirical, rule-based detection engine that analyzes sliding time windows and provides transparent forensic justifications:

| Rule ID | Rule Name | Category | Default Threshold | Window | Severity | Trigger Description |
|:---|:---|:---|:---:|:---:|:---:|:---|
| `RULE-AUTH-001` | Brute-Force Auth Attempt | Authentication | 5 failures | 180s | `HIGH` | Repeated login failures from single IP |
| `RULE-ENUM-001` | Account Enumeration | Authentication | 3 usernames | 300s | `HIGH` | Probing multiple distinct usernames from single IP |
| `RULE-PRIV-001` | Privilege Escalation | Privilege | 1 occurrence | 60s | `HIGH` | Sudo execution of shells, `/bin/cat /etc/shadow`, or root switches |
| `RULE-TRAV-001` | Directory Traversal | Reconnaissance | 1 occurrence | 60s | `CRITICAL` | Signatures for `../`, `/etc/passwd`, `/.env`, `boot.ini` |
| `RULE-ADMIN-001` | Admin Endpoint Scan | Reconnaissance | 8 hits | 120s | `MEDIUM` | Rapid queries to `/admin`, `/wp-admin`, `/actuator` |
| `RULE-404-001` | Excessive 404 Probing | Reconnaissance | 50 hits | 3600s | `MEDIUM` | High-frequency 404 Not Found generation |

> [!NOTE]
> **Behavioral Pattern vs. Confirmed Incident:**
> The LogShield rules engine explicitly flags detected anomalies as *behavioral patterns* (`is_confirmed_incident = False`) until verified through SOC analyst triage, preventing premature or unfounded attribution.

---

## 4. Multi-Format Security Log Parsing

In addition to Apache CLF/Combined and Nginx HTTP access logs, LogShield supports standard Linux `auth.log` and OpenSSH syslog formats:
- **SSH Password Failures**: `Failed password for [invalid user] <user> from <ip>`
- **SSH Successful Authentication**: `Accepted password/publickey for <user> from <ip>`
- **Privilege Escalation**: `sudo: <user> : TTY=... ; COMMAND=...`
- **Account Lockouts**: `account locked due to N failed logins`
- **PAM Failures**: `pam_unix(sshd:auth): authentication failure`

---

## 5. Defensive Security Utilities

### 1. Cryptographic File Integrity Verification (`FileIntegrityChecker`)
Computes dual **SHA-256** and **MD5** checksums across raw logs, analytical summaries, and Hadoop cluster configs:
```python
from src.logshield.security import FileIntegrityChecker

record = FileIntegrityChecker.audit_file("server.log")
print(f"Status: {record.status} | SHA-256: {record.sha256}")
```
Output manifest is persisted at [`integrity_manifest.json`](../integrity_manifest.json).

### 2. Confidential Log Sanitizer (`LogSanitizer`)
Automatically scrubs credentials, passwords (`password=***`), OAuth bearer tokens (`Bearer [REDACTED_AUTH]`), API keys, and session cookies prior to export or sharing:
```python
from src.logshield.security import LogSanitizer

clean_text = LogSanitizer.sanitize_content(raw_log_string)
```

### 3. Safe File Upload Inspector (`SafeFileAnalyzer`)
Enforces maximum 50MB file size bounds, strips path traversal components from filenames, and inspects binary byte markers to reject executable injection.

---

## 6. Automated Remediation Output

For every detected security incident, LogShield generates copyable remediation rules:

### Linux `iptables` Rule:
```bash
iptables -A INPUT -s 10.0.15.95 -j DROP -m comment --comment "LogShield WAF Drop"
```

### `fail2ban` Command:
```bash
fail2ban-client set apache-auth banip 10.0.15.95
```

### Nginx Rate-Limiting Directive:
```nginx
limit_req_zone $binary_remote_addr zone=login_limit:10m rate=5r/m;
```

---

## 7. Benchmark Results on 200,000 Records

From the baseline dataset of 200,000 access log records:
* **Total Security Incidents Flagged**: 494 events.
* **Unique Threat Actor IPs Identified**: 50 IPs.
* **Highest Recorded Risk Score**: 95 / 100.
* **Dominant Attack Vector**: Admin Probing & Overnight Bot Scanning during 02:00–04:00 AM UTC.
* **Automated Test Coverage**: 67/67 Pytest tests passing (100% test pass rate).
