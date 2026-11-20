"""
backend/storage/timeseries_repository.py
Repository for querying and retrieving service metrics and health status.
"""

from __future__ import annotations
import csv
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
from backend.models.contracts import RawMetricPoint

DATA_CSV_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "metrics_timeseries.csv"


class TimeseriesRepository:
    def __init__(self, csv_path: Optional[Path] = None):
        self.csv_path = csv_path or DATA_CSV_PATH

    def get_service_metrics(
        self,
        service: Optional[str] = None,
        metric_name: Optional[str] = None,
        limit: int = 500
    ) -> List[RawMetricPoint]:
        """Queries metric points from the storage CSV."""
        if not self.csv_path.exists():
            return []

        results: List[RawMetricPoint] = []
        with open(self.csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if service and row["service"] != service:
                    continue
                if metric_name and row["metric_name"] != metric_name:
                    continue
                try:
                    results.append(RawMetricPoint(
                        timestamp=row["timestamp"],
                        service=row["service"],
                        metric_name=row["metric_name"],
                        value=float(row["value"])
                    ))
                except Exception:
                    continue

        return results[-limit:]

    def get_service_health_summary(self) -> List[Dict[str, Any]]:
        """Calculates current health status for all 6 microservices."""
        services = [
            "api-gateway",
            "checkout-api",
            "payment-service",
            "inventory-service",
            "orders-postgres-primary",
            "redis-cache"
        ]
        summaries = []
        for svc in services:
            points = self.get_service_metrics(service=svc, limit=60)
            # Find latest error rate or latency
            err_points = [p.value for p in points if "error" in p.metric_name]
            lat_points = [p.value for p in points if "latency" in p.metric_name]
            cpu_points = [p.value for p in points if "cpu" in p.metric_name]

            avg_err = (sum(err_points) / len(err_points)) if err_points else 0.0
            avg_lat = (sum(lat_points) / len(lat_points)) if lat_points else 0.0
            avg_cpu = (sum(cpu_points) / len(cpu_points)) if cpu_points else 0.0

            if avg_err > 5.0 or avg_lat > 1000.0:
                status = "DEGRADED"
            elif avg_err > 15.0 or avg_lat > 3000.0:
                status = "OUTAGE"
            else:
                status = "HEALTHY"

            summaries.append({
                "service": svc,
                "status": status,
                "error_rate_5xx": round(avg_err, 2),
                "latency_p99_ms": round(avg_lat, 1),
                "cpu_utilization_pct": round(avg_cpu, 1),
                "sample_count": len(points)
            })

        return summaries
