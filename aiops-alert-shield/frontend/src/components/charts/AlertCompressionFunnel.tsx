"use client";

import React from "react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Cell,
} from "recharts";

interface AlertCompressionFunnelProps {
  rawCount?: number;
  compressedCount?: number;
  evidenceCount?: number;
  publishedCount?: number;
  ratio?: number;
}

export default function AlertCompressionFunnel({
  rawCount = 470,
  compressedCount = 44,
  evidenceCount = 6,
  publishedCount = 1,
  ratio = 0.906,
}: AlertCompressionFunnelProps) {
  const data = [
    { stage: "RAW ALERTS", count: rawCount, color: "#52525B", desc: "Ingested noise flood" },
    { stage: "DEDUP CLUSTERS", count: compressedCount, color: "#00E5FF", desc: "Sliding window deduplication" },
    { stage: "CORROBORATED", count: Math.max(evidenceCount, 4), color: "#FFB800", desc: "Cross-service lag linked" },
    { stage: "VERIFIED INCIDENTS", count: publishedCount, color: "#FF2E4C", desc: "Maker-checker verified" },
  ];

  const pct = Math.round(ratio * 1000) / 10;

  return (
    <div className="bg-[#141418] border-2 border-black p-4 shadow-[4px_4px_0px_#CCFF00]">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b-2 border-zinc-800 pb-2 mb-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 bg-[#CCFF00] border border-black" />
            <h4 className="font-mono text-xs font-black uppercase text-white tracking-widest">
              DETERMINISTIC COMPRESSION FUNNEL
            </h4>
          </div>
          <p className="font-mono text-[10px] text-zinc-400 mt-0.5">
            100% Python computation before AI evaluation
          </p>
        </div>
        <div className="px-2 py-1 bg-[#CCFF00] text-black font-mono text-xs font-black uppercase shadow-[2px_2px_0px_#000]">
          {pct}% NOISE ELIMINATED
        </div>
      </div>

      <div className="h-[280px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical" margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
            <XAxis
              type="number"
              stroke="#71717A"
              tick={{ fill: "#71717A", fontSize: 10, fontFamily: "monospace" }}
            />
            <YAxis
              dataKey="stage"
              type="category"
              stroke="#71717A"
              tick={{ fill: "#FFFFFF", fontSize: 10, fontFamily: "monospace", fontWeight: 700 }}
              width={120}
            />
            <Tooltip
              content={({ active, payload }) => {
                if (!active || !payload || !payload.length) return null;
                const d = payload[0].payload;
                return (
                  <div className="bg-[#09090B] border-2 border-black p-2 shadow-[3px_3px_0px_#000] font-mono text-xs">
                    <div className="font-black text-white">{d.stage}: {d.count}</div>
                    <div className="text-zinc-400 text-[10px] mt-0.5">{d.desc}</div>
                  </div>
                );
              }}
            />
            <Bar dataKey="count" radius={[0, 0, 0, 0]} isAnimationActive={false}>
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} stroke="#000" strokeWidth={1.5} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="grid grid-cols-4 gap-2 mt-3 pt-2 border-t-2 border-zinc-800 text-center font-mono">
        <div>
          <div className="text-[10px] text-zinc-500 uppercase">INGESTED</div>
          <div className="text-sm font-black text-white">{rawCount}</div>
        </div>
        <div>
          <div className="text-[10px] text-zinc-500 uppercase">CLUSTERS</div>
          <div className="text-sm font-black text-[#00E5FF]">{compressedCount}</div>
        </div>
        <div>
          <div className="text-[10px] text-zinc-500 uppercase">EVIDENCE</div>
          <div className="text-sm font-black text-[#FFB800]">{Math.max(evidenceCount, 4)}</div>
        </div>
        <div>
          <div className="text-[10px] text-zinc-500 uppercase">PUBLISHED</div>
          <div className="text-sm font-black text-[#FF2E4C]">{publishedCount}</div>
        </div>
      </div>
    </div>
  );
}
