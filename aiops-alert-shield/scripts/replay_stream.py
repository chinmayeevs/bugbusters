"""
scripts/replay_stream.py
Live 400-Alert Stream Replay Engine for aiops-alert-shield.
Streams alerts from data/alerts.jsonl in micro-batches through PipelineOrchestrator,
updating live telemetry counters and broadcasting real-time WebSocket progress.
Runnable as a standalone CLI or invoked via GraphQL mutation startStreamReplay.
"""

from __future__ import annotations
import argparse
import asyncio
import csv
import json
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.orchestration.pipeline_orchestrator import PipelineOrchestrator
from backend.storage.incident_repository import IncidentRepository
from backend.storage.case_repository import CaseRepository

# Module-level state tracking for polling & UI streaming
REPLAY_STATE: Dict[str, Any] = {
    "replay_id": "",
    "is_running": False,
    "progress_pct": 0.0,
    "raw_count": 0,
    "collapsed_count": 0,
    "suppressed_blips": 0,
    "verified_count": 0,
    "current_scenario": "IDLE",
    "latest_message": "Stream replay idle.",
    "started_at": None,
    "completed_at": None
}


async def run_stream_replay(
    speed_multiplier: float = 5.0,
    include_sea_cases: bool = True,
    data_dir: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Executes the micro-batched 400-alert stream replay.
    """
    global REPLAY_STATE

    replay_id = f"RPL-{int(time.time())}-{uuid.uuid4().hex[:4].upper()}"
    REPLAY_STATE.update({
        "replay_id": replay_id,
        "is_running": True,
        "progress_pct": 0.0,
        "raw_count": 0,
        "collapsed_count": 0,
        "suppressed_blips": 0,
        "verified_count": 0,
        "current_scenario": "INITIALIZING",
        "latest_message": "Loading 400-alert stream dataset...",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None
    })

    base_dir = data_dir or (Path(__file__).resolve().parent.parent / "data")
    alerts_file = base_dir / "alerts.jsonl"
    metrics_file = base_dir / "metrics_timeseries.csv"
    logs_file = base_dir / "logs.jsonl"

    alerts: List[Dict[str, Any]] = []
    if alerts_file.exists():
        with open(alerts_file, "r", encoding="utf-8") as f:
            alerts = [json.loads(line) for line in f if line.strip()]

    metrics: List[Dict[str, Any]] = []
    if metrics_file.exists():
        with open(metrics_file, "r", encoding="utf-8") as f:
            metrics = list(csv.DictReader(f))

    logs: List[Dict[str, Any]] = []
    if logs_file.exists():
        with open(logs_file, "r", encoding="utf-8") as f:
            logs = [json.loads(line) for line in f if line.strip()]

    total_alerts = len(alerts)
    if total_alerts == 0:
        REPLAY_STATE.update({
            "is_running": False,
            "progress_pct": 100.0,
            "latest_message": "No alerts found to replay."
        })
        return REPLAY_STATE

    batch_size = 28  # ~16-17 batches for 470 alerts
    batches = [alerts[i:i + batch_size] for i in range(0, total_alerts, batch_size)]
    extra_steps = 2 if include_sea_cases else 0
    total_steps = len(batches) + extra_steps

    orchestrator = PipelineOrchestrator(
        incident_repo=IncidentRepository(),
        case_repo=CaseRepository()
    )

    step_delay = max(0.05, 0.75 / max(0.1, speed_multiplier))

    try:
        # Replay raw alert batches
        for idx, batch in enumerate(batches):
            # Calculate corresponding slice of metrics and logs
            metric_slice = metrics[:min(len(metrics), (idx + 1) * 35)]
            log_slice = logs[:min(len(logs), (idx + 1) * 10)]

            first_msg = batch[0].get("message", "")[:45] if batch else ""
            REPLAY_STATE["current_scenario"] = f"Batch {idx + 1}/{total_steps}: {batch[0].get('service', 'system')}"
            REPLAY_STATE["latest_message"] = f"Ingesting {len(batch)} alerts: '{first_msg}'..."

            inc = await orchestrator.run_pipeline(
                raw_alerts=batch,
                raw_metrics=metric_slice,
                raw_logs=log_slice,
                force_mock_ai=True
            )

            pkt = inc.evidence_packet
            REPLAY_STATE["raw_count"] += len(batch)
            collapsed_in_batch = max(0, pkt.raw_alert_count - pkt.compressed_alert_count)
            REPLAY_STATE["collapsed_count"] += collapsed_in_batch

            blips_in_batch = sum(c.count for c in pkt.deduplicated_clusters if c.is_flapping)
            REPLAY_STATE["suppressed_blips"] += blips_in_batch

            if inc.status == "VERIFIED_INCIDENT":
                REPLAY_STATE["verified_count"] += 1

            step_idx = idx + 1
            REPLAY_STATE["progress_pct"] = round((step_idx / total_steps) * 100.0, 1)

            # Broadcast update via PIPELINE_EVENT_QUEUE
            try:
                from backend.graphql.subscriptions import PIPELINE_EVENT_QUEUE
                PIPELINE_EVENT_QUEUE.put_nowait({
                    "type": "REPLAY_PROGRESS",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "data": {
                        "replay_id": replay_id,
                        "raw_count": REPLAY_STATE["raw_count"],
                        "collapsed_count": REPLAY_STATE["collapsed_count"],
                        "suppressed_blips": REPLAY_STATE["suppressed_blips"],
                        "verified_count": REPLAY_STATE["verified_count"],
                        "progress_pct": REPLAY_STATE["progress_pct"],
                        "current_scenario": REPLAY_STATE["current_scenario"]
                    }
                })
            except Exception:
                pass

            await asyncio.sleep(step_delay)

        # Replay SEA Case A (Benign Backup)
        if include_sea_cases:
            REPLAY_STATE["current_scenario"] = "SEA Case A: 02:00 pg_dump Scheduled Backup Repeat"
            REPLAY_STATE["latest_message"] = "Testing benign scheduled maintenance pattern recognition..."

            case_a_alert = [{
                "alert_id": f"alt_sea_a_{uuid.uuid4().hex[:6]}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "service": "orders-postgres-primary",
                "alert_name": "PostgresHighCPUContention",
                "severity": "WARNING",
                "metric_name": "cpu_pct",
                "metric_value": 91.5,
                "threshold": 85.0,
                "message": "High CPU utilization during pg_dump backup"
            }]
            inc_a = await orchestrator.run_pipeline(
                raw_alerts=case_a_alert,
                raw_metrics=metrics[:15],
                raw_logs=[],
                runtime_context={
                    "time_window": "02:00-03:00 UTC",
                    "cron_job_active": "pg_dump_nightly",
                    "downstream_latency_spike": False,
                    "customer_impact": False
                },
                force_mock_ai=True
            )
            REPLAY_STATE["raw_count"] += 1
            if inc_a.status == "VERIFIED_INCIDENT":
                REPLAY_STATE["verified_count"] += 1
            else:
                REPLAY_STATE["suppressed_blips"] += 1

            REPLAY_STATE["progress_pct"] = round(((len(batches) + 1) / total_steps) * 100.0, 1)
            await asyncio.sleep(step_delay)

            # Replay SEA Case B (Context Divergence Escalation)
            REPLAY_STATE["current_scenario"] = "SEA Case B: Midday Peak Lock Contention (Context Divergence)"
            REPLAY_STATE["latest_message"] = "Context divergence detected! Suppressing blocked, escalating to P0 incident..."

            case_b_alert = [{
                "alert_id": f"alt_sea_b_{uuid.uuid4().hex[:6]}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "service": "orders-postgres-primary",
                "alert_name": "PostgresHighCPUContention",
                "severity": "WARNING",
                "metric_name": "cpu_pct",
                "metric_value": 94.0,
                "threshold": 85.0,
                "message": "High CPU utilization on orders-postgres-primary"
            }]
            inc_b = await orchestrator.run_pipeline(
                raw_alerts=case_b_alert,
                raw_metrics=metrics[:25],
                raw_logs=logs[:8],
                runtime_context={
                    "time_window": "14:15 UTC (Midday Peak)",
                    "cron_job_active": None,
                    "downstream_latency_spike": True,
                    "customer_impact": True
                },
                force_mock_ai=True
            )
            REPLAY_STATE["raw_count"] += 1
            if inc_b.status == "VERIFIED_INCIDENT":
                REPLAY_STATE["verified_count"] += 1
            REPLAY_STATE["progress_pct"] = 100.0

        REPLAY_STATE.update({
            "is_running": False,
            "progress_pct": 100.0,
            "current_scenario": "COMPLETED",
            "latest_message": f"Stream replay complete. Processed {REPLAY_STATE['raw_count']} alerts, collapsed {REPLAY_STATE['collapsed_count']} redundant signals.",
            "completed_at": datetime.now(timezone.utc).isoformat()
        })

    except Exception as e:
        REPLAY_STATE.update({
            "is_running": False,
            "current_scenario": "ERROR",
            "latest_message": f"Stream replay encountered error: {str(e)}",
            "completed_at": datetime.now(timezone.utc).isoformat()
        })
        raise

    return REPLAY_STATE


def main():
    parser = argparse.ArgumentParser(description="Live 400-Alert Stream Replay Engine")
    parser.add_argument("--speed", type=float, default=5.0, help="Playback speed multiplier (e.g. 1.0, 5.0, 10.0)")
    parser.add_argument("--include-sea", action="store_true", default=True, help="Include SEA Case A & B scenarios")
    args = parser.parse_args()

    print("================================================================================")
    print(f"  AIOPS ALERT SHIELD // LIVE STREAM REPLAY (Speed: {args.speed}x)")
    print("================================================================================")

    res = asyncio.run(run_stream_replay(speed_multiplier=args.speed, include_sea_cases=args.include_sea))
    print(f"\nReplay Finished:")
    print(f"  Raw Alerts Ingested:    {res['raw_count']}")
    print(f"  Collapsed Redundancies: {res['collapsed_count']}")
    print(f"  Suppressed Blips:       {res['suppressed_blips']}")
    print(f"  Verified Incidents:     {res['verified_count']}")
    print(f"  Status:                 {res['latest_message']}")


if __name__ == "__main__":
    main()
