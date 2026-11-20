"use client";

import React from "react";
import { CompressionSummary } from "../lib/api";
import { ArrowRight, Layers, Filter, CheckCircle2, AlertOctagon } from "lucide-react";

interface CompressionTickerProps {
  summary: CompressionSummary | null;
}

export const AlertCompressionTicker: React.FC<CompressionTickerProps> = ({ summary }) => {
  const raw = summary?.totalRawAlerts || 470;
  const compressed = summary?.totalCompressedClusters || 44;
  const ratio = summary?.overallCompressionPct || 90.6;
  const activeInc = summary?.activeIncidentsCount || 1;
  const suppressed = summary?.suppressedNoiseCount || 3;

  return (
    <section className="bg-charcoal border-b-2 border-borderStructural p-4">
      <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-4">
        {/* Ticker Header */}
        <div className="flex items-center gap-3">
          <div className="bg-obsidian border-2 border-borderStructural p-2">
            <Layers className="w-5 h-5 text-signal-cyan" />
          </div>
          <div>
            <span className="text-[10px] font-mono uppercase tracking-widest text-mutedLabel block">
              PIPELINE FUNNEL TELEMETRY
            </span>
            <span className="text-sm font-black uppercase text-primaryText font-sans">
              DETERMINISTIC COMPRESSION STACK
            </span>
          </div>
        </div>

        {/* Compression Cascade Blocks */}
        <div className="flex-1 flex flex-wrap items-center justify-start lg:justify-center gap-2 md:gap-3">
          {/* Step 1: Raw Ingest */}
          <div className="bg-obsidian border-2 border-borderStructural px-3 py-2 flex items-center gap-3 shadow-neo-sm">
            <span className="text-xs font-mono text-mutedLabel uppercase">RAW ALERTS:</span>
            <span className="text-base font-mono font-black text-primaryText">{raw}</span>
          </div>

          <ArrowRight className="w-4 h-4 text-borderStructural hidden sm:block" />

          {/* Step 2: Deduplication & Flap Filter */}
          <div className="bg-obsidian border-2 border-signal-cyan px-3 py-2 flex items-center gap-3 shadow-neo-sm">
            <Filter className="w-4 h-4 text-signal-cyan" />
            <span className="text-xs font-mono text-mutedLabel uppercase">DEDUP CLUSTERS:</span>
            <span className="text-base font-mono font-black text-signal-cyan">{compressed}</span>
          </div>

          <ArrowRight className="w-4 h-4 text-borderStructural hidden sm:block" />

          {/* Step 3: Verified Incidents */}
          <div className="bg-obsidian border-2 border-signal-crimson px-3 py-2 flex items-center gap-3 shadow-neo-sm">
            <AlertOctagon className="w-4 h-4 text-signal-crimson" />
            <span className="text-xs font-mono text-mutedLabel uppercase">VERIFIED INCIDENTS:</span>
            <span className="text-base font-mono font-black text-signal-crimson">{activeInc}</span>
          </div>

          <ArrowRight className="w-4 h-4 text-borderStructural hidden sm:block" />

          {/* Step 4: Suppressed Noise */}
          <div className="bg-obsidian border-2 border-signal-lime px-3 py-2 flex items-center gap-3 shadow-neo-sm">
            <CheckCircle2 className="w-4 h-4 text-signal-lime" />
            <span className="text-xs font-mono text-mutedLabel uppercase">NOISE SUPPRESSED:</span>
            <span className="text-base font-mono font-black text-signal-lime">{suppressed}</span>
          </div>
        </div>

        {/* Highlight Compression Ratio Badge */}
        <div className="bg-signal-lime text-obsidian border-2 border-borderActive px-4 py-2 flex items-center justify-between lg:justify-center gap-3 shadow-neo-lime">
          <span className="text-xs font-mono font-black uppercase">NOISE REDUCTION:</span>
          <span className="text-xl font-mono font-black">{ratio.toFixed(1)}%</span>
        </div>
      </div>
    </section>
  );
};
