"""
scripts/validate_normalize.py
Validates and normalizes alerts, metrics, and logs into standard internal formats.
Ensures deterministic schema enforcement and timestamp alignment (UTC ISO 8601).
"""

from __future__ import annotations
import re
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple
from backend.models.contracts import RawAlert, RawMetricPoint, RawLogEntry

VALID_SERVICES = {
    "api-gateway",
    "checkout-api",
    "payment-service",
    "inventory-service",
    "orders-postgres-primary",
    "redis-cache",
}

SEVERITY_MAP = {
    "crit": "CRITICAL",
    "critical": "CRITICAL",
    "fatal": "CRITICAL",
    "p0": "CRITICAL",
    "p1": "CRITICAL",
    "warn": "WARNING",
    "warning": "WARNING",
    "p2": "WARNING",
    "info": "INFO",
    "information": "INFO",
    "p3": "INFO",
    "low": "LOW",
    "p4": "LOW",
    "debug": "LOW",
}


def normalize_iso_timestamp(ts: Any) -> str:
    """Normalizes epoch or ISO strings into standard UTC ISO format: YYYY-MM-DDTHH:MM:SSZ."""
    if isinstance(ts, (int, float)):
        # Treat as epoch seconds or ms
        if ts > 1e11:
            ts = ts / 1000.0
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    ts_str = str(ts).strip()
    # Replace +00:00 with Z
    ts_str = re.sub(r'\+00:?00$', 'Z', ts_str)
    try:
        # Parse standard ISO
        if ts_str.endswith("Z"):
            dt = datetime.fromisoformat(ts_str[:-1] + "+00:00")
        else:
            dt = datetime.fromisoformat(ts_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        # Fallback to current UTC if unparseable
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def normalize_service_name(service: str) -> str:
    """Normalizes and maps service names to canonical identifiers."""
    cleaned = str(service).strip().lower().replace("_", "-")
    if cleaned in VALID_SERVICES:
        return cleaned
    # Fuzzy mappings
    if "gateway" in cleaned:
        return "api-gateway"
    if "checkout" in cleaned:
        return "checkout-api"
    if "payment" in cleaned:
        return "payment-service"
    if "inventory" in cleaned:
        return "inventory-service"
    if "postgres" in cleaned or "order-db" in cleaned or "orders-db" in cleaned:
        return "orders-postgres-primary"
    if "redis" in cleaned or "cache" in cleaned:
        return "redis-cache"
    return cleaned


def normalize_severity(sev: Any) -> str:
    s = str(sev).strip().lower()
    return SEVERITY_MAP.get(s, "WARNING")


def validate_and_normalize_alert(raw: Dict[str, Any]) -> Optional[RawAlert]:
    """Validates and returns normalized RawAlert, or None if completely invalid."""
    try:
        alert_id = str(raw.get("alert_id") or raw.get("id") or f"alt_{hash(str(raw)) & 0xffffffff:08x}")
        timestamp = normalize_iso_timestamp(raw.get("timestamp") or raw.get("time"))
        service = normalize_service_name(raw.get("service") or raw.get("source") or "unknown")
        alert_name = str(raw.get("alert_name") or raw.get("name") or "UnnamedAlert").strip()
        severity = normalize_severity(raw.get("severity", "WARNING"))
        message = str(raw.get("message") or raw.get("description") or alert_name)

        metric_name = raw.get("metric_name")
        metric_value = None
        if raw.get("metric_value") is not None:
            try:
                metric_value = float(raw["metric_value"])
            except (ValueError, TypeError):
                pass

        threshold = None
        if raw.get("threshold") is not None:
            try:
                threshold = float(raw["threshold"])
            except (ValueError, TypeError):
                pass

        entity = raw.get("entity") or raw.get("host") or raw.get("instance")
        tags = raw.get("tags") if isinstance(raw.get("tags"), dict) else {}

        return RawAlert(
            alert_id=alert_id,
            timestamp=timestamp,
            service=service,
            alert_name=alert_name,
            severity=severity,  # type: ignore
            metric_name=metric_name,
            metric_value=metric_value,
            threshold=threshold,
            entity=str(entity) if entity else None,
            message=message,
            tags=tags
        )
    except Exception:
        return None


def validate_and_normalize_metric(raw: Dict[str, Any]) -> Optional[RawMetricPoint]:
    """Validates and returns normalized RawMetricPoint."""
    try:
        ts = normalize_iso_timestamp(raw.get("timestamp") or raw.get("time"))
        svc = normalize_service_name(raw.get("service", ""))
        metric = str(raw.get("metric_name") or raw.get("metric", "")).strip()
        val = float(raw.get("value", 0.0))
        return RawMetricPoint(timestamp=ts, service=svc, metric_name=metric, value=val)
    except Exception:
        return None


def validate_and_normalize_log(raw: Dict[str, Any]) -> Optional[RawLogEntry]:
    """Validates and returns normalized RawLogEntry."""
    try:
        log_id = str(raw.get("log_id") or f"log_{hash(str(raw)) & 0xffffffff:08x}")
        ts = normalize_iso_timestamp(raw.get("timestamp") or raw.get("time"))
        svc = normalize_service_name(raw.get("service", "unknown"))
        lvl = str(raw.get("level", "INFO")).upper()
        if lvl not in ("DEBUG", "INFO", "WARN", "WARNING", "ERROR", "CRITICAL", "FATAL"):
            lvl = "INFO"
        msg = str(raw.get("message", ""))
        trace_id = raw.get("trace_id")
        span_id = raw.get("span_id")
        attrs = raw.get("attributes") if isinstance(raw.get("attributes"), dict) else {}

        return RawLogEntry(
            log_id=log_id,
            timestamp=ts,
            service=svc,
            level=lvl,  # type: ignore
            message=msg,
            trace_id=trace_id,
            span_id=span_id,
            attributes=attrs
        )
    except Exception:
        return None
