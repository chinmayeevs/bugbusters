"""
scripts/generate_mock_data.py
Generates deterministic, high-fidelity mock datasets and benchmark scenarios
for the e-commerce checkout stack:
  api-gateway -> checkout-api -> [payment-service, inventory-service, orders-postgres-primary, redis-cache]

Outputs:
  data/alerts.jsonl
  data/metrics_timeseries.csv
  data/logs.jsonl
  data/ground_truth.json
  data/past_incidents_seed.json
"""

from __future__ import annotations
import csv
import json
import math
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Dict, Any

SERVICES = [
    "api-gateway",
    "checkout-api",
    "payment-service",
    "inventory-service",
    "orders-postgres-primary",
    "redis-cache",
]

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True, parents=True)

# Fixed seed for 100% deterministic reproducibility
RANDOM_SEED = 42


def get_base_timestamp() -> datetime:
    return datetime(2026, 11, 19, 14, 0, 0, tzinfo=timezone.utc)


def generate_timeseries(base_time: datetime, duration_minutes: int = 60) -> List[Dict[str, Any]]:
    """Generates 10-second resolution metrics across all 6 services with injected anomalies."""
    rng = random.Random(RANDOM_SEED)
    rows: List[Dict[str, Any]] = []
    total_steps = (duration_minutes * 60) // 10

    # Normal baselines
    baselines = {
        "api-gateway": {"rps": 450.0, "latency_p99": 45.0, "error_rate_5xx": 0.05, "cpu_pct": 35.0},
        "checkout-api": {"rps": 220.0, "latency_p99": 110.0, "error_rate_5xx": 0.02, "cpu_pct": 42.0},
        "payment-service": {"rps": 95.0, "latency_p99": 180.0, "error_rate_5xx": 0.01, "cpu_pct": 28.0},
        "inventory-service": {"rps": 180.0, "latency_p99": 35.0, "error_rate_5xx": 0.01, "cpu_pct": 30.0},
        "orders-postgres-primary": {"conn_pool_pct": 45.0, "lock_wait_count": 1.0, "query_latency_ms": 12.0, "cpu_pct": 38.0},
        "redis-cache": {"hit_ratio": 0.96, "memory_pct": 55.0, "eviction_rate": 0.0, "latency_p99": 2.5},
    }

    for step in range(total_steps):
        current_time = base_time + timedelta(seconds=step * 10)
        time_str = current_time.isoformat()
        minute_offset = step * 10 / 60.0

        for service, metrics in baselines.items():
            for metric, base_val in metrics.items():
                noise = rng.gauss(0, base_val * 0.04)
                val = max(0.0, base_val + noise)

                # Scenario 1: Postgres lock contention cascade from minute 15 to 30
                if 15.0 <= minute_offset <= 30.0:
                    # Postgres primary anomaly begins at minute 15
                    if service == "orders-postgres-primary":
                        if metric == "lock_wait_count":
                            val = 45.0 + rng.uniform(10.0, 30.0)
                        elif metric == "conn_pool_pct":
                            val = min(99.5, 88.0 + rng.uniform(5.0, 11.0))
                        elif metric == "query_latency_ms":
                            val = 1200.0 + rng.uniform(200.0, 800.0)
                        elif metric == "cpu_pct":
                            val = 94.0 + rng.uniform(2.0, 5.0)

                    # Checkout-API degrades with 15-second lag (minute 15.25)
                    if minute_offset >= 15.25 and service == "checkout-api":
                        if metric == "latency_p99":
                            val = 3200.0 + rng.uniform(300.0, 1200.0)
                        elif metric == "error_rate_5xx":
                            val = 14.5 + rng.uniform(2.0, 6.0)

                    # API-Gateway degrades with 30-second lag (minute 15.5)
                    if minute_offset >= 15.5 and service == "api-gateway":
                        if metric == "latency_p99":
                            val = 4100.0 + rng.uniform(400.0, 900.0)
                        elif metric == "error_rate_5xx":
                            val = 18.2 + rng.uniform(3.0, 8.0)

                # Scenario 2: Nightly 02:00 pg_dump backup CPU spike from minute 45 to 55
                # (Symptom: High DB CPU, but ZERO downstream latency increase or errors)
                if 45.0 <= minute_offset <= 55.0:
                    if service == "orders-postgres-primary" and metric == "cpu_pct":
                        val = 91.0 + rng.uniform(1.0, 4.0)

                rows.append({
                    "timestamp": time_str,
                    "service": service,
                    "metric_name": metric,
                    "value": round(val, 4)
                })

    return rows


def generate_alerts(base_time: datetime) -> List[Dict[str, Any]]:
    """Generates realistic alert floods, flapping alerts, and warnings with simulated propagation."""
    rng = random.Random(RANDOM_SEED)
    alerts: List[Dict[str, Any]] = []
    alert_idx = 1000

    # 1. Background low-level noise (40 informational/warning alerts scattered)
    for _ in range(40):
        alert_idx += 1
        sec_offset = rng.randint(0, 3500)
        svc = rng.choice(SERVICES)
        alerts.append({
            "alert_id": f"alt_{alert_idx}",
            "timestamp": (base_time + timedelta(seconds=sec_offset)).isoformat(),
            "service": svc,
            "alert_name": "TransientLatencyWarning",
            "severity": "LOW",
            "metric_name": "latency_p99",
            "metric_value": round(rng.uniform(60, 90), 2),
            "threshold": 100.0,
            "entity": f"instance-{rng.randint(1, 3)}",
            "message": f"Transient latency jitter detected on {svc}",
            "tags": {"env": "prod", "region": "us-east-1"}
        })

    # 2. Flapping Alert Noise (80 alerts rapidly toggling on/off for redis-cache)
    for f in range(80):
        alert_idx += 1
        sec_offset = 300 + (f * 5)  # Every 5s
        alerts.append({
            "alert_id": f"alt_{alert_idx}",
            "timestamp": (base_time + timedelta(seconds=sec_offset)).isoformat(),
            "service": "redis-cache",
            "alert_name": "RedisConnectionFlap",
            "severity": "WARNING",
            "metric_name": "conn_jitter",
            "metric_value": round(rng.uniform(1.0, 5.0), 2),
            "threshold": 3.0,
            "entity": "redis-cluster-node-2",
            "message": "Redis client connection dropped and reconnected",
            "tags": {"env": "prod", "flapping_cluster": "true"}
        })

    # 3. Scenario 1: Postgres Lock Cascade Alert Flood (350 alerts cascading across services)
    # T0: Minute 15 (900 seconds)
    t0 = base_time + timedelta(seconds=900)

    # 3a. Root cause alerts on orders-postgres-primary (80 alerts)
    for i in range(80):
        alert_idx += 1
        dt = t0 + timedelta(seconds=rng.randint(0, 300))
        name = rng.choice(["PostgresConnectionPoolExhausted", "PostgresTransactionLockTimeout", "PostgresHighCPUContention"])
        sev = "CRITICAL"
        alerts.append({
            "alert_id": f"alt_{alert_idx}",
            "timestamp": dt.isoformat(),
            "service": "orders-postgres-primary",
            "alert_name": name,
            "severity": sev,
            "metric_name": "lock_wait_count" if "Lock" in name else "conn_pool_pct",
            "metric_value": round(rng.uniform(85, 99), 2),
            "threshold": 80.0,
            "entity": "orders-db-master",
            "message": f"Active transactions blocked waiting on exclusive table lock on orders_v2; pool at 98%",
            "tags": {"env": "prod", "tier": "database", "cluster": "aurora-pg-primary"}
        })

    # 3b. Downstream checkout-api alerts (Lag ~15s, 140 alerts)
    t_checkout = t0 + timedelta(seconds=15)
    for i in range(140):
        alert_idx += 1
        dt = t_checkout + timedelta(seconds=rng.randint(0, 360))
        alerts.append({
            "alert_id": f"alt_{alert_idx}",
            "timestamp": dt.isoformat(),
            "service": "checkout-api",
            "alert_name": "CheckoutDatabasePoolTimeout",
            "severity": "CRITICAL",
            "metric_name": "latency_p99",
            "metric_value": round(rng.uniform(2800, 4800), 2),
            "threshold": 500.0,
            "entity": "checkout-pod-x8f2",
            "message": "Connection acquisition timeout (5000ms) waiting for orders-postgres-primary pool",
            "tags": {"env": "prod", "tier": "backend"}
        })

    # 3c. Downstream api-gateway alerts (Lag ~30s, 130 alerts)
    t_gw = t0 + timedelta(seconds=30)
    for i in range(130):
        alert_idx += 1
        dt = t_gw + timedelta(seconds=rng.randint(0, 400))
        alerts.append({
            "alert_id": f"alt_{alert_idx}",
            "timestamp": dt.isoformat(),
            "service": "api-gateway",
            "alert_name": "Gateway504TimeoutSurge",
            "severity": "CRITICAL",
            "metric_name": "error_rate_5xx",
            "metric_value": round(rng.uniform(14.0, 26.0), 2),
            "threshold": 5.0,
            "entity": "ingress-edge-envoy",
            "message": "Upstream service checkout-api timed out responding to /v1/checkout/confirm",
            "tags": {"env": "prod", "tier": "ingress"}
        })

    # Sort strictly by timestamp
    alerts.sort(key=lambda x: x["timestamp"])
    return alerts


def generate_logs(base_time: datetime) -> List[Dict[str, Any]]:
    """Generates structured logs with injected realistic PII and trace IDs."""
    rng = random.Random(RANDOM_SEED)
    logs: List[Dict[str, Any]] = []
    log_idx = 5000

    sample_emails = ["alice.smith@customer.net", "bob_buyer99@gmail.com", "carol.v@company.org"]
    sample_cards = ["4532-0150-1234-5674", "5424-0012-3456-7890", "3782-822463-10005"]
    sample_tokens = ["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"]

    # Generate normal logs
    for i in range(100):
        log_idx += 1
        svc = rng.choice(SERVICES)
        trace_id = f"trace_{rng.randint(100000, 999999):08x}"
        span_id = f"span_{rng.randint(1000, 9999):04x}"
        t = base_time + timedelta(seconds=rng.randint(0, 3600))
        email = rng.choice(sample_emails)
        card = rng.choice(sample_cards)
        jwt = rng.choice(sample_tokens)

        # Injected sensitive PII into log body
        msg = f"Processed checkout order for user {email} card {card} with auth Bearer {jwt} status 200 OK"
        logs.append({
            "log_id": f"log_{log_idx}",
            "timestamp": t.isoformat(),
            "service": svc,
            "level": "INFO",
            "message": msg,
            "trace_id": trace_id,
            "span_id": span_id,
            "attributes": {"http_status": 200}
        })

    # Generate incident logs during cascade (minute 15-25)
    t_inc = base_time + timedelta(seconds=900)
    for i in range(60):
        log_idx += 1
        t = t_inc + timedelta(seconds=rng.randint(0, 600))
        email = rng.choice(sample_emails)
        card = rng.choice(sample_cards)
        trace_id = f"trace_fail_{i:04x}"

        if i % 3 == 0:
            msg = f"ERROR: orders-postgres-primary lock acquisition failed on orders_v2 for customer {email} payment_token Bearer sk_live_secret_key_891238917238: lock timeout after 5000ms"
            svc = "orders-postgres-primary"
            lvl = "ERROR"
        elif i % 3 == 1:
            msg = f"CRITICAL: checkout-api failed calling orders-postgres-primary. Client {email} card {card} failed with DBConnectionTimeoutException"
            svc = "checkout-api"
            lvl = "CRITICAL"
        else:
            msg = f"WARN: api-gateway route /v1/checkout/confirm timed out after 5000ms for user {email}. Sending HTTP 504 to client"
            svc = "api-gateway"
            lvl = "WARNING"

        logs.append({
            "log_id": f"log_{log_idx}",
            "timestamp": t.isoformat(),
            "service": svc,
            "level": lvl,
            "message": msg,
            "trace_id": trace_id,
            "span_id": f"span_{i:04x}",
            "attributes": {"http_status": 504 if svc == "api-gateway" else 500}
        })

    logs.sort(key=lambda x: x["timestamp"])
    return logs


def generate_past_incidents() -> List[Dict[str, Any]]:
    """Generates historical casebook seed data for the Self-Evolving Agent (SEA)."""
    return [
        {
            "case_id": "CASE-HIST-001",
            "symptom_signature": "orders-postgres-primary:high_cpu:lock_contention",
            "title": "Nightly Automated Backup pg_dump Maintenance",
            "category": "MAINTENANCE_SCHEDULED",
            "historical_outcome": "BENIGN_NOISE",
            "context_conditions": {
                "time_window": "02:00-03:00 UTC",
                "cron_job_active": "pg_dump_nightly",
                "downstream_latency_spike": False,
                "error_rate_spike": False,
                "customer_impact": False
            },
            "remediation_recommendation": "Suppress alert if executed during scheduled 02:00 maintenance window with 0 downstream error rate.",
            "verified_by": "lead-sre-alice",
            "version": 1
        },
        {
            "case_id": "CASE-HIST-002",
            "symptom_signature": "orders-postgres-primary:high_cpu:lock_contention",
            "title": "Unindexed Table Lock Contention on orders_v2 during Flash Sale",
            "category": "DATABASE_OUTAGE",
            "historical_outcome": "VERIFIED_INCIDENT",
            "context_conditions": {
                "time_window": "14:00-16:00 UTC",
                "cron_job_active": None,
                "downstream_latency_spike": True,
                "error_rate_spike": True,
                "customer_impact": True
            },
            "remediation_recommendation": "Kill blocking transaction PID with pg_terminate_backend; scale connection pool.",
            "verified_by": "staff-dba-bob",
            "version": 1
        },
        {
            "case_id": "CASE-HIST-003",
            "symptom_signature": "redis-cache:connection_jitter:flapping",
            "title": "Transient Kubernetes Node Rotation Redis Flap",
            "category": "NETWORK_FLAP",
            "historical_outcome": "BENIGN_NOISE",
            "context_conditions": {
                "duration_seconds": "<120",
                "downstream_latency_spike": False,
                "error_rate_spike": False,
                "customer_impact": False
            },
            "remediation_recommendation": "Deduplicate and suppress flapping Redis heartbeat alerts under 2 minutes.",
            "verified_by": "infra-sre-carol",
            "version": 1
        }
    ]


def generate_ground_truth() -> Dict[str, Any]:
    """Generates benchmark scenarios with explicit expected outcomes for automated test verification."""
    return {
        "scenarios": {
            "scenario_1_postgres_cascade": {
                "name": "Postgres Lock Contention & Connection Exhaustion Cascade",
                "window": {"start": "2026-11-19T14:15:00Z", "end": "2026-11-19T14:30:00Z"},
                "expected_verdict": "VERIFIED_INCIDENT",
                "expected_root_cause": "orders-postgres-primary",
                "expected_severity": "CRITICAL",
                "expected_causal_chain": ["orders-postgres-primary", "checkout-api", "api-gateway"],
                "expected_context_divergence": False,
                "min_compression_ratio": 0.85
            },
            "scenario_2_benign_backup": {
                "name": "Nightly 02:00 pg_dump Backup (Case A - Same Symptom, Same Benign Context)",
                "window": {"start": "2026-11-19T02:00:00Z", "end": "2026-11-19T02:15:00Z"},
                "expected_verdict": "SUPPRESSED_NOISE",
                "expected_root_cause": "orders-postgres-primary",
                "expected_historical_match": "CASE-HIST-001",
                "expected_context_divergence": False
            },
            "scenario_3_context_divergence": {
                "name": "Midday Lock Spike (Case B - Same Symptom, Divergent Context)",
                "window": {"start": "2026-11-19T14:15:00Z", "end": "2026-11-19T14:30:00Z"},
                "expected_verdict": "VERIFIED_INCIDENT",
                "expected_root_cause": "orders-postgres-primary",
                "expected_historical_match": "CASE-HIST-001",
                "expected_context_divergence": True,
                "divergence_trigger": "Downstream latency spike and non-maintenance midday time window"
            },
            "scenario_4_transient_flap": {
                "name": "Redis Heartbeat Flapping Noise",
                "expected_verdict": "SUPPRESSED_NOISE",
                "expected_root_cause": "redis-cache",
                "is_flapping": True
            }
        }
    }


def write_all():
    base_time = get_base_timestamp()

    # 1. Alerts JSONL
    alerts = generate_alerts(base_time)
    alerts_path = DATA_DIR / "alerts.jsonl"
    with open(alerts_path, "w", encoding="utf-8") as f:
        for a in alerts:
            f.write(json.dumps(a) + "\n")
    print(f"Generated {len(alerts)} alerts -> {alerts_path}")

    # 2. Metrics Timeseries CSV
    timeseries = generate_timeseries(base_time, duration_minutes=60)
    metrics_path = DATA_DIR / "metrics_timeseries.csv"
    with open(metrics_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["timestamp", "service", "metric_name", "value"])
        writer.writeheader()
        writer.writerows(timeseries)
    print(f"Generated {len(timeseries)} metric points -> {metrics_path}")

    # 3. Logs JSONL
    logs = generate_logs(base_time)
    logs_path = DATA_DIR / "logs.jsonl"
    with open(logs_path, "w", encoding="utf-8") as f:
        for l in logs:
            f.write(json.dumps(l) + "\n")
    print(f"Generated {len(logs)} logs -> {logs_path}")

    # 4. Past Incidents Seed JSON
    past = generate_past_incidents()
    past_path = DATA_DIR / "past_incidents_seed.json"
    with open(past_path, "w", encoding="utf-8") as f:
        json.dump(past, f, indent=2)
    print(f"Generated {len(past)} historical cases -> {past_path}")

    # 5. Ground Truth JSON
    gt = generate_ground_truth()
    gt_path = DATA_DIR / "ground_truth.json"
    with open(gt_path, "w", encoding="utf-8") as f:
        json.dump(gt, f, indent=2)
    print(f"Generated ground truth benchmark -> {gt_path}")


if __name__ == "__main__":
    write_all()
