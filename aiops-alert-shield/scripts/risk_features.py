"""
scripts/risk_features.py
Deterministic Risk Scoring and Fail-Open Policy Evaluation.
Calculates risk score, deterministic severity, and fail-open guarantees.
"""

from __future__ import annotations
from typing import Tuple, Literal, Optional
from backend.models.contracts import BlastRadiusReport


def evaluate_deterministic_risk(
    composite_anomaly_score: float,
    blast_radius: BlastRadiusReport,
    has_critical_db_breach: bool = False,
    is_flapping_only: bool = False
) -> Tuple[float, Literal["CRITICAL", "HIGH", "MEDIUM", "LOW", "BENIGN"], bool, Optional[str]]:
    """
    Evaluates risk score, deterministic severity, and fail-open requirement.
    Returns:
      - risk_score: float [0.0, 1.0]
      - severity: CRITICAL | HIGH | MEDIUM | LOW | BENIGN
      - fail_open_recommended: bool
      - fail_open_reason: Optional[str]
    """
    if is_flapping_only and not blast_radius.customer_facing_impact:
        return 0.15, "BENIGN", False, None

    # Base weighted components
    # 45% blast radius, 40% anomaly deviation, 15% customer impact bonus
    base_risk = (0.45 * blast_radius.blast_radius_score) + (0.40 * composite_anomaly_score)
    if blast_radius.customer_facing_impact:
        base_risk += 0.15
    if has_critical_db_breach:
        base_risk += 0.10

    risk_score = round(min(1.0, max(0.0, base_risk)), 3)

    # Determine severity
    if risk_score >= 0.70 or (blast_radius.customer_facing_impact and has_critical_db_breach):
        severity = "CRITICAL"
    elif risk_score >= 0.45:
        severity = "HIGH"
    elif risk_score >= 0.25:
        severity = "MEDIUM"
    elif risk_score >= 0.10:
        severity = "LOW"
    else:
        severity = "BENIGN"

    # Deterministic Fail-Open Policy:
    # If the deterministic risk is CRITICAL (or risk_score >= 0.75) and customer path is breached,
    # the system MUST publish an incident even if AI models fail or are unreachable.
    fail_open = False
    fail_open_reason = None
    if severity == "CRITICAL" and blast_radius.customer_facing_impact:
        fail_open = True
        fail_open_reason = (
            f"Deterministic threshold breached: risk_score={risk_score} with customer-facing ingress "
            f"impact and critical path compromise. Fail-open incident publication enforced."
        )

    return risk_score, severity, fail_open, fail_open_reason
