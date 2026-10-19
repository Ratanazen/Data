"""
Configurable & Explainable Security Detection Rules Engine
===========================================================
Applies empirical detection rules across parsed authentication logs and HTTP access logs.
Features sliding time-window evaluation, user-configurable thresholds, and transparent
forensic explanations distinguishing detected behavioral patterns from confirmed incidents.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from .models import AuthLogRecord, DetectionRule, SecurityEvent, SeverityLevel


class DetectionRulesEngine:
    """
    Central rules engine managing cybersecurity detection policies.
    """

    def __init__(self):
        self.rules: Dict[str, DetectionRule] = {
            "RULE-AUTH-001": DetectionRule(
                rule_id="RULE-AUTH-001",
                name="Brute-Force Authentication Attempt",
                description="Detects repeated authentication failures from the same source IP within a sliding time window.",
                category="Authentication",
                severity="HIGH",
                threshold=5,
                window_seconds=180,
                enabled=True,
                trigger_count=0
            ),
            "RULE-ENUM-001": DetectionRule(
                rule_id="RULE-ENUM-001",
                name="Account Enumeration Probing",
                description="Detects attempts targeting multiple distinct usernames from a single source IP.",
                category="Authentication",
                severity="HIGH",
                threshold=3,
                window_seconds=300,
                enabled=True,
                trigger_count=0
            ),
            "RULE-PRIV-001": DetectionRule(
                rule_id="RULE-PRIV-001",
                name="Suspicious Privilege Escalation",
                description="Identifies sudo execution of interactive shells, security bypass tools, or permission modifications.",
                category="Privilege",
                severity="HIGH",
                threshold=1,
                window_seconds=60,
                enabled=True,
                trigger_count=0
            ),
            "RULE-TRAV-001": DetectionRule(
                rule_id="RULE-TRAV-001",
                name="Directory Traversal / Sensitive File Access",
                description="Flags attempts to read sensitive operating system or credential files (e.g., ../, /etc/passwd, .env).",
                category="Reconnaissance",
                severity="CRITICAL",
                threshold=1,
                window_seconds=60,
                enabled=True,
                trigger_count=0
            ),
            "RULE-ADMIN-001": DetectionRule(
                rule_id="RULE-ADMIN-001",
                name="Automated Admin Endpoint Scanning",
                description="Detects high-volume probing targeting administrative routes (/admin, /wp-admin, /actuator).",
                category="Reconnaissance",
                severity="MEDIUM",
                threshold=8,
                window_seconds=120,
                enabled=True,
                trigger_count=0
            ),
            "RULE-404-001": DetectionRule(
                rule_id="RULE-404-001",
                name="Excessive 404 Resource Probing",
                description="Identifies client IPs generating disproportionate 404 Not Found error responses.",
                category="Reconnaissance",
                severity="MEDIUM",
                threshold=50,
                window_seconds=3600,
                enabled=True,
                trigger_count=0
            )
        }

    def list_rules(self) -> List[DetectionRule]:
        """Returns all configured detection rules."""
        return list(self.rules.values())

    def get_rule(self, rule_id: str) -> Optional[DetectionRule]:
        """Retrieves a specific rule by ID."""
        return self.rules.get(rule_id.upper())

    def update_rule(
        self,
        rule_id: str,
        threshold: Optional[int] = None,
        window_seconds: Optional[int] = None,
        enabled: Optional[bool] = None,
        severity: Optional[SeverityLevel] = None
    ) -> Optional[DetectionRule]:
        """Dynamically updates rule configuration and thresholds."""
        rule = self.rules.get(rule_id.upper())
        if not rule:
            return None
        if threshold is not None:
            rule.threshold = max(1, threshold)
        if window_seconds is not None:
            rule.window_seconds = max(1, window_seconds)
        if enabled is not None:
            rule.enabled = enabled
        if severity is not None:
            rule.severity = severity
        return rule

    def evaluate_auth_logs(self, records: List[AuthLogRecord]) -> List[SecurityEvent]:
        """
        Evaluates a sequence of AuthLogRecords against enabled detection rules.
        Distinguishes detected behavioral patterns from confirmed security incidents.
        """
        events: List[SecurityEvent] = []
        if not records:
            return events

        # Sort records chronologically
        sorted_records = sorted(records, key=lambda r: r.timestamp)

        rule_auth = self.rules.get("RULE-AUTH-001")
        rule_enum = self.rules.get("RULE-ENUM-001")
        rule_priv = self.rules.get("RULE-PRIV-001")

        # 1. Evaluate sliding window brute force login per IP
        if rule_auth and rule_auth.enabled:
            ip_fails: Dict[str, List[AuthLogRecord]] = {}
            for r in sorted_records:
                if r.event_type == "failed_login" and r.source_ip:
                    ip_fails.setdefault(r.source_ip, []).append(r)

            for ip, fails in ip_fails.items():
                # Sliding window check
                window_delta = timedelta(seconds=rule_auth.window_seconds)
                for i in range(len(fails)):
                    start_time = fails[i].timestamp
                    end_time = start_time + window_delta
                    window_hits = [f for f in fails[i:] if f.timestamp <= end_time]
                    if len(window_hits) >= rule_auth.threshold:
                        target_users = list({f.user for f in window_hits if f.user})
                        rule_auth.trigger_count += 1
                        events.append(SecurityEvent(
                            timestamp=window_hits[-1].timestamp,
                            ip=ip,
                            event_type=rule_auth.name,
                            severity=rule_auth.severity,
                            risk_score=min(95, 50 + len(window_hits) * 3),
                            evidence=f"Rule {rule_auth.rule_id} triggered: Observed {len(window_hits)} failed logins within {rule_auth.window_seconds}s (Threshold: {rule_auth.threshold}). Target user(s): {', '.join(target_users) or 'unknown'}",
                            request_count=len(window_hits),
                            recommendation=f"Enforce temporary WAF rate-limiting or fail2ban jail for IP {ip}",
                            is_confirmed_incident=False  # Clearly flagged as detected pattern
                        ))
                        break  # Alert once per incident window for this IP

        # 2. Evaluate Account Enumeration
        if rule_enum and rule_enum.enabled:
            ip_inv_users: Dict[str, List[AuthLogRecord]] = {}
            for r in sorted_records:
                if r.event_type in ("invalid_user", "failed_login") and r.source_ip and r.user:
                    ip_inv_users.setdefault(r.source_ip, []).append(r)

            for ip, attempts in ip_inv_users.items():
                unique_users = {a.user for a in attempts}
                if len(unique_users) >= rule_enum.threshold:
                    rule_enum.trigger_count += 1
                    events.append(SecurityEvent(
                        timestamp=attempts[-1].timestamp,
                        ip=ip,
                        event_type=rule_enum.name,
                        severity=rule_enum.severity,
                        risk_score=min(90, 45 + len(unique_users) * 5),
                        evidence=f"Rule {rule_enum.rule_id} triggered: Probed {len(unique_users)} distinct usernames from {ip} (Threshold: {rule_enum.threshold}). Users: {', '.join(sorted(unique_users)[:5])}",
                        request_count=len(attempts),
                        recommendation=f"Audit authentication gateway logs and challenge IP {ip} with multi-factor authentication",
                        is_confirmed_incident=False
                    ))

        # 3. Evaluate Privilege Escalation
        if rule_priv and rule_priv.enabled:
            for r in sorted_records:
                if r.event_type == "privilege_escalation" and r.severity in ("HIGH", "CRITICAL"):
                    rule_priv.trigger_count += 1
                    events.append(SecurityEvent(
                        timestamp=r.timestamp,
                        ip=r.source_ip or "127.0.0.1",
                        event_type=rule_priv.name,
                        severity=r.severity,
                        risk_score=85,
                        evidence=f"Rule {rule_priv.rule_id} triggered: Privileged execution by '{r.user}': {r.details}",
                        request_count=1,
                        recommendation="Review user sudoers policy and verify whether root elevation was authorized in change-management ticket",
                        is_confirmed_incident=False
                    ))

        return events


# Global singleton engine instance
default_rules_engine = DetectionRulesEngine()
