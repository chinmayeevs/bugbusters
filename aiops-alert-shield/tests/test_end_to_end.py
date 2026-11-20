"""
tests/test_end_to_end.py
End-to-end integration test running the complete AIOps verification pipeline:
Raw Alert Flood -> Pure Python Compute -> SEA Read -> AI Orchestrator ->
Maker-Checker Verification -> Storage -> GraphQL API -> Engineer Resolution & SEA Write.
"""

import json
import csv
import pytest
from pathlib import Path
from starlette.testclient import TestClient

from backend.main import app
from backend.orchestration.pipeline_orchestrator import PipelineOrchestrator
from backend.storage.incident_repository import IncidentRepository

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@pytest.fixture(scope="module")
def sample_data():
    with open(DATA_DIR / "alerts.jsonl", "r", encoding="utf-8") as f:
        alerts = [json.loads(line) for line in f]
    with open(DATA_DIR / "logs.jsonl", "r", encoding="utf-8") as f:
        logs = [json.loads(line) for line in f]
    with open(DATA_DIR / "metrics_timeseries.csv", "r", encoding="utf-8") as f:
        metrics = list(csv.DictReader(f))
    return alerts, metrics, logs


@pytest.mark.asyncio
async def test_end_to_end_pipeline_and_graphql(sample_data):
    alerts, metrics, logs = sample_data
    orchestrator = PipelineOrchestrator()

    # 1. Execute full verification pipeline
    incident = await orchestrator.run_pipeline(alerts, metrics, logs, force_mock_ai=True)

    assert incident.incident_id.startswith("INC-")
    assert incident.status in ("VERIFIED_INCIDENT", "SUPPRESSED_NOISE", "NEEDS_HUMAN_REVIEW")
    assert incident.root_cause_service in ("orders-postgres-primary", "checkout-api", "api-gateway")
    assert incident.evidence_packet.compression_ratio > 0.80
    assert len(incident.evidence_packet.all_evidence_ids) > 0

    # 2. Query via GraphQL
    client = TestClient(app)
    query = f"""
    query {{
      incident(id: "{incident.incident_id}") {{
        incidentId
        title
        status
        severity
        rootCauseService
        confidenceScore
        evidencePacket {{
          rawAlertCount
          compressedAlertCount
          compressionRatio
          riskScore
          correlations {{
            evidenceId
            sourceService
            targetService
            lagSeconds
          }}
        }}
      }}
    }}
    """
    resp = client.post("/graphql", json={"query": query})
    assert resp.status_code == 200
    data = resp.json()["data"]["incident"]
    assert data is not None
    assert data["incidentId"] == incident.incident_id
    assert data["evidencePacket"]["rawAlertCount"] == incident.evidence_packet.raw_alert_count

    # 3. Test Mutation: Acknowledge Incident
    ack_mutation = f"""
    mutation {{
      acknowledgeIncident(incidentId: "{incident.incident_id}", acknowledgedBy: "lead-sre-alice") {{
        incidentId
        status
        acknowledgedBy
      }}
    }}
    """
    ack_resp = client.post("/graphql", json={"query": ack_mutation})
    assert ack_resp.status_code == 200
    ack_data = ack_resp.json()["data"]["acknowledgeIncident"]
    assert ack_data["status"] == "ACKNOWLEDGED"
    assert ack_data["acknowledgedBy"] == "lead-sre-alice"

    # 4. Test Mutation: Submit Resolution
    resolve_mutation = f"""
    mutation {{
      submitResolution(
        incidentId: "{incident.incident_id}",
        resolution: "Terminated blocking lock PID and scaled pool",
        resolvedBy: "lead-sre-alice"
      ) {{
        incidentId
        status
        resolvedBy
      }}
    }}
    """
    res_resp = client.post("/graphql", json={"query": resolve_mutation})
    assert res_resp.status_code == 200
    res_data = res_resp.json()["data"]["submitResolution"]
    assert res_data["status"] == "RESOLVED"
    assert res_data["resolvedBy"] == "lead-sre-alice"


@pytest.mark.asyncio
async def test_fail_open_path_when_ai_layer_fails(sample_data):
    alerts, metrics, logs = sample_data
    orchestrator = PipelineOrchestrator()

    # Force AI failure to simulate total LLM downtime / network partition
    fail_open_inc = await orchestrator.run_pipeline(alerts, metrics, logs, force_ai_failure=True)

    assert fail_open_inc.status == "FAIL_OPEN_CRITICAL"
    assert fail_open_inc.severity == "CRITICAL"
    assert "FAIL-OPEN" in fail_open_inc.title
    assert fail_open_inc.confidence_score == 1.0  # 100% deterministic threshold guarantee
