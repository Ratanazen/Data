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
* **CRITICAL (75 – 100)**: Active malicious exploitation (traversal, high-volume brute-force). Requires immediate firewall isolation.
* **HIGH (50 – 74)**: Persistent scanning of protected admin routes and configuration files.
* **MEDIUM (25 – 49)**: Suspicious error spikes, unmapped route probing.
* **LOW (0 – 24)**: Standard benign client traffic, occasional 404 broken link hits.

---

## 3. Automated Remediation Output

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

## 4. Benchmark Results on 200,000 Records

From the baseline dataset of 200,000 access log records:
* **Total Security Incidents Flagged**: 494 events.
* **Unique Threat Actor IPs Identified**: 50 IPs.
* **Highest Recorded Risk Score**: 95 / 100.
* **Dominant Attack Vector**: Admin Probing & Overnight Bot Scanning during 02:00–04:00 AM UTC.
