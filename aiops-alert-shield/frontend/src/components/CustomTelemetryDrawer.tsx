"use client";

import React, { useState } from "react";
import {
  ingestCustomTelemetry,
  uploadTelemetryFile,
  triggerPipeline,
  CustomIngestResult,
  UploadSummaryResult,
} from "@/lib/api";

interface CustomTelemetryDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (incidentId: string) => void;
}

export default function CustomTelemetryDrawer({
  isOpen,
  onClose,
  onSuccess,
}: CustomTelemetryDrawerProps) {
  const [activeTab, setActiveTab] = useState<"form" | "json" | "file">("form");

  // Form Mode State
  const [alertName, setAlertName] = useState<string>("PaymentGatewayTimeoutSpike");
  const [service, setService] = useState<string>("payment-service");
  const [severity, setSeverity] = useState<string>("CRITICAL");
  const [message, setMessage] = useState<string>(
    "Downstream payment gateway handshake timeout during authorization capture."
  );
  const [metricName, setMetricName] = useState<string>("p99_latency_ms");
  const [metricValue, setMetricValue] = useState<number>(2450.0);
  const [threshold, setThreshold] = useState<number>(500.0);

  // JSON Mode State
  const [jsonText, setJsonText] = useState<string>(
    JSON.stringify(
      {
        alerts: [
          {
            alertName: "DatabaseLockContentionSpike",
            service: "orders-postgres-primary",
            severity: "CRITICAL",
            message: "Exclusive row-level lock contention on orders_v2 table",
            metricName: "lock_wait_count",
            metricValue: 45.0,
            threshold: 15.0,
          },
        ],
        metrics: [
          { service: "orders-postgres-primary", metricName: "lock_wait_count", value: 45.0 },
          { service: "checkout-api", metricName: "p99_latency_ms", value: 1850.0 },
        ],
        logs: [
          {
            service: "orders-postgres-primary",
            level: "ERROR",
            message: "Lock wait timeout reached for transaction PID 8812 on table orders_v2",
          },
        ],
      },
      null,
      2
    )
  );

  // File Upload State
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadResult, setUploadResult] = useState<UploadSummaryResult | null>(null);

  // Submission & Pipeline Tracking
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [stageTimings, setStageTimings] = useState<{
    computeMs?: number;
    aiReasoningMs?: number;
    totalMs?: number;
  } | null>(null);

  if (!isOpen) return null;

  const insertTestPII = () => {
    setMessage(
      (prev) =>
        prev +
        " Customer CC: 4532-0150-1234-5674 and SSN: 000-12-3456 reported in payload transaction."
    );
  };

  const loadPreset = (preset: "cascade" | "benign" | "divergence" | "flap") => {
    if (preset === "cascade") {
      setJsonText(
        JSON.stringify(
          {
            alerts: [
              {
                alertName: "PostgresDeadlockCascade",
                service: "orders-postgres-primary",
                severity: "CRITICAL",
                message: "Deadlock detected on orders_v2; conn pool 100% saturated",
                metricName: "conn_pool_pct",
                metricValue: 98.5,
                threshold: 85.0,
              },
            ],
            metrics: [
              { service: "orders-postgres-primary", metricName: "conn_pool_pct", value: 98.5 },
              { service: "checkout-api", metricName: "p99_latency_ms", value: 2100.0 },
              { service: "api-gateway", metricName: "error_rate_5xx", value: 42.0 },
            ],
          },
          null,
          2
        )
      );
    } else if (preset === "benign") {
      setJsonText(
        JSON.stringify(
          {
            alerts: [
              {
                alertName: "PostgresHighCPUContention",
                service: "orders-postgres-primary",
                severity: "WARNING",
                message: "High CPU utilization detected on orders-postgres-primary (pg_dump active)",
                metricName: "cpu_pct",
                metricValue: 92.5,
                threshold: 85.0,
              },
            ],
            runtimeContextJson: JSON.stringify({
              time_window: "02:00-03:00 UTC",
              cron_job_active: "pg_dump_nightly",
              downstream_latency_spike: false,
              customer_impact: false,
            }),
          },
          null,
          2
        )
      );
    } else if (preset === "divergence") {
      setJsonText(
        JSON.stringify(
          {
            alerts: [
              {
                alertName: "PostgresHighCPUContention",
                service: "orders-postgres-primary",
                severity: "WARNING",
                message: "High CPU contention on orders-postgres-primary",
                metricName: "cpu_pct",
                metricValue: 94.0,
                threshold: 85.0,
              },
            ],
            runtimeContextJson: JSON.stringify({
              time_window: "14:15 UTC (Midday Peak)",
              cron_job_active: null,
              downstream_latency_spike: true,
              error_rate_spike: true,
              customer_impact: true,
            }),
          },
          null,
          2
        )
      );
    } else if (preset === "flap") {
      setJsonText(
        JSON.stringify(
          {
            alerts: [
              {
                alertName: "RedisHeartbeatFlap",
                service: "redis-cache",
                severity: "WARNING",
                message: "Intermittent ping flap on redis node 2",
              },
              {
                alertName: "RedisHeartbeatFlap",
                service: "redis-cache",
                severity: "WARNING",
                message: "Intermittent ping flap on redis node 2",
              },
            ],
          },
          null,
          2
        )
      );
    }
  };

  const handleFormSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setStageTimings(null);

    try {
      const res = await ingestCustomTelemetry({
        alerts: [
          {
            alertName,
            service,
            severity,
            message,
            metricName,
            metricValue: Number(metricValue),
            threshold: Number(threshold),
          },
        ],
      });
      setStageTimings({
        computeMs: res.computeMs,
        aiReasoningMs: res.aiReasoningMs,
        totalMs: res.totalPipelineMs,
      });
      setTimeout(() => {
        onSuccess(res.incidentId);
        onClose();
      }, 800);
    } catch (err) {
      alert(`Ingestion failed: ${err}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleJsonSubmit = async () => {
    setIsSubmitting(true);
    setStageTimings(null);

    try {
      const parsed = JSON.parse(jsonText);
      const res = await ingestCustomTelemetry({
        alerts: parsed.alerts,
        metrics: parsed.metrics,
        logs: parsed.logs,
        runtimeContextJson: parsed.runtimeContextJson,
      });
      setStageTimings({
        computeMs: res.computeMs,
        aiReasoningMs: res.aiReasoningMs,
        totalMs: res.totalPipelineMs,
      });
      setTimeout(() => {
        onSuccess(res.incidentId);
        onClose();
      }, 800);
    } catch (err) {
      alert(`Invalid JSON or ingestion error: ${err}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleFileUpload = async () => {
    if (!selectedFile) {
      alert("Please select a file to upload (.json, .jsonl, .csv)");
      return;
    }
    setIsSubmitting(true);
    setUploadResult(null);
    try {
      const res = await uploadTelemetryFile(selectedFile);
      setUploadResult(res);
      setStageTimings({
        totalMs: res.totalPipelineMs,
      });
    } catch (err) {
      alert(`Upload error: ${err}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/80 flex justify-end">
      <div className="bg-[#141418] border-l-4 border-black w-full max-w-2xl h-full flex flex-col p-6 shadow-[-8px_0px_0px_#CCFF00] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between border-b-2 border-zinc-800 pb-4 mb-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 bg-[#CCFF00] border border-black" />
              <h2 className="font-mono text-base font-black uppercase text-white tracking-wider">
                INJECT CUSTOM TELEMETRY & TEST ATTACKS
              </h2>
            </div>
            <p className="font-mono text-xs text-zinc-400 mt-1">
              Test deterministic compute, PII redaction, and AI verification with custom telemetry
            </p>
          </div>
          <button
            onClick={onClose}
            className="px-2.5 py-1 bg-zinc-800 hover:bg-zinc-700 text-white font-mono text-xs font-black uppercase border-2 border-black"
          >
            ✕ CLOSE
          </button>
        </div>

        {/* Mode Tabs */}
        <div className="flex gap-2 font-mono text-xs mb-4">
          <button
            onClick={() => setActiveTab("form")}
            className={`px-3 py-1.5 font-black uppercase border-2 border-black ${
              activeTab === "form"
                ? "bg-[#CCFF00] text-black shadow-[2px_2px_0px_#000]"
                : "bg-[#1C1C22] text-zinc-400"
            }`}
          >
            FORM MODE
          </button>
          <button
            onClick={() => setActiveTab("json")}
            className={`px-3 py-1.5 font-black uppercase border-2 border-black ${
              activeTab === "json"
                ? "bg-[#00E5FF] text-black shadow-[2px_2px_0px_#000]"
                : "bg-[#1C1C22] text-zinc-400"
            }`}
          >
            JSON / CODE EDITOR
          </button>
          <button
            onClick={() => setActiveTab("file")}
            className={`px-3 py-1.5 font-black uppercase border-2 border-black ${
              activeTab === "file"
                ? "bg-[#FFB800] text-black shadow-[2px_2px_0px_#000]"
                : "bg-[#1C1C22] text-zinc-400"
            }`}
          >
            DROPZONE / FILE UPLOAD
          </button>
        </div>

        {/* Tab 1: Form Mode */}
        {activeTab === "form" && (
          <form onSubmit={handleFormSubmit} className="space-y-4 font-mono text-xs">
            <div>
              <label className="block text-zinc-400 uppercase font-bold mb-1">ALERT NAME</label>
              <input
                type="text"
                value={alertName}
                onChange={(e) => setAlertName(e.target.value)}
                required
                className="w-full bg-[#09090B] border-2 border-zinc-700 p-2 text-white outline-none focus:border-[#CCFF00]"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-zinc-400 uppercase font-bold mb-1">TARGET SERVICE</label>
                <select
                  value={service}
                  onChange={(e) => setService(e.target.value)}
                  className="w-full bg-[#09090B] border-2 border-zinc-700 p-2 text-white outline-none focus:border-[#CCFF00]"
                >
                  <option value="api-gateway">api-gateway</option>
                  <option value="checkout-api">checkout-api</option>
                  <option value="payment-service">payment-service</option>
                  <option value="inventory-service">inventory-service</option>
                  <option value="orders-postgres-primary">orders-postgres-primary</option>
                  <option value="redis-cache">redis-cache</option>
                </select>
              </div>
              <div>
                <label className="block text-zinc-400 uppercase font-bold mb-1">SEVERITY</label>
                <select
                  value={severity}
                  onChange={(e) => setSeverity(e.target.value)}
                  className="w-full bg-[#09090B] border-2 border-zinc-700 p-2 text-white outline-none focus:border-[#CCFF00]"
                >
                  <option value="CRITICAL">CRITICAL</option>
                  <option value="HIGH">HIGH</option>
                  <option value="WARNING">WARNING</option>
                  <option value="INFO">INFO</option>
                </select>
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="text-zinc-400 uppercase font-bold">ALERT MESSAGE / LOG BODY</label>
                <button
                  type="button"
                  onClick={insertTestPII}
                  className="text-[10px] text-[#00E5FF] hover:underline uppercase font-bold"
                >
                  + INSERT TEST PII (CARD/SSN)
                </button>
              </div>
              <textarea
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                rows={3}
                required
                className="w-full bg-[#09090B] border-2 border-zinc-700 p-2 text-white outline-none focus:border-[#CCFF00] resize-none"
              />
            </div>

            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="block text-zinc-400 uppercase font-bold mb-1">METRIC NAME</label>
                <input
                  type="text"
                  value={metricName}
                  onChange={(e) => setMetricName(e.target.value)}
                  className="w-full bg-[#09090B] border-2 border-zinc-700 p-2 text-white outline-none focus:border-[#CCFF00]"
                />
              </div>
              <div>
                <label className="block text-zinc-400 uppercase font-bold mb-1">VALUE</label>
                <input
                  type="number"
                  step="any"
                  value={metricValue}
                  onChange={(e) => setMetricValue(parseFloat(e.target.value) || 0)}
                  className="w-full bg-[#09090B] border-2 border-zinc-700 p-2 text-white outline-none focus:border-[#CCFF00]"
                />
              </div>
              <div>
                <label className="block text-zinc-400 uppercase font-bold mb-1">THRESHOLD</label>
                <input
                  type="number"
                  step="any"
                  value={threshold}
                  onChange={(e) => setThreshold(parseFloat(e.target.value) || 0)}
                  className="w-full bg-[#09090B] border-2 border-zinc-700 p-2 text-white outline-none focus:border-[#CCFF00]"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full py-3 bg-[#CCFF00] hover:bg-[#B3E600] text-black font-black uppercase text-sm border-2 border-black shadow-[4px_4px_0px_#000] active:translate-x-0.5 active:translate-y-0.5 disabled:opacity-50 mt-4"
            >
              {isSubmitting ? "PROCESSING DETERMINISTIC COMPUTE..." : "RUN FULL VERIFICATION PIPELINE"}
            </button>
          </form>
        )}

        {/* Tab 2: JSON Editor Mode */}
        {activeTab === "json" && (
          <div className="space-y-3 font-mono text-xs flex-1 flex flex-col">
            <div className="flex flex-wrap gap-1.5 items-center">
              <span className="text-zinc-500 text-[10px] uppercase font-bold">PRESETS:</span>
              <button
                type="button"
                onClick={() => loadPreset("cascade")}
                className="px-2 py-1 bg-zinc-800 hover:bg-zinc-700 text-[#FF2E4C] border border-black text-[10px] font-bold"
              >
                P0 Postgres Cascade
              </button>
              <button
                type="button"
                onClick={() => loadPreset("benign")}
                className="px-2 py-1 bg-zinc-800 hover:bg-zinc-700 text-[#CCFF00] border border-black text-[10px] font-bold"
              >
                Benign 02:00 pg_dump
              </button>
              <button
                type="button"
                onClick={() => loadPreset("divergence")}
                className="px-2 py-1 bg-zinc-800 hover:bg-zinc-700 text-[#00E5FF] border border-black text-[10px] font-bold"
              >
                Midday Context Divergence
              </button>
              <button
                type="button"
                onClick={() => loadPreset("flap")}
                className="px-2 py-1 bg-zinc-800 hover:bg-zinc-700 text-[#FFB800] border border-black text-[10px] font-bold"
              >
                Redis Flap
              </button>
            </div>

            <textarea
              value={jsonText}
              onChange={(e) => setJsonText(e.target.value)}
              rows={12}
              className="w-full bg-[#09090B] border-2 border-zinc-700 p-3 text-[#CCFF00] font-mono text-xs outline-none focus:border-[#00E5FF] resize-none"
            />

            <button
              type="button"
              onClick={handleJsonSubmit}
              disabled={isSubmitting}
              className="w-full py-3 bg-[#00E5FF] hover:bg-[#33EAFF] text-black font-black uppercase text-sm border-2 border-black shadow-[4px_4px_0px_#000] active:translate-x-0.5 active:translate-y-0.5 disabled:opacity-50"
            >
              {isSubmitting ? "PROCESSING..." : "INGEST RAW JSON & VERIFY"}
            </button>
          </div>
        )}

        {/* Tab 3: File Upload Mode */}
        {activeTab === "file" && (
          <div className="space-y-4 font-mono text-xs">
            <div className="border-2 border-dashed border-zinc-700 hover:border-[#FFB800] p-8 text-center bg-[#09090B] cursor-pointer">
              <input
                type="file"
                accept=".json,.jsonl,.csv"
                onChange={(e) => {
                  setSelectedFile(e.target.files?.[0] || null);
                  setUploadResult(null);
                }}
                className="hidden"
                id="file-upload"
              />
              <label htmlFor="file-upload" className="cursor-pointer block">
                <div className="text-2xl mb-2">📁</div>
                <div className="text-white font-bold text-xs uppercase mb-1">
                  {selectedFile ? selectedFile.name : "SELECT OR DRAG & DROP TELEMETRY FILE"}
                </div>
                <div className="text-zinc-500 text-[10px]">
                  Supports .json (alert/metric array), .jsonl (raw streams), or .csv
                </div>
              </label>
            </div>

            <button
              type="button"
              onClick={handleFileUpload}
              disabled={isSubmitting || !selectedFile}
              className="w-full py-3 bg-[#FFB800] hover:bg-[#FFC933] text-black font-black uppercase text-sm border-2 border-black shadow-[4px_4px_0px_#000] active:translate-x-0.5 active:translate-y-0.5 disabled:opacity-50 cursor-pointer"
            >
              {isSubmitting ? "UPLOADING & RUNNING PIPELINE..." : "UPLOAD & EXECUTE VERIFICATION"}
            </button>

            {/* Neo-Brutalist Upload Result Banner */}
            {uploadResult && (
              <div className="p-4 bg-[#09090B] border-2 border-[#CCFF00] font-mono shadow-[4px_4px_0px_#000] space-y-3 mt-4">
                <div className="flex items-center justify-between border-b border-zinc-800 pb-2">
                  <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 bg-[#CCFF00] border border-black inline-block" />
                    <span className="text-white font-black text-xs uppercase tracking-wide">
                      INGESTION BATCH SUMMARY
                    </span>
                  </div>
                  <span className="text-[10px] text-zinc-500 font-bold">
                    BATCH: {uploadResult.batchId}
                  </span>
                </div>

                <div className="p-2.5 bg-[#141418] border border-zinc-700 text-center font-black text-xs text-[#CCFF00]">
                  {uploadResult.rawAlertsIngested.toLocaleString()} RAW ALERTS &rarr; {uploadResult.clustersCreated} CLUSTERS &rarr; {uploadResult.suppressedNoiseCount.toLocaleString()} SUPPRESSED &rarr; {uploadResult.incidentsCreated} INCIDENT CREATED
                </div>

                <div className="flex flex-wrap gap-2 text-[10px]">
                  <span className="px-2 py-0.5 bg-[#1C1C22] border border-zinc-700 text-zinc-300">
                    AI MODE: <strong className="text-white">{uploadResult.aiMode}</strong>
                  </span>
                  <span className="px-2 py-0.5 bg-[#1C1C22] border border-zinc-700 text-zinc-300">
                    MODEL: <strong className="text-[#00E5FF]">{uploadResult.modelUsed}</strong>
                  </span>
                  <span className="px-2 py-0.5 bg-[#1C1C22] border border-zinc-700 text-zinc-300">
                    TOKENS: <strong className="text-[#CCFF00]">{uploadResult.totalTokens.toLocaleString()}</strong>
                  </span>
                  <span className="px-2 py-0.5 bg-[#1C1C22] border border-zinc-700 text-zinc-300">
                    SEVERITY: <strong className={uploadResult.severity === "CRITICAL" ? "text-[#FF2E4C]" : "text-[#FFB800]"}>{uploadResult.severity}</strong>
                  </span>
                  <span className="px-2 py-0.5 bg-[#1C1C22] border border-zinc-700 text-zinc-300">
                    ROOT CAUSE: <strong className="text-white">{uploadResult.rootCauseService}</strong>
                  </span>
                </div>

                <div className="pt-2 flex gap-2">
                  <button
                    type="button"
                    onClick={() => {
                      onSuccess(uploadResult.primaryIncidentId);
                      onClose();
                    }}
                    className="flex-1 py-2.5 bg-[#CCFF00] hover:bg-[#B3E600] text-black font-black uppercase text-xs border-2 border-black shadow-[3px_3px_0px_#000] active:translate-x-0.5 active:translate-y-0.5 cursor-pointer"
                  >
                    [ OPEN NEW INCIDENT: {uploadResult.primaryIncidentId} ]
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setUploadResult(null);
                      setSelectedFile(null);
                    }}
                    className="px-3 py-2.5 bg-zinc-800 hover:bg-zinc-700 text-white font-black uppercase text-xs border border-black cursor-pointer"
                  >
                    RESET
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Pipeline Stage Timing Tracker */}
        {stageTimings && (
          <div className="mt-4 p-3 bg-[#09090B] border-2 border-[#CCFF00] font-mono text-xs">
            <div className="text-[#CCFF00] font-bold uppercase mb-1">
              PIPELINE EXECUTION COMPLETED:
            </div>
            <div className="flex gap-4 text-zinc-300 text-[11px]">
              {stageTimings.computeMs != null && (
                <div>Compute: <strong>{stageTimings.computeMs}ms</strong></div>
              )}
              {stageTimings.aiReasoningMs != null && (
                <div>AI Reasoning: <strong>{stageTimings.aiReasoningMs}ms</strong></div>
              )}
              {stageTimings.totalMs != null && (
                <div>Total: <strong>{stageTimings.totalMs}ms</strong></div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
