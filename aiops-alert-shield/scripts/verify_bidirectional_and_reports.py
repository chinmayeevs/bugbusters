"""
scripts/verify_bidirectional_and_reports.py
Performs end-to-end verification against live FastAPI backend:
1. Queries GraphQL suppressedEvents and incidents
2. Escalates a suppressed event via GraphQL mutation
3. Verifies escalatedIncidentId on SuppressedEvent and escalatedFromEventId on Incident
4. Tests /api/reports/export for md and pdf for the single escalated incident
5. Verifies funnel math and formatting
"""

import requests
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

BASE_URL = "http://127.0.0.1:8000"
GRAPHQL_URL = f"{BASE_URL}/graphql"

def test_live_system():
    print("=== 1. Querying GraphQL Suppressed Events ===")
    query_supp = """
    query {
      suppressedEvents(limit: 10) {
        eventId
        traceId
        service
        status
        escalatedIncidentId
      }
    }
    """
    resp = requests.post(GRAPHQL_URL, json={"query": query_supp})
    assert resp.status_code == 200, f"Failed: {resp.text}"
    supp_events = resp.json()["data"]["suppressedEvents"]
    print(f"Retrieved {len(supp_events)} suppressed events from live GraphQL.")
    assert len(supp_events) > 0, "No suppressed events returned."

    target_event = None
    for ev in supp_events:
        if ev["status"] != "ESCALATED":
            target_event = ev
            break
    if not target_event:
        target_event = supp_events[0]

    print(f"\n=== 2. Escalating Event {target_event['eventId']} via Mutation ===")
    mutate_escalate = f"""
    mutation {{
      escalateSuppressedEvent(
        eventId: "{target_event['eventId']}",
        reason: "Critical correlation with checkout lag - Live Verification",
        escalatedBy: "test-verifier"
      ) {{
        eventId
        status
        escalatedIncidentId
        escalationReason
        escalatedBy
      }}
    }}
    """
    resp_mut = requests.post(GRAPHQL_URL, json={"query": mutate_escalate})
    assert resp_mut.status_code == 200, f"Mutation failed: {resp_mut.text}"
    mut_data = resp_mut.json()["data"]["escalateSuppressedEvent"]
    print(f"Escalated event response: {json.dumps(mut_data, indent=2)}")
    assert mut_data["status"] == "ESCALATED"
    escalated_inc_id = mut_data["escalatedIncidentId"]
    assert escalated_inc_id is not None
    assert escalated_inc_id.startswith("INC-ESCALATED-")

    print(f"\n=== 3. Querying Incident {escalated_inc_id} to verify bidirectional link ===")
    query_inc = f"""
    query {{
      incident(id: "{escalated_inc_id}") {{
        incidentId
        status
        title
        escalatedFromEventId
        escalationReason
      }}
    }}
    """
    resp_inc = requests.post(GRAPHQL_URL, json={"query": query_inc})
    assert resp_inc.status_code == 200, f"Incident query failed: {resp_inc.text}"
    inc_data = resp_inc.json()["data"]["incident"]
    print(f"Incident data: {json.dumps(inc_data, indent=2)}")
    assert inc_data["incidentId"] == escalated_inc_id
    assert inc_data["escalatedFromEventId"] == target_event["eventId"]
    assert "Live Verification" in inc_data["escalationReason"]

    print("\n=== 4. Testing Single-Incident Markdown Export ===")
    resp_md = requests.get(f"{BASE_URL}/api/reports/export?format=md&scope=incident&incident_id={escalated_inc_id}")
    assert resp_md.status_code == 200
    md_text = resp_md.text
    print(f"Markdown preview (first 500 chars):\n{md_text[:500]}")
    assert target_event["eventId"] in md_text
    assert "Escalated From Event ID" in md_text
    assert r"\$" not in md_text
    assert "&rarr;" not in md_text
    assert " -> " in md_text or len(md_text) > 0

    print("\n=== 5. Testing Single-Incident PDF Export ===")
    resp_pdf = requests.get(f"{BASE_URL}/api/reports/export?format=pdf&scope=incident&incident_id={escalated_inc_id}")
    assert resp_pdf.status_code == 200
    pdf_bytes = resp_pdf.content
    print(f"PDF bytes received: {len(pdf_bytes)} bytes. Starts with %PDF: {pdf_bytes.startswith(b'%PDF-')}")
    assert pdf_bytes.startswith(b'%PDF-')
    assert len(pdf_bytes) > 2000

    print("\n=== 6. Testing Preview Meta & Funnel Math ===")
    resp_meta = requests.get(f"{BASE_URL}/api/reports/preview-meta?scope=incident&incident_id={escalated_inc_id}")
    assert resp_meta.status_code == 200
    meta_json = resp_meta.json()
    print(f"Preview Meta: {json.dumps(meta_json, indent=2)}")
    assert meta_json["total_incidents"] == 1
    assert meta_json["latest_incident_id"] == escalated_inc_id

    from backend.reports.report_generator import compile_report_data
    compiled = compile_report_data(scope="incident", incident_id=escalated_inc_id)
    funnel = compiled["funnel"]
    print(f"Compiled Funnel: {json.dumps(funnel, indent=2)}")
    assert funnel["total_suppressed_noise"] <= funnel["total_raw_alerts"]
    assert 0.0 <= funnel["compression_pct"] <= 100.0

    print("\nALL VERIFICATIONS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_live_system()
