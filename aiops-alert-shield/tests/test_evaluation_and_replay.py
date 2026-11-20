"""
tests/test_evaluation_and_replay.py
Comprehensive test suite verifying:
1. Automated ground-truth evaluation engine (recall, precision, compression, SEA Case A & B, fail-open)
2. Live 400-alert stream replay engine execution and telemetry counters
3. "No Silent Suppression" audit logging and engineer escalation override
4. SEA casebook vector cosine similarity and context matching
"""

import pytest
import asyncio
import time
from pathlib import Path
from scripts.evaluate_system import run_system_evaluation
from scripts.replay_stream import run_stream_replay, REPLAY_STATE
from backend.storage.incident_repository import IncidentRepository
from backend.storage.case_repository import CaseRepository, compute_vector_cosine_similarity


@pytest.mark.asyncio
async def test_evaluation_engine_benchmark():
    """Verify ground-truth evaluation runner passes 100% of benchmark criteria."""
    report = await run_system_evaluation(force_mock_ai=True)

    assert report["overall_status"] == "PASSED"
    metrics = report["metrics"]
    assert metrics["incident_recall_pct"] == 100.0
    assert metrics["alert_compression_pct"] >= 70.0
    assert metrics["verifier_precision_pct"] == 100.0
    assert metrics["evidence_traceability_pct"] == 100.0
    assert metrics["sea_case_a_passed"] is True
    assert metrics["sea_case_b_passed"] is True
    assert metrics["fail_open_passed"] is True

    # Check that all 4 scenarios passed
    scenarios = report["per_incident_breakdown"]
    assert len(scenarios) == 4
    for s in scenarios:
        assert s["passed"] is True


@pytest.mark.asyncio
async def test_stream_replay_engine():
    """Verify live stream replay processes alerts in micro-batches and updates counters."""
    result = await run_stream_replay(speed_multiplier=50.0, include_sea_cases=False)

    assert result["is_running"] is False
    assert result["progress_pct"] == 100.0
    assert result["raw_count"] > 100
    assert result["collapsed_count"] > 0
    assert result["current_scenario"] == "COMPLETED"


def test_suppressed_events_audit_and_escalation():
    """Verify suppressed events are recorded and can be escalated to human review."""
    repo = IncidentRepository()
    test_event_id = f"SUP-TEST-{int(time.time() * 1000)}"

    repo.record_suppressed_events([{
        "event_id": test_event_id,
        "trace_id": "trc_test_suppression",
        "service": "inventory-service",
        "metric": "stock_reservation_timeout",
        "category": "TRANSIENT_BLIPS",
        "suppression_reason": "Single spike without downstream impact",
        "collapsed_count": 5,
        "mad_z_score": 1.4,
        "status": "SUPPRESSED"
    }])

    # Query events
    events = repo.list_suppressed_events(limit=50, category="TRANSIENT_BLIPS", trace_id="trc_test_suppression")
    found = [e for e in events if e["event_id"] == test_event_id]
    assert len(found) == 1
    assert found[0]["status"] == "SUPPRESSED"

    # Escalate event
    escalated = repo.escalate_suppressed_event(
        event_id=test_event_id,
        reason="Suspicious correlation with checkout timeout",
        escalated_by="lead_sre"
    )
    assert escalated is not None
    assert escalated["status"] == "ESCALATED"
    assert escalated["escalated_by"] == "lead_sre"

    # Verify escalated incident created in incidents table with bidirectional links
    expected_inc_id = f"INC-ESCALATED-{test_event_id.replace('SUP-', '')[:8]}"
    assert escalated.get("escalated_incident_id") == expected_inc_id
    inc = repo.get_incident(expected_inc_id)
    assert inc is not None
    assert inc.status == "NEEDS_HUMAN_REVIEW"
    assert inc.root_cause_service == "inventory-service"
    assert inc.escalated_from_event_id == test_event_id
    assert inc.escalation_reason == "Suspicious correlation with checkout timeout"


def test_sea_vector_cosine_similarity():
    """Verify cosine similarity calculation between symptom signatures."""
    sig1 = "orders-postgres-primary:cpu_pct:lock_timeout:exhaustion"
    sig2 = "orders-postgres-primary:cpu_pct:lock_timeout:exhaustion"
    sig3 = "orders-postgres-primary:cpu_pct:backup:pg_dump"
    sig4 = "redis-cache:memory_pct:eviction_storm"

    # Identical texts must equal 1.0
    sim_identical = compute_vector_cosine_similarity(sig1, sig2)
    assert sim_identical == 1.0

    # Partially overlapping texts must be > 0.0 and < 1.0
    sim_partial = compute_vector_cosine_similarity(sig1, sig3)
    assert 0.0 < sim_partial < 1.0

    # Orthogonal texts should be 0.0
    sim_orthogonal = compute_vector_cosine_similarity(sig1, sig4)
    assert sim_orthogonal == 0.0
