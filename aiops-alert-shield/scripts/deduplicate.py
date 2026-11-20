"""
scripts/deduplicate.py
Performs deterministic deduplication and flapping detection on raw alerts.
Compresses alert storms into typed DeduplicatedAlertClusters.
"""

from __future__ import annotations
import hashlib
import re
from datetime import datetime, timezone
from typing import List, Dict, Tuple
from backend.models.contracts import RawAlert, DeduplicatedAlertCluster


def compute_alert_fingerprint(alert: RawAlert) -> str:
    """Computes a deterministic SHA256 fingerprint for clustering."""
    # Normalize message to remove specific numbers or IDs
    normalized_msg = re.sub(r'\d+', 'N', alert.message.lower().strip())
    entity_str = alert.entity or "default_entity"
    key = f"{alert.service}:{alert.alert_name}:{entity_str}:{normalized_msg}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def parse_iso(ts_str: str) -> datetime:
    try:
        clean = ts_str.replace("Z", "+00:00")
        return datetime.fromisoformat(clean)
    except Exception:
        return datetime.now(timezone.utc)


SEVERITY_WEIGHT = {
    "CRITICAL": 4,
    "WARNING": 3,
    "INFO": 2,
    "LOW": 1,
}


def deduplicate_alerts(
    alerts: List[RawAlert],
    window_seconds: int = 300,
    flap_threshold_count: int = 6
) -> Tuple[List[DeduplicatedAlertCluster], float]:
    """
    Deduplicates alerts using sliding time window and fingerprinting.
    Detects flapping if alert arrivals exceed flap_threshold_count within the window.
    Returns: (clusters, compression_ratio)
    """
    if not alerts:
        return [], 0.0

    # Sort alerts by timestamp
    sorted_alerts = sorted(alerts, key=lambda a: a.timestamp)
    clusters_map: Dict[str, Dict] = {}

    for alert in sorted_alerts:
        fp = compute_alert_fingerprint(alert)
        alert_time = parse_iso(alert.timestamp)

        if fp not in clusters_map:
            clusters_map[fp] = {
                "cluster_id": f"cluster_{fp}",
                "fingerprint": fp,
                "service": alert.service,
                "alert_name": alert.alert_name,
                "severity": alert.severity,
                "count": 1,
                "first_seen": alert.timestamp,
                "last_seen": alert.timestamp,
                "first_time": alert_time,
                "last_time": alert_time,
                "raw_alert_ids": [alert.alert_id],
                "representative_message": alert.message,
                "timestamps": [alert_time],
            }
        else:
            c = clusters_map[fp]
            # Check if within sliding window from last seen
            delta_seconds = (alert_time - c["last_time"]).total_seconds()
            if delta_seconds <= window_seconds:
                c["count"] += 1
                c["last_seen"] = alert.timestamp
                c["last_time"] = alert_time
                c["raw_alert_ids"].append(alert.alert_id)
                c["timestamps"].append(alert_time)
                # Keep highest severity
                if SEVERITY_WEIGHT.get(alert.severity, 0) > SEVERITY_WEIGHT.get(c["severity"], 0):
                    c["severity"] = alert.severity
            else:
                # Window expired: start a new cluster with distinct ID suffix
                new_fp = f"{fp}_{alert_time.strftime('%H%M%S')}"
                clusters_map[new_fp] = {
                    "cluster_id": f"cluster_{new_fp}",
                    "fingerprint": fp,
                    "service": alert.service,
                    "alert_name": alert.alert_name,
                    "severity": alert.severity,
                    "count": 1,
                    "first_seen": alert.timestamp,
                    "last_seen": alert.timestamp,
                    "first_time": alert_time,
                    "last_time": alert_time,
                    "raw_alert_ids": [alert.alert_id],
                    "representative_message": alert.message,
                    "timestamps": [alert_time],
                }

    typed_clusters: List[DeduplicatedAlertCluster] = []
    for c in clusters_map.values():
        # Check flapping: frequent bursts
        is_flapping = False
        duration = max(1.0, (c["last_time"] - c["first_time"]).total_seconds())
        frequency_per_minute = (c["count"] / duration) * 60.0
        if c["count"] >= flap_threshold_count and frequency_per_minute > 4.0:
            is_flapping = True

        typed_clusters.append(DeduplicatedAlertCluster(
            cluster_id=c["cluster_id"],
            fingerprint=c["fingerprint"],
            service=c["service"],
            alert_name=c["alert_name"],
            severity=c["severity"],
            count=c["count"],
            first_seen=c["first_seen"],
            last_seen=c["last_seen"],
            raw_alert_ids=c["raw_alert_ids"],
            is_flapping=is_flapping,
            representative_message=c["representative_message"]
        ))

    raw_count = len(alerts)
    cluster_count = len(typed_clusters)
    compression_ratio = 1.0 - (cluster_count / raw_count) if raw_count > 0 else 0.0

    return typed_clusters, round(compression_ratio, 4)
