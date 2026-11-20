"use client";

import React, { useState, useEffect } from "react";
import { fetchReportPreviewMeta, downloadReport, ReportPreviewMeta } from "@/lib/api";
import { Download, FileText, CheckCircle2, AlertTriangle, X } from "lucide-react";

interface ExportReportModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentIncidentId?: string | null;
}

export default function ExportReportModal({
  isOpen,
  onClose,
  currentIncidentId,
}: ExportReportModalProps) {
  const [scope, setScope] = useState<"all" | "latest" | "incident">("all");
  const [meta, setMeta] = useState<ReportPreviewMeta | null>(null);
  const [loadingMeta, setLoadingMeta] = useState<boolean>(false);
  const [isDownloading, setIsDownloading] = useState<boolean>(false);
  const [downloadFormat, setDownloadFormat] = useState<"md" | "pdf" | null>(null);
  const [statusMessage, setStatusMessage] = useState<{
    type: "success" | "error";
    text: string;
  } | null>(null);

  // Default to single incident scope if currentIncidentId is selected and modal is opened from incident view
  useEffect(() => {
    if (isOpen) {
      if (currentIncidentId) {
        setScope("incident");
      } else {
        setScope("all");
      }
      setStatusMessage(null);
    }
  }, [isOpen, currentIncidentId]);

  // Fetch preview metadata whenever scope changes
  useEffect(() => {
    if (!isOpen) return;
    setLoadingMeta(true);
    setStatusMessage(null);

    const incId = scope === "incident" ? currentIncidentId || undefined : undefined;
    fetchReportPreviewMeta(scope, incId)
      .then((data) => {
        setMeta(data);
      })
      .catch((err) => {
        console.error("Failed to load report metadata:", err);
      })
      .finally(() => {
        setLoadingMeta(false);
      });
  }, [isOpen, scope, currentIncidentId]);

  if (!isOpen) return null;

  const handleDownload = async (format: "md" | "pdf") => {
    setIsDownloading(true);
    setDownloadFormat(format);
    setStatusMessage(null);

    const incId = scope === "incident" ? currentIncidentId || undefined : undefined;
    try {
      const res = await downloadReport(format, scope, incId);
      setStatusMessage({
        type: "success",
        text: `Downloaded ${res.filename} (${(res.sizeBytes / 1024).toFixed(1)} KB) successfully!`,
      });
    } catch (err: any) {
      setStatusMessage({
        type: "error",
        text: err?.message || "Failed to download report",
      });
    } finally {
      setIsDownloading(false);
      setDownloadFormat(null);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/85 flex items-center justify-center p-4">
      <div className="bg-[#141418] border-4 border-black p-6 max-w-xl w-full shadow-[8px_8px_0px_#00E5FF] select-none font-mono">
        {/* Modal Header */}
        <div className="flex items-center justify-between border-b-2 border-zinc-800 pb-3 mb-4">
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 bg-[#00E5FF] border border-black inline-block" />
            <div>
              <h3 className="text-sm font-black text-white uppercase tracking-wider">
                1-CLICK INCIDENT & AUDIT REPORT EXPORTER
              </h3>
              <p className="text-[10px] text-zinc-400 mt-0.5">
                Deterministic Compute Proof • Three-Agent Chain • PII Redacted • Runbooks Included
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 bg-zinc-800 hover:bg-zinc-700 text-white border-2 border-black active:translate-x-0.5 active:translate-y-0.5"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Scope Selector Chips */}
        <div className="mb-4">
          <label className="block text-zinc-400 uppercase font-black text-[11px] mb-2">
            SELECT EXPORT SCOPE
          </label>
          <div className="grid grid-cols-3 gap-2 text-xs">
            <button
              type="button"
              onClick={() => setScope("all")}
              className={`py-2 px-2.5 font-black uppercase border-2 border-black transition-all text-center ${
                scope === "all"
                  ? "bg-[#CCFF00] text-black shadow-[3px_3px_0px_#000]"
                  : "bg-[#09090B] text-zinc-400 hover:text-white"
              }`}
            >
              ALL INCIDENTS
            </button>
            <button
              type="button"
              onClick={() => setScope("latest")}
              className={`py-2 px-2.5 font-black uppercase border-2 border-black transition-all text-center ${
                scope === "latest"
                  ? "bg-[#00E5FF] text-black shadow-[3px_3px_0px_#000]"
                  : "bg-[#09090B] text-zinc-400 hover:text-white"
              }`}
            >
              LATEST UPLOAD
            </button>
            <button
              type="button"
              onClick={() => setScope("incident")}
              disabled={!currentIncidentId}
              title={!currentIncidentId ? "Select an incident in the dashboard first" : ""}
              className={`py-2 px-2.5 font-black uppercase border-2 border-black transition-all text-center disabled:opacity-40 disabled:cursor-not-allowed ${
                scope === "incident"
                  ? "bg-[#FFB800] text-black shadow-[3px_3px_0px_#000]"
                  : "bg-[#09090B] text-zinc-400 hover:text-white"
              }`}
            >
              CURRENT INCIDENT
            </button>
          </div>
        </div>

        {/* Live Preview Summary Box */}
        <div className="bg-[#09090B] border-2 border-zinc-700 p-3.5 mb-4 shadow-[3px_3px_0px_#000]">
          <div className="flex items-center justify-between border-b border-zinc-800 pb-2 mb-2.5">
            <span className="text-[10px] text-zinc-400 uppercase font-bold">
              REPORT AUDIT PREVIEW ({scope.toUpperCase()})
            </span>
            <span className="text-[10px] text-[#CCFF00] font-black">
              100% REAL PERSISTED DATA
            </span>
          </div>

          {loadingMeta ? (
            <div className="py-4 text-center text-zinc-500 text-xs">
              COMPILING LIVE METRIC TELEMETRY...
            </div>
          ) : meta ? (
            <div className="space-y-2 text-xs">
              <div className="p-2 bg-[#141418] border border-zinc-700 text-[#00E5FF] font-black text-center text-[11px]">
                {meta.criticalCount} CRITICAL INCIDENT(S) &bull; {meta.suppressedCount} SUPPRESSED CLUSTERS &bull; ACTIONABLE RUNBOOKS
              </div>

              <div className="grid grid-cols-2 gap-2 text-[10px] text-zinc-300 pt-1">
                <div>
                  Scope: <strong className="text-white">{scope.toUpperCase()}</strong>
                </div>
                <div>
                  Target ID: <strong className="text-white">{meta.latestIncidentId || "ALL"}</strong>
                </div>
                <div>
                  PII Sanitization: <strong className="text-[#CCFF00]">STRICTLY ENFORCED</strong>
                </div>
                <div>
                  Tamper-Evident: <strong className="text-[#CCFF00]">TRACE ID LINKED</strong>
                </div>
              </div>
            </div>
          ) : (
            <div className="py-2 text-center text-zinc-500 text-xs">
              Preview metadata unavailable. Export will compile live from database.
            </div>
          )}
        </div>

        {/* Status / Error Message */}
        {statusMessage && (
          <div
            className={`p-2.5 mb-4 border-2 font-mono text-xs flex items-center gap-2 ${
              statusMessage.type === "success"
                ? "bg-[#CCFF00]/10 border-[#CCFF00] text-[#CCFF00]"
                : "bg-[#FF2E4C]/10 border-[#FF2E4C] text-[#FF2E4C]"
            }`}
          >
            {statusMessage.type === "success" ? (
              <CheckCircle2 className="w-4 h-4 shrink-0" />
            ) : (
              <AlertTriangle className="w-4 h-4 shrink-0" />
            )}
            <span className="text-[11px] font-bold">{statusMessage.text}</span>
          </div>
        )}

        {/* Primary Download Buttons */}
        <div className="grid grid-cols-2 gap-3 pt-1">
          <button
            type="button"
            onClick={() => handleDownload("md")}
            disabled={isDownloading}
            className="py-3 px-4 bg-[#CCFF00] hover:bg-[#B3E600] text-black font-black uppercase text-xs border-2 border-black shadow-[4px_4px_0px_#000] active:translate-x-0.5 active:translate-y-0.5 disabled:opacity-50 flex items-center justify-center gap-2 cursor-pointer"
          >
            <Download className="w-4 h-4" />
            {isDownloading && downloadFormat === "md" ? "COMPILING..." : "↓ DOWNLOAD MARKDOWN (.MD)"}
          </button>

          <button
            type="button"
            onClick={() => handleDownload("pdf")}
            disabled={isDownloading}
            className="py-3 px-4 bg-[#00E5FF] hover:bg-[#33EAFF] text-black font-black uppercase text-xs border-2 border-black shadow-[4px_4px_0px_#000] active:translate-x-0.5 active:translate-y-0.5 disabled:opacity-50 flex items-center justify-center gap-2 cursor-pointer"
          >
            <FileText className="w-4 h-4" />
            {isDownloading && downloadFormat === "pdf" ? "COMPILING..." : "↓ DOWNLOAD PDF REPORT (.PDF)"}
          </button>
        </div>

        {/* Footer Note */}
        <div className="mt-3 text-center text-[10px] text-zinc-500">
          Pure-Python Windows-safe PDF compilation (ReportLab). Zero native DLL dependencies.
        </div>
      </div>
    </div>
  );
}
