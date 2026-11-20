"""
scripts/anomaly_features.py
Aggregates window statistics into normalized anomaly feature vectors
and computes deterministic symptom signatures.
"""

from __future__ import annotations
import hashlib
from typing import List, Dict, Tuple
from backend.models.contracts import RawMetricPoint, WindowMetricStats
from scripts.window_stats import calculate_window_stats

METRIC_WEIGHTS: Dict[str, float] = {
    "error_rate_5xx": 1.0,
    "lock_wait_count": 0.95,
    "conn_pool_pct": 0.9,
    "latency_p99": 0.85,
    "query_latency_ms": 0.8,
    "eviction_rate": 0.75,
    "hit_ratio": 0.7,
    "cpu_pct": 0.5,
    "rps": 0.4,
}


def extract_anomaly_features(
    metrics_points: List[RawMetricPoint],
    window_limit: int = 50,
    scan_all_windows: bool = True
) -> Tuple[List[WindowMetricStats], str, float]:
    """
    Extracts anomaly features from metric points.
    If scan_all_windows is True, scans through the series to find the maximum anomaly
    or persistent breach window, ensuring incident bursts across the timeseries are detected.
    Returns:
      - anomalies: list of statistically significant WindowMetricStats
      - symptom_signature: deterministic signature string
      - composite_anomaly_score: float between 0.0 and 1.0
    """
    # Group by (service, metric_name)
    grouped: Dict[Tuple[str, str], List[RawMetricPoint]] = {}
    for p in metrics_points:
        key = (p.service, p.metric_name)
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(p)

    all_stats: List[WindowMetricStats] = []
    anomalies: List[WindowMetricStats] = []
    evidence_counter = 1

    for (service, metric), points in grouped.items():
        if not points:
            continue

        best_stat: Optional[WindowMetricStats] = None
        if scan_all_windows and len(points) > window_limit:
            # Step through chunks to find peak anomaly
            step = max(5, window_limit // 4)
            for idx in range(0, len(points) - window_limit + 1, step):
                chunk = points[idx:idx + window_limit]
                stat = calculate_window_stats(service, metric, chunk, evidence_idx=evidence_counter)
                if stat:
                    if best_stat is None or stat.z_score_mad > best_stat.z_score_mad or (stat.is_static_breach and not best_stat.is_static_breach):
                        best_stat = stat
        else:
            recent_points = points[-window_limit:] if len(points) > window_limit else points
            best_stat = calculate_window_stats(service, metric, recent_points, evidence_idx=evidence_counter)

        if best_stat is not None:
            all_stats.append(best_stat)
            if best_stat.is_anomaly or best_stat.is_static_breach:
                anomalies.append(best_stat)
            evidence_counter += 1

    # Deterministic symptom signature calculation
    # Format: sorted list of anomalous service:metric pairs
    anom_keys = sorted([f"{a.service}:{a.metric_name}" for a in anomalies])
    if anom_keys:
        raw_sig = "|".join(anom_keys)
        sig_hash = hashlib.sha256(raw_sig.encode("utf-8")).hexdigest()[:12]
        # Prefer root suspect or backend storage service if anomalous
        pref_order = ["orders-postgres-primary", "redis-cache", "payment-service", "inventory-service", "checkout-api", "api-gateway"]
        primary = anomalies[0]
        for pref in pref_order:
            found = [a for a in anomalies if a.service == pref]
            if found:
                primary = found[0]
                break
        symptom_signature = f"{primary.service}:{primary.metric_name}:{sig_hash}"
    else:
        symptom_signature = "nominal:no_anomalies:000000000000"

    # Composite score calculation (weighted MAD z-scores & breaches)
    if not anomalies:
        composite_score = 0.0
    else:
        weighted_sum = 0.0
        total_weight = 0.0
        for a in anomalies:
            w = METRIC_WEIGHTS.get(a.metric_name, 0.5)
            # Normalize z-score (cap at 10.0 for scaling)
            capped_z = min(10.0, a.z_score_mad) / 10.0
            static_factor = 1.0 if a.is_static_breach else 0.7
            weighted_sum += w * capped_z * static_factor
            total_weight += w

        composite_score = min(1.0, weighted_sum / (total_weight if total_weight > 0 else 1.0))

    return anomalies, symptom_signature, round(composite_score, 4)
