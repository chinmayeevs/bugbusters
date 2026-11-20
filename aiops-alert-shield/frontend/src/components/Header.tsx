"use client";

import React, { useState, useEffect } from "react";
import { ShieldAlert, Cpu, Activity, Clock, Sliders, PlusCircle, Download } from "lucide-react";

interface HeaderProps {
  activeCount: number;
  onRefresh: () => void;
  isRefreshing: boolean;
  onOpenInjectDrawer?: () => void;
  onOpenIntelligenceModal?: () => void;
  onOpenBenchmarkModal?: () => void;
  onOpenExportModal?: () => void;
  intelligenceMode?: string;
  llmProvider?: string;
  llmModel?: string;
  totalTokensUsed?: number;
}

export const Header: React.FC<HeaderProps> = ({
  activeCount,
  onRefresh,
  isRefreshing,
  onOpenInjectDrawer,
  onOpenIntelligenceModal,
  onOpenBenchmarkModal,
  onOpenExportModal,
  intelligenceMode = "MOCK_LLM",
  llmProvider = "gemini",
  llmModel = "gemini-3.5-flash-lite",
  totalTokensUsed = 0,
}) => {
  const [time, setTime] = useState<string>("");

  useEffect(() => {
    const update = () => {
      setTime(new Date().toISOString().replace("T", " ").substring(0, 19) + " UTC");
    };
    update();
    const timer = setInterval(update, 1000);
    return () => clearInterval(timer);
  }, []);

  const isLive = intelligenceMode === "LIVE_LLM";

  return (
    <header className="bg-charcoal border-b-2 border-borderStructural px-6 py-4 flex flex-wrap items-center justify-between gap-4 select-none">
      {/* Brand & System Title */}
      <div className="flex items-center gap-4">
        <div className="bg-signal-crimson p-2.5 border-2 border-borderActive shadow-neo flex items-center justify-center">
          <ShieldAlert className="w-6 h-6 text-obsidian" strokeWidth={2.5} />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-black uppercase tracking-wider text-primaryText font-sans">
              AIOPS // ALERT SHIELD
            </h1>
            <span className="bg-obsidian border border-signal-lime text-signal-lime text-[11px] font-mono px-2 py-0.5 font-bold">
              v1.0.0-PROD
            </span>
          </div>
          <p className="text-xs font-mono text-mutedLabel mt-0.5">
            ORCHESTRATED SELF-EVOLVING HYBRID VERIFICATION ENGINE
          </p>
        </div>
      </div>

      {/* Telemetry Pills & Action Buttons */}
      <div className="flex flex-wrap items-center gap-3 font-mono">
        {/* AI Mode Indicator Pill */}
        <button
          onClick={onOpenIntelligenceModal}
          title="Click to configure LLM provider & API keys"
          className={`border-2 px-3 py-1.5 flex items-center gap-2 shadow-neo-sm transition-all hover:scale-105 ${
            isLive
              ? "bg-[#00E5FF]/10 border-[#00E5FF] text-[#00E5FF]"
              : "bg-[#CCFF00]/10 border-[#CCFF00] text-[#CCFF00]"
          }`}
        >
          <span
            className={`w-2.5 h-2.5 border border-black ${
              isLive ? "bg-[#00E5FF]" : "bg-[#CCFF00]"
            }`}
          />
          <span className="text-[10px] uppercase text-zinc-400">ENGINE:</span>
          <span className="text-xs font-black uppercase">
            {isLive ? `LIVE [${llmProvider}]` : "MOCK DETERMINISTIC"}
          </span>
          <Sliders className="w-3.5 h-3.5 ml-1 opacity-70" />
        </button>

        {/* Live Token Usage Badge */}
        {totalTokensUsed > 0 && (
          <div className="hidden lg:flex bg-obsidian border-2 border-zinc-700 px-2.5 py-1.5 items-center gap-1.5 text-xs text-[#CCFF00] shadow-neo-sm font-mono">
            <span className="text-zinc-400 text-[10px] uppercase">TOKENS:</span>
            <span className="font-black text-white">{totalTokensUsed.toLocaleString()}</span>
          </div>
        )}

        {/* Fail-open guarantee status */}
        <div className="bg-obsidian border-2 border-borderStructural px-3 py-1.5 flex items-center gap-2 shadow-neo-sm">
          <Activity className="w-4 h-4 text-signal-lime" />
          <span className="text-xs uppercase text-mutedLabel">FAIL-OPEN:</span>
          <span className="text-xs font-bold text-signal-lime">ENFORCED</span>
        </div>

        {/* Active Incidents Counter */}
        <div className="bg-obsidian border-2 border-signal-crimson px-3 py-1.5 flex items-center gap-2 shadow-neo-sm">
          <span className="w-2.5 h-2.5 bg-signal-crimson" />
          <span className="text-xs uppercase text-mutedLabel">ACTIVE P0/P1:</span>
          <span className="text-xs font-black text-signal-crimson">{activeCount}</span>
        </div>

        {/* Live Clock */}
        <div className="hidden xl:flex bg-obsidian border-2 border-borderStructural px-3 py-1.5 items-center gap-2">
          <Clock className="w-3.5 h-3.5 text-mutedLabel" />
          <span className="text-xs text-primaryText">{time || "SYNCING..."}</span>
        </div>

        {/* [ EXPORT REPORT ] Modal Trigger */}
        <button
          onClick={onOpenExportModal}
          className="px-3.5 py-1.5 bg-[#141418] hover:bg-[#00E5FF]/10 text-[#00E5FF] border-2 border-[#00E5FF] font-black text-xs uppercase shadow-[3px_3px_0px_#00E5FF] flex items-center gap-1.5 active:translate-x-0.5 active:translate-y-0.5 cursor-pointer"
          title="Export incident dossier and audit report (Markdown / PDF)"
        >
          <Download className="w-4 h-4 stroke-[2.5]" />
          EXPORT REPORT
        </button>

        {/* [ BENCHMARK SCORECARD ] Modal Trigger */}
        <button
          onClick={onOpenBenchmarkModal}
          className="px-3.5 py-1.5 bg-[#00FF66] hover:bg-[#33FF85] text-black border-2 border-black font-black text-xs uppercase shadow-[3px_3px_0px_#000] flex items-center gap-1.5 active:translate-x-0.5 active:translate-y-0.5"
        >
          <Activity className="w-4 h-4 stroke-[2.5]" />
          BENCHMARK SCORECARD
        </button>

        {/* [ + INJECT CUSTOM DATA ] Drawer Trigger */}
        <button
          onClick={onOpenInjectDrawer}
          className="px-3.5 py-1.5 bg-[#FFB800] hover:bg-[#FFC933] text-black border-2 border-black font-black text-xs uppercase shadow-[3px_3px_0px_#000] flex items-center gap-1.5 active:translate-x-0.5 active:translate-y-0.5"
        >
          <PlusCircle className="w-4 h-4 stroke-[2.5]" />
          + INJECT CUSTOM DATA
        </button>

        {/* Refresh Button */}
        <button
          onClick={onRefresh}
          disabled={isRefreshing}
          className="neo-btn bg-signal-lime text-obsidian border-2 border-borderActive px-4 py-1.5 text-xs font-black shadow-neo-lime hover:bg-white disabled:opacity-50"
        >
          {isRefreshing ? "SYNCING..." : "POLL TELEMETRY"}
        </button>
      </div>
    </header>
  );
};
