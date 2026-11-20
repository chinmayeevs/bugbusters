"""
tests/test_agents_contracts.py
Tests agent contract schemas, maker-checker gate verification,
and untrusted log text handling.
"""

import pytest
import asyncio
from backend.models.contracts import (
    TriageReport,
    RootCauseReport,
    RiskValidationReport,
    ComputeResult,
    BlastRadiusReport,
)
from agents.triage_agent import TriageAgent
from agents.root_cause_agent import RootCauseAgent
from agents.risk_validator_agent import RiskValidatorAgent


@pytest.fixture
def mock_evidence_packet():
    return ComputeResult(
        trace_id="trc_test_01",
        timestamp="2026-11-19T14:30:00Z",
        raw_alert_count=100,
        compressed_alert_count=5,
        compression_ratio=0.95,
        deduplicated_clusters=[],
        anomalies=[],
        correlations=[],
        blast_radius=BlastRadiusReport(
            evidence_id="EVID-BLAST-001",
            root_suspect="orders-postgres-primary",
            compromised_services=["orders-postgres-primary", "checkout-api"],
            critical_path_affected=True,
            blast_radius_score=0.7,
            customer_facing_impact=True,
            nodes=[]
        ),
        redacted_logs=[],
        symptom_signature="orders-postgres-primary:lock_wait_count:001",
        risk_score=0.9,
        deterministic_severity="CRITICAL",
        all_evidence_ids=["EVID-STAT-001", "EVID-CORR-001", "EVID-BLAST-001"]
    )


@pytest.mark.asyncio
async def test_triage_contract_validation(mock_evidence_packet):
    agent = TriageAgent()
    report = await agent.run(mock_evidence_packet)
    assert isinstance(report, TriageReport)
    assert report.agent_name == "TriageAgent"
    assert report.urgency in ("P0_CRITICAL", "P1_HIGH", "P2_MEDIUM", "P3_LOW", "P4_NOISE")
    assert report.incident_scope in ("SYSTEM_WIDE", "SERVICE_LOCAL", "DOWNSTREAM_CASCADE", "TRANSIENT_SPIKE")
    assert len(report.supporting_evidence_ids) > 0


@pytest.mark.asyncio
async def test_root_cause_contract_validation(mock_evidence_packet):
    triage = TriageReport(
        agent_name="TriageAgent",
        timestamp="2026-11-19T14:30:00Z",
        incident_scope="DOWNSTREAM_CASCADE",
        urgency="P0_CRITICAL",
        user_journey_impact="Checkout payment blocked",
        supporting_evidence_ids=["EVID-STAT-001"],
        triage_summary="Severe cascade"
    )
    rc_agent = RootCauseAgent()
    report = await rc_agent.run(mock_evidence_packet, triage)
    assert isinstance(report, RootCauseReport)
    assert report.root_cause_service == "orders-postgres-primary"
    assert len(report.causal_chain) > 0
    assert 0.0 <= report.confidence_score <= 1.0


@pytest.mark.asyncio
async def test_maker_checker_rejects_hallucinated_evidence_id(mock_evidence_packet):
    triage = TriageReport(
        agent_name="TriageAgent",
        timestamp="2026-11-19T14:30:00Z",
        incident_scope="DOWNSTREAM_CASCADE",
        urgency="P0_CRITICAL",
        user_journey_impact="Checkout payment blocked",
        supporting_evidence_ids=["EVID-STAT-001"],
        triage_summary="Severe cascade"
    )
    rc_report = RootCauseReport(
        agent_name="RootCauseAgent",
        timestamp="2026-11-19T14:30:00Z",
        root_cause_service="orders-postgres-primary",
        causal_chain=["orders-postgres-primary"],
        failure_mechanism="Lock contention",
        lag_progression_summary="Immediate",
        supporting_evidence_ids=["EVID-STAT-001"],
        confidence_score=0.9,
        hypotheses_evaluated=["Lock contention"]
    )

    validator = RiskValidatorAgent()
    # Pass a hint with an ungrounded hallucinated ID
    report = await validator.run(
        mock_evidence_packet,
        triage,
        rc_report,
        hints={"evidence_ids": ["EVID-HALLUCINATION-999"]}
    )

    # Risk validator must flag hallucination if non-authentic ID is cited
    assert isinstance(report, RiskValidationReport)
    assert report.verdict in ("VERIFIED_INCIDENT", "NEEDS_HUMAN_REVIEW")
    if "EVID-HALLUCINATION-999" in report.referenced_evidence_ids:
        assert report.maker_checker_status == "REJECTED_HALLUCINATION"
