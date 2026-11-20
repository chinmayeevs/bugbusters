"use client";

import React, { useState } from "react";
import { IncidentSummary } from "../lib/api";
import { AlertCircle, CheckCircle, ShieldAlert, Compass, Eye } from "lucide-react";

interface IncidentListProps {
  incidents: IncidentSummary[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

export const IncidentList: React.FC<IncidentListProps> = ({ incidents, selectedId, onSelect }) => {
  const [filter, setFilter] = useState<string>("ALL");

  const filtered = incidents.filter((inc) => {
    if (filter === "CRITICAL") return inc.severity === "CRITICAL";
    if (filter === "DIVERGENCE") return inc.contextDivergenceFlag;
    if (filter === "SUPPRESSED") return inc.status === "SUPPRESSED_NOISE";
    if (filter === "ACKNOWLEDGED") return inc.status === "ACKNOWLEDGED";
    return true;
  });

  return (
    <div className="bg-charcoal border-r-2 border-borderStructural h-full flex flex-col">
      {/* Filter Tabs */}
      <div className="p-3 border-b-2 border-borderStructural flex flex-wrap gap-1.5 bg-obsidian">
        {["ALL", "CRITICAL", "DIVERGENCE", "SUPPRESSED", "ACKNOWLEDGED"].map((tab) => (
          <button
            key={tab}
            onClick={() => setFilter(tab)}
            className={`neo-btn text-[10px] font-mono font-bold px-2.5 py-1 border-2 ${
              filter === tab
                ? "bg-signal-lime text-obsidian border-borderActive shadow-neo-sm"
                : "bg-charcoal text-mutedLabel border-borderStructural hover:text-primaryText"
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Incident Cards Feed */}
      <div className="flex-1 overflow-y-auto divide-y-2 divide-borderStructural p-2 space-y-2">
        {filtered.length === 0 ? (
          <div className="p-8 text-center text-mutedLabel font-mono text-xs">
            NO INCIDENTS MATCHING FILTER.
          </div>
        ) : (
          filtered.map((inc) => {
            const isSelected = inc.incidentId === selectedId;
            const isCritical = inc.severity === "CRITICAL" || inc.status === "FAIL_OPEN_CRITICAL";
            const isDivergence = inc.contextDivergenceFlag;
            const isSuppressed = inc.status === "SUPPRESSED_NOISE";

            let borderClass = "border-borderStructural";
            let shadowClass = "shadow-neo-sm";
            let badgeBg = "bg-charcoal text-primaryText";

            if (inc.status === "FAIL_OPEN_CRITICAL") {
              borderClass = "border-signal-crimson";
              shadowClass = "shadow-neo-crimson";
              badgeBg = "bg-signal-crimson text-obsidian font-black";
            } else if (isDivergence) {
              borderClass = "border-signal-amber";
              shadowClass = "shadow-neo-amber";
              badgeBg = "bg-signal-amber text-obsidian font-bold";
            } else if (isCritical) {
              borderClass = "border-signal-crimson";
              shadowClass = "shadow-neo-crimson";
              badgeBg = "bg-signal-crimson text-obsidian font-bold";
            } else if (isSuppressed) {
              borderClass = "border-borderStructural opacity-80";
              badgeBg = "bg-obsidian border border-signal-lime text-signal-lime";
            }

            return (
              <div
                key={inc.incidentId}
                onClick={() => onSelect(inc.incidentId)}
                className={`p-3 cursor-pointer transition-all border-2 ${borderClass} ${
                  isSelected ? "bg-elevated ring-2 ring-borderActive " + shadowClass : "bg-obsidian hover:bg-elevated"
                }`}
              >
                {/* Header row: ID, Badge, Timestamp */}
                <div className="flex items-center justify-between gap-2 mb-1.5">
                  <span className="font-mono text-xs font-black text-signal-cyan">
                    {inc.incidentId}
                  </span>
                  <span className={`text-[10px] font-mono uppercase px-2 py-0.5 ${badgeBg}`}>
                    {inc.status}
                  </span>
                </div>

                {/* Title */}
                <h4 className="text-xs font-black uppercase text-primaryText line-clamp-2 leading-snug">
                  {inc.title}
                </h4>

                {/* Escalation Traceability Pill */}
                {inc.escalatedFromEventId && (
                  <div className="mt-1.5 bg-[#00E5FF]/10 border border-[#00E5FF] p-1 flex items-center gap-1.5">
                    <span className="h-1.5 w-1.5 bg-[#00E5FF]" />
                    <span className="text-[9px] font-mono text-[#00E5FF] font-black uppercase tracking-wider">
                      ESCALATED FROM: {inc.escalatedFromEventId}
                    </span>
                  </div>
                )}

                {/* SEA Divergence Callout Badge */}
                {isDivergence && (
                  <div className="mt-2 bg-charcoal border border-signal-amber p-1.5 flex items-center gap-1.5">
                    <Compass className="w-3.5 h-3.5 text-signal-amber flex-shrink-0" />
                    <span className="text-[10px] font-mono text-signal-amber font-bold uppercase">
                      CONTEXT DIVERGENCE DETECTED // OVERRIDE
                    </span>
                  </div>
                )}

                {/* Footer metrics: Root cause, compression, confidence */}
                <div className="mt-2.5 pt-2 border-t border-borderStructural flex items-center justify-between text-[10px] font-mono text-mutedLabel">
                  <span>ROOT: <strong className="text-primaryText">{inc.rootCauseService}</strong></span>
                  <span>CONF: <strong className="text-signal-lime font-mono">{(inc.confidenceScore * 100).toFixed(0)}%</strong></span>
                  <span>COMPR: <strong className="text-signal-cyan font-mono">{(inc.evidencePacket.compressionRatio * 100).toFixed(0)}%</strong></span>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
