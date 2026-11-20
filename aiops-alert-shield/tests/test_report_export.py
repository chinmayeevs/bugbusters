"""
tests/test_report_export.py
Integration and unit tests for 1-Click Incident & Audit Report Exporter.
Verifies Markdown (.md) and PDF (.pdf) exports, scope filtering,
provenance headers, runbook commands, and tamper-evident audit ledger generation.
"""

import pytest
from starlette.testclient import TestClient
from backend.main import app
from backend.storage.incident_repository import IncidentRepository


@pytest.fixture
def client():
    return TestClient(app)


def test_report_preview_meta(client):
    """Verifies preview metadata returns valid counts before download."""
    resp = client.get("/api/reports/preview-meta")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_incidents" in data
    assert "critical_count" in data
    assert "suppressed_count" in data
    assert "latest_incident_id" in data
    assert "generated_at" in data
    assert data["total_incidents"] >= 1


def test_report_preview_meta_single_incident(client):
    """Verifies preview metadata for a single specific incident."""
    repo = IncidentRepository()
    all_incidents = repo.list_incidents(limit=1)
    assert len(all_incidents) > 0
    inc_id = all_incidents[0].incident_id

    resp = client.get(f"/api/reports/preview-meta?scope=incident&incident_id={inc_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_incidents"] == 1
    assert data["latest_incident_id"] == inc_id

    # Test unknown incident returns 404
    resp_404 = client.get("/api/reports/preview-meta?scope=incident&incident_id=UNKNOWN_ID_999")
    assert resp_404.status_code == 404


def test_export_markdown_all_incidents(client):
    """Verifies full Markdown report export with real sections and runbook steps."""
    resp = client.get("/api/reports/export?format=md&scope=all")
    assert resp.status_code == 200
    assert "text/markdown" in resp.headers.get("content-type", "")
    assert "attachment; filename=" in resp.headers.get("content-disposition", "")
    assert ".md" in resp.headers.get("content-disposition", "")

    text = resp.text
    # Verify core sections are present
    assert "# AIOps Alert Shield" in text
    assert "1. Executive Summary & Alert Compression Funnel" in text
    assert "2. Verified Critical Incidents & Actionable Runbooks" in text
    assert "3. Suppressed Noise & Audit Ledger" in text
    assert "4. SEA Casebook Memory & Benchmark Verification" in text

    # Verify real data rendered
    assert "Deduplicated Clusters" in text
    assert "Actionable Remediation Runbook & Commands" in text
    assert "pg_stat_activity" in text or "kubectl" in text


def test_export_pdf_all_incidents(client):
    """Verifies full PDF export compiles with valid PDF header and non-trivial byte size."""
    resp = client.get("/api/reports/export?format=pdf&scope=all")
    assert resp.status_code == 200
    assert resp.headers.get("content-type") == "application/pdf"
    assert "attachment; filename=" in resp.headers.get("content-disposition", "")
    assert ".pdf" in resp.headers.get("content-disposition", "")

    pdf_bytes = resp.content
    assert pdf_bytes.startswith(b"%PDF-"), "Invalid PDF header bytes"
    assert len(pdf_bytes) > 5000, f"PDF file size too small: {len(pdf_bytes)} bytes"


def test_export_latest_upload_scope(client):
    """Verifies report export scoped to latest upload only."""
    resp_md = client.get("/api/reports/export?format=md&scope=latest")
    assert resp_md.status_code == 200
    assert "aiops-report-latest" in resp_md.headers.get("content-disposition", "")
    assert "2.1 Incident Dossier:" in resp_md.text

    resp_pdf = client.get("/api/reports/export?format=pdf&scope=latest")
    assert resp_pdf.status_code == 200
    assert resp_pdf.content.startswith(b"%PDF-")


def test_export_single_incident_scope_and_404(client):
    """Verifies report export scoped to a specific incident ID, and 404 for unknown IDs."""
    repo = IncidentRepository()
    all_incidents = repo.list_incidents(limit=1)
    assert len(all_incidents) > 0
    inc_id = all_incidents[0].incident_id

    # Valid incident export
    resp_inc = client.get(f"/api/reports/export?format=md&scope=incident&incident_id={inc_id}")
    assert resp_inc.status_code == 200
    assert inc_id in resp_inc.text

    # PDF format for single incident
    resp_inc_pdf = client.get(f"/api/reports/export?format=pdf&scope=incident&incident_id={inc_id}")
    assert resp_inc_pdf.status_code == 200
    assert resp_inc_pdf.content.startswith(b"%PDF-")

    # Unknown incident returns 404
    resp_404 = client.get("/api/reports/export?format=md&scope=incident&incident_id=INC-DOESNT-EXIST-404")
    assert resp_404.status_code == 404

    # Missing incident_id when scope=incident returns 400
    resp_400 = client.get("/api/reports/export?format=md&scope=incident")
    assert resp_400.status_code == 400


def test_export_invalid_format_returns_400(client):
    """Verifies that an unsupported format returns HTTP 400."""
    resp = client.get("/api/reports/export?format=docx&scope=all")
    assert resp.status_code == 400
    assert "format must be 'md' or 'pdf'" in resp.json()["error"]


def test_export_escalated_incident_contains_links_and_funnel_math(client):
    """Verifies bidirectional escalation link rendering, funnel math bounds, and clean typography."""
    import time
    from backend.reports.report_generator import compile_report_data

    repo = IncidentRepository()
    test_event_id = f"SUP-TEST-EXPORT-{int(time.time() * 1000)}"

    repo.record_suppressed_events([{
        "event_id": test_event_id,
        "trace_id": "trc_test_export_trace",
        "service": "checkout-api",
        "metric": "p99_latency_timeout",
        "category": "TRANSIENT_BLIPS",
        "suppression_reason": "Single spike without customer impact",
        "collapsed_count": 4,
        "mad_z_score": 1.5,
        "status": "SUPPRESSED"
    }])

    # Escalate event
    reason_text = "Correlated spike during payment webhook outage"
    escalated = repo.escalate_suppressed_event(
        event_id=test_event_id,
        reason=reason_text,
        escalated_by="lead_sre"
    )
    assert escalated is not None
    inc_id = escalated["escalated_incident_id"]

    # Verify report data compilation bounds
    data = compile_report_data(scope="incident", incident_id=inc_id)
    funnel = data["funnel"]
    assert funnel["total_suppressed_noise"] <= funnel["total_raw_alerts"]
    assert 0.0 <= funnel["compression_pct"] <= 100.0

    # Test Markdown export
    resp_md = client.get(f"/api/reports/export?format=md&scope=incident&incident_id={inc_id}")
    assert resp_md.status_code == 200
    md_text = resp_md.text

    # Verify bidirectional link is rendered in report
    assert test_event_id in md_text
    assert reason_text in md_text
    assert "- **Escalated From Event ID:**" in md_text
    assert "- **Escalation Reason:**" in md_text

    # Verify no accidental escaped dollars and no &rarr;
    assert r"\$" not in md_text
    assert "&rarr;" not in md_text

    # Test PDF export
    resp_pdf = client.get(f"/api/reports/export?format=pdf&scope=incident&incident_id={inc_id}")
    assert resp_pdf.status_code == 200
    assert resp_pdf.content.startswith(b"%PDF-")


def test_funnel_math_invariant_across_all_scopes():
    """Verifies that suppressed noise volume is strictly <= total raw alerts for all scopes."""
    from backend.reports.report_generator import compile_report_data

    repo = IncidentRepository()
    all_incidents = repo.list_incidents(limit=5)
    assert len(all_incidents) > 0

    for scope in ["all", "latest"]:
        data = compile_report_data(scope=scope)
        funnel = data["funnel"]
        assert funnel["total_suppressed_noise"] <= funnel["total_raw_alerts"]
        assert 0.0 <= funnel["compression_pct"] <= 100.0

    primary_id = all_incidents[0].incident_id
    data_inc = compile_report_data(scope="incident", incident_id=primary_id)
    funnel_inc = data_inc["funnel"]
    assert funnel_inc["total_suppressed_noise"] <= funnel_inc["total_raw_alerts"]
    assert 0.0 <= funnel_inc["compression_pct"] <= 100.0
