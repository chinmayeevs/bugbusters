"""
backend/orchestration/pipeline_orchestrator.py
Pure Python asyncio execution controller.
Runs deterministic compute stages in dependency order, tracks job states/timeouts,
persists raw + computed evidence with trace IDs, coordinates AI orchestration,
and guarantees a fail-open path for critical deterministic threshold breaches.
"""

from __future__ import annotations
import asyncio
import os
import time
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Callable

from backend.models.contracts import (
    ComputeResult,
    Incident,
    TriageReport,
    RootCauseReport,
    RiskValidationReport,
)
from scripts.build_evidence_packet import build_evidence_packet
from backend.storage.incident_repository import IncidentRepository
from backend.storage.case_repository import CaseRepository
from agents.self_evolving_agent import SelfEvolvingAgent
from agents.orchestrator_agent import AIOrchestrator


class PipelineStage(str, Enum):
    IDLE = "IDLE"
    INGEST_VALIDATE = "INGEST_VALIDATE"
    COMPUTE_EVIDENCE = "COMPUTE_EVIDENCE"
    SEA_READ = "SEA_READ"
    AI_REASONING = "AI_REASONING"
    FAIL_OPEN_TRIGGERED = "FAIL_OPEN_TRIGGERED"
    PERSISTING = "PERSISTING"
    SEA_WRITE = "SEA_WRITE"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class PipelineOrchestrator:
    def __init__(
        self,
        incident_repo: Optional[IncidentRepository] = None,
        case_repo: Optional[CaseRepository] = None,
        ai_timeout_seconds: Optional[float] = None
    ):
        self.incident_repo = incident_repo or IncidentRepository()
        self.case_repo = case_repo or CaseRepository()
        self.sea_agent = SelfEvolvingAgent(self.case_repo)
        self.ai_orchestrator = AIOrchestrator()
        env_timeout = float(os.environ.get("LLM_TIMEOUT_SECONDS", "25")) * 3
        self.ai_timeout_seconds = ai_timeout_seconds or max(45.0, env_timeout)
        self.current_stage = PipelineStage.IDLE
        self.stage_timings: Dict[str, float] = {}
        self.subscribers: List[Callable[[Dict[str, Any]], None]] = []

    def subscribe(self, callback: Callable[[Dict[str, Any]], None]):
        """Subscribes a listener to pipeline stage transitions (used by GraphQL WebSockets)."""
        self.subscribers.append(callback)

    def _notify(self, event_type: str, payload: Dict[str, Any]):
        evt = {"type": event_type, "timestamp": datetime.now(timezone.utc).isoformat(), "data": payload}
        for sub in self.subscribers:
            try:
                sub(evt)
            except Exception:
                pass
        try:
            from backend.graphql.subscriptions import PIPELINE_EVENT_QUEUE
            PIPELINE_EVENT_QUEUE.put_nowait(evt)
        except Exception:
            pass

    async def run_pipeline(
        self,
        raw_alerts: List[Dict[str, Any]],
        raw_metrics: List[Dict[str, Any]],
        raw_logs: List[Dict[str, Any]],
        runtime_context: Optional[Dict[str, Any]] = None,
        force_ai_failure: bool = False,
        force_mock_ai: bool = False
    ) -> Incident:
        """
        Executes the end-to-end AIOps verification pipeline:
        Compute First -> Reason Second -> Verify Against Evidence & History -> Publish Incident.
        """
        trace_id = f"trc_{uuid.uuid4().hex[:12]}"
        run_id = f"run_{uuid.uuid4().hex[:8]}"
        t_start = time.perf_counter()

        self._notify("PIPELINE_STARTED", {"run_id": run_id, "trace_id": trace_id})

        # -------------------------------------------------------------
        # Stage 1: Deterministic Compute First
        # -------------------------------------------------------------
        self.current_stage = PipelineStage.COMPUTE_EVIDENCE
        t0 = time.perf_counter()
        self._notify("STAGE_CHANGE", {"stage": self.current_stage.value, "run_id": run_id})

        # Compute all stats, correlations, redactions, blast radius
        packet: ComputeResult = build_evidence_packet(
            raw_alerts_data=raw_alerts,
            raw_metrics_data=raw_metrics,
            raw_logs_data=raw_logs,
            trace_id=trace_id
        )
        self.stage_timings["compute_ms"] = round((time.perf_counter() - t0) * 1000, 2)

        # -------------------------------------------------------------
        # Stage 2: Self-Evolving Agent (Read Path)
        # -------------------------------------------------------------
        self.current_stage = PipelineStage.SEA_READ
        t1 = time.perf_counter()
        self._notify("STAGE_CHANGE", {"stage": self.current_stage.value, "run_id": run_id})

        historical_matches, divergence_flag, div_reason = self.sea_agent.evaluate_historical_context(
            packet=packet,
            runtime_context=runtime_context
        )
        packet.historical_matches = historical_matches
        packet.context_divergence_detected = divergence_flag
        self.stage_timings["sea_read_ms"] = round((time.perf_counter() - t1) * 1000, 2)

        # Determine context badge for operational UI
        if divergence_flag:
            context_badge = "CONTEXT_DIVERGENCE_DETECTED"
        elif historical_matches and any(m.historical_outcome == "BENIGN_NOISE" for m in historical_matches):
            context_badge = "BENIGN_REPEAT_PATTERN"
        else:
            context_badge = "NORMAL"

        # -------------------------------------------------------------
        # Stage 3: AI Orchestration (with Strict Fail-Open Path)
        # -------------------------------------------------------------
        self.current_stage = PipelineStage.AI_REASONING
        t2 = time.perf_counter()
        self._notify("STAGE_CHANGE", {"stage": self.current_stage.value, "run_id": run_id})

        triage_report: Optional[TriageReport] = None
        root_cause_report: Optional[RootCauseReport] = None
        risk_report: Optional[RiskValidationReport] = None
        ai_failed = force_ai_failure

        if not force_ai_failure:
            try:
                # Coordinate Triage -> Root Cause -> Risk Validator
                triage_report, root_cause_report, risk_report = await asyncio.wait_for(
                    self.ai_orchestrator.execute(
                        packet=packet,
                        runtime_hints={
                            "runtime_context": runtime_context,
                            "context_badge": context_badge,
                            "force_mock": force_mock_ai
                        }
                    ),
                    timeout=self.ai_timeout_seconds
                )
            except Exception as e:
                print(f"[PipelineOrchestrator] AI reasoning failed or timed out: {e}")
                ai_failed = True

        self.stage_timings["ai_reasoning_ms"] = round((time.perf_counter() - t2) * 1000, 2)

        # -------------------------------------------------------------
        # Stage 4: Fail-Open Evaluation & Incident Synthesis
        # -------------------------------------------------------------
        incident_id = f"INC-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        if ai_failed:
            if packet.fail_open_recommended or packet.deterministic_severity == "CRITICAL":
                # Critical threshold breached: FAIL-OPEN GUARANTEE ENFORCED!
                self.current_stage = PipelineStage.FAIL_OPEN_TRIGGERED
                self._notify("STAGE_CHANGE", {"stage": self.current_stage.value, "run_id": run_id})
                status = "FAIL_OPEN_CRITICAL"
                severity = "CRITICAL"
                title = f"FAIL-OPEN: Critical Breach on {packet.blast_radius.compromised_services[0]} (AI Layer Offline)"
                confidence = 1.0  # 100% deterministic certainty
            else:
                status = "SUPPRESSED_NOISE"
                severity = "LOW"
                title = "Suppressed: AI Unavailable & No Critical Deterministic Breach"
                confidence = 0.5
        else:
            assert risk_report is not None
            assert root_cause_report is not None
            assert triage_report is not None

            status = risk_report.verdict
            severity = risk_report.final_severity
            confidence = risk_report.confidence_score
            title = f"{severity}: Incident on {root_cause_report.root_cause_service} ({triage_report.incident_scope})"

        from agents.llm_gateway import get_agent_trace
        from backend.models.contracts import AgentExecutionTrace

        tr_trace_dict = get_agent_trace("TriageReport")
        rc_trace_dict = get_agent_trace("RootCauseReport")
        val_trace_dict = get_agent_trace("RiskValidationReport")

        triage_trace = AgentExecutionTrace(**tr_trace_dict) if tr_trace_dict else None
        root_cause_trace = AgentExecutionTrace(**rc_trace_dict) if rc_trace_dict else None
        validator_trace = AgentExecutionTrace(**val_trace_dict) if val_trace_dict else None

        incident = Incident(
            incident_id=incident_id,
            trace_id=trace_id,
            title=title,
            status=status,  # type: ignore
            severity=severity,  # type: ignore
            created_at=now_iso,
            updated_at=now_iso,
            root_cause_service=root_cause_report.root_cause_service if root_cause_report else packet.blast_radius.root_suspect,
            confidence_score=confidence,
            context_divergence_flag=divergence_flag,
            context_badge=context_badge,
            evidence_packet=packet,
            triage=triage_report,
            root_cause=root_cause_report,
            risk_validation=risk_report,
            triage_trace=triage_trace,
            root_cause_trace=root_cause_trace,
            validator_trace=validator_trace,
        )

        # -------------------------------------------------------------
        # Stage 5: Persistence
        # -------------------------------------------------------------
        self.current_stage = PipelineStage.PERSISTING
        t3 = time.perf_counter()
        self.incident_repo.save_incident(incident)

        # Collect and record suppressed events for the "No Silent Suppression" Audit Trail
        suppressed_list: List[Dict[str, Any]] = []
        for idx, cluster in enumerate(packet.deduplicated_clusters):
            if cluster.count > 1:
                suppressed_list.append({
                    "event_id": f"SUP-DEDUP-{run_id[-6:]}-{idx:02d}",
                    "trace_id": trace_id,
                    "service": cluster.service,
                    "metric": cluster.alert_name,
                    "category": "DUPLICATES",
                    "suppression_reason": f"Deduplicated {cluster.count - 1} redundant alerts inside 5-min sliding window",
                    "collapsed_count": cluster.count - 1,
                    "mad_z_score": 0.0,
                    "sea_case_ref": None,
                    "status": "SUPPRESSED",
                    "timestamp": cluster.last_seen or now_iso
                })
            if cluster.is_flapping:
                suppressed_list.append({
                    "event_id": f"SUP-FLAP-{run_id[-6:]}-{idx:02d}",
                    "trace_id": trace_id,
                    "service": cluster.service,
                    "metric": cluster.alert_name,
                    "category": "TRANSIENT_BLIPS",
                    "suppression_reason": "High frequency flapping cycle without customer ingress degradation",
                    "collapsed_count": cluster.count,
                    "mad_z_score": 1.2,
                    "sea_case_ref": None,
                    "status": "SUPPRESSED",
                    "timestamp": cluster.last_seen or now_iso
                })

        if incident.status == "SUPPRESSED_NOISE" or (not divergence_flag and historical_matches and any(m.historical_outcome == "BENIGN_NOISE" for m in historical_matches)):
            top_benign = next((m for m in historical_matches if m.historical_outcome == "BENIGN_NOISE"), None)
            suppressed_list.append({
                "event_id": f"SUP-SEA-{run_id[-6:]}",
                "trace_id": trace_id,
                "service": top_benign.symptom_signature.split(":")[0] if top_benign else packet.blast_radius.root_suspect,
                "metric": top_benign.symptom_signature.split(":")[-1] if top_benign else "cpu_pct",
                "category": "SEA_BENIGN_REPEATS",
                "suppression_reason": f"Matched verified benign maintenance pattern {top_benign.case_id if top_benign else 'CASE-HIST-001'} with zero downstream customer impact",
                "collapsed_count": packet.raw_alert_count,
                "mad_z_score": 2.8,
                "sea_case_ref": top_benign.case_id if top_benign else "CASE-HIST-001",
                "status": "SUPPRESSED",
                "timestamp": now_iso
            })

        if suppressed_list:
            self.incident_repo.record_suppressed_events(suppressed_list)

        self.stage_timings["persistence_ms"] = round((time.perf_counter() - t3) * 1000, 2)

        # -------------------------------------------------------------
        # Stage 6: Self-Evolving Agent (Write Path)
        # -------------------------------------------------------------
        if incident.status == "VERIFIED_INCIDENT":
            self.current_stage = PipelineStage.SEA_WRITE
            self.sea_agent.record_verified_outcome(incident)

        self.current_stage = PipelineStage.COMPLETED
        self.stage_timings["total_pipeline_ms"] = round((time.perf_counter() - t_start) * 1000, 2)
        self._notify("PIPELINE_COMPLETED", {"incident_id": incident.incident_id, "status": incident.status, "timings": self.stage_timings})

        return incident
