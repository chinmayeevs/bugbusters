"use client";

import React from "react";
import { RiskFeatureItem } from "@/lib/api";

interface RiskMeterGridProps {
  score?: number;
  severity?: string;
  failOpen?: boolean;
  failOpenReason?: string | null;
  breakdown?: RiskFeatureItem[];
}

export default function RiskMeterGrid({
  score = 0.88,
  severity = "CRITICAL",
  failOpen = true,
  failOpenReason,
  breakdown = [],
}: RiskMeterGridProps) {
  const defaultBreakdown: RiskFeatureItem[] = [
    {
      name: "Blast Radius Scope",
      score: 0.9,
      weight: 0.35,
      contribution: 0.315,
      description: "Compromised ingress & data tier cascade",
    },
    {
      name: "Anomaly Departure",
      score: 0.95,
      weight: 0.3,
      contribution: 0.285,
      description: "Peak MAD z-score departure across 3 windows",
    },
    {
      name: "Customer Ingress Impact",
      score: 1.0,
      weight: 0.15,
      contribution: 0.15,
      description: "api-gateway 504 gateway timeout elevation",
    },
    {
      name: "Critical Tier Breach",
      score: 1.0,
      weight: 0.1,
      contribution: 0.1,
      description: "Postgres orders_v2 row-level lock contention",
    },
    {
      name: "Flapping & Noise Filter",
      score: 0.9,
      weight: 0.1,
      contribution: 0.09,
      description: "Non-flapping sustained failure progression",
    },
  ];

  const items = breakdown && breakdown.length > 0 ? breakdown : defaultBreakdown;

  const getScoreColor = (val: number) => {
    if (val >= 0.7) return "bg-[#FF2E4C] text-white";
    if (val >= 0.45) return "bg-[#FFB800] text-black";
    if (val >= 0.2) return "bg-[#00E5FF] text-black";
    return "bg-zinc-600 text-white";
  };

  return (
    <div className="bg-[#141418] border-2 border-black p-4 shadow-[4px_4px_0px_#FFB800]">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b-2 border-zinc-800 pb-2 mb-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 bg-[#FF2E4C] border border-black" />
            <h4 className="font-mono text-xs font-black uppercase text-white tracking-widest">
              DETERMINISTIC RISK & FAIL-OPEN ENGINE
            </h4>
          </div>
          <p className="font-mono text-[10px] text-zinc-400 mt-0.5">
            Mathematical risk score based on blast radius, statistical departure, and topology
          </p>
        </div>
        <div className="flex items-center gap-2 font-mono">
          <span className={`px-2 py-1 font-black text-xs uppercase border-2 border-black ${getScoreColor(score)}`}>
            {severity} • {(score * 100).toFixed(0)}%
          </span>
        </div>
      </div>

      {/* Main Score Progress Bar */}
      <div className="mb-4">
        <div className="flex justify-between font-mono text-[10px] text-zinc-400 mb-1">
          <span>COMPOSITE RISK SCORE</span>
          <span>{score.toFixed(3)} / 1.000</span>
        </div>
        <div className="h-4 bg-[#09090B] border-2 border-black relative overflow-hidden">
          <div
            className={`h-full transition-all duration-500 ${
              score >= 0.7 ? "bg-[#FF2E4C]" : score >= 0.45 ? "bg-[#FFB800]" : "bg-[#00E5FF]"
            }`}
            style={{ width: `${Math.min(100, Math.max(0, score * 100))}%` }}
          />
          {/* Threshold marker at 0.70 */}
          <div
            className="absolute top-0 bottom-0 w-1 bg-white"
            style={{ left: "70%" }}
            title="Fail-Open Critical Threshold (0.70)"
          />
        </div>
        <div className="flex justify-between font-mono text-[9px] text-zinc-500 mt-1">
          <span>0.00 BENIGN</span>
          <span>0.45 HIGH</span>
          <span className="text-red-400 font-bold">▲ 0.70 FAIL-OPEN CRITICAL</span>
          <span>1.00 MAX</span>
        </div>
      </div>

      {/* Fail-Open Guarantee Callout */}
      {failOpen && (
        <div className="mb-4 p-2.5 bg-[#FF2E4C]/10 border-2 border-[#FF2E4C] font-mono">
          <div className="flex items-center gap-2 text-[#FF2E4C] font-black text-xs uppercase">
            <span className="w-2 h-2 bg-[#FF2E4C]" />
            FAIL-OPEN GUARANTEE ACTIVE
          </div>
          <p className="text-[10px] text-zinc-300 mt-1">
            {failOpenReason ||
              "Deterministic critical threshold breached with customer path compromise. Incident publication guaranteed even if AI reasoning layer is unreachable."}
          </p>
        </div>
      )}

      {/* 5-Feature Breakdown Meters */}
      <div className="space-y-2.5">
        {items.map((item, idx) => {
          const pct = Math.round(item.score * 100);
          return (
            <div key={idx} className="bg-[#09090B] border border-zinc-800 p-2 font-mono">
              <div className="flex justify-between items-center text-xs mb-1">
                <span className="font-bold text-white text-[11px]">{item.name}</span>
                <span className="text-zinc-400 text-[10px]">
                  Score: <strong className="text-white">{item.score.toFixed(2)}</strong> | Weight:{" "}
                  {item.weight * 100}% | +{(item.contribution * 100).toFixed(1)}%
                </span>
              </div>
              <div className="h-2 bg-zinc-900 border border-zinc-700">
                <div
                  className="h-full bg-[#FFB800]"
                  style={{ width: `${Math.min(100, Math.max(0, pct))}%` }}
                />
              </div>
              <div className="text-[9px] text-zinc-500 mt-1 truncate">{item.description}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
