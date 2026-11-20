"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import { Header } from "../components/Header";
import { AlertCompressionTicker } from "../components/AlertCompressionTicker";
import { SimulationControls } from "../components/SimulationControls";
import { ServiceHealthGrid } from "../components/ServiceHealthGrid";
import { IncidentList } from "../components/IncidentList";
import { IncidentDetail } from "../components/IncidentDetail";
import CustomTelemetryDrawer from "../components/CustomTelemetryDrawer";
import IntelligenceConfigModal from "../components/IntelligenceConfigModal";
import BenchmarkScorecardModal from "../components/BenchmarkScorecardModal";
import ExportReportModal from "../components/ExportReportModal";
import LiveReplayStrip from "../components/LiveReplayStrip";
import SuppressedAuditView from "../components/SuppressedAuditView";
import SeaCasebookExplorer from "../components/SeaCasebookExplorer";
import {
  IncidentSummary,
  FullIncident,
  CompressionSummary,
  ServiceHealth,
  IntelligenceStatus,
  getIncidents,
  getIncidentById,
  getCompressionSummary,
  getServiceHealth,
  getIntelligenceStatus,
} from "../lib/api";

export default function Home() {
  const [incidents, setIncidents] = useState<IncidentSummary[]>([]);
  const [selectedIncident, setSelectedIncident] = useState<FullIncident | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [compression, setCompression] = useState<CompressionSummary | null>(null);
  const [health, setHealth] = useState<ServiceHealth[]>([]);
  const [intelStatus, setIntelStatus] = useState<IntelligenceStatus | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Batch filtering and latest upload tracking
  const [batchFilter, setBatchFilter] = useState<"ALL" | "LATEST">("ALL");
  const [latestIncidentId, setLatestIncidentId] = useState<string | null>(null);

  // Workspace Navigation Tabs
  const [activeTab, setActiveTab] = useState<"incidents" | "suppressed" | "casebook">("incidents");

  // Modals & Drawers
  const [isDrawerOpen, setIsDrawerOpen] = useState<boolean>(false);
  const [isConfigModalOpen, setIsConfigModalOpen] = useState<boolean>(false);
  const [isBenchmarkOpen, setIsBenchmarkOpen] = useState<boolean>(false);
  const [isExportModalOpen, setIsExportModalOpen] = useState<boolean>(false);

  // References to preserve user selection across background poll cycles
  const selectedIdRef = useRef<string | null>(null);
  const selectedIncidentRef = useRef<FullIncident | null>(null);

  useEffect(() => {
    selectedIdRef.current = selectedId;
  }, [selectedId]);

  useEffect(() => {
    selectedIncidentRef.current = selectedIncident;
  }, [selectedIncident]);

  const loadData = useCallback(async (isManualRefresh = false, overrideId?: string) => {
    if (isManualRefresh) setIsRefreshing(true);
    try {
      const [incList, compSumm, sHealth, intel] = await Promise.all([
        getIncidents(),
        getCompressionSummary(),
        getServiceHealth(),
        getIntelligenceStatus().catch(() => null),
      ]);

      setIncidents(incList);
      setCompression(compSumm);
      setHealth(sHealth);
      if (intel) setIntelStatus(intel);

      // Preserve currently selected incident unless manual refresh or explicit override
      const targetId = overrideId || selectedIdRef.current || (incList.length > 0 ? incList[0].incidentId : null);
      if (targetId) {
        if (isManualRefresh || overrideId || !selectedIncidentRef.current || selectedIncidentRef.current.incidentId !== targetId) {
          setSelectedId(targetId);
          const detailed = await getIncidentById(targetId);
          setSelectedIncident(detailed);
        }
      }
      setError(null);
    } catch (err: any) {
      console.error("Failed to load dashboard data:", err);
      setError(err.message || "Failed to reach GraphQL API");
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadData();
    // Non-intrusive background telemetry polling every 8 seconds
    const interval = setInterval(() => {
      loadData(false);
    }, 8000);
    return () => clearInterval(interval);
  }, [loadData]);

  const handleSelectIncident = async (id: string) => {
    setSelectedId(id);
    try {
      const detailed = await getIncidentById(id);
      setSelectedIncident(detailed);
    } catch (err) {
      console.error("Failed to fetch detailed incident:", err);
    }
  };

  const displayedIncidents =
    batchFilter === "LATEST" && latestIncidentId
      ? incidents.filter((i) => i.incidentId === latestIncidentId)
      : incidents;

  const activeP0Count = incidents.filter(
    (i) => i.severity === "CRITICAL" || i.status === "FAIL_OPEN_CRITICAL"
  ).length;

  return (
    <div className="min-h-screen flex flex-col bg-obsidian text-primaryText">
      {/* 1. Header with Live Intelligence API Pill & Action Drawers */}
      <Header
        activeCount={activeP0Count}
        onRefresh={() => loadData(true)}
        isRefreshing={isRefreshing}
        onOpenInjectDrawer={() => setIsDrawerOpen(true)}
        onOpenIntelligenceModal={() => setIsConfigModalOpen(true)}
        onOpenBenchmarkModal={() => setIsBenchmarkOpen(true)}
        onOpenExportModal={() => setIsExportModalOpen(true)}
        intelligenceMode={intelStatus?.mode}
        llmProvider={intelStatus?.provider}
        llmModel={intelStatus?.model}
        totalTokensUsed={intelStatus?.totalTokensUsed}
      />

      {/* 2. Live 400-Alert Telemetry Ingestion Strip */}
      <LiveReplayStrip onIncidentTriggered={() => loadData(true)} />

      {/* 3. Primary Workspace Navigation Tabs & Batch Filter */}
      <nav className="bg-[#141418] border-b-2 border-[#27272A] px-6 py-2.5 flex flex-wrap items-center justify-between gap-3 font-mono text-xs select-none">
        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={() => setActiveTab("incidents")}
            className={`px-4 py-2 font-black uppercase tracking-wider border-2 transition-all ${
              activeTab === "incidents"
                ? "bg-[#00FF66] text-black border-black shadow-[3px_3px_0px_#000]"
                : "bg-[#1E1E24] text-[#A1A1AA] border-[#27272A] hover:text-white hover:border-[#3F3F46]"
            }`}
          >
            [ 01 // VERIFIED INCIDENTS ]
          </button>
          <button
            onClick={() => setActiveTab("suppressed")}
            className={`px-4 py-2 font-black uppercase tracking-wider border-2 transition-all ${
              activeTab === "suppressed"
                ? "bg-[#FFCC00] text-black border-black shadow-[3px_3px_0px_#000]"
                : "bg-[#1E1E24] text-[#A1A1AA] border-[#27272A] hover:text-white hover:border-[#3F3F46]"
            }`}
          >
            [ 02 // SUPPRESSED & AUDIT LOG ]
          </button>
          <button
            onClick={() => setActiveTab("casebook")}
            className={`px-4 py-2 font-black uppercase tracking-wider border-2 transition-all ${
              activeTab === "casebook"
                ? "bg-[#00E5FF] text-black border-black shadow-[3px_3px_0px_#000]"
                : "bg-[#1E1E24] text-[#A1A1AA] border-[#27272A] hover:text-white hover:border-[#3F3F46]"
            }`}
          >
            [ 03 // SEA CASEBOOK MEMORY ]
          </button>
        </div>

        {/* Batch Filter & Feed Reset Controls */}
        {activeTab === "incidents" && (
          <div className="flex items-center gap-2">
            <button
              onClick={() => setBatchFilter("ALL")}
              className={`px-2.5 py-1 text-[10px] font-black uppercase border-2 border-black transition-all ${
                batchFilter === "ALL"
                  ? "bg-[#CCFF00] text-black shadow-[2px_2px_0px_#000]"
                  : "bg-[#1E1E24] text-zinc-400 hover:text-white"
              }`}
            >
              ALL BATCHES ({incidents.length})
            </button>
            <button
              onClick={() => latestIncidentId && setBatchFilter("LATEST")}
              disabled={!latestIncidentId}
              className={`px-2.5 py-1 text-[10px] font-black uppercase border-2 border-black transition-all disabled:opacity-40 ${
                batchFilter === "LATEST"
                  ? "bg-[#00E5FF] text-black shadow-[2px_2px_0px_#000]"
                  : "bg-[#1E1E24] text-zinc-400 hover:text-white"
              }`}
            >
              LATEST UPLOAD {latestIncidentId ? `[${latestIncidentId}]` : ""}
            </button>
            <button
              onClick={() => {
                setBatchFilter("ALL");
                setLatestIncidentId(null);
                loadData(true);
              }}
              className="px-2.5 py-1 text-[10px] font-black uppercase border-2 border-black bg-zinc-800 text-zinc-300 hover:bg-zinc-700 active:translate-x-0.5 active:translate-y-0.5"
              title="Reset feed and refetch all data"
            >
              [ CLEAR / RESET FEED ]
            </button>
          </div>
        )}
      </nav>

      {/* Tab 1: Operational Incident Console */}
      {activeTab === "incidents" && (
        <>
          {/* Live Alert Compression Ticker */}
          <AlertCompressionTicker summary={compression} />

          {/* Scenario Simulation Controls */}
          <SimulationControls onSimulationComplete={() => loadData(true)} />

          {/* Topological Fleet Health */}
          <ServiceHealthGrid services={health} />

          {/* API Error Notification */}
          {error && (
            <div className="bg-signal-crimson text-obsidian px-4 py-2 font-mono text-xs font-bold flex items-center justify-between">
              <span>API CONNECTION NOTICE: {error}. (Ensure backend FastAPI is running on port 8000)</span>
              <button
                onClick={() => loadData(true)}
                className="underline uppercase font-black"
              >
                Retry Now
              </button>
            </div>
          )}

          {/* Main Split View: Incident Feed & Deep Dossier */}
          <main className="flex-1 flex flex-col lg:flex-row overflow-hidden min-h-[600px]">
            {/* Left: Incident Feed */}
            <section className="w-full lg:w-[420px] lg:max-w-[440px] flex-shrink-0 h-full border-r-2 border-borderStructural">
              <IncidentList
                incidents={displayedIncidents}
                selectedId={selectedId}
                onSelect={handleSelectIncident}
              />
            </section>

            {/* Right: Expandable Proof Bundle & Reasoning Dossier */}
            <section className="flex-1 h-full overflow-hidden bg-obsidian">
              {selectedIncident ? (
                <IncidentDetail
                  incident={selectedIncident}
                  onUpdate={() => loadData(true)}
                />
              ) : (
                <div className="h-full flex items-center justify-center p-12 text-center text-mutedLabel font-mono text-xs">
                  {loading ? "INITIALIZING EVIDENCE PACKETS..." : "NO INCIDENTS SELECTED."}
                </div>
              )}
            </section>
          </main>
        </>
      )}

      {/* Tab 2: No Silent Suppression Audit Log */}
      {activeTab === "suppressed" && (
        <div className="flex-1 p-6 overflow-y-auto">
          <SuppressedAuditView
            onSelectIncident={async (incId) => {
              setActiveTab("incidents");
              setBatchFilter("ALL");
              await loadData(true, incId);
              handleSelectIncident(incId);
            }}
          />
        </div>
      )}

      {/* Tab 3: Self-Evolving Agent (SEA) Casebook Memory */}
      {activeTab === "casebook" && (
        <div className="flex-1 p-6 overflow-y-auto">
          <SeaCasebookExplorer />
        </div>
      )}

      {/* Custom Telemetry Ingestion Slide-Over Drawer */}
      <CustomTelemetryDrawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        onSuccess={(newId) => {
          setLatestIncidentId(newId);
          setBatchFilter("LATEST");
          setSelectedId(newId);
          loadData(true, newId);
        }}
      />

      {/* Intelligence Config Modal */}
      <IntelligenceConfigModal
        isOpen={isConfigModalOpen}
        onClose={() => setIsConfigModalOpen(false)}
        onConfigUpdated={(st) => {
          setIntelStatus(st);
          loadData(true);
        }}
      />

      {/* Benchmark Scorecard Modal */}
      <BenchmarkScorecardModal
        isOpen={isBenchmarkOpen}
        onClose={() => setIsBenchmarkOpen(false)}
      />

      {/* 1-Click Incident & Audit Report Export Modal */}
      <ExportReportModal
        isOpen={isExportModalOpen}
        onClose={() => setIsExportModalOpen(false)}
        currentIncidentId={selectedId}
      />
    </div>
  );
}
