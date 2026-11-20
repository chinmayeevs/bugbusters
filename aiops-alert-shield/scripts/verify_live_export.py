import requests
import json

def test_live_exports():
    base_url = "http://localhost:8000"
    print("=== 1. VERIFYING PREVIEW-META ENDPOINT ===")
    resp_meta = requests.get(f"{base_url}/api/reports/preview-meta")
    assert resp_meta.status_code == 200, f"Preview meta failed: {resp_meta.text}"
    meta = resp_meta.json()
    print("Preview Meta Response:")
    print(json.dumps(meta, indent=2))
    assert meta["total_incidents"] > 0
    assert meta["critical_count"] > 0
    latest_id = meta["latest_incident_id"]

    print("\n=== 2. VERIFYING FULL MARKDOWN EXPORT (scope=all) ===")
    resp_md = requests.get(f"{base_url}/api/reports/export?format=md&scope=all")
    assert resp_md.status_code == 200, f"MD export failed: {resp_md.text}"
    assert "text/markdown" in resp_md.headers.get("content-type", "")
    assert "attachment; filename=" in resp_md.headers.get("content-disposition", "")
    md_content = resp_md.text
    print(f"  Filename: {resp_md.headers.get('content-disposition')}")
    print(f"  Size: {len(md_content.encode('utf-8')):,} bytes")
    print(f"  First 300 chars:\n{md_content[:300]}")
    assert "# AIOps Alert Shield" in md_content
    assert "Executive Summary & Alert Compression Funnel" in md_content
    assert "Verified Critical Incidents" in md_content
    assert "Suppressed Noise & Audit Ledger" in md_content
    assert "SEA Casebook Memory" in md_content

    print("\n=== 3. VERIFYING FULL PDF EXPORT (scope=all) ===")
    resp_pdf = requests.get(f"{base_url}/api/reports/export?format=pdf&scope=all")
    assert resp_pdf.status_code == 200, f"PDF export failed: {resp_pdf.text}"
    assert resp_pdf.headers.get("content-type") == "application/pdf"
    assert "attachment; filename=" in resp_pdf.headers.get("content-disposition", "")
    pdf_content = resp_pdf.content
    print(f"  Filename: {resp_pdf.headers.get('content-disposition')}")
    print(f"  Size: {len(pdf_content):,} bytes")
    print(f"  Header Bytes: {pdf_content[:8]}")
    assert pdf_content.startswith(b"%PDF-"), "Invalid PDF header!"
    assert len(pdf_content) > 10000, "PDF file suspiciously small!"

    print("\n=== 4. VERIFYING LATEST UPLOAD SCOPE EXPORTS ===")
    resp_latest_md = requests.get(f"{base_url}/api/reports/export?format=md&scope=latest")
    assert resp_latest_md.status_code == 200
    assert "aiops-report-latest" in resp_latest_md.headers.get("content-disposition", "")
    print(f"  Latest MD Size: {len(resp_latest_md.content):,} bytes")

    resp_latest_pdf = requests.get(f"{base_url}/api/reports/export?format=pdf&scope=latest")
    assert resp_latest_pdf.status_code == 200
    assert resp_latest_pdf.content.startswith(b"%PDF-")
    print(f"  Latest PDF Size: {len(resp_latest_pdf.content):,} bytes")

    print("\n=== 5. VERIFYING SINGLE INCIDENT SCOPE EXPORTS ===")
    assert latest_id, "No latest_incident_id found in meta!"
    resp_inc_md = requests.get(f"{base_url}/api/reports/export?format=md&scope=incident&incident_id={latest_id}")
    assert resp_inc_md.status_code == 200
    assert latest_id in resp_inc_md.text
    print(f"  Incident {latest_id} MD Size: {len(resp_inc_md.content):,} bytes")

    resp_inc_pdf = requests.get(f"{base_url}/api/reports/export?format=pdf&scope=incident&incident_id={latest_id}")
    assert resp_inc_pdf.status_code == 200
    assert resp_inc_pdf.content.startswith(b"%PDF-")
    print(f"  Incident {latest_id} PDF Size: {len(resp_inc_pdf.content):,} bytes")

    print("\n=== 6. VERIFYING 404 ON UNKNOWN INCIDENT ===")
    resp_404 = requests.get(f"{base_url}/api/reports/export?format=md&scope=incident&incident_id=UNKNOWN-404")
    assert resp_404.status_code == 404
    print(f"  Unknown incident returned HTTP {resp_404.status_code} as expected")

    print("\n=== 7. VERIFYING FRONTEND ON PORT 3000 ===")
    resp_fe = requests.get("http://localhost:3000")
    assert resp_fe.status_code == 200
    print(f"  Frontend is LIVE (HTTP {resp_fe.status_code})")

    print("\n>>> ALL LIVE EXPORT VERIFICATIONS SUCCEEDED CLEANLY! <<<")

if __name__ == "__main__":
    test_live_exports()
