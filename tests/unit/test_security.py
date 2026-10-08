"""Unit tests for LogShield security rules, risk scoring, and threat detection."""

from src.logshield.security.risk import RiskCalculator, compute_severity
from src.logshield.security.rules import (
    is_admin_or_sensitive_path,
    is_suspicious_user_agent,
    matches_suspicious_path_signature,
)


def test_sensitive_route_matching():
    assert is_admin_or_sensitive_path("/admin/login") is True
    assert is_admin_or_sensitive_path("/wp-login.php") is True
    assert is_admin_or_sensitive_path("/.env") is True
    assert is_admin_or_sensitive_path("/index.html") is False
    assert is_admin_or_sensitive_path("/product/123") is False


def test_directory_traversal_matching():
    assert matches_suspicious_path_signature("/../../etc/passwd") is True
    assert matches_suspicious_path_signature("/etc/passwd") is True
    assert matches_suspicious_path_signature("/home") is False


def test_scanner_ua_matching():
    assert is_suspicious_user_agent("sqlmap/1.4") is True
    assert is_suspicious_user_agent("Nikto/2.1.6") is True
    assert is_suspicious_user_agent("Mozilla/5.0 (Windows NT 10.0; Win64; x64)") is False


def test_risk_score_calculation():
    # Normal profile
    score, sev, evidence = RiskCalculator.evaluate_profile(
        request_count=50,
        count_404=2,
        count_403=0,
        count_500=0,
        login_failures=0,
        admin_scan_count=0,
        traversal_attempts=0,
        error_rate_pct=4.0,
    )
    assert score <= 10
    assert sev == "LOW"

    # Attacker profile with admin scan and 404s
    score_att, sev_att, evidence_att = RiskCalculator.evaluate_profile(
        request_count=400,
        count_404=90,
        count_403=15,
        count_500=10,
        login_failures=65,
        admin_scan_count=65,
        traversal_attempts=2,
        error_rate_pct=28.0,
    )
    assert score_att >= 50
    assert sev_att in ("HIGH", "CRITICAL")
    assert len(evidence_att) > 0


def test_severity_categorization():
    assert compute_severity(10) == "LOW"
    assert compute_severity(35) == "MEDIUM"
    assert compute_severity(60) == "HIGH"
    assert compute_severity(85) == "CRITICAL"
