"""
backend/graphql/schema.py
Strawberry GraphQL Schema Definitions for AIOps Alert Shield.
Zero heavy compute inside resolvers: all queries serve pre-processed, persisted records.
"""

from __future__ import annotations
import strawberry
from typing import List, Optional, Dict, Any


@strawberry.type
class AlertClusterType:
    cluster_id: str
    fingerprint: str
    service: str
    alert_name: str
    severity: str
    count: int
    first_seen: str
    last_seen: str
    raw_alert_ids: List[str]
    is_flapping: bool
    representative_message: str


@strawberry.type
class MetricStatType:
    evidence_id: str
    service: str
    metric_name: str
    current_value: float
    median: float
    mad: float
    ewma: float
    rate_of_change: float
    z_score_mad: float
    is_static_breach: bool
    is_anomaly: bool


@strawberry.type
class CorrelationType:
    evidence_id: str
    source_service: str
    source_metric: str
    target_service: str
    target_metric: str
    lag_seconds: int
    pearson_r: float
    causal_order_verified: bool
    description: str


@strawberry.type
class BlastRadiusNodeType:
    service: str
    role: str
    hop_distance: int
    impact_level: str
    traffic_loss_pct: float


@strawberry.type
class BlastRadiusReportType:
    evidence_id: str
    root_suspect: str
    compromised_services: List[str]
    critical_path_affected: bool
    blast_radius_score: float
    customer_facing_impact: bool
    nodes: List[BlastRadiusNodeType]


@strawberry.type
class RedactedLogType:
    log_id: str
    timestamp: str
    service: str
    level: str
    redacted_message: str
    trace_id: Optional[str]
    span_id: Optional[str]
    redactions_count: int


@strawberry.type
class HistoricalMatchGraphQLType:
    case_id: str
    symptom_signature: str
    title: str
    similarity_score: float
    historical_outcome: str
    context_divergence_flag: bool
    divergence_reason: Optional[str]
    remediation_recommendation: Optional[str]


@strawberry.type
class MetricDataPointType:
    timestamp: str
    service: str
    metric_name: str
    value: float
    ewma: float
    median: float
    mad_lower: float
    mad_upper: float
    static_threshold: Optional[float]
    is_anomaly: bool


@strawberry.type
class RiskFeatureItemType:
    name: str
    score: float
    weight: float
    contribution: float
    description: str


@strawberry.type
class ComputeResultType:
    trace_id: str
    timestamp: str
    raw_alert_count: int
    compressed_alert_count: int
    compression_ratio: float
    symptom_signature: str
    risk_score: float
    deterministic_severity: str
    fail_open_recommended: bool
    fail_open_reason: Optional[str]
    context_divergence_detected: bool
    deduplicated_clusters: List[AlertClusterType]
    anomalies: List[MetricStatType]
    correlations: List[CorrelationType]
    blast_radius: BlastRadiusReportType
    redacted_logs: List[RedactedLogType]
    historical_matches: List[HistoricalMatchGraphQLType]
    all_evidence_ids: List[str]
    metric_series: List[MetricDataPointType]
    risk_breakdown: List[RiskFeatureItemType]
    mermaid_diagram: str


@strawberry.type
class TriageReportType:
    agent_name: str
    timestamp: str
    incident_scope: str
    urgency: str
    user_journey_impact: str
    supporting_evidence_ids: List[str]
    triage_summary: str


@strawberry.type
class RootCauseReportType:
    agent_name: str
    timestamp: str
    root_cause_service: str
    causal_chain: List[str]
    failure_mechanism: str
    lag_progression_summary: str
    supporting_evidence_ids: List[str]
    confidence_score: float
    hypotheses_evaluated: List[str]


@strawberry.type
class RiskValidationReportType:
    agent_name: str
    timestamp: str
    verdict: str
    maker_checker_status: str
    final_severity: str
    confidence_score: float
    justification: str
    recommended_actions: List[str]
    referenced_evidence_ids: List[str]
    suggested_human_checks: List[str]
    diagnostic_runbook: List[str]


@strawberry.type
class AgentExecutionTraceType:
    agent_name: str
    mode: str
    provider: str
    model: str
    latency_ms: float
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    compact_evidence_prompt: str
    raw_json_output: str
    verified_evidence_refs: List[str]


@strawberry.type
class IncidentType:
    incident_id: str
    trace_id: str
    title: str
    status: str
    severity: str
    created_at: str
    updated_at: str
    root_cause_service: str
    confidence_score: float
    context_divergence_flag: bool
    context_badge: str
    evidence_packet: ComputeResultType
    triage: Optional[TriageReportType]
    root_cause: Optional[RootCauseReportType]
    risk_validation: Optional[RiskValidationReportType]
    triage_trace: Optional[AgentExecutionTraceType] = None
    root_cause_trace: Optional[AgentExecutionTraceType] = None
    validator_trace: Optional[AgentExecutionTraceType] = None
    engineer_notes: Optional[str]
    acknowledged_by: Optional[str]
    acknowledged_at: Optional[str]
    resolved_by: Optional[str]
    resolved_at: Optional[str]
    escalated_from_event_id: Optional[str] = None
    escalation_reason: Optional[str] = None


@strawberry.type
class AlertCompressionSummaryType:
    total_raw_alerts: int
    total_compressed_clusters: int
    overall_compression_pct: float
    active_incidents_count: int
    suppressed_noise_count: int


@strawberry.type
class ServiceHealthType:
    service: str
    status: str
    error_rate_5xx: float
    latency_p99_ms: float
    cpu_utilization_pct: float
    sample_count: int


@strawberry.type
class HistoricalCaseType:
    case_id: str
    symptom_signature: str
    title: str
    category: str
    historical_outcome: str
    remediation_recommendation: Optional[str]
    version: int


@strawberry.type
class PipelineStatusUpdateType:
    run_id: str
    stage: str
    timestamp: str
    message: Optional[str]


@strawberry.type
class IntelligenceStatusType:
    mode: str
    provider: str
    model: str
    apiKeyConfigured: bool
    lastLatencyMs: float
    totalTokensUsed: int
    lastError: Optional[str]
    repairRetries: int


@strawberry.input
class ConfigureIntelligenceInput:
    mock_llm: Optional[bool] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    api_key: Optional[str] = None


@strawberry.type
class TestLlmConnectionResultType:
    success: bool
    mode: str
    provider: str
    model: str
    latency_ms: float
    message: str


@strawberry.input
class CustomAlertInput:
    alert_name: str
    service: str
    severity: str
    message: str
    timestamp: Optional[str] = None
    metric_name: Optional[str] = None
    metric_value: Optional[float] = None
    threshold: Optional[float] = None


@strawberry.input
class CustomMetricInput:
    metric_name: str
    service: str
    value: float
    timestamp: Optional[str] = None


@strawberry.input
class CustomLogInput:
    service: str
    level: str
    message: str
    timestamp: Optional[str] = None


@strawberry.input
class IngestCustomTelemetryInput:
    alerts: Optional[List[CustomAlertInput]] = None
    metrics: Optional[List[CustomMetricInput]] = None
    logs: Optional[List[CustomLogInput]] = None
    runtime_context_json: Optional[str] = None


@strawberry.type
class CustomIngestResultType:
    success: bool
    incident_id: str
    trace_id: str
    verdict: str
    severity: str
    root_cause_service: str
    compute_ms: float
    ai_reasoning_ms: float
    total_pipeline_ms: float
    incident: IncidentType


# ---------------------------------------------------------------------------
# Benchmark Evaluation & Replay GraphQL Types
# ---------------------------------------------------------------------------

@strawberry.type
class EvaluationMetricsType:
    incident_recall: str
    alert_compression_pct: float
    verifier_precision_pct: float
    evidence_traceability_pct: float
    sea_case_a_passed: bool
    sea_case_b_passed: bool
    fail_open_passed: bool
    p50_latency_ms: float
    p95_latency_ms: float
    total_alerts_evaluated: int


@strawberry.type
class ScenarioBreakdownType:
    scenario_key: str
    scenario_name: str
    expected_verdict: str
    detected_verdict: str
    historical_match_id: Optional[str]
    context_divergence_detected: bool
    latency_ms: float
    passed: bool


@strawberry.type
class EvaluationReportType:
    report_id: str
    timestamp: str
    status: str
    metrics: EvaluationMetricsType
    scenarios: List[ScenarioBreakdownType]


@strawberry.type
class SuppressedEventType:
    event_id: str
    trace_id: str
    service: str
    metric: str
    category: str
    suppression_reason: str
    collapsed_count: int
    mad_z_score: float
    sea_case_ref: Optional[str]
    status: str
    timestamp: str
    escalated_by: Optional[str] = None
    escalation_reason: Optional[str] = None
    escalated_at: Optional[str] = None
    escalated_incident_id: Optional[str] = None
    batch_id: Optional[str] = None


@strawberry.type
class ReplayStatusType:
    replay_id: str
    is_running: bool
    progress_pct: float
    raw_count: int
    collapsed_count: int
    suppressed_blips: int
    verified_count: int
    current_scenario: str
    latest_message: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


@strawberry.type
class StartReplayResultType:
    success: bool
    replay_id: str
    message: str


@strawberry.type
class SeaCasebookDetailType:
    case_id: str
    title: str
    symptom_signature: str
    category: str
    historical_outcome: str
    version: int
    provenance: str
    context_conditions: str
    remediation_recommendation: Optional[str]
    diagnostic_runbook: List[str]
    created_at: str
    updated_at: str

