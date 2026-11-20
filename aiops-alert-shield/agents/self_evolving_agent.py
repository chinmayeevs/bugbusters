"""
agents/self_evolving_agent.py
Self-Evolving Agent (SEA) with dual touchpoints on the versioned Casebook:
1. Read Path (pre-agents): Retrieves historical match candidates and detects Context Divergence:
   - Case A: Same symptom + same benign context (e.g. 02:00 pg_dump maintenance).
   - Case B: Same symptom + different context (e.g. midday lock contention, rising downstream latency).
   * Enforces: Historical matches never silently suppress critical alerts without Risk Validator verification.
2. Write Path (post-verification/feedback): Appends versioned casebook entries only from verified outcomes
   and confirmed engineer resolutions. Never executes auto-remediation.
"""

from __future__ import annotations
from typing import List, Dict, Any, Tuple, Optional
from backend.models.contracts import ComputeResult, HistoricalMatch, Incident
from backend.storage.case_repository import CaseRepository


class SelfEvolvingAgent:
    def __init__(self, case_repo: Optional[CaseRepository] = None):
        self.case_repo = case_repo or CaseRepository()

    def evaluate_historical_context(
        self,
        packet: ComputeResult,
        runtime_context: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[HistoricalMatch], bool, Optional[str]]:
        """
        Read Path: Evaluates deterministic symptom signature against historical casebook.
        Extracts operational runtime context (downstream latency, error rates, time of day)
        and detects Context Divergence.
        """
        # Build current context from packet and runtime flags
        has_downstream_latency = any(
            a.service in ("checkout-api", "api-gateway") and "latency" in a.metric_name and a.is_anomaly
            for a in packet.anomalies
        ) or any(
            c.service in ("checkout-api", "api-gateway") and "timeout" in c.alert_name.lower()
            for c in packet.deduplicated_clusters
        )

        has_downstream_errors = any(
            a.service in ("checkout-api", "api-gateway") and "error" in a.metric_name and a.is_anomaly
            for a in packet.anomalies
        ) or any(
            c.service in ("checkout-api", "api-gateway") and "504" in c.alert_name
            for c in packet.deduplicated_clusters
        )

        current_ctx: Dict[str, Any] = {
            "downstream_latency_spike": has_downstream_latency,
            "error_rate_spike": has_downstream_errors,
            "customer_impact": packet.blast_radius.customer_facing_impact,
            "cron_job_active": None,
        }

        # Merge with explicit runtime context if provided (e.g. time of day, active backup cron)
        if runtime_context:
            current_ctx.update(runtime_context)

        matches = self.case_repo.search_matches(packet.symptom_signature, current_ctx)

        # Context Divergence is evaluated specifically against benign/maintenance candidates
        # that would otherwise trigger suppression:
        divergence_detected = False
        divergence_explanation = None

        for m in matches:
            # Check benign/suppressible historical patterns
            if m.historical_outcome in ("BENIGN_NOISE", "FALSE_POSITIVE"):
                if m.context_divergence_flag:
                    divergence_detected = True
                    divergence_explanation = (
                        f"Context Divergence on case {m.case_id} ('{m.title}'): {m.divergence_reason}"
                    )
                    break

        return matches, divergence_detected, divergence_explanation

    def record_verified_outcome(
        self,
        incident: Incident,
        engineer_feedback: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Write Path: Appends or increments versioned entry in casebook ONLY from
        verified outcomes or confirmed engineer feedback.
        Never executes auto-remediation on production infrastructure.
        """
        # Only record verified incidents or confirmed resolutions
        if incident.status not in ("VERIFIED_INCIDENT", "RESOLVED"):
            return None

        # Build context conditions from verified evidence
        packet = incident.evidence_packet
        has_downstream_lat = any(
            a.service in ("checkout-api", "api-gateway") and "latency" in a.metric_name
            for a in packet.anomalies
        )
        has_downstream_err = any(
            a.service in ("checkout-api", "api-gateway") and "error" in a.metric_name
            for a in packet.anomalies
        )

        ctx_conditions = {
            "downstream_latency_spike": has_downstream_lat,
            "error_rate_spike": has_downstream_err,
            "customer_impact": packet.blast_radius.customer_facing_impact,
            "critical_path_affected": packet.blast_radius.critical_path_affected,
        }

        remediation = ""
        if incident.risk_validation and incident.risk_validation.recommended_actions:
            remediation = "; ".join(incident.risk_validation.recommended_actions)
        if incident.engineer_notes:
            remediation += f" | Engineer note: {incident.engineer_notes}"

        verified_by = incident.resolved_by or incident.acknowledged_by or "ai-risk-validator"

        case_id = self.case_repo.append_verified_case(
            symptom_signature=packet.symptom_signature,
            title=incident.title,
            category=incident.root_cause_service.upper(),
            outcome=incident.status,
            context_conditions=ctx_conditions,
            remediation=remediation,
            verified_by=verified_by
        )
        return case_id
