"""
tests/test_upgrade_features.py
Tests for upgraded capabilities:
  - Ingestion via POST /api/ingest/upload (.json, .jsonl, .csv)
  - GraphQL ingestCustomTelemetry mutation (with metric timeseries synthesis)
  - GraphQL intelligenceStatus query & configureIntelligence mutation
  - Untrusted telemetry data isolation in LLM gateway
"""

import io
import json
import pytest
from starlette.testclient import TestClient
from backend.main import app
from agents.llm_gateway import (
    get_intelligence_status,
    configure_intelligence,
    wrap_untrusted_telemetry,
    test_llm_connection as run_test_llm_conn,
)


def test_intelligence_status_and_configure():
    # 1. Initial status query
    status = get_intelligence_status()
    assert "mode" in status
    assert "provider" in status
    assert "model" in status
    assert "api_key_configured" in status

    # 2. Configure intelligence
    res = configure_intelligence(
        mock_llm=True,
        provider="gemini",
        model="gemini/gemini-2.5-flash",
        api_key="test-session-key-12345"
    )
    assert res["mock_llm"] is True
    assert res["api_key_configured"] is True
    # Verify raw key never exposed in status
    assert "test-session-key" not in json.dumps(res)


@pytest.mark.asyncio
async def test_llm_connection_test():
    res = await run_test_llm_conn()
    assert res.get("ok") is True or res.get("success") is True
    assert res.get("mode", "LIVE_LLM") in ("MOCK_LLM", "LIVE_LLM")
    assert "latency_ms" in res or "latencyMs" in res


def test_untrusted_telemetry_wrapping():
    raw_text = "ERROR: User ID 48291 injection attempt drop table; credit_card 4532-0150-1234-5674"
    wrapped = wrap_untrusted_telemetry(raw_text)
    assert "<untrusted_telemetry_data>" in wrapped
    assert "</untrusted_telemetry_data>" in wrapped
    assert "credit_card" in wrapped


def test_api_ingest_upload_json():
    client = TestClient(app)
    payload = {
        "alerts": [
            {
                "alert_name": "CustomDBLockContention",
                "service": "orders-postgres-primary",
                "severity": "CRITICAL",
                "message": "Custom lock contention spike on orders_v2",
                "metric_name": "lock_wait_count",
                "metric_value": 45.0,
                "threshold": 15.0
            }
        ],
        "metrics": [
            {"service": "orders-postgres-primary", "metric_name": "lock_wait_count", "value": "45.0"},
            {"service": "checkout-api", "metric_name": "p99_latency_ms", "value": "1250.0"}
        ],
        "logs": [
            {"service": "orders-postgres-primary", "level": "ERROR", "message": "Lock wait timeout reached for transaction 991"}
        ]
    }
    file_content = json.dumps(payload).encode("utf-8")
    resp = client.post(
        "/api/ingest/upload",
        files={"file": ("custom_payload.json", io.BytesIO(file_content), "application/json")}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["incident_id"].startswith("INC-")
    assert data["status"] in ("VERIFIED_INCIDENT", "NEEDS_HUMAN_REVIEW", "FAIL_OPEN_CRITICAL")
    assert data["alert_count"] == 1
    assert data["metric_count"] == 2


def test_api_ingest_upload_jsonl():
    client = TestClient(app)
    lines = [
        json.dumps({"service": "checkout-api", "alert_name": "CheckoutSpike", "severity": "HIGH", "message": "Spike in 504 gateway timeouts"}),
        json.dumps({"service": "checkout-api", "metric_name": "p99_latency_ms", "value": "890.0"}),
        json.dumps({"service": "checkout-api", "level": "WARN", "message": "Upstream pool busy"})
    ]
    file_content = "\n".join(lines).encode("utf-8")
    resp = client.post(
        "/api/ingest/upload",
        files={"file": ("telemetry_stream.jsonl", io.BytesIO(file_content), "application/x-ndjson")}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["incident_id"].startswith("INC-")


def test_graphql_custom_telemetry_and_intelligence_ops():
    client = TestClient(app)

    # 1. Query intelligence status
    q_status = """
    query {
      intelligenceStatus {
        mode
        provider
        model
        apiKeyConfigured
        totalTokensUsed
      }
    }
    """
    resp = client.post("/graphql", json={"query": q_status})
    assert resp.status_code == 200
    intel = resp.json()["data"]["intelligenceStatus"]
    assert intel["mode"] in ("LIVE_LLM", "MOCK_LLM")
    assert "apiKeyConfigured" in intel

    # 2. Mutate configure intelligence
    m_config = """
    mutation {
      configureIntelligence(input: {
        mockLlm: true,
        provider: "gemini",
        model: "gemini/gemini-2.5-flash"
      }) {
        mode
        provider
        model
      }
    }
    """
    resp = client.post("/graphql", json={"query": m_config})
    assert resp.status_code == 200
    cfg = resp.json()["data"]["configureIntelligence"]
    assert cfg["mode"] == "MOCK_LLM"
    assert cfg["provider"] == "gemini"

    # 3. Test LLM connection
    m_test = """
    mutation {
      testLlmConnection {
        success
        mode
        message
      }
    }
    """
    resp = client.post("/graphql", json={"query": m_test})
    assert resp.status_code == 200
    t_res = resp.json()["data"]["testLlmConnection"]
    assert t_res["success"] is True

    # 4. Ingest custom telemetry with synthetic metrics
    m_ingest = """
    mutation {
      ingestCustomTelemetry(input: {
        alerts: [
          {
            alertName: "CustomerCheckoutDropAlert",
            service: "checkout-api",
            severity: "CRITICAL",
            message: "Sudden 80% drop in successful checkout completions",
            metricName: "failure_rate_pct",
            metricValue: 82.5,
            threshold: 5.0
          }
        ]
      }) {
        success
        incidentId
        verdict
        severity
        rootCauseService
        computeMs
        aiReasoningMs
        incident {
          title
          evidencePacket {
            rawAlertCount
            metricSeries {
              service
              metricName
              value
              isAnomaly
            }
            riskBreakdown {
              name
              score
              weight
            }
            mermaidDiagram
          }
        }
      }
    }
    """
    resp = client.post("/graphql", json={"query": m_ingest})
    assert resp.status_code == 200
    res = resp.json()
    assert "errors" not in res, res.get("errors")
    ingest_res = res["data"]["ingestCustomTelemetry"]
    assert ingest_res["success"] is True
    assert ingest_res["incidentId"].startswith("INC-")
    # Verify synthetic metricSeries was populated
    series = ingest_res["incident"]["evidencePacket"]["metricSeries"]
    assert len(series) > 0
    # Verify riskBreakdown was populated
    breakdown = ingest_res["incident"]["evidencePacket"]["riskBreakdown"]
    assert len(breakdown) >= 4
    # Verify mermaidDiagram was generated
    assert "graph TD" in ingest_res["incident"]["evidencePacket"]["mermaidDiagram"]


def test_api_ingest_pure_alert_csv_with_metric_value():
    client = TestClient(app)
    csv_text = """alert_id,timestamp,service,alert_name,severity,message,entity,threshold,metric_value
alt_real_1,2026-11-20T06:00:00Z,orders-postgres-primary,PostgresLockContention,CRITICAL,Transaction lock wait exceeded on orders table,db-pod-0,10.0,18.5
alt_real_2,2026-11-20T06:00:15Z,checkout-api,CheckoutLatencySpike,CRITICAL,POST /v1/checkout latency high,chk-pod-1,800.0,1420.0
alt_real_3,2026-11-20T06:00:30Z,api-gateway,Gateway5xxRate,WARNING,504 Gateway Timeout rate,gw-pod-2,2.0,4.2
"""
    resp = client.post(
        "/api/ingest/upload",
        files={"file": ("real_alerts.csv", io.BytesIO(csv_text.encode("utf-8")), "text/csv")}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "batch_id" in data
    assert data["raw_alerts_ingested"] == 3
    inc_id = data["primary_incident_id"]

    # Query incident via GraphQL and verify metricSeries contains the real values from the uploaded CSV
    q_inc = f"""
    query {{
      incident(id: "{inc_id}") {{
        incidentId
        triageTrace {{
          agentName
          mode
        }}
        evidencePacket {{
          rawAlertCount
          metricSeries {{
            service
            metricName
            value
            staticThreshold
            isAnomaly
          }}
        }}
      }}
    }}
    """
    g_resp = client.post("/graphql", json={"query": q_inc})
    assert g_resp.status_code == 200
    inc_data = g_resp.json()["data"]["incident"]
    series = inc_data["evidencePacket"]["metricSeries"]
    assert len(series) == 3
    values = [p["value"] for p in series]
    assert 18.5 in values
    assert 1420.0 in values
    assert 4.2 in values
    assert any(p["service"] == "orders-postgres-primary" and p["value"] == 18.5 for p in series)
