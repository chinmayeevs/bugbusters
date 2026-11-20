"""
scripts/evaluate_system.py
Deterministic Ground-Truth Evaluation Engine for aiops-alert-shield.
Runs automated benchmarks measuring recall, precision, compression, SEA Case A/B handling,
evidence traceability, fail-open enforcement, and stage latencies against data/ground_truth.json.
"""

from __future__ import annotations
import asyncio
import csv
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.orchestration.pipeline_orchestrator import PipelineOrchestrator
from backend.storage.incident_repository import IncidentRepository
from backend.storage.case_repository import CaseRepository


async def run_system_evaluation(data_dir: Path | None = None, force_mock_ai: bool = False) -> Dict[str, Any]:
    """
    Executes the comprehensive automated benchmark suite against ground-truth scenarios.
    Returns a structured evaluation scorecard dictionary and persists report to data/evaluation_report.json.
    """
    base_dir = data_dir or (Path(__file__).resolve().parent.parent / "data")
    ground_truth_file = base_dir / "ground_truth.json"
    alerts_file = base_dir / "alerts.jsonl"
    logs_file = base_dir / "logs.jsonl"
    metrics_file = base_dir / "metrics_timeseries.csv"

    # Load ground truth spec
    with open(ground_truth_file, "r", encoding="utf-8") as f:
        ground_truth = json.load(f)["scenarios"]

    # Load raw telemetry
    with open(alerts_file, "r", encoding="utf-8") as f:
        all_alerts = [json.loads(line) for line in f]
    with open(logs_file, "r", encoding="utf-8") as f:
        all_logs = [json.loads(line) for line in f]
    with open(metrics_file, "r", encoding="utf-8") as f:
        all_metrics = list(csv.DictReader(f))

    # Isolated repos for benchmark run
    incident_repo = IncidentRepository()
    case_repo = CaseRepository()
    orchestrator = PipelineOrchestrator(incident_repo=incident_repo, case_repo=case_repo)

    latencies: List[float] = []
    breakdowns: List[Dict[str, Any]] = []

    # -------------------------------------------------------------------------
    # 1. Evaluate Scenario 1: Primary Postgres Cascade (P0 Verified Incident)
    # -------------------------------------------------------------------------
    t0 = time.perf_counter()
    inc1 = await orchestrator.run_pipeline(
        raw_alerts=all_alerts,
        raw_metrics=all_metrics,
        raw_logs=all_logs,
        runtime_context={"cron_job_active": None, "downstream_latency_spike": True},
        force_mock_ai=force_mock_ai
    )
    lat1 = round((time.perf_counter() - t0) * 1000, 2)
    latencies.append(lat1)

    s1_spec = ground_truth["scenario_1_postgres_cascade"]
    s1_passed = (
        inc1.status == s1_spec["expected_verdict"]
        and inc1.root_cause_service == s1_spec["expected_root_cause"]
        and inc1.severity == s1_spec["expected_severity"]
    )
    breakdowns.append({
        "scenario_key": "scenario_1_postgres_cascade",
        "scenario_name": s1_spec["name"],
        "expected_verdict": s1_spec["expected_verdict"],
        "detected_verdict": inc1.status,
        "expected_root_cause": s1_spec["expected_root_cause"],
        "detected_root_cause": inc1.root_cause_service,
        "latency_ms": lat1,
        "passed": s1_passed
    })

    # Evidence traceability on Scenario 1
    cited_ids = inc1.risk_validation.referenced_evidence_ids if inc1.risk_validation else []
    valid_ids_set = set(inc1.evidence_packet.all_evidence_ids)
    traceability_matched = sum(1 for cid in cited_ids if cid in valid_ids_set)
    traceability_pct = round((traceability_matched / max(1, len(cited_ids))) * 100.0, 1) if cited_ids else 100.0

    # Compression ratio on Scenario 1
    raw_alert_count = inc1.evidence_packet.raw_alert_count
    compressed_count = inc1.evidence_packet.compressed_alert_count
    compression_pct = round((1.0 - (compressed_count / max(1, raw_alert_count))) * 100.0, 1)

    # -------------------------------------------------------------------------
    # 2. Evaluate Scenario 2: SEA Case A (Benign 02:00 pg_dump Backup Repeat)
    # -------------------------------------------------------------------------
    s2_spec = ground_truth["scenario_2_benign_backup"]
    s2_alerts = [
        {
            "alert_id": "alt_eval_backup_01",
            "timestamp": "2026-11-19T02:05:00Z",
            "service": "orders-postgres-primary",
            "alert_name": "PostgresHighCPUContention",
            "severity": "WARNING",
            "metric_name": "cpu_pct",
            "metric_value": 92.5,
            "threshold": 85.0,
            "message": "High CPU utilization on orders-postgres-primary during pg_dump backup"
        }
    ]
    s2_metrics = [
        {"timestamp": f"2026-11-19T02:{i:02d}:00Z", "service": "orders-postgres-primary", "metric_name": "cpu_pct", "value": "92.0"}
        for i in range(8)
    ]
    t0 = time.perf_counter()
    inc2 = await orchestrator.run_pipeline(
        raw_alerts=s2_alerts,
        raw_metrics=s2_metrics,
        raw_logs=[],
        runtime_context={
            "time_window": "02:00-03:00 UTC",
            "cron_job_active": "pg_dump_nightly",
            "downstream_latency_spike": False,
            "error_rate_spike": False,
            "customer_impact": False
        },
        force_mock_ai=force_mock_ai
    )
    lat2 = round((time.perf_counter() - t0) * 1000, 2)
    latencies.append(lat2)

    sea_case_a_passed = (
        inc2.status == "SUPPRESSED_NOISE"
        and not inc2.context_divergence_flag
        and any(m.historical_outcome == "BENIGN_NOISE" for m in inc2.evidence_packet.historical_matches)
    )
    breakdowns.append({
        "scenario_key": "scenario_2_benign_backup",
        "scenario_name": s2_spec["name"],
        "expected_verdict": s2_spec["expected_verdict"],
        "detected_verdict": inc2.status,
        "historical_match_id": inc2.evidence_packet.historical_matches[0].case_id if inc2.evidence_packet.historical_matches else None,
        "context_divergence_detected": inc2.context_divergence_flag,
        "latency_ms": lat2,
        "passed": sea_case_a_passed
    })

    # -------------------------------------------------------------------------
    # 3. Evaluate Scenario 3: SEA Case B (Context Divergence Escalation)
    # -------------------------------------------------------------------------
    s3_spec = ground_truth["scenario_3_context_divergence"]
    t0 = time.perf_counter()
    inc3 = await orchestrator.run_pipeline(
        raw_alerts=s2_alerts,  # Same symptom!
        raw_metrics=all_metrics[:20],
        raw_logs=all_logs[:5],
        runtime_context={
            "time_window": "14:15 UTC (Midday Peak)",
            "cron_job_active": None,
            "downstream_latency_spike": True,
            "error_rate_spike": True,
            "customer_impact": True
        },
        force_mock_ai=force_mock_ai
    )
    lat3 = round((time.perf_counter() - t0) * 1000, 2)
    latencies.append(lat3)

    sea_case_b_passed = (
        inc3.context_divergence_flag is True
        and inc3.status == "VERIFIED_INCIDENT"
        and inc3.severity == "CRITICAL"
    )
    breakdowns.append({
        "scenario_key": "scenario_3_context_divergence",
        "scenario_name": s3_spec["name"],
        "expected_verdict": s3_spec["expected_verdict"],
        "detected_verdict": inc3.status,
        "context_divergence_detected": inc3.context_divergence_flag,
        "maker_checker_status": inc3.risk_validation.maker_checker_status if inc3.risk_validation else "PASSED",
        "latency_ms": lat3,
        "passed": sea_case_b_passed
    })

    # -------------------------------------------------------------------------
    # 4. Evaluate Fail-Open Path (AI Layer Failure on Critical Breach)
    # -------------------------------------------------------------------------
    t0 = time.perf_counter()
    inc_fo = await orchestrator.run_pipeline(
        raw_alerts=all_alerts,
        raw_metrics=all_metrics,
        raw_logs=all_logs,
        force_ai_failure=True
    )
    lat_fo = round((time.perf_counter() - t0) * 1000, 2)
    latencies.append(lat_fo)

    fail_open_passed = (
        inc_fo.status == "FAIL_OPEN_CRITICAL"
        and inc_fo.severity == "CRITICAL"
        and inc_fo.confidence_score == 1.0
    )
    breakdowns.append({
        "scenario_key": "fail_open_outage_simulation",
        "scenario_name": "Simulated AI Layer Outage with Critical Deterministic DB Breach",
        "expected_verdict": "FAIL_OPEN_CRITICAL",
        "detected_verdict": inc_fo.status,
        "deterministic_severity": inc_fo.severity,
        "confidence": inc_fo.confidence_score,
        "latency_ms": lat_fo,
        "passed": fail_open_passed
    })

    # -------------------------------------------------------------------------
    # Aggregate Metrics Calculation
    # -------------------------------------------------------------------------
    true_incidents_expected = 3  # Scenario 1, Scenario 3, Fail-Open Critical
    true_incidents_detected = sum(1 for inc in [inc1, inc3, inc_fo] if inc.status in ("VERIFIED_INCIDENT", "FAIL_OPEN_CRITICAL"))
    incident_recall_ratio = true_incidents_detected / true_incidents_expected

    # Precision: no false alarms reaching feed
    false_positives = 1 if inc2.status == "VERIFIED_INCIDENT" else 0
    total_feed_incidents = true_incidents_detected + false_positives
    precision_pct = round((true_incidents_detected / max(1, total_feed_incidents)) * 100.0, 1)

    latencies_sorted = sorted(latencies)
    p50_ms = latencies_sorted[len(latencies_sorted) // 2]
    p95_ms = latencies_sorted[int(len(latencies_sorted) * 0.95)]

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    report: Dict[str, Any] = {
        "benchmark_timestamp": now_iso,
        "overall_status": "PASSED" if (incident_recall_ratio == 1.0 and sea_case_a_passed and sea_case_b_passed and fail_open_passed) else "FAILED",
        "metrics": {
            "incident_recall": f"{true_incidents_detected} / {true_incidents_expected} ({incident_recall_ratio * 100:.1f}%)",
            "incident_recall_pct": round(incident_recall_ratio * 100.0, 1),
            "alert_compression_pct": compression_pct,
            "verifier_precision_pct": precision_pct,
            "evidence_traceability_pct": traceability_pct,
            "sea_case_a_passed": sea_case_a_passed,
            "sea_case_b_passed": sea_case_b_passed,
            "fail_open_passed": fail_open_passed,
            "pipeline_latency_ms": {
                "p50": p50_ms,
                "p95": p95_ms,
                "min": latencies_sorted[0],
                "max": latencies_sorted[-1]
            }
        },
        "per_incident_breakdown": breakdowns
    }

    # Persist report
    out_file = base_dir / "evaluation_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    return report


def main():
    print("=" * 80)
    print("  AIOPS ALERT SHIELD // GROUND-TRUTH EVALUATION & AUDIT RUNNER")
    print("=" * 80)
    print("Executing full pipeline verification against data/ground_truth.json ...\n")

    report = asyncio.run(run_system_evaluation())

    m = report["metrics"]
    print("+" + "-" * 78 + "+")
    print(f"| BENCHMARK SCORECARD: {report['overall_status']:<57} |")
    print("+" + "-" * 78 + "+")
    print(f"| Incident Recall:            {m['incident_recall']:<48} |")
    print(f"| Alert Noise Compression:    {m['alert_compression_pct']}%{'':<51} |")
    print(f"| Verifier Precision:         {m['verifier_precision_pct']}%{'':<51} |")
    print(f"| Evidence Traceability:      {m['evidence_traceability_pct']}%{'':<51} |")
    print(f"| SEA Case A (Benign Repeat): {'PASSED (Recognized & Suppressed)' if m['sea_case_a_passed'] else 'FAILED':<48} |")
    print(f"| SEA Case B (Divergence):    {'PASSED (Detected & Escalated)' if m['sea_case_b_passed'] else 'FAILED':<48} |")
    print(f"| Fail-Open Path Guarantee:   {'PASSED (Mandatory P0 Published)' if m['fail_open_passed'] else 'FAILED':<48} |")
    print(f"| Pipeline Latency (p50/p95): {m['pipeline_latency_ms']['p50']}ms / {m['pipeline_latency_ms']['p95']}ms{'':<43} |")
    print("+" + "-" * 78 + "+")

    print("\n[ SCENARIO BREAKDOWN ]")
    for s in report["per_incident_breakdown"]:
        status_sym = "[ PASS ]" if s["passed"] else "[ FAIL ]"
        print(f"  {status_sym} {s['scenario_name']:<60} ({s['latency_ms']}ms)")
        print(f"          Expected: {s['expected_verdict']} | Detected: {s['detected_verdict']}")

    print("\nReport successfully written to data/evaluation_report.json.\n")


if __name__ == "__main__":
    main()
