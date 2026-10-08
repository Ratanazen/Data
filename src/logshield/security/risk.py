"""
Transparent Rule-Based Risk Scoring Calculator

NOTE: This is a deterministic rule-based heuristic for incident response prioritization,
not a black-box machine learning classifier.
"""

from typing import List, Tuple

from .models import SeverityLevel


def compute_severity(score: int) -> SeverityLevel:
    """
    Maps numeric risk score (0-100) to operational severity:
      0  - 24 : LOW
      25 - 49 : MEDIUM
      50 - 74 : HIGH
      75 - 100: CRITICAL
    """
    if score >= 75:
        return "CRITICAL"
    if score >= 50:
        return "HIGH"
    if score >= 25:
        return "MEDIUM"
    return "LOW"

class RiskCalculator:
    """
    Evaluates empirical indicators for an IP profile and computes
    an additive risk score bounded strictly between 0 and 100.
    """

    @staticmethod
    def evaluate_profile(
        request_count: int,
        count_404: int,
        count_403: int,
        count_500: int,
        login_failures: int,
        admin_scan_count: int,
        traversal_attempts: int,
        error_rate_pct: float
    ) -> Tuple[int, SeverityLevel, List[str]]:
        """
        Calculates cumulative risk score, assigns severity, and generates forensic evidence tags.
        """
        score = 0
        evidence: List[str] = []

        # 1. Excessive 404 Spike (+20 pts)
        if count_404 >= 100 or (request_count >= 50 and (count_404 / request_count) > 0.5):
            score += 20
            evidence.append(f"Excessive 404 errors ({count_404} hits, >50% failure rate)")

        # 2. Excessive 403 Forbidden Spike (+20 pts)
        if count_403 >= 30 or (request_count >= 30 and (count_403 / request_count) > 0.3):
            score += 20
            evidence.append(f"Excessive 403 Forbidden attempts ({count_403} hits)")

        # 3. Brute-Force-Like Login Probing (+25 pts)
        if login_failures >= 15:
            score += 25
            evidence.append(f"Potential brute-force authentication activity ({login_failures} failed login hits)")

        # 4. Sensitive Admin / Config Scanning (+20 pts)
        if admin_scan_count >= 10:
            score += 20
            evidence.append(f"Automated admin/reconnaissance path scanning ({admin_scan_count} sensitive routes)")

        # 5. Directory Traversal / Probe Signatures (+15 pts)
        if traversal_attempts > 0:
            score += 15
            evidence.append(f"Path traversal or probe attempt signatures detected ({traversal_attempts} hits)")

        # 6. Overall High Error Ratio (+15 pts)
        if request_count >= 40 and error_rate_pct >= 75.0:
            score += 15
            evidence.append(f"Abnormally high overall error rate ({error_rate_pct:.1f}%)")

        # Cap score between 0 and 100
        final_score = min(100, max(0, score))
        severity = compute_severity(final_score)

        return final_score, severity, evidence
