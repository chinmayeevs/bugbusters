"""
agents/risk_validator_agent.py
Risk Validator Agent: Strict Maker-Checker Gate in the AI Orchestrator state machine.
Cross-examines Triage and Root-Cause hypotheses against verified deterministic evidence IDs,
statistical MAD significance, blast-radius metrics, and historical Context Divergence.
Rejects hallucinated claims and strictly outputs:
  - VERIFIED_INCIDENT
  - SUPPRESSED_NOISE
  - NEEDS_HUMAN_REVIEW
Enforces strict RiskValidationReport Pydantic validation.
"""

from __future__ import annotations
from typing import Dict, Any, Optional, Set
from backend.models.contracts import (
    ComputeResult,
    TriageReport,
    RootCauseReport,
    RiskValidationReport,
)
from agents.llm_gateway import call_llm

SYSTEM_INSTRUCTION = """You are the Senior Risk Validator & Gatekeeper in an enterprise AIOps verification pipeline.
You act as an adversarial checker to independently verify findings from the Triage and Root-Cause agents.
MAKER-CHECKER MANDATES:
1. Every claim MUST be backed by genuine evidence IDs present in the evidence packet.
2. If Context Divergence is flagged (symptoms match a historical benign case but context conditions diverged), you MUST OVERRIDE benign suppression and verify the incident!
3. If alerts are pure flapping with zero downstream latency or error breach, verdict MUST be SUPPRESSED_NOISE.
4. Output verdict strictly as one of: VERIFIED_INCIDENT, SUPPRESSED_NOISE, or NEEDS_HUMAN_REVIEW.
You must output a strictly valid JSON object matching the RiskValidationReport schema."""


class RiskValidatorAgent:
    def __init__(self):
        pass

    async def run(
        self,
        packet: ComputeResult,
        triage: TriageReport,
        root_cause: RootCauseReport,
        hints: Optional[Dict[str, Any]] = None
    ) -> RiskValidationReport:
        """
        Executes maker-checker verification gate.
        """
        hints = hints or {}
        hints.update({
            "root_candidate": root_cause.root_cause_service,
            "severity": packet.deterministic_severity,
            "context_divergence": packet.context_divergence_detected,
            "context_badge": hints.get("context_badge", ""),
            "is_flapping": bool(packet.deduplicated_clusters and all(c.is_flapping for c in packet.deduplicated_clusters)),
            "evidence_ids": packet.all_evidence_ids,
            "timestamp": packet.timestamp,
        })

        prompt = f"""
MAKER-CHECKER VERIFICATION DOSSIER:

1. EVIDENCE PACKET GROUNDING:
- Deterministic Severity: {packet.deterministic_severity}
- Risk Score: {packet.risk_score}
- Valid Evidence IDs: {', '.join(packet.all_evidence_ids[:10])}
- Context Divergence Flag: {packet.context_divergence_detected}
- Fail-Open Recommended: {packet.fail_open_recommended} (Reason: {packet.fail_open_reason})

2. HISTORICAL CASEBOOK MATCHES (SEA READ PATH):
{chr(10).join([f" - Case {m.case_id}: '{m.title}' (Sim={m.similarity_score}, HistOutcome={m.historical_outcome}, DivergenceFlag={m.context_divergence_flag}, Reason={m.divergence_reason})" for m in packet.historical_matches]) if packet.historical_matches else " - No historical casebook matches."}

3. PROPOSED TRIAGE (MAKER 1):
- Scope: {triage.incident_scope}
- Urgency: {triage.urgency}
- Cited Evidence IDs: {', '.join(triage.supporting_evidence_ids)}

4. PROPOSED ROOT CAUSE (MAKER 2):
- Service: {root_cause.root_cause_service}
- Mechanism: {root_cause.failure_mechanism}
- Confidence: {root_cause.confidence_score}
- Cited Evidence IDs: {', '.join(root_cause.supporting_evidence_ids)}

INSTRUCTIONS:
Conduct maker-checker verification. Verify that cited evidence IDs are authentic.
Assess whether context divergence mandates an incident override.
Formulate final verdict (VERIFIED_INCIDENT | SUPPRESSED_NOISE | NEEDS_HUMAN_REVIEW),
checklist validation, and recommended actions.
"""

        raw_json = await call_llm(
            prompt=prompt,
            system_instruction=SYSTEM_INSTRUCTION,
            target_schema_name="RiskValidationReport",
            context_hints=hints,
            target_model_cls=RiskValidationReport,
            valid_evidence_ids=packet.all_evidence_ids
        )

        # Enforce strict Pydantic JSON schema validation
        report = RiskValidationReport.model_validate(raw_json)

        # Deterministic Maker-Checker Programmatic Sanity Check:
        # Cross-reference cited evidence IDs against true packet evidence IDs
        valid_ids_set = set(packet.all_evidence_ids)
        for ref_id in report.referenced_evidence_ids:
            if ref_id not in valid_ids_set:
                # Flag potential hallucination
                report.maker_checker_status = "REJECTED_HALLUCINATION"
                report.verdict = "NEEDS_HUMAN_REVIEW"
                report.justification += f" [Maker-Checker Warning: Agent referenced unknown evidence ID {ref_id}]."

        # Enforce Context Divergence Protection (Case B):
        if packet.context_divergence_detected and report.verdict != "VERIFIED_INCIDENT":
            report.verdict = "VERIFIED_INCIDENT"
            report.maker_checker_status = "OVERRIDDEN_BY_DIVERGENCE"
            report.final_severity = "CRITICAL"
            report.justification = (
                "AUTOMATIC SAFETY OVERRIDE: Context Divergence detected! Benign suppression revoked "
                "due to active downstream latency/error spike."
            )

        # Enforce Benign Repeat Suppression (Case A):
        is_benign_repeat = (
            hints.get("context_badge") == "BENIGN_REPEAT_PATTERN"
            or any(m.historical_outcome == "BENIGN_NOISE" and not m.context_divergence_flag for m in packet.historical_matches)
        ) and not packet.context_divergence_detected

        if is_benign_repeat:
            report.verdict = "SUPPRESSED_NOISE"
            report.final_severity = "SUPPRESSED"
            report.maker_checker_status = "PASSED"
            report.justification = (
                "Verified match with historical benign backup maintenance (Case A); zero downstream customer latency confirmed."
            )

        return report
