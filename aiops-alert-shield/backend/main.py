"""
backend/main.py
FastAPI entrypoint for AIOps Alert Shield.
Mounts Strawberry GraphQL with WebSockets and /health endpoint.
"""

from __future__ import annotations
import os
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from contextlib import asynccontextmanager

import strawberry
from strawberry.fastapi import GraphQLRouter
from fastapi import FastAPI, File, UploadFile, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.graphql.queries import Query
from backend.graphql.mutations import Mutation
from backend.graphql.subscriptions import Subscription
from backend.storage.incident_repository import IncidentRepository
from backend.storage.case_repository import CaseRepository
from backend.storage.timeseries_repository import TimeseriesRepository
from backend.orchestration.pipeline_orchestrator import PipelineOrchestrator
from backend.reports.report_generator import compile_report_data, generate_markdown_report, generate_pdf_report
from agents.llm_gateway import get_intelligence_status

schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
    subscription=Subscription
)

graphql_app = GraphQLRouter(
    schema,
    graphql_ide="graphiql",
    subscription_protocols=["graphql-transport-ws", "graphql-ws"]
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure data exists on startup
    data_dir = Path(__file__).resolve().parent.parent / "data"
    if not (data_dir / "alerts.jsonl").exists():
        from scripts.generate_mock_data import write_all
        write_all()

    # Pre-seed at least one incident if none exist
    repo = IncidentRepository()
    if len(repo.list_incidents(limit=1)) == 0:
        import json, csv
        from backend.orchestration.pipeline_orchestrator import PipelineOrchestrator
        with open(data_dir / "alerts.jsonl", "r", encoding="utf-8") as f:
            alerts = [json.loads(line) for line in f]
        with open(data_dir / "logs.jsonl", "r", encoding="utf-8") as f:
            logs = [json.loads(line) for line in f]
        with open(data_dir / "metrics_timeseries.csv", "r", encoding="utf-8") as f:
            metrics = list(csv.DictReader(f))

        orchestrator = PipelineOrchestrator(incident_repo=repo)
        await orchestrator.run_pipeline(alerts, metrics, logs)
        print("[Startup] Seed incident generated and persisted.")

    yield


app = FastAPI(
    title="AIOps Alert Shield API",
    version="1.0.0",
    description="Orchestrated, Self-Evolving Hybrid AIOps Alert Verification Platform",
    lifespan=lifespan
)

# Enable CORS for local Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount GraphQL Endpoint
app.include_router(graphql_app, prefix="/graphql")


@app.post("/api/ingest/upload")
async def upload_telemetry_file(file: UploadFile = File(...)):
    """
    Multipart/form-data ingestion endpoint for telemetry files (.json, .jsonl, .csv).
    Parses alerts, metrics, and logs, then executes deterministic compute + AI verification.
    """
    import io
    import csv
    import json
    import uuid

    filename = file.filename or "upload.json"
    contents = await file.read()
    text = contents.decode("utf-8", errors="replace")

    raw_alerts = []
    raw_metrics = []
    raw_logs = []

    if filename.endswith(".jsonl"):
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
                if "alert_name" in item or "severity" in item:
                    raw_alerts.append(item)
                elif "metric_name" in item or "value" in item:
                    raw_metrics.append(item)
                elif "level" in item or "message" in item:
                    raw_logs.append(item)
                else:
                    raw_alerts.append(item)
            except Exception:
                pass
    elif filename.endswith(".csv"):
        reader = csv.DictReader(io.StringIO(text))
        for row in reader:
            if "alert_name" in row or "severity" in row:
                raw_alerts.append(row)
            elif "metric_name" in row or "value" in row:
                raw_metrics.append(row)
            elif "level" in row or "message" in row:
                raw_logs.append(row)
            else:
                raw_metrics.append(row)
    else:  # Assume JSON
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                raw_alerts = data.get("alerts", [])
                raw_metrics = data.get("metrics", [])
                raw_logs = data.get("logs", [])
                if not raw_alerts and not raw_metrics and not raw_logs:
                    # Single item object
                    if "alert_name" in data or "severity" in data:
                        raw_alerts.append(data)
                    elif "metric_name" in data:
                        raw_metrics.append(data)
                    elif "level" in data:
                        raw_logs.append(data)
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        if "alert_name" in item or "severity" in item:
                            raw_alerts.append(item)
                        elif "metric_name" in item:
                            raw_metrics.append(item)
                        elif "level" in item:
                            raw_logs.append(item)
                        else:
                            raw_alerts.append(item)
        except Exception as e:
            return JSONResponse(
                status_code=400,
                content={"error": f"Failed to parse JSON telemetry file: {str(e)}"}
            )

    # Fallback default alert if empty
    if not raw_alerts and not raw_metrics and not raw_logs:
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        raw_alerts.append({
            "alert_id": f"alt_up_{uuid.uuid4().hex[:6]}",
            "timestamp": now_iso,
            "service": "checkout-api",
            "alert_name": "CustomUploadedSignal",
            "severity": "WARNING",
            "metric_name": "error_rate",
            "metric_value": 45.0,
            "threshold": 10.0,
            "entity": "upload-batch",
            "message": f"Custom telemetry ingested via {filename}",
            "tags": {"source": "upload"}
        })

    repo = IncidentRepository()
    orchestrator = PipelineOrchestrator(incident_repo=repo)
    incident = await orchestrator.run_pipeline(
        raw_alerts=raw_alerts,
        raw_metrics=raw_metrics,
        raw_logs=raw_logs
    )

    intel_status = get_intelligence_status()
    raw_alerts_count = len(raw_alerts)
    clusters_count = len(incident.evidence_packet.deduplicated_clusters) if incident.evidence_packet else 1
    suppressed_count = max(0, raw_alerts_count - clusters_count)
    batch_id = f"batch_{uuid.uuid4().hex[:8]}"

    return JSONResponse({
        "success": True,
        "batch_id": batch_id,
        "raw_alerts_ingested": raw_alerts_count,
        "clusters_created": clusters_count,
        "suppressed_noise_count": suppressed_count,
        "incidents_created": 1 if incident.status in ("VERIFIED_INCIDENT", "FAIL_OPEN_CRITICAL") else 0,
        "primary_incident_id": incident.incident_id,
        "ai_mode": intel_status.get("mode", "LIVE_LLM"),
        "model_used": intel_status.get("model", "gemini-3.5-flash-lite"),
        "total_tokens": intel_status.get("total_tokens_used", 0),
        "incident_id": incident.incident_id,
        "trace_id": incident.trace_id,
        "status": incident.status,
        "severity": incident.severity,
        "root_cause_service": incident.root_cause_service,
        "title": incident.title,
        "alert_count": raw_alerts_count,
        "metric_count": len(raw_metrics),
        "log_count": len(raw_logs),
        "total_pipeline_ms": orchestrator.stage_timings.get("total_pipeline_ms", 0.0)
    })


@app.get("/health")
def health_check():
    """Health check endpoint exposing system readiness and runtime mode."""
    repo = IncidentRepository()
    case_repo = CaseRepository()
    incident_count = len(repo.list_incidents(limit=100))
    intel_status = get_intelligence_status()

    return JSONResponse({
        "status": "HEALTHY",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0",
        "architecture": "Hybrid Deterministic-AI",
        "llm_mode": intel_status["mode"],
        "llm_provider": intel_status["provider"],
        "llm_model": intel_status["model"],
        "api_key_configured": intel_status["api_key_configured"],
        "active_incidents": incident_count,
        "database": {
            "incident_store": "sqlite_wal",
            "casebook_store": "sqlite_wal"
        },
        "services_monitored": [
            "api-gateway",
            "checkout-api",
            "payment-service",
            "inventory-service",
            "orders-postgres-primary",
            "redis-cache"
        ]
    })


@app.get("/api/reports/preview-meta")
def report_preview_meta(
    scope: str = "all",
    incident_id: str = None
):
    """Returns lightweight metadata counts for the export modal."""
    repo = IncidentRepository()
    all_incidents = repo.list_incidents(limit=100)
    critical_count = sum(
        1 for inc in all_incidents
        if inc.severity == "CRITICAL" or inc.status in ("VERIFIED_INCIDENT", "FAIL_OPEN_CRITICAL")
    )
    suppressed_count = len(repo.list_suppressed_events(limit=100))
    latest_id = all_incidents[0].incident_id if all_incidents else None

    if scope == "incident" and incident_id:
        inc = repo.get_incident(incident_id)
        if not inc:
            return JSONResponse(status_code=404, content={"error": f"Incident {incident_id} not found"})
        return JSONResponse({
            "total_incidents": 1,
            "critical_count": 1 if inc.severity == "CRITICAL" or inc.status in ("VERIFIED_INCIDENT", "FAIL_OPEN_CRITICAL") else 0,
            "suppressed_count": len(inc.evidence_packet.deduplicated_clusters) if inc.evidence_packet else 0,
            "latest_incident_id": inc.incident_id,
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        })

    return JSONResponse({
        "total_incidents": len(all_incidents),
        "critical_count": critical_count,
        "suppressed_count": suppressed_count,
        "latest_incident_id": latest_id,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    })


@app.get("/api/reports/export")
def export_report(
    format: str = "md",
    scope: str = "all",
    incident_id: str = None
):
    """
    Exports a comprehensive audit and incident report in Markdown (.md) or PDF (.pdf).
    """
    fmt = format.lower().strip()
    if fmt not in ("md", "pdf"):
        return JSONResponse(status_code=400, content={"error": "format must be 'md' or 'pdf'"})

    try:
        report_data = compile_report_data(scope=scope, incident_id=incident_id)
    except KeyError as e:
        return JSONResponse(status_code=404, content={"error": str(e)})
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Failed to compile report: {str(e)}"})

    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    safe_scope = scope.lower().replace(" ", "_")
    filename = f"aiops-report-{safe_scope}-{timestamp_str}.{fmt}"

    if fmt == "md":
        content_str = generate_markdown_report(report_data)
        return Response(
            content=content_str.encode("utf-8"),
            media_type="text/markdown; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
    else:  # pdf
        pdf_bytes = generate_pdf_report(report_data)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
