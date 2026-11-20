"""
tests/test_compute.py
Comprehensive unit and integration tests for deterministic compute modules.
Enforces Rule 1: 100% of arithmetic, stats, dedup, PII redaction, blast radius,
and lag correlation run in pure Python before any AI invocation.
"""

import pytest
from datetime import datetime, timezone
from scripts.privacy_mask import mask_pii_text, mask_log_entry
from scripts.validate_normalize import (
    validate_and_normalize_alert,
    validate_and_normalize_metric,
    normalize_iso_timestamp,
    normalize_service_name,
)
from scripts.deduplicate import deduplicate_alerts
from scripts.window_stats import (
    calculate_median_and_mad,
    calculate_ewma,
    calculate_window_stats,
)
from scripts.anomaly_features import extract_anomaly_features
from scripts.correlate_services import pearson_correlation, align_and_correlate
from scripts.dependency_graph import compute_blast_radius, get_upstream_impact
from scripts.risk_features import evaluate_deterministic_risk
from backend.models.contracts import RawAlert, RawMetricPoint


def test_privacy_mask_redacts_pii():
    raw_text = "Customer alice@store.com paid with card 4532-0150-1234-5674 and token Bearer eyJhbGciOi.eyJzdWIi.SflK on trace_id 00a98f12"
    masked, count, types = mask_pii_text(raw_text)

    assert "[REDACTED_EMAIL]" in masked
    assert "alice@store.com" not in masked
    assert "[REDACTED_CREDIT_CARD]" in masked
    assert "4532-0150-1234-5674" not in masked
    assert "Bearer [REDACTED_TOKEN]" in masked
    assert "00a98f12" in masked  # Trace IDs must be preserved!
    assert count >= 3
    assert "EMAIL" in types
    assert "CREDIT_CARD" in types
    assert "JWT_OR_BEARER" in types


def test_validate_and_normalize_alert():
    raw = {
        "id": "alt_999",
        "time": "2026-11-19 14:00:00",
        "source": "Orders_Postgres_Primary",
        "name": "HighConnPool",
        "severity": "CRITICAL",
        "metric_name": "conn_pool_pct",
        "metric_value": "94.5",
        "message": "Connection pool saturated"
    }
    norm = validate_and_normalize_alert(raw)
    assert norm is not None
    assert norm.alert_id == "alt_999"
    assert norm.service == "orders-postgres-primary"
    assert norm.severity == "CRITICAL"
    assert norm.metric_value == 94.5
    assert norm.timestamp.endswith("Z")


def test_deduplicate_and_flapping():
    now = datetime(2026, 11, 19, 14, 0, 0, tzinfo=timezone.utc)
    alerts = []
    # 20 identical alerts within 30 seconds -> should be compressed and flagged flapping
    for i in range(20):
        alerts.append(RawAlert(
            alert_id=f"alt_{i}",
            timestamp=(now).isoformat(),
            service="redis-cache",
            alert_name="ConnJitter",
            severity="WARNING",
            message="Redis client dropped connection",
            tags={}
        ))

    clusters, ratio = deduplicate_alerts(alerts, window_seconds=60, flap_threshold_count=5)
    assert len(clusters) == 1
    assert clusters[0].count == 20
    assert clusters[0].is_flapping is True
    assert ratio >= 0.90  # At least 90% compression


def test_sliding_window_stats_mad_and_ewma():
    # Constant baseline 50.0, then sudden spike to 500.0
    series = [RawMetricPoint(timestamp=f"2026-11-19T14:{i:02d}:00Z", service="checkout-api", metric_name="latency_p99", value=50.0) for i in range(15)]
    series.extend([RawMetricPoint(timestamp=f"2026-11-19T14:{15+i:02d}:00Z", service="checkout-api", metric_name="latency_p99", value=1200.0) for i in range(4)])

    stat = calculate_window_stats("checkout-api", "latency_p99", series)
    assert stat is not None
    assert stat.is_anomaly is True
    assert stat.z_score_mad > 3.0
    assert stat.is_static_breach is True
    assert stat.hysteresis_triggered is True


def test_cross_service_lag_correlation():
    # Synthetic series where A leads B by exactly 20 seconds
    series_a = [(t, float(10 + (100 if 200 <= t <= 400 else 0))) for t in range(0, 600, 10)]
    series_b = [(t, float(20 + (80 if 220 <= t <= 420 else 0))) for t in range(0, 600, 10)]

    best_lag, max_r = align_and_correlate(series_a, series_b, lags=[0, 10, 20, 30, 40])
    assert best_lag == 20
    assert max_r > 0.85


def test_dependency_graph_blast_radius():
    # Root suspect: orders-postgres-primary
    report = compute_blast_radius(
        anomalous_services=["orders-postgres-primary", "checkout-api"],
        root_candidate="orders-postgres-primary"
    )
    assert report.root_suspect == "orders-postgres-primary"
    assert "checkout-api" in report.compromised_services
    assert "api-gateway" in report.compromised_services
    assert report.critical_path_affected is True
    assert report.customer_facing_impact is True
    assert report.blast_radius_score >= 0.5


def test_risk_features_and_fail_open_guarantee():
    report = compute_blast_radius(["orders-postgres-primary", "checkout-api", "api-gateway"], "orders-postgres-primary")
    score, sev, fail_open, reason = evaluate_deterministic_risk(
        composite_anomaly_score=0.95,
        blast_radius=report,
        has_critical_db_breach=True
    )
    assert sev == "CRITICAL"
    assert score >= 0.75
    assert fail_open is True
    assert "Fail-open incident publication enforced" in reason
