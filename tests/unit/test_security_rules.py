"""Unit tests for DetectionRulesEngine, configurable thresholds, and explainability."""

from datetime import datetime, timedelta

from src.logshield.security.detection_engine import DetectionRulesEngine
from src.logshield.security.models import AuthLogRecord


def test_rules_engine_listing_and_lookup():
    engine = DetectionRulesEngine()
    rules = engine.list_rules()
    assert len(rules) >= 5

    rule_auth = engine.get_rule("RULE-AUTH-001")
    assert rule_auth is not None
    assert rule_auth.category == "Authentication"
    assert rule_auth.threshold == 5
    assert rule_auth.window_seconds == 180


def test_rules_engine_threshold_update():
    engine = DetectionRulesEngine()
    updated = engine.update_rule("RULE-AUTH-001", threshold=3, window_seconds=60, enabled=False)
    assert updated is not None
    assert updated.threshold == 3
    assert updated.window_seconds == 60
    assert updated.enabled is False

    # Lookup reflects change
    rule = engine.get_rule("RULE-AUTH-001")
    assert rule.threshold == 3
    assert rule.enabled is False


def test_brute_force_sliding_window_detection():
    engine = DetectionRulesEngine()
    engine.update_rule("RULE-AUTH-001", threshold=3, window_seconds=120, enabled=True)

    base_time = datetime(2026, 9, 1, 3, 15, 0)
    records = [
        AuthLogRecord(
            timestamp=base_time + timedelta(seconds=10),
            source_ip="192.168.1.50",
            user="root",
            event_type="failed_login",
            severity="HIGH",
            details="Failed password for root",
            raw_message="Failed password for root from 192.168.1.50 port 22"
        ),
        AuthLogRecord(
            timestamp=base_time + timedelta(seconds=20),
            source_ip="192.168.1.50",
            user="root",
            event_type="failed_login",
            severity="HIGH",
            details="Failed password for root",
            raw_message="Failed password for root from 192.168.1.50 port 22"
        ),
        AuthLogRecord(
            timestamp=base_time + timedelta(seconds=35),
            source_ip="192.168.1.50",
            user="admin",
            event_type="failed_login",
            severity="HIGH",
            details="Failed password for admin",
            raw_message="Failed password for admin from 192.168.1.50 port 22"
        ),
    ]

    events = engine.evaluate_auth_logs(records)
    assert len(events) >= 1
    event = events[0]
    assert event.ip == "192.168.1.50"
    assert "RULE-AUTH-001" in event.evidence
    assert event.is_confirmed_incident is False  # Explicitly distinguished from confirmed incident
    assert event.risk_score >= 50


def test_account_enumeration_detection():
    engine = DetectionRulesEngine()
    engine.update_rule("RULE-AUTH-001", enabled=False)  # Isolate enumeration rule
    engine.update_rule("RULE-ENUM-001", threshold=3, window_seconds=300, enabled=True)

    base_time = datetime(2026, 9, 1, 3, 20, 0)
    records = [
        AuthLogRecord(
            timestamp=base_time + timedelta(seconds=5),
            source_ip="203.0.113.10",
            user="alice",
            event_type="invalid_user",
            severity="HIGH",
            details="Invalid user alice",
            raw_message="Invalid user alice"
        ),
        AuthLogRecord(
            timestamp=base_time + timedelta(seconds=10),
            source_ip="203.0.113.10",
            user="bob",
            event_type="invalid_user",
            severity="HIGH",
            details="Invalid user bob",
            raw_message="Invalid user bob"
        ),
        AuthLogRecord(
            timestamp=base_time + timedelta(seconds=15),
            source_ip="203.0.113.10",
            user="charlie",
            event_type="invalid_user",
            severity="HIGH",
            details="Invalid user charlie",
            raw_message="Invalid user charlie"
        ),
    ]

    events = engine.evaluate_auth_logs(records)
    assert len(events) == 1
    assert events[0].event_type == "Account Enumeration Probing"
    assert "RULE-ENUM-001" in events[0].evidence


def test_privilege_escalation_detection():
    engine = DetectionRulesEngine()
    records = [
        AuthLogRecord(
            timestamp=datetime(2026, 9, 1, 3, 30, 0),
            source_ip=None,
            user="developer",
            event_type="privilege_escalation",
            severity="HIGH",
            details="User 'developer' executed privileged command as 'root': /bin/bash (TTY=pts/1, PWD=/root)",
            raw_message="sudo:   developer : TTY=pts/1 ; PWD=/root ; USER=root ; COMMAND=/bin/bash"
        )
    ]

    events = engine.evaluate_auth_logs(records)
    assert len(events) == 1
    assert events[0].event_type == "Suspicious Privilege Escalation"
    assert events[0].severity == "HIGH"
    assert events[0].risk_score == 85
