"""
scripts/window_stats.py
Deterministic sliding-window statistics module.
Computes:
  - Static thresholds
  - Rolling Median & MAD (Median Absolute Deviation)
  - EWMA (Exponentially Weighted Moving Average)
  - Rate of Change (derivative)
  - Persistence and Hysteresis
"""

from __future__ import annotations
import math
from typing import List, Dict, Optional, Tuple
from backend.models.contracts import RawMetricPoint, WindowMetricStats

# Default static thresholds for e-commerce checkout stack
STATIC_THRESHOLDS: Dict[Tuple[str, str], float] = {
    ("orders-postgres-primary", "conn_pool_pct"): 85.0,
    ("orders-postgres-primary", "lock_wait_count"): 10.0,
    ("orders-postgres-primary", "cpu_pct"): 85.0,
    ("orders-postgres-primary", "query_latency_ms"): 250.0,
    ("checkout-api", "latency_p99"): 800.0,
    ("checkout-api", "error_rate_5xx"): 3.0,
    ("checkout-api", "cpu_pct"): 80.0,
    ("api-gateway", "latency_p99"): 500.0,
    ("api-gateway", "error_rate_5xx"): 2.0,
    ("payment-service", "latency_p99"): 1000.0,
    ("payment-service", "error_rate_5xx"): 2.0,
    ("inventory-service", "latency_p99"): 300.0,
    ("redis-cache", "memory_pct"): 85.0,
    ("redis-cache", "hit_ratio"): 0.70,  # Below 0.70 is anomalous
}


def calculate_median_and_mad(values: List[float]) -> Tuple[float, float]:
    """Calculates median and median absolute deviation (MAD)."""
    if not values:
        return 0.0, 0.0
    s = sorted(values)
    n = len(s)
    mid = n // 2
    if n % 2 == 1:
        med = s[mid]
    else:
        med = (s[mid - 1] + s[mid]) / 2.0

    abs_deviations = sorted(abs(x - med) for x in values)
    if n % 2 == 1:
        mad = abs_deviations[mid]
    else:
        mad = (abs_deviations[mid - 1] + abs_deviations[mid]) / 2.0

    return med, mad


def calculate_ewma(values: List[float], alpha: float = 0.3) -> float:
    """Calculates Exponentially Weighted Moving Average."""
    if not values:
        return 0.0
    ewma = values[0]
    for val in values[1:]:
        ewma = alpha * val + (1.0 - alpha) * ewma
    return ewma


def calculate_window_stats(
    service: str,
    metric_name: str,
    series: List[RawMetricPoint],
    evidence_idx: int = 1,
    mad_threshold_z: float = 3.0,
    persistence_required: int = 2
) -> Optional[WindowMetricStats]:
    """
    Computes statistical features over a window of metric points.
    Returns typed WindowMetricStats.
    """
    if not series:
        return None

    # Filter by service and metric
    points = [p for p in series if p.service == service and p.metric_name == metric_name]
    if not points:
        return None

    values = [p.value for p in points]
    current_val = values[-1]

    # Rolling median and MAD
    med, mad = calculate_median_and_mad(values)
    # Scaled MAD consistent with normal distribution (factor 1.4826)
    scale = 1.4826 * (mad + 1e-6)
    z_score = abs(current_val - med) / scale

    # EWMA
    ewma_val = calculate_ewma(values, alpha=0.3)

    # Rate of change
    prev_val = values[-2] if len(values) >= 2 else current_val
    rate_of_change = current_val - prev_val

    # Static threshold check
    static_thresh = STATIC_THRESHOLDS.get((service, metric_name))
    is_static_breach = False
    if static_thresh is not None:
        if metric_name == "hit_ratio":
            is_static_breach = current_val < static_thresh
        else:
            is_static_breach = current_val > static_thresh

    # Statistical anomaly check (MAD z-score > 3.0)
    is_stat_anomaly = z_score >= mad_threshold_z

    # Persistence check: count how many recent points breached
    breach_count = 0
    recent_tail = values[-min(5, len(values)):]
    for v in reversed(recent_tail):
        if static_thresh is not None:
            breached = (v < static_thresh) if metric_name == "hit_ratio" else (v > static_thresh)
            if breached:
                breach_count += 1
            else:
                break
        elif abs(v - med) / scale >= mad_threshold_z:
            breach_count += 1
        else:
            break

    # Hysteresis: triggers if breach count >= persistence_required
    hysteresis_triggered = breach_count >= persistence_required or (z_score > 5.0)
    is_anomaly = (is_static_breach or is_stat_anomaly) and hysteresis_triggered

    evidence_id = f"EVID-STAT-{evidence_idx:03d}"

    return WindowMetricStats(
        evidence_id=evidence_id,
        service=service,
        metric_name=metric_name,
        window_seconds=len(values) * 10,
        current_value=round(current_val, 4),
        median=round(med, 4),
        mad=round(mad, 4),
        ewma=round(ewma_val, 4),
        rate_of_change=round(rate_of_change, 4),
        z_score_mad=round(z_score, 2),
        is_static_breach=is_static_breach,
        static_threshold=static_thresh,
        is_anomaly=is_anomaly,
        persistence_count=breach_count,
        hysteresis_triggered=hysteresis_triggered
    )
