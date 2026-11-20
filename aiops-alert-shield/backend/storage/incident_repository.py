"""
backend/storage/incident_repository.py
SQLite-backed persistent store for Incidents, Proof Bundles, and Engineer Feedback.
"""

from __future__ import annotations
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional
from backend.models.contracts import Incident, ComputeResult

DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "incidents.db"


class IncidentRepository:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS incidents (
                    incident_id TEXT PRIMARY KEY,
                    trace_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    status TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    root_cause_service TEXT NOT NULL,
                    confidence_score REAL NOT NULL,
                    context_divergence_flag INTEGER NOT NULL,
                    context_badge TEXT NOT NULL,
                    evidence_packet TEXT NOT NULL,
                    triage_report TEXT,
                    root_cause_report TEXT,
                    risk_validation_report TEXT,
                    engineer_notes TEXT,
                    engineer_feedback TEXT,
                    acknowledged_by TEXT,
                    acknowledged_at TEXT,
                    resolved_by TEXT,
                    resolved_at TEXT,
                    escalated_from_event_id TEXT,
                    escalation_reason TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_incidents_status ON incidents (status);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_incidents_severity ON incidents (severity);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_incidents_created ON incidents (created_at DESC);")

            # Check and add execution trace and escalation columns if not present
            cur = conn.execute("PRAGMA table_info(incidents);")
            existing_cols = {r["name"] for r in cur.fetchall()}
            for col in ["triage_trace", "root_cause_trace", "validator_trace", "escalated_from_event_id", "escalation_reason"]:
                if col not in existing_cols:
                    try:
                        conn.execute(f"ALTER TABLE incidents ADD COLUMN {col} TEXT;")
                    except Exception:
                        pass

            conn.execute("""
                CREATE TABLE IF NOT EXISTS suppressed_events (
                    event_id TEXT PRIMARY KEY,
                    trace_id TEXT NOT NULL,
                    batch_id TEXT,
                    service TEXT NOT NULL,
                    metric TEXT NOT NULL,
                    category TEXT NOT NULL,
                    suppression_reason TEXT NOT NULL,
                    collapsed_count INTEGER DEFAULT 1,
                    mad_z_score REAL DEFAULT 0.0,
                    sea_case_ref TEXT,
                    status TEXT DEFAULT 'SUPPRESSED',
                    escalated_incident_id TEXT,
                    escalation_reason TEXT,
                    escalated_by TEXT,
                    escalated_at TEXT,
                    timestamp TEXT NOT NULL
                );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_supp_cat ON suppressed_events (category);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_supp_time ON suppressed_events (timestamp DESC);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_supp_trace ON suppressed_events (trace_id);")

            cur = conn.execute("PRAGMA table_info(suppressed_events);")
            existing_supp_cols = {r["name"] for r in cur.fetchall()}
            for col in ["escalated_incident_id", "batch_id"]:
                if col not in existing_supp_cols:
                    try:
                        conn.execute(f"ALTER TABLE suppressed_events ADD COLUMN {col} TEXT;")
                    except Exception:
                        pass

    def save_incident(self, incident: Incident) -> Incident:
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO incidents (
                    incident_id, trace_id, title, status, severity,
                    root_cause_service, confidence_score, context_divergence_flag,
                    context_badge, evidence_packet, triage_report, root_cause_report,
                    risk_validation_report, engineer_notes, engineer_feedback,
                    acknowledged_by, acknowledged_at, resolved_by, resolved_at,
                    triage_trace, root_cause_trace, validator_trace,
                    escalated_from_event_id, escalation_reason,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                incident.incident_id,
                incident.trace_id,
                incident.title,
                incident.status,
                incident.severity,
                incident.root_cause_service,
                incident.confidence_score,
                1 if incident.context_divergence_flag else 0,
                incident.context_badge,
                incident.evidence_packet.model_dump_json(),
                incident.triage.model_dump_json() if incident.triage else None,
                incident.root_cause.model_dump_json() if incident.root_cause else None,
                incident.risk_validation.model_dump_json() if incident.risk_validation else None,
                incident.engineer_notes,
                json.dumps(incident.engineer_feedback) if incident.engineer_feedback else None,
                incident.acknowledged_by,
                incident.acknowledged_at,
                incident.resolved_by,
                incident.resolved_at,
                incident.triage_trace.model_dump_json() if incident.triage_trace else None,
                incident.root_cause_trace.model_dump_json() if incident.root_cause_trace else None,
                incident.validator_trace.model_dump_json() if incident.validator_trace else None,
                incident.escalated_from_event_id,
                incident.escalation_reason,
                incident.created_at or now_iso,
                now_iso
            ))
            conn.commit()
        return incident

    def get_incident(self, incident_id: str) -> Optional[Incident]:
        with self._get_connection() as conn:
            cur = conn.execute("SELECT * FROM incidents WHERE incident_id = ?;", (incident_id,))
            row = cur.fetchone()
            if not row:
                return None
            return self._row_to_incident(row)

    def list_incidents(
        self,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 50
    ) -> List[Incident]:
        query = "SELECT * FROM incidents WHERE 1=1"
        params: List[Any] = []

        if status:
            query += " AND status = ?"
            params.append(status)
        if severity:
            query += " AND severity = ?"
            params.append(severity)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        with self._get_connection() as conn:
            cur = conn.execute(query, params)
            rows = cur.fetchall()
            return [self._row_to_incident(r) for r in rows]

    def acknowledge_incident(self, incident_id: str, acknowledged_by: str = "engineer") -> Optional[Incident]:
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE incidents SET
                    status = 'ACKNOWLEDGED',
                    acknowledged_by = ?,
                    acknowledged_at = ?,
                    updated_at = ?
                WHERE incident_id = ?;
            """, (acknowledged_by, now_iso, now_iso, incident_id))
            conn.commit()
        return self.get_incident(incident_id)

    def resolve_incident(
        self,
        incident_id: str,
        resolution: str,
        resolved_by: str = "engineer"
    ) -> Optional[Incident]:
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE incidents SET
                    status = 'RESOLVED',
                    engineer_notes = ?,
                    resolved_by = ?,
                    resolved_at = ?,
                    updated_at = ?
                WHERE incident_id = ?;
            """, (resolution, resolved_by, now_iso, now_iso, incident_id))
            conn.commit()
        return self.get_incident(incident_id)

    def submit_feedback(
        self,
        incident_id: str,
        feedback: Dict[str, Any]
    ) -> Optional[Incident]:
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE incidents SET
                    engineer_feedback = ?,
                    updated_at = ?
                WHERE incident_id = ?;
            """, (json.dumps(feedback), now_iso, incident_id))
            conn.commit()
        return self.get_incident(incident_id)

    def _row_to_incident(self, row: sqlite3.Row) -> Incident:
        evid_data = json.loads(row["evidence_packet"])
        triage_data = json.loads(row["triage_report"]) if row["triage_report"] else None
        rc_data = json.loads(row["root_cause_report"]) if row["root_cause_report"] else None
        risk_data = json.loads(row["risk_validation_report"]) if row["risk_validation_report"] else None
        feedback_data = json.loads(row["engineer_feedback"]) if row["engineer_feedback"] else None

        from backend.models.contracts import TriageReport, RootCauseReport, RiskValidationReport, AgentExecutionTrace

        tr_trace = None
        if "triage_trace" in row.keys() and row["triage_trace"]:
            try:
                tr_trace = AgentExecutionTrace(**json.loads(row["triage_trace"]))
            except Exception:
                pass
        rc_trace = None
        if "root_cause_trace" in row.keys() and row["root_cause_trace"]:
            try:
                rc_trace = AgentExecutionTrace(**json.loads(row["root_cause_trace"]))
            except Exception:
                pass
        val_trace = None
        if "validator_trace" in row.keys() and row["validator_trace"]:
            try:
                val_trace = AgentExecutionTrace(**json.loads(row["validator_trace"]))
            except Exception:
                pass

        return Incident(
            incident_id=row["incident_id"],
            trace_id=row["trace_id"],
            title=row["title"],
            status=row["status"],
            severity=row["severity"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            root_cause_service=row["root_cause_service"],
            confidence_score=row["confidence_score"],
            context_divergence_flag=bool(row["context_divergence_flag"]),
            context_badge=row["context_badge"],
            evidence_packet=ComputeResult(**evid_data),
            triage=TriageReport(**triage_data) if triage_data else None,
            root_cause=RootCauseReport(**rc_data) if rc_data else None,
            risk_validation=RiskValidationReport(**risk_data) if risk_data else None,
            triage_trace=tr_trace,
            root_cause_trace=rc_trace,
            validator_trace=val_trace,
            engineer_notes=row["engineer_notes"],
            engineer_feedback=feedback_data,
            acknowledged_by=row["acknowledged_by"],
            acknowledged_at=row["acknowledged_at"],
            resolved_by=row["resolved_by"],
            resolved_at=row["resolved_at"],
            escalated_from_event_id=row["escalated_from_event_id"] if "escalated_from_event_id" in row.keys() else None,
            escalation_reason=row["escalation_reason"] if "escalation_reason" in row.keys() else None,
        )

    def record_suppressed_events(self, events: List[Dict[str, Any]]) -> None:
        if not events:
            return
        with self._get_connection() as conn:
            for ev in events:
                batch_id = ev.get("batch_id") or ev.get("trace_id")
                conn.execute("""
                    INSERT OR REPLACE INTO suppressed_events (
                        event_id, trace_id, batch_id, service, metric, category,
                        suppression_reason, collapsed_count, mad_z_score,
                        sea_case_ref, status, escalated_incident_id, escalation_reason, escalated_by,
                        escalated_at, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, (
                    ev["event_id"],
                    ev["trace_id"],
                    batch_id,
                    ev["service"],
                    ev.get("metric", "unknown"),
                    ev["category"],
                    ev["suppression_reason"],
                    ev.get("collapsed_count", 1),
                    ev.get("mad_z_score", 0.0),
                    ev.get("sea_case_ref"),
                    ev.get("status", "SUPPRESSED"),
                    ev.get("escalated_incident_id"),
                    ev.get("escalation_reason"),
                    ev.get("escalated_by"),
                    ev.get("escalated_at"),
                    ev.get("timestamp", datetime.now(timezone.utc).isoformat())
                ))
            conn.commit()

    def list_suppressed_events(
        self,
        limit: int = 100,
        category: Optional[str] = None,
        trace_id: Optional[str] = None,
        batch_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        query = "SELECT * FROM suppressed_events WHERE 1=1"
        params: List[Any] = []
        if category and category != "ALL":
            query += " AND category = ?"
            params.append(category)
        if trace_id:
            query += " AND (trace_id = ? OR batch_id = ?)"
            params.extend([trace_id, trace_id])
        elif batch_id:
            query += " AND (batch_id = ? OR trace_id = ?)"
            params.extend([batch_id, batch_id])
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        with self._get_connection() as conn:
            cur = conn.execute(query, params)
            rows = cur.fetchall()
            return [dict(r) for r in rows]

    def escalate_suppressed_event(
        self,
        event_id: str,
        reason: str,
        escalated_by: str = "engineer"
    ) -> Optional[Dict[str, Any]]:
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        inc_id = f"INC-ESCALATED-{event_id.replace('SUP-', '')[:8]}"

        with self._get_connection() as conn:
            conn.execute("""
                UPDATE suppressed_events SET
                    status = 'ESCALATED',
                    escalated_incident_id = ?,
                    escalation_reason = ?,
                    escalated_by = ?,
                    escalated_at = ?
                WHERE event_id = ?;
            """, (inc_id, reason, escalated_by, now_iso, event_id))
            conn.commit()
            cur = conn.execute("SELECT * FROM suppressed_events WHERE event_id = ?;", (event_id,))
            row = cur.fetchone()
            if not row:
                return None
            ev = dict(row)

        from backend.models.contracts import ComputeResult, BlastRadiusReport, RiskValidationReport
        existing = self.get_incident(inc_id)
        if not existing:
            dummy_pkt = ComputeResult(
                trace_id=ev["trace_id"],
                timestamp=now_iso,
                raw_alert_count=ev.get("collapsed_count", 1),
                compressed_alert_count=1,
                compression_ratio=0.0,
                deduplicated_clusters=[],
                anomalies=[],
                correlations=[],
                blast_radius=BlastRadiusReport(
                    evidence_id="EVID-BLAST-ESCALATED",
                    root_suspect=ev["service"],
                    compromised_services=[ev["service"]],
                    critical_path_affected=False,
                    blast_radius_score=0.4,
                    nodes=[],
                    customer_facing_impact=False
                ),
                redacted_logs=[],
                symptom_signature=f"{ev['service']}:{ev.get('metric', 'unknown')}",
                risk_score=0.45,
                deterministic_severity="MEDIUM",
                fail_open_recommended=False,
                all_evidence_ids=["EVID-ESCALATED-OVERRIDE"]
            )
            escalated_inc = Incident(
                incident_id=inc_id,
                trace_id=ev["trace_id"],
                title=f"HUMAN REVIEW: Escalated Suppressed Event on {ev['service']}",
                status="NEEDS_HUMAN_REVIEW",
                severity="MEDIUM",
                created_at=now_iso,
                updated_at=now_iso,
                root_cause_service=ev["service"],
                confidence_score=0.75,
                context_badge="HUMAN_OVERRIDE",
                evidence_packet=dummy_pkt,
                escalated_from_event_id=event_id,
                escalation_reason=reason,
                engineer_notes=f"Escalated from suppressed audit log by {escalated_by}: {reason}",
                risk_validation=RiskValidationReport(
                    agent_name="RiskValidatorAgent",
                    timestamp=now_iso,
                    verdict="NEEDS_HUMAN_REVIEW",
                    maker_checker_status="PASSED",
                    final_severity="MEDIUM",
                    confidence_score=0.75,
                    validation_checklist={"human_override": True},
                    justification=f"Engineer {escalated_by} manually revoked suppression: {reason}",
                    recommended_actions=[f"Investigate escalated anomaly on {ev['service']}"],
                    referenced_evidence_ids=["EVID-ESCALATED-OVERRIDE"]
                )
            )
            self.save_incident(escalated_inc)
        else:
            existing.escalated_from_event_id = event_id
            existing.escalation_reason = reason
            self.save_incident(existing)

        return ev
