import requests
import json

def main():
    csv_content = """alert_id,timestamp,service,alert_name,severity,message,entity,threshold,metric_value
alt_demo_1,2026-11-20T07:00:00Z,orders-postgres-primary,PostgresLockContention,CRITICAL,Lock wait contention on orders table,db-master,10.0,42.5
alt_demo_2,2026-11-20T07:00:15Z,checkout-api,CheckoutLatencySpike,CRITICAL,POST /checkout latency high,pod-chk-1,800.0,1850.0
alt_demo_3,2026-11-20T07:00:30Z,api-gateway,Gateway5xxRate,WARNING,504 Gateway Timeouts elevated,pod-gw-1,2.0,5.8
"""

    files = {"file": ("test_alerts.csv", csv_content.encode("utf-8"), "text/csv")}
    resp = requests.post("http://localhost:8000/api/ingest/upload", files=files)
    assert resp.status_code == 200, f"Upload failed: {resp.text}"
    upload_data = resp.json()
    print("=== 1. UPLOAD RESPONSE SUMMARY ===")
    summary_keys = [
        "success", "batch_id", "raw_alerts_ingested", "clusters_created",
        "suppressed_noise_count", "incidents_created", "primary_incident_id",
        "ai_mode", "model_used", "total_tokens"
    ]
    print(json.dumps({k: upload_data[k] for k in summary_keys}, indent=2))

    inc_id = upload_data["primary_incident_id"]
    gql_query = f"""
    query {{
      incident(id: "{inc_id}") {{
        incidentId
        status
        severity
        rootCauseService
        triageTrace {{
          agentName
          mode
          model
          latencyMs
          promptTokens
          completionTokens
          totalTokens
          verifiedEvidenceRefs
        }}
        rootCauseTrace {{
          agentName
          mode
          model
          totalTokens
        }}
        validatorTrace {{
          agentName
          mode
          model
          totalTokens
        }}
        evidencePacket {{
          rawAlertCount
          compressedAlertCount
          metricSeries {{
            timestamp
            service
            metricName
            value
            staticThreshold
            isAnomaly
          }}
        }}
      }}
      intelligenceStatus {{
        mode
        provider
        model
        totalTokensUsed
        lastLatencyMs
      }}
    }}
    """

    gql_resp = requests.post("http://localhost:8000/graphql", json={"query": gql_query}).json()
    print("\n=== 2. GRAPHQL INCIDENT & INTELLIGENCE VERIFICATION ===")
    print(json.dumps(gql_resp["data"], indent=2))

    inc = gql_resp["data"]["incident"]
    series = inc["evidencePacket"]["metricSeries"]
    print(f"\n=== 3. REAL CSV METRIC POINTS VERIFIED ({len(series)} points) ===")
    for p in series:
        print(f"  Service: {p['service']} | Metric: {p['metricName']} | Value: {p['value']} | Thresh: {p['staticThreshold']} | Anomaly: {p['isAnomaly']}")

    values = [p["value"] for p in series]
    assert 42.5 in values, "42.5 not found in metricSeries!"
    assert 1850.0 in values, "1850.0 not found in metricSeries!"
    assert 5.8 in values, "5.8 not found in metricSeries!"
    print("\n>>> ALL CSV METRIC VALUES MATCH GROUND TRUTH DIRECTLY (NO DUMMY SYNTHESIS) <<<")

if __name__ == "__main__":
    main()
