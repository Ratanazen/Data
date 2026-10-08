"""
Security Rule Signatures & Behavioral Detection Patterns
"""

import re
from typing import Set

# Sensitive administrative and configuration probe routes
ADMIN_PROBE_ROUTES: Set[str] = {
    "/admin",
    "/admin/login",
    "/admin/config",
    "/wp-admin",
    "/wp-login.php",
    "/login",
    "/administrator",
    "/.env",
    "/.git",
    "/.git/config",
    "/config.json",
    "/actuator",
    "/actuator/health",
    "/phpmyadmin",
    "/server-status"
}

# Regex patterns for malicious path traversal, injection, and evasion
SUSPICIOUS_PATH_PATTERNS = [
    re.compile(r"\.\./"),                    # Directory traversal
    re.compile(r"etc/passwd", re.IGNORECASE), # Linux credential probe
    re.compile(r"boot\.ini", re.IGNORECASE),  # Windows system probe
    re.compile(r"\.git/", re.IGNORECASE),     # Exposed repository probe
    re.compile(r"\.env", re.IGNORECASE),      # Environment secret probe
    re.compile(r"union\s+select", re.IGNORECASE), # SQL injection probe
    re.compile(r"<script>", re.IGNORECASE),   # XSS probe
]

# Suspicious reconnaissance / vulnerability scanner user agents
SUSPICIOUS_UA_PATTERNS = [
    re.compile(r"sqlmap", re.IGNORECASE),
    re.compile(r"nikto", re.IGNORECASE),
    re.compile(r"nmap", re.IGNORECASE),
    re.compile(r"masscan", re.IGNORECASE),
    re.compile(r"acunetix", re.IGNORECASE),
    re.compile(r"zgrab", re.IGNORECASE),
]

def is_admin_or_sensitive_path(path: str) -> bool:
    """Checks whether the requested route targets sensitive management endpoints."""
    clean_path = path.split("?")[0].rstrip("/")
    if clean_path in ADMIN_PROBE_ROUTES or clean_path + "/" in ADMIN_PROBE_ROUTES:
        return True
    return any(clean_path.startswith(prefix) for prefix in ["/admin", "/wp-admin", "/.git", "/actuator"])

def matches_suspicious_path_signature(path: str) -> bool:
    """Checks whether the path contains traversal or injection signatures."""
    return any(p.search(path) is not None for p in SUSPICIOUS_PATH_PATTERNS)

def is_suspicious_user_agent(ua: str) -> bool:
    """Checks whether user-agent belongs to known automated reconnaissance scanners."""
    if not ua or ua == "-":
        return False
    return any(p.search(ua) is not None for p in SUSPICIOUS_UA_PATTERNS)
