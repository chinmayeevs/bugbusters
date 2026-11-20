/**
 * GraphQL API client and TypeScript contracts for AIOps Alert Shield.
 */

const GRAPHQL_ENDPOINT = process.env.NEXT_PUBLIC_GRAPHQL_ENDPOINT || "http://127.0.0.1:8000/graphql";
const BACKEND_BASE_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";

export interface IncidentSummary {
  incidentId: string;
  traceId: string;
  title: string;
  status: string;
  severity: string;
  rootCauseService: string;
  confidenceScore: number;
  contextDivergenceFlag: boolean;
  contextBadge: string;
  createdAt: string;
  updatedAt: string;
  escalatedFromEventId?: string | null;
  escalationReason?: string | null;
  evidencePacket: {
    rawAlertCount: number;
    compressedAlertCount: number;
    compressionRatio: number;
    riskScore: number;
    deterministicSeverity: string;
    failOpenRecommended: boolean;
  };
}

export interface MetricStat {
  evidenceId: string;
  service: string;
  metricName: string;
  currentValue: number;
  median: number;
  mad: number;
  ewma: number;
  rateOfChange: number;
  zScoreMad: number;
  isStaticBreach: boolean;
  isAnomaly: boolean;
}

export interface MetricDataPoint {
  timestamp: string;
  service: string;
  metricName: string;
  value: number;
  ewma: number;
  median: number;
  madLower: number;
  madUpper: number;
  staticThreshold?: number | null;
  isAnomaly: boolean;
}

export interface RiskFeatureItem {
  name: string;
  score: number;
  weight: number;
  contribution: number;
  description: string;
}

export interface Correlation {
  evidenceId: string;
  sourceService: string;
  sourceMetric: string;
  targetService: string;
  targetMetric: string;
  lagSeconds: number;
  pearsonR: number;
  causalOrderVerified: boolean;
  description: string;
}

export interface BlastRadiusNode {
  service: string;
  role: string;
  hopDistance: number;
  impactLevel: string;
  trafficLossPct: number;
}

export interface RedactedLog {
  logId: string;
  timestamp: string;
  service: string;
  level: string;
  redactedMessage: string;
  traceId?: string;
  spanId?: string;
  redactionsCount: number;
}

export interface HistoricalMatchItem {
  caseId: string;
  symptomSignature: string;
  title: string;
  similarityScore: number;
  historicalOutcome: string;
  contextDivergenceFlag: boolean;
  divergenceReason?: string;
  remediationRecommendation?: string;
}

export interface AgentExecutionTrace {
  agentName: string;
  mode: string;
  provider: string;
  model: string;
  latencyMs: number;
  promptTokens: number;
  completionTokens: number;
  totalTokens: number;
  compactEvidencePrompt: string;
  rawJsonOutput: string;
  verifiedEvidenceRefs: string[];
}

export interface FullIncident extends IncidentSummary {
  evidencePacket: {
    traceId: string;
    timestamp: string;
    rawAlertCount: number;
    compressedAlertCount: number;
    compressionRatio: number;
    symptomSignature: string;
    riskScore: number;
    deterministicSeverity: string;
    failOpenRecommended: boolean;
    failOpenReason?: string;
    contextDivergenceDetected: boolean;
    allEvidenceIds: string[];
    anomalies: MetricStat[];
    correlations: Correlation[];
    blastRadius: {
      evidenceId: string;
      rootSuspect: string;
      compromisedServices: string[];
      criticalPathAffected: boolean;
      blastRadiusScore: number;
      customerFacingImpact: boolean;
      nodes: BlastRadiusNode[];
    };
    redactedLogs: RedactedLog[];
    historicalMatches: HistoricalMatchItem[];
    metricSeries?: MetricDataPoint[];
    riskBreakdown?: RiskFeatureItem[];
    mermaidDiagram?: string;
  };
  triage?: {
    agentName: string;
    timestamp: string;
    incidentScope: string;
    urgency: string;
    userJourneyImpact: string;
    supportingEvidenceIds: string[];
    triageSummary: string;
  };
  rootCause?: {
    agentName: string;
    timestamp: string;
    rootCauseService: string;
    causalChain: string[];
    failureMechanism: string;
    lagProgressionSummary: string;
    supportingEvidenceIds: string[];
    confidenceScore: number;
    hypothesesEvaluated: string[];
  };
  riskValidation?: {
    agentName: string;
    timestamp: string;
    verdict: string;
    makerCheckerStatus: string;
    finalSeverity: string;
    confidenceScore: number;
    justification: string;
    recommendedActions: string[];
    referencedEvidenceIds: string[];
    suggestedHumanChecks?: string[];
    diagnosticRunbook?: string[];
  };
  triageTrace?: AgentExecutionTrace;
  rootCauseTrace?: AgentExecutionTrace;
  validatorTrace?: AgentExecutionTrace;
  engineerNotes?: string;
  acknowledgedBy?: string;
  acknowledgedAt?: string;
  resolvedBy?: string;
  resolvedAt?: string;
  escalatedFromEventId?: string | null;
  escalationReason?: string | null;
}

export interface CompressionSummary {
  totalRawAlerts: number;
  totalCompressedClusters: number;
  overallCompressionPct: number;
  activeIncidentsCount: number;
  suppressedNoiseCount: number;
}

export interface ServiceHealth {
  service: string;
  status: string;
  errorRate5xx: number;
  latencyP99Ms: number;
  cpuUtilizationPct: number;
  sampleCount: number;
}

export interface IntelligenceStatus {
  mode: string;
  provider: string;
  model: string;
  apiKeyConfigured: boolean;
  lastLatencyMs: number;
  totalTokensUsed: number;
  lastError?: string | null;
  repairRetries: number;
}

export interface CustomAlertInput {
  alertName: string;
  service: string;
  severity: string;
  message: string;
  timestamp?: string;
  metricName?: string;
  metricValue?: number;
  threshold?: number;
}

export interface CustomMetricInput {
  metricName: string;
  service: string;
  value: number;
  timestamp?: string;
}

export interface CustomLogInput {
  service: string;
  level: string;
  message: string;
  timestamp?: string;
}

export interface IngestCustomTelemetryInput {
  alerts?: CustomAlertInput[];
  metrics?: CustomMetricInput[];
  logs?: CustomLogInput[];
  runtimeContextJson?: string;
}

export interface CustomIngestResult {
  success: boolean;
  incidentId: string;
  traceId: string;
  verdict: string;
  severity: string;
  rootCauseService: string;
  computeMs: number;
  aiReasoningMs: number;
  totalPipelineMs: number;
  incident: FullIncident;
}

async function fetchGraphQL<T>(query: string, variables: Record<string, any> = {}): Promise<T> {
  const res = await fetch(GRAPHQL_ENDPOINT, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ query, variables }),
    cache: "no-store",
  });

  if (!res.ok) {
    throw new Error(`HTTP error! status: ${res.status}`);
  }

  const json = await res.json();
  if (json.errors && json.errors.length > 0) {
    throw new Error(json.errors[0].message);
  }
  return json.data;
}

export async function getIncidents(): Promise<IncidentSummary[]> {
  const query = `
    query GetIncidents {
      incidents(limit: 50) {
        incidentId
        traceId
        title
        status
        severity
        rootCauseService
        confidenceScore
        contextDivergenceFlag
        contextBadge
        createdAt
        updatedAt
        escalatedFromEventId
        escalationReason
        evidencePacket {
          rawAlertCount
          compressedAlertCount
          compressionRatio
          riskScore
          deterministicSeverity
          failOpenRecommended
        }
      }
    }
  `;
  const data = await fetchGraphQL<{ incidents: IncidentSummary[] }>(query);
  return data.incidents;
}

export async function getIncidentById(id: string): Promise<FullIncident | null> {
  const query = `
    query GetIncidentById($id: String!) {
      incident(id: $id) {
        incidentId
        traceId
        title
        status
        severity
        rootCauseService
        confidenceScore
        contextDivergenceFlag
        contextBadge
        createdAt
        updatedAt
        engineerNotes
        acknowledgedBy
        acknowledgedAt
        resolvedBy
        resolvedAt
        escalatedFromEventId
        escalationReason
        evidencePacket {
          traceId
          timestamp
          rawAlertCount
          compressedAlertCount
          compressionRatio
          symptomSignature
          riskScore
          deterministicSeverity
          failOpenRecommended
          failOpenReason
          contextDivergenceDetected
          allEvidenceIds
          mermaidDiagram
          anomalies {
            evidenceId
            service
            metricName
            currentValue
            median
            mad
            ewma
            rateOfChange
            zScoreMad
            isStaticBreach
            isAnomaly
          }
          metricSeries {
            timestamp
            service
            metricName
            value
            ewma
            median
            madLower
            madUpper
            staticThreshold
            isAnomaly
          }
          riskBreakdown {
            name
            score
            weight
            contribution
            description
          }
          correlations {
            evidenceId
            sourceService
            sourceMetric
            targetService
            targetMetric
            lagSeconds
            pearsonR
            causalOrderVerified
            description
          }
          blastRadius {
            evidenceId
            rootSuspect
            compromisedServices
            criticalPathAffected
            blastRadiusScore
            customerFacingImpact
            nodes {
              service
              role
              hopDistance
              impactLevel
              trafficLossPct
            }
          }
          redactedLogs {
            logId
            timestamp
            service
            level
            redactedMessage
            traceId
            spanId
            redactionsCount
          }
          historicalMatches {
            caseId
            symptomSignature
            title
            similarityScore
            historicalOutcome
            contextDivergenceFlag
            divergenceReason
            remediationRecommendation
          }
        }
        triage {
          agentName
          timestamp
          incidentScope
          urgency
          userJourneyImpact
          supportingEvidenceIds
          triageSummary
        }
        rootCause {
          agentName
          timestamp
          rootCauseService
          causalChain
          failureMechanism
          lagProgressionSummary
          supportingEvidenceIds
          confidenceScore
          hypothesesEvaluated
        }
        riskValidation {
          agentName
          timestamp
          verdict
          makerCheckerStatus
          finalSeverity
          confidenceScore
          justification
          recommendedActions
          referencedEvidenceIds
          suggestedHumanChecks
          diagnosticRunbook
        }
        triageTrace {
          agentName
          mode
          provider
          model
          latencyMs
          promptTokens
          completionTokens
          totalTokens
          compactEvidencePrompt
          rawJsonOutput
          verifiedEvidenceRefs
        }
        rootCauseTrace {
          agentName
          mode
          provider
          model
          latencyMs
          promptTokens
          completionTokens
          totalTokens
          compactEvidencePrompt
          rawJsonOutput
          verifiedEvidenceRefs
        }
        validatorTrace {
          agentName
          mode
          provider
          model
          latencyMs
          promptTokens
          completionTokens
          totalTokens
          compactEvidencePrompt
          rawJsonOutput
          verifiedEvidenceRefs
        }
      }
    }
  `;
  const data = await fetchGraphQL<{ incident: FullIncident }>(query, { id });
  return data.incident;
}

export async function getCompressionSummary(): Promise<CompressionSummary> {
  const query = `
    query GetCompressionSummary {
      alertCompressionSummary {
        totalRawAlerts
        totalCompressedClusters
        overallCompressionPct
        activeIncidentsCount
        suppressedNoiseCount
      }
    }
  `;
  const data = await fetchGraphQL<{ alertCompressionSummary: CompressionSummary }>(query);
  return data.alertCompressionSummary;
}

export async function getServiceHealth(): Promise<ServiceHealth[]> {
  const query = `
    query GetServiceHealth {
      serviceHealth {
        service
        status
        errorRate5xx
        latencyP99Ms
        cpuUtilizationPct
        sampleCount
      }
    }
  `;
  const data = await fetchGraphQL<{ serviceHealth: ServiceHealth[] }>(query);
  return data.serviceHealth;
}

export async function getIntelligenceStatus(): Promise<IntelligenceStatus> {
  const query = `
    query GetIntelligenceStatus {
      intelligenceStatus {
        mode
        provider
        model
        apiKeyConfigured
        lastLatencyMs
        totalTokensUsed
        lastError
        repairRetries
      }
    }
  `;
  const data = await fetchGraphQL<{ intelligenceStatus: IntelligenceStatus }>(query);
  return data.intelligenceStatus;
}

export async function configureIntelligence(params: {
  mockLlm?: boolean;
  provider?: string;
  model?: string;
  apiKey?: string;
}): Promise<IntelligenceStatus> {
  const mutation = `
    mutation ConfigureIntelligence($input: ConfigureIntelligenceInput!) {
      configureIntelligence(input: $input) {
        mode
        provider
        model
        apiKeyConfigured
        lastLatencyMs
        totalTokensUsed
        lastError
        repairRetries
      }
    }
  `;
  const data = await fetchGraphQL<{ configureIntelligence: IntelligenceStatus }>(mutation, {
    input: {
      mockLlm: params.mockLlm,
      provider: params.provider,
      model: params.model,
      apiKey: params.apiKey,
    },
  });
  return data.configureIntelligence;
}

export async function testLlmConnection(): Promise<{
  success: boolean;
  mode: string;
  provider: string;
  model: string;
  latencyMs: number;
  message: string;
}> {
  const mutation = `
    mutation TestLlmConnection {
      testLlmConnection {
        success
        mode
        provider
        model
        latencyMs
        message
      }
    }
  `;
  const data = await fetchGraphQL<{
    testLlmConnection: {
      success: boolean;
      mode: string;
      provider: string;
      model: string;
      latencyMs: number;
      message: string;
    };
  }>(mutation);
  return data.testLlmConnection;
}

export async function ingestCustomTelemetry(input: IngestCustomTelemetryInput): Promise<CustomIngestResult> {
  const mutation = `
    mutation IngestCustomTelemetry($input: IngestCustomTelemetryInput!) {
      ingestCustomTelemetry(input: $input) {
        success
        incidentId
        traceId
        verdict
        severity
        rootCauseService
        computeMs
        aiReasoningMs
        totalPipelineMs
        incident {
          incidentId
          title
          status
          severity
          rootCauseService
          confidenceScore
          contextDivergenceFlag
          contextBadge
          createdAt
          updatedAt
          evidencePacket {
            rawAlertCount
            compressedAlertCount
            compressionRatio
            riskScore
            deterministicSeverity
            failOpenRecommended
            symptomSignature
            mermaidDiagram
            allEvidenceIds
            anomalies {
              evidenceId
              service
              metricName
              currentValue
              isAnomaly
            }
            metricSeries {
              timestamp
              service
              metricName
              value
              ewma
              median
              madLower
              madUpper
              staticThreshold
              isAnomaly
            }
            riskBreakdown {
              name
              score
              weight
              contribution
              description
            }
          }
          triage {
            incidentScope
            urgency
            triageSummary
          }
          rootCause {
            rootCauseService
            failureMechanism
            confidenceScore
          }
          riskValidation {
            verdict
            finalSeverity
            confidenceScore
            justification
            suggestedHumanChecks
            diagnosticRunbook
          }
        }
      }
    }
  `;
  const data = await fetchGraphQL<{ ingestCustomTelemetry: CustomIngestResult }>(mutation, { input });
  return data.ingestCustomTelemetry;
}

export interface UploadSummaryResult {
  success: boolean;
  batchId: string;
  rawAlertsIngested: number;
  clustersCreated: number;
  suppressedNoiseCount: number;
  incidentsCreated: number;
  primaryIncidentId: string;
  aiMode: string;
  modelUsed: string;
  totalTokens: number;
  incidentId: string;
  traceId: string;
  status: string;
  severity: string;
  rootCauseService: string;
  title: string;
  alertCount: number;
  metricCount: number;
  logCount: number;
  totalPipelineMs: number;
}

export async function uploadTelemetryFile(file: File): Promise<UploadSummaryResult> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${BACKEND_BASE_URL}/api/ingest/upload`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`Upload failed (${res.status}): ${errorText}`);
  }

  const json = await res.json();
  return {
    success: json.success,
    batchId: json.batch_id || `batch_${Date.now().toString(16)}`,
    rawAlertsIngested: json.raw_alerts_ingested ?? json.alert_count ?? 0,
    clustersCreated: json.clusters_created ?? 1,
    suppressedNoiseCount: json.suppressed_noise_count ?? 0,
    incidentsCreated: json.incidents_created ?? 1,
    primaryIncidentId: json.primary_incident_id || json.incident_id,
    aiMode: json.ai_mode || "LIVE_LLM",
    modelUsed: json.model_used || "gemini-3.5-flash-lite",
    totalTokens: json.total_tokens || 0,
    incidentId: json.incident_id || json.primary_incident_id,
    traceId: json.trace_id,
    status: json.status,
    severity: json.severity,
    rootCauseService: json.root_cause_service,
    title: json.title,
    alertCount: json.alert_count,
    metricCount: json.metric_count,
    logCount: json.log_count,
    totalPipelineMs: json.total_pipeline_ms,
  };
}

export async function acknowledgeIncident(incidentId: string, acknowledgedBy: string = "lead-sre"): Promise<FullIncident> {
  const mutation = `
    mutation AcknowledgeIncident($incidentId: String!, $acknowledgedBy: String) {
      acknowledgeIncident(incidentId: $incidentId, acknowledgedBy: $acknowledgedBy) {
        incidentId
        status
        acknowledgedBy
        acknowledgedAt
      }
    }
  `;
  const data = await fetchGraphQL<{ acknowledgeIncident: FullIncident }>(mutation, { incidentId, acknowledgedBy });
  return data.acknowledgeIncident;
}

export async function submitResolution(incidentId: string, resolution: string, resolvedBy: string = "lead-sre"): Promise<FullIncident> {
  const mutation = `
    mutation SubmitResolution($incidentId: String!, $resolution: String!, $resolvedBy: String) {
      submitResolution(incidentId: $incidentId, resolution: $resolution, resolvedBy: $resolvedBy) {
        incidentId
        status
        resolvedBy
        resolvedAt
        engineerNotes
      }
    }
  `;
  const data = await fetchGraphQL<{ submitResolution: FullIncident }>(mutation, { incidentId, resolution, resolvedBy });
  return data.submitResolution;
}

export async function submitFeedback(incidentId: string, feedback: Record<string, any>): Promise<FullIncident> {
  const mutation = `
    mutation SubmitFeedback($incidentId: String!, $feedbackJson: String!) {
      submitFeedback(incidentId: $incidentId, feedbackJson: $feedbackJson) {
        incidentId
      }
    }
  `;
  const data = await fetchGraphQL<{ submitFeedback: FullIncident }>(mutation, {
    incidentId,
    feedbackJson: JSON.stringify(feedback),
  });
  return data.submitFeedback;
}

export async function triggerPipeline(scenarioName: string, forceAiFailure: boolean = false): Promise<FullIncident> {
  const mutation = `
    mutation TriggerPipeline($scenarioName: String, $forceAiFailure: Boolean) {
      triggerPipeline(scenarioName: $scenarioName, forceAiFailure: $forceAiFailure) {
        incidentId
        status
        severity
        title
      }
    }
  `;
  const data = await fetchGraphQL<{ triggerPipeline: FullIncident }>(mutation, {
    scenarioName,
    forceAiFailure,
  });
  return data.triggerPipeline;
}

// ---------------------------------------------------------------------------
// Evaluation Benchmark, Stream Replay & Audit Trail Contracts & Methods
// ---------------------------------------------------------------------------

export interface EvaluationMetrics {
  incidentRecall: string;
  alertCompressionPct: number;
  verifierPrecisionPct: number;
  evidenceTraceabilityPct: number;
  seaCaseAPassed: boolean;
  seaCaseBPassed: boolean;
  failOpenPassed: boolean;
  p50LatencyMs: number;
  p95LatencyMs: number;
  totalAlertsEvaluated: number;
}

export interface ScenarioBreakdown {
  scenarioKey: string;
  scenarioName: string;
  expectedVerdict: string;
  detectedVerdict: string;
  historicalMatchId?: string | null;
  contextDivergenceDetected: boolean;
  latencyMs: number;
  passed: boolean;
}

export interface EvaluationReport {
  reportId: string;
  timestamp: string;
  status: string;
  metrics: EvaluationMetrics;
  scenarios: ScenarioBreakdown[];
}

export interface SuppressedEvent {
  eventId: string;
  traceId: string;
  service: string;
  metric: string;
  category: string;
  suppressionReason: string;
  collapsedCount: number;
  madZScore: number;
  seaCaseRef?: string | null;
  status: string;
  timestamp: string;
  escalatedBy?: string | null;
  escalationReason?: string | null;
  escalatedAt?: string | null;
  escalatedIncidentId?: string | null;
  batchId?: string | null;
}

export interface ReplayStatus {
  replayId: string;
  isRunning: boolean;
  progressPct: number;
  rawCount: number;
  collapsedCount: number;
  suppressedBlips: number;
  verifiedCount: number;
  currentScenario: string;
  latestMessage: string;
  startedAt?: string | null;
  completedAt?: string | null;
}

export interface StartReplayResult {
  success: boolean;
  replayId: string;
  message: string;
}

export interface SeaCasebookDetail {
  caseId: string;
  title: string;
  symptomSignature: string;
  category: string;
  historicalOutcome: string;
  version: number;
  provenance: string;
  contextConditions: string;
  remediationRecommendation?: string | null;
  diagnosticRunbook: string[];
  createdAt: string;
  updatedAt: string;
}

export async function fetchEvaluationBenchmark(): Promise<EvaluationReport> {
  const query = `
    query GetEvaluationBenchmark {
      evaluationBenchmark {
        reportId
        timestamp
        status
        metrics {
          incidentRecall
          alertCompressionPct
          verifierPrecisionPct
          evidenceTraceabilityPct
          seaCaseAPassed
          seaCaseBPassed
          failOpenPassed
          p50LatencyMs
          p95LatencyMs
          totalAlertsEvaluated
        }
        scenarios {
          scenarioKey
          scenarioName
          expectedVerdict
          detectedVerdict
          historicalMatchId
          contextDivergenceDetected
          latencyMs
          passed
        }
      }
    }
  `;
  const data = await fetchGraphQL<{ evaluationBenchmark: EvaluationReport }>(query);
  return data.evaluationBenchmark;
}

export async function runEvaluationBenchmark(): Promise<EvaluationReport> {
  const mutation = `
    mutation RunEvaluationBenchmark {
      runEvaluationBenchmark {
        reportId
        timestamp
        status
        metrics {
          incidentRecall
          alertCompressionPct
          verifierPrecisionPct
          evidenceTraceabilityPct
          seaCaseAPassed
          seaCaseBPassed
          failOpenPassed
          p50LatencyMs
          p95LatencyMs
          totalAlertsEvaluated
        }
        scenarios {
          scenarioKey
          scenarioName
          expectedVerdict
          detectedVerdict
          historicalMatchId
          contextDivergenceDetected
          latencyMs
          passed
        }
      }
    }
  `;
  const data = await fetchGraphQL<{ runEvaluationBenchmark: EvaluationReport }>(mutation);
  return data.runEvaluationBenchmark;
}

export async function fetchSuppressedEvents(limit: number = 100, category?: string): Promise<SuppressedEvent[]> {
  const query = `
    query GetSuppressedEvents($limit: Int, $category: String) {
      suppressedEvents(limit: $limit, category: $category) {
        eventId
        traceId
        service
        metric
        category
        suppressionReason
        collapsedCount
        madZScore
        seaCaseRef
        status
        timestamp
        escalatedBy
        escalationReason
        escalatedAt
        escalatedIncidentId
        batchId
      }
    }
  `;
  const data = await fetchGraphQL<{ suppressedEvents: SuppressedEvent[] }>(query, { limit, category });
  return data.suppressedEvents;
}

export async function escalateSuppressedEvent(
  eventId: string,
  reason: string,
  escalatedBy: string = "lead-sre"
): Promise<SuppressedEvent> {
  const mutation = `
    mutation EscalateSuppressedEvent($eventId: String!, $reason: String!, $escalatedBy: String) {
      escalateSuppressedEvent(eventId: $eventId, reason: $reason, escalatedBy: $escalatedBy) {
        eventId
        traceId
        service
        metric
        category
        suppressionReason
        collapsedCount
        status
        escalatedBy
        escalationReason
        escalatedIncidentId
        batchId
      }
    }
  `;
  const data = await fetchGraphQL<{ escalateSuppressedEvent: SuppressedEvent }>(mutation, {
    eventId,
    reason,
    escalatedBy,
  });
  return data.escalateSuppressedEvent;
}

export async function fetchSeaCasebook(limit: number = 50): Promise<SeaCasebookDetail[]> {
  const query = `
    query GetSeaCasebook($limit: Int) {
      seaCasebook(limit: $limit) {
        caseId
        title
        symptomSignature
        category
        historicalOutcome
        version
        provenance
        contextConditions
        remediationRecommendation
        diagnosticRunbook
        createdAt
        updatedAt
      }
    }
  `;
  const data = await fetchGraphQL<{ seaCasebook: SeaCasebookDetail[] }>(query, { limit });
  return data.seaCasebook;
}

export async function fetchReplayStatus(replayId?: string): Promise<ReplayStatus> {
  const query = `
    query GetReplayStatus($replayId: String) {
      replayStatus(replayId: $replayId) {
        replayId
        isRunning
        progressPct
        rawCount
        collapsedCount
        suppressedBlips
        verifiedCount
        currentScenario
        latestMessage
        startedAt
        completedAt
      }
    }
  `;
  const data = await fetchGraphQL<{ replayStatus: ReplayStatus }>(query, { replayId });
  return data.replayStatus;
}

export async function startStreamReplay(
  speedMultiplier: number = 5.0,
  includeSeaCases: boolean = true
): Promise<StartReplayResult> {
  const mutation = `
    mutation StartStreamReplay($speedMultiplier: Float, $includeSeaCases: Boolean) {
      startStreamReplay(speedMultiplier: $speedMultiplier, includeSeaCases: $includeSeaCases) {
        success
        replayId
        message
      }
    }
  `;
  const data = await fetchGraphQL<{ startStreamReplay: StartReplayResult }>(mutation, {
    speedMultiplier,
    includeSeaCases,
  });
  return data.startStreamReplay;
}

// ---------------------------------------------------------------------------
// Report Exporter Contracts & Client Methods
// ---------------------------------------------------------------------------

export interface ReportPreviewMeta {
  totalIncidents: number;
  criticalCount: number;
  suppressedCount: number;
  latestIncidentId?: string | null;
  generatedAt: string;
}

export async function fetchReportPreviewMeta(
  scope: string = "all",
  incidentId?: string
): Promise<ReportPreviewMeta> {
  const params = new URLSearchParams();
  params.set("scope", scope);
  if (incidentId) params.set("incident_id", incidentId);

  const res = await fetch(`${BACKEND_BASE_URL}/api/reports/preview-meta?${params.toString()}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch report preview metadata (${res.status})`);
  }
  const json = await res.json();
  return {
    totalIncidents: json.total_incidents,
    criticalCount: json.critical_count,
    suppressedCount: json.suppressed_count,
    latestIncidentId: json.latest_incident_id,
    generatedAt: json.generated_at,
  };
}

export async function downloadReport(
  format: "md" | "pdf",
  scope: string = "all",
  incidentId?: string
): Promise<{ filename: string; sizeBytes: number }> {
  const params = new URLSearchParams();
  params.set("format", format);
  params.set("scope", scope);
  if (incidentId) params.set("incident_id", incidentId);

  const res = await fetch(`${BACKEND_BASE_URL}/api/reports/export?${params.toString()}`);
  if (!res.ok) {
    const errText = await res.text();
    throw new Error(`Report export failed (${res.status}): ${errText}`);
  }

  const disposition = res.headers.get("content-disposition");
  let filename = `aiops-report-${scope}.${format}`;
  if (disposition && disposition.includes("filename=")) {
    const match = disposition.match(/filename="?([^";]+)"?/);
    if (match && match[1]) filename = match[1];
  }

  const blob = await res.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);

  return { filename, sizeBytes: blob.size };
}


