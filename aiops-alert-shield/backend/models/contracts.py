"""
Data Contracts and Schema Definitions for aiops-alert-shield.
Strict Pydantic models ensuring end-to-end evidence traceability,
deterministic compute types, agent responses, and incident records.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any, Literal
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Raw Ingestion Contracts
# ---------------------------------------------------------------------------

class RawAlert(BaseModel):
    alert_id: str = Field(..., description="Unique alert identifier")
    timestamp: str = Field(..., description="ISO 8601 UTC timestamp")
    service: str = Field(..., description="Target service name")
    alert_name: str = Field(..., description="Normalized alert rule name")
    severity: Literal["CRITICAL", "WARNING", "INFO", "LOW"]
    metric_name: Optional[str] = None
    metric_value: Optional[float] = None
    threshold: Optional[float] = None
    entity: Optional[str] = None
    message: str
    tags: Dict[str, Any] = Field(default_factory=dict)


class RawMetricPoint(BaseModel):
    timestamp: str
    service: str
    metric_name: str
    value: float


class RawLogEntry(BaseModel):
    log_id: str
    timestamp: str
    service: str
    level: Literal["DEBUG", "INFO", "WARN", "WARNING", "ERROR", "CRITICAL", "FATAL"]
    message: str
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Privacy & Deduplication Contracts
# ---------------------------------------------------------------------------

class RedactedLogEntry(BaseModel):
    log_id: str
    timestamp: str
    service: str
    level: str
    redacted_message: str
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    redactions_count: int = 0
    redaction_types: List[str] = Field(default_factory=list)


class DeduplicatedAlertCluster(BaseModel):
    cluster_id: str
    fingerprint: str
    service: str
    alert_name: str
    severity: str
    count: int
    first_seen: str
    last_seen: str
    raw_alert_ids: List[str]
    is_flapping: bool = False
    representative_message: str


# ---------------------------------------------------------------------------
# Sliding-Window & Anomaly Feature Contracts
# ---------------------------------------------------------------------------

class WindowMetricStats(BaseModel):
    evidence_id: str = Field(..., description="Unique deterministic evidence ID (e.g. EVID-STAT-001)")
    service: str
    metric_name: str
    window_seconds: int = 300
    current_value: float
    median: float
    mad: float
    ewma: float
    rate_of_change: float
    z_score_mad: float
    is_static_breach: bool = False
    static_threshold: Optional[float] = None
    is_anomaly: bool = False
    persistence_count: int = 1
    hysteresis_triggered: bool = False


class MetricDataPoint(BaseModel):
    timestamp: str
    service: str
    metric_name: str
    value: float
    ewma: float
    median: float
    mad_lower: float
    mad_upper: float
    static_threshold: Optional[float] = None
    is_anomaly: bool = False


class RiskFeatureItem(BaseModel):
    name: str
    score: float
    weight: float
    contribution: float
    description: str


# ---------------------------------------------------------------------------
# Dependency Graph & Lag Correlation Contracts
# ---------------------------------------------------------------------------

class CrossServiceCorrelation(BaseModel):
    evidence_id: str = Field(..., description="Unique correlation evidence ID (e.g. EVID-CORR-001)")
    source_service: str
    source_metric: str
    target_service: str
    target_metric: str
    lag_seconds: int
    pearson_r: float
    causal_order_verified: bool = False
    description: str


class BlastRadiusNode(BaseModel):
    service: str
    role: Literal["ROOT_SUSPECT", "AFFECTED_UPSTREAM", "AFFECTED_DOWNSTREAM", "UNAFFECTED"]
    hop_distance: int
    impact_level: Literal["CRITICAL", "DEGRADED", "NORMAL"]
    traffic_loss_pct: float = 0.0


class BlastRadiusReport(BaseModel):
    evidence_id: str
    root_suspect: str = "orders-postgres-primary"
    compromised_services: List[str]
    critical_path_affected: bool
    blast_radius_score: float = Field(..., ge=0.0, le=1.0)
    nodes: List[BlastRadiusNode]
    customer_facing_impact: bool


# ---------------------------------------------------------------------------
# Self-Evolving Historical Match Contract
# ---------------------------------------------------------------------------

class HistoricalMatch(BaseModel):
    case_id: str
    symptom_signature: str
    title: str
    similarity_score: float
    historical_outcome: Literal["VERIFIED_INCIDENT", "BENIGN_NOISE", "FALSE_POSITIVE", "RESOLVED"]
    context_divergence_flag: bool = False
    divergence_reason: Optional[str] = None
    matching_features: Dict[str, Any] = Field(default_factory=dict)
    divergent_features: Dict[str, Any] = Field(default_factory=dict)
    remediation_recommendation: Optional[str] = None
    matched_context_keys: List[str] = Field(default_factory=list)
    diverged_context_keys: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Typed Deterministic Evidence Packet (ComputeResult)
# ---------------------------------------------------------------------------

class ComputeResult(BaseModel):
    trace_id: str
    timestamp: str
    raw_alert_count: int
    compressed_alert_count: int
    compression_ratio: float
    deduplicated_clusters: List[DeduplicatedAlertCluster]
    anomalies: List[WindowMetricStats]
    correlations: List[CrossServiceCorrelation]
    blast_radius: BlastRadiusReport
    redacted_logs: List[RedactedLogEntry]
    symptom_signature: str
    risk_score: float = Field(..., ge=0.0, le=1.0)
    deterministic_severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW", "BENIGN"]
    fail_open_recommended: bool = False
    fail_open_reason: Optional[str] = None
    historical_matches: List[HistoricalMatch] = Field(default_factory=list)
    context_divergence_detected: bool = False
    all_evidence_ids: List[str] = Field(default_factory=list)
    metric_series: List[MetricDataPoint] = Field(default_factory=list)
    risk_breakdown: List[RiskFeatureItem] = Field(default_factory=list)
    mermaid_diagram: str = ""


# ---------------------------------------------------------------------------
# AI Agent Output Contracts (Strict JSON schemas)
# ---------------------------------------------------------------------------

class TriageReport(BaseModel):
    agent_name: Literal["TriageAgent"] = "TriageAgent"
    timestamp: str
    incident_scope: Literal["SYSTEM_WIDE", "SERVICE_LOCAL", "DOWNSTREAM_CASCADE", "TRANSIENT_SPIKE"]
    urgency: Literal["P0_CRITICAL", "P1_HIGH", "P2_MEDIUM", "P3_LOW", "P4_NOISE"]
    user_journey_impact: str
    supporting_evidence_ids: List[str]
    triage_summary: str


class RootCauseReport(BaseModel):
    agent_name: Literal["RootCauseAgent"] = "RootCauseAgent"
    timestamp: str
    root_cause_service: str
    causal_chain: List[str]
    failure_mechanism: str
    lag_progression_summary: str
    supporting_evidence_ids: List[str]
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    hypotheses_evaluated: List[str]
    diagnostic_runbook: List[str] = Field(default_factory=list)


class RiskValidationReport(BaseModel):
    agent_name: Literal["RiskValidatorAgent"] = "RiskValidatorAgent"
    timestamp: str
    verdict: Literal["VERIFIED_INCIDENT", "SUPPRESSED_NOISE", "NEEDS_HUMAN_REVIEW"]
    maker_checker_status: Literal["PASSED", "REJECTED_HALLUCINATION", "INSUFFICIENT_EVIDENCE", "OVERRIDDEN_BY_DIVERGENCE"]
    final_severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW", "SUPPRESSED"]
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    validation_checklist: Dict[str, bool]
    justification: str
    recommended_actions: List[str]
    referenced_evidence_ids: List[str]
    suggested_human_checks: List[str] = Field(default_factory=list)
    diagnostic_runbook: List[str] = Field(default_factory=list)


class AgentExecutionTrace(BaseModel):
    agent_name: str
    mode: str = "LIVE_LLM"
    provider: str = "gemini"
    model: str = "gemini-3.5-flash-lite"
    latency_ms: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    compact_evidence_prompt: str = ""
    raw_json_output: Dict[str, Any] = Field(default_factory=dict)
    verified_evidence_refs: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Complete Incident Representation
# ---------------------------------------------------------------------------

class Incident(BaseModel):
    incident_id: str
    trace_id: str
    title: str
    status: Literal[
        "VERIFIED_INCIDENT",
        "SUPPRESSED_NOISE",
        "NEEDS_HUMAN_REVIEW",
        "FAIL_OPEN_CRITICAL",
        "ACKNOWLEDGED",
        "RESOLVED"
    ]
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW", "SUPPRESSED"]
    created_at: str
    updated_at: str
    root_cause_service: str
    confidence_score: float = 0.0
    context_divergence_flag: bool = False
    context_badge: str = "NORMAL"
    evidence_packet: ComputeResult
    triage: Optional[TriageReport] = None
    root_cause: Optional[RootCauseReport] = None
    risk_validation: Optional[RiskValidationReport] = None
    triage_trace: Optional[AgentExecutionTrace] = None
    root_cause_trace: Optional[AgentExecutionTrace] = None
    validator_trace: Optional[AgentExecutionTrace] = None
    engineer_notes: Optional[str] = None
    engineer_feedback: Optional[Dict[str, Any]] = None
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[str] = None
    resolved_by: Optional[str] = None
    resolved_at: Optional[str] = None
    escalated_from_event_id: Optional[str] = None
    escalation_reason: Optional[str] = None
