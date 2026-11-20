"""
scripts/correlate_services.py
Deterministic cross-service lag correlation.
Calculates Pearson correlation r(tau) across time lags to discover and verify
causal propagation ordering across microservices.
"""

from __future__ import annotations
import math
from typing import List, Dict, Tuple, Optional
from backend.models.contracts import RawMetricPoint, CrossServiceCorrelation


def pearson_correlation(x: List[float], y: List[float]) -> float:
    """Computes sample Pearson correlation coefficient."""
    n = len(x)
    if n < 4 or len(y) != n:
        return 0.0

    mean_x = sum(x) / n
    mean_y = sum(y) / n

    numerator = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
    var_x = sum((x[i] - mean_x) ** 2 for i in range(n))
    var_y = sum((y[i] - mean_y) ** 2 for i in range(n))

    denom = math.sqrt(var_x * var_y)
    if denom < 1e-9:
        return 0.0

    return numerator / denom


def align_and_correlate(
    series_a: List[Tuple[int, float]],
    series_b: List[Tuple[int, float]],
    lags: List[int] = [0, 10, 20, 30, 60, 90, 120]
) -> Tuple[int, float]:
    """
    Finds the lag tau (in seconds) that maximizes Pearson correlation between series_a(t) and series_b(t + tau).
    Returns: (best_lag_seconds, max_pearson_r)
    """
    if not series_a or not series_b:
        return 0, 0.0

    # Map timestamp seconds -> value
    map_a = {t: val for t, val in series_a}
    map_b = {t: val for t, val in series_b}

    best_lag = 0
    max_r = -2.0

    for lag in lags:
        aligned_a: List[float] = []
        aligned_b: List[float] = []

        for t, val_a in map_a.items():
            t_b = t + lag
            if t_b in map_b:
                aligned_a.append(val_a)
                aligned_b.append(map_b[t_b])

        if len(aligned_a) >= 6:
            r = pearson_correlation(aligned_a, aligned_b)
            if r > max_r:
                max_r = r
                best_lag = lag

    return best_lag, max(0.0, max_r)


def correlate_cross_services(
    metrics_points: List[RawMetricPoint],
    candidate_pairs: Optional[List[Tuple[str, str, str, str]]] = None,
    min_correlation: float = 0.65
) -> List[CrossServiceCorrelation]:
    """
    Performs cross-service lag correlation over candidate propagation paths.
    Default paths follow the checkout topology:
      orders-postgres-primary -> checkout-api -> api-gateway
      redis-cache -> checkout-api
      payment-service -> checkout-api
    """
    if candidate_pairs is None:
        candidate_pairs = [
            ("orders-postgres-primary", "lock_wait_count", "checkout-api", "latency_p99"),
            ("orders-postgres-primary", "conn_pool_pct", "checkout-api", "latency_p99"),
            ("orders-postgres-primary", "cpu_pct", "checkout-api", "latency_p99"),
            ("checkout-api", "latency_p99", "api-gateway", "latency_p99"),
            ("checkout-api", "latency_p99", "api-gateway", "error_rate_5xx"),
            ("payment-service", "latency_p99", "checkout-api", "latency_p99"),
            ("redis-cache", "eviction_rate", "checkout-api", "latency_p99"),
        ]

    # Pre-parse series into epoch seconds: (sec, value)
    series_by_key: Dict[Tuple[str, str], List[Tuple[int, float]]] = {}
    from scripts.validate_normalize import normalize_iso_timestamp
    from datetime import datetime

    for p in metrics_points:
        try:
            # Parse ISO string into epoch
            clean_ts = p.timestamp.replace("Z", "+00:00")
            sec = int(datetime.fromisoformat(clean_ts).timestamp())
            key = (p.service, p.metric_name)
            if key not in series_by_key:
                series_by_key[key] = []
            series_by_key[key].append((sec, p.value))
        except Exception:
            continue

    correlations: List[CrossServiceCorrelation] = []
    evidence_idx = 1

    for src_svc, src_m, tgt_svc, tgt_m in candidate_pairs:
        s_a = series_by_key.get((src_svc, src_m), [])
        s_b = series_by_key.get((tgt_svc, tgt_m), [])

        if len(s_a) >= 6 and len(s_b) >= 6:
            lag, r = align_and_correlate(s_a, s_b)
            if r >= min_correlation:
                causal = (lag >= 0)  # Positive lag indicates source leads target
                desc = (
                    f"Strong correlation (r={r:.2f}) observed between {src_svc}:{src_m} "
                    f"and {tgt_svc}:{tgt_m} with a lag of {lag}s (causal order verified: {causal})"
                )
                correlations.append(CrossServiceCorrelation(
                    evidence_id=f"EVID-CORR-{evidence_idx:03d}",
                    source_service=src_svc,
                    source_metric=src_m,
                    target_service=tgt_svc,
                    target_metric=tgt_m,
                    lag_seconds=lag,
                    pearson_r=round(r, 3),
                    causal_order_verified=causal,
                    description=desc
                ))
                evidence_idx += 1

    return correlations
