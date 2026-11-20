"""
tests/test_sea_cases.py
Tests Self-Evolving Agent (SEA) casebook touchpoints:
  Case A: Same symptom + same benign context (02:00 pg_dump CPU spike) -> Benign match, no divergence.
  Case B: Same symptom + divergent context (midday lock timeout, no backup, downstream latency spike) -> Context Divergence detected!
  Write Path: Appends versioned entries from verified outcomes and engineer resolution.
"""

import pytest
from pathlib import Path
from backend.storage.case_repository import CaseRepository
from agents.self_evolving_agent import SelfEvolvingAgent
from backend.models.contracts import ComputeResult, BlastRadiusReport, Incident


@pytest.fixture
def temp_case_repo(tmp_path):
    db_file = tmp_path / "test_casebook.db"
    repo = CaseRepository(db_path=db_file)
    return repo


def test_sea_case_a_benign_match_no_divergence(temp_case_repo):
    sea = SelfEvolvingAgent(case_repo=temp_case_repo)

    # Symptom: orders-postgres-primary CPU / lock
    # Context A: Nightly maintenance window, backup running, zero downstream latency or errors
    packet = ComputeResult(
        trace_id="trc_sea_a",
        timestamp="2026-11-19T02:10:00Z",
        raw_alert_count=10,
        compressed_alert_count=2,
        compression_ratio=0.8,
        deduplicated_clusters=[],
        anomalies=[],
        correlations=[],
        blast_radius=BlastRadiusReport(
            evidence_id="EVID-BLAST-001",
            root_suspect="orders-postgres-primary",
            compromised_services=["orders-postgres-primary"],
            critical_path_affected=False,
            blast_radius_score=0.2,
            customer_facing_impact=False,
            nodes=[]
        ),
        redacted_logs=[],
        symptom_signature="orders-postgres-primary:high_cpu:lock_contention",
        risk_score=0.2,
        deterministic_severity="BENIGN",
        all_evidence_ids=["EVID-STAT-001"]
    )

    runtime_ctx = {
        "time_window": "02:00-03:00 UTC",
        "cron_job_active": "pg_dump_nightly",
        "downstream_latency_spike": False,
        "error_rate_spike": False,
        "customer_impact": False
    }

    matches, divergence_flag, div_reason = sea.evaluate_historical_context(packet, runtime_context=runtime_ctx)

    assert len(matches) > 0
    # CASE-HIST-001 should match with benign outcome
    top_match = matches[0]
    assert top_match.case_id == "CASE-HIST-001"
    assert top_match.historical_outcome == "BENIGN_NOISE"
    # Case A: context conditions match -> NO divergence!
    assert divergence_flag is False
    assert div_reason is None


def test_sea_case_b_context_divergence_detected(temp_case_repo):
    sea = SelfEvolvingAgent(case_repo=temp_case_repo)

    # Symptom: Exactly same symptom signature: orders-postgres-primary:high_cpu:lock_contention
    # Context B: Midday 14:15, NO backup running, downstream checkout latency spiked to 4200ms!
    packet = ComputeResult(
        trace_id="trc_sea_b",
        timestamp="2026-11-19T14:15:00Z",
        raw_alert_count=200,
        compressed_alert_count=15,
        compression_ratio=0.92,
        deduplicated_clusters=[],
        anomalies=[],
        correlations=[],
        blast_radius=BlastRadiusReport(
            evidence_id="EVID-BLAST-002",
            root_suspect="orders-postgres-primary",
            compromised_services=["orders-postgres-primary", "checkout-api", "api-gateway"],
            critical_path_affected=True,
            blast_radius_score=0.8,
            customer_facing_impact=True,
            nodes=[]
        ),
        redacted_logs=[],
        symptom_signature="orders-postgres-primary:high_cpu:lock_contention",
        risk_score=0.9,
        deterministic_severity="CRITICAL",
        all_evidence_ids=["EVID-STAT-018", "EVID-BLAST-002"]
    )

    runtime_ctx = {
        "time_window": "14:15 UTC",
        "cron_job_active": None,
        "downstream_latency_spike": True,
        "error_rate_spike": True,
        "customer_impact": True
    }

    matches, divergence_flag, div_reason = sea.evaluate_historical_context(packet, runtime_context=runtime_ctx)

    assert len(matches) > 0
    # Case B: Context conditions diverged sharply from the benign 02:00 case -> Divergence MUST BE FLAGGED!
    assert divergence_flag is True
    assert div_reason is not None
    assert "latency" in div_reason.lower() or "active" in div_reason.lower()


def test_sea_write_path_versioned_append(temp_case_repo):
    sea = SelfEvolvingAgent(case_repo=temp_case_repo)

    # Construct verified incident
    packet = ComputeResult(
        trace_id="trc_sea_write",
        timestamp="2026-11-19T14:45:00Z",
        raw_alert_count=50,
        compressed_alert_count=4,
        compression_ratio=0.92,
        deduplicated_clusters=[],
        anomalies=[],
        correlations=[],
        blast_radius=BlastRadiusReport(
            evidence_id="EVID-BLAST-003",
            root_suspect="redis-cache",
            compromised_services=["redis-cache", "checkout-api"],
            critical_path_affected=True,
            blast_radius_score=0.6,
            customer_facing_impact=True,
            nodes=[]
        ),
        redacted_logs=[],
        symptom_signature="redis-cache:eviction_rate:high_memory",
        risk_score=0.75,
        deterministic_severity="HIGH",
        all_evidence_ids=["EVID-STAT-005"]
    )

    incident = Incident(
        incident_id="INC-20261119-TESTWRITE",
        trace_id="trc_sea_write",
        title="HIGH: Redis Memory Eviction Storm",
        status="VERIFIED_INCIDENT",
        severity="HIGH",
        created_at="2026-11-19T14:45:00Z",
        updated_at="2026-11-19T14:45:00Z",
        root_cause_service="redis-cache",
        confidence_score=0.94,
        context_divergence_flag=False,
        context_badge="NORMAL",
        evidence_packet=packet,
        resolved_by="staff-sre-dave"
    )

    case_id = sea.record_verified_outcome(incident)
    assert case_id is not None

    # Check casebook in database
    matches = temp_case_repo.search_matches("redis-cache:eviction_rate:high_memory", {})
    assert len(matches) > 0
    matched = [m for m in matches if m.case_id == case_id]
    assert len(matched) == 1
    assert matched[0].title == "HIGH: Redis Memory Eviction Storm"
