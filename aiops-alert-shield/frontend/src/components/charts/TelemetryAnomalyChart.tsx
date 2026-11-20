"use client";

import React, { useState } from "react";
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
} from "recharts";
import { MetricDataPoint } from "@/lib/api";

interface TelemetryAnomalyChartProps {
  series?: MetricDataPoint[];
  rootService?: string;
}

export default function TelemetryAnomalyChart({ series = [], rootService = "orders-postgres-primary" }: TelemetryAnomalyChartProps) {
  const [selectedService, setSelectedService] = useState<string>("ALL");

  if (!series || series.length === 0) {
    return (
      <div className="p-4 bg-[#141418] border-2 border-[#27272A] text-zinc-500 font-mono text-xs">
        NO TIMESERIES DATA AVAILABLE FOR CURRENT INCIDENT
      </div>
    );
  }

  // Find unique services in series
  const services = Array.from(new Set(series.map((s) => s.service)));

  // Aggregate points by timestamp for multi-line display
  const timestamps = Array.from(new Set(series.map((s) => s.timestamp)));
  const chartData = timestamps.map((ts) => {
    const points = series.filter((s) => s.timestamp === ts);
    const primary = points.find((p) => p.service === rootService) || points[0];
    const downstream = points.find((p) => p.service === "checkout-api" || p.service === "api-gateway") || points[1];

    return {
      timestamp: ts,
      primaryValue: primary?.value,
      primaryEwma: primary?.ewma,
      primaryMedian: primary?.median,
      madLower: primary?.madLower ?? 0,
      madUpper: primary?.madUpper ?? 0,
      staticThreshold: primary?.staticThreshold,
      primaryAnomaly: primary?.isAnomaly,
      primaryMetric: primary?.metricName,
      downstreamValue: downstream?.value,
      downstreamMetric: downstream?.metricName,
      downstreamService: downstream?.service,
    };
  });

  const staticThresh = chartData.find((d) => d.staticThreshold != null)?.staticThreshold;

  return (
    <div className="bg-[#141418] border-2 border-black p-4 shadow-[4px_4px_0px_#00E5FF]">
      <div className="flex flex-wrap items-center justify-between gap-2 mb-3 border-b-2 border-zinc-800 pb-2">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 bg-[#FF2E4C] border border-black" />
            <h4 className="font-mono text-xs font-black uppercase text-white tracking-widest">
              SLIDING-WINDOW ANOMALY & EWMA CORRELATION
            </h4>
          </div>
          <p className="font-mono text-[10px] text-zinc-400 mt-0.5">
            Primary suspect [{rootService}] vs Downstream Latency with MAD Upper/Lower Bounds
          </p>
        </div>
        <div className="flex items-center gap-3 font-mono text-[10px]">
          <span className="flex items-center gap-1 text-[#FF2E4C]">
            <span className="w-2 h-2 bg-[#FF2E4C]" /> Primary Metric
          </span>
          <span className="flex items-center gap-1 text-[#FFB800]">
            <span className="w-2 h-0.5 bg-[#FFB800]" /> EWMA (α=0.3)
          </span>
          <span className="flex items-center gap-1 text-[#00E5FF]">
            <span className="w-2 h-2 bg-[#00E5FF]" /> Downstream Lag
          </span>
          <span className="flex items-center gap-1 text-zinc-400">
            <span className="w-2 h-2 bg-zinc-600/40 border border-zinc-500" /> MAD ±2.5
          </span>
        </div>
      </div>

      <div className="h-[280px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <XAxis
              dataKey="timestamp"
              stroke="#71717A"
              tick={{ fill: "#71717A", fontSize: 10, fontFamily: "monospace" }}
              tickLine={{ stroke: "#3F3F46" }}
            />
            <YAxis
              yAxisId="left"
              stroke="#71717A"
              tick={{ fill: "#71717A", fontSize: 10, fontFamily: "monospace" }}
              tickLine={{ stroke: "#3F3F46" }}
            />
            <YAxis
              yAxisId="right"
              orientation="right"
              stroke="#00E5FF"
              tick={{ fill: "#00E5FF", fontSize: 10, fontFamily: "monospace" }}
              tickLine={{ stroke: "#00E5FF" }}
            />
            <Tooltip
              content={({ active, payload, label }) => {
                if (!active || !payload || !payload.length) return null;
                const d = payload[0].payload;
                return (
                  <div className="bg-[#09090B] border-2 border-[#FFB800] p-3 shadow-[4px_4px_0px_#000] font-mono text-xs">
                    <div className="text-zinc-400 font-bold border-b border-zinc-800 pb-1 mb-2">
                      TIMESTAMP: {label}
                    </div>
                    <div className="space-y-1">
                      <div className="text-[#FF2E4C] font-black">
                        {d.primaryMetric || "Primary"}: {d.primaryValue}{" "}
                        {d.primaryAnomaly && (
                          <span className="ml-1 px-1 bg-[#FF2E4C] text-black font-black text-[9px]">
                            ANOMALY
                          </span>
                        )}
                      </div>
                      <div className="text-[#FFB800]">EWMA: {d.primaryEwma}</div>
                      <div className="text-zinc-400 text-[10px]">
                        MAD Range: [{d.madLower} - {d.madUpper}] (Median: {d.primaryMedian})
                      </div>
                      {d.staticThreshold && (
                        <div className="text-red-400 text-[10px]">
                          Static Thresh: {d.staticThreshold}
                        </div>
                      )}
                      {d.downstreamValue != null && (
                        <div className="text-[#00E5FF] font-bold pt-1 border-t border-zinc-800">
                          {d.downstreamService} ({d.downstreamMetric}): {d.downstreamValue}ms
                        </div>
                      )}
                    </div>
                  </div>
                );
              }}
            />
            {/* MAD Confidence Band */}
            <Area
              yAxisId="left"
              type="monotone"
              dataKey="madUpper"
              stroke="none"
              fill="#3F3F46"
              fillOpacity={0.25}
              isAnimationActive={false}
            />
            {/* Static Threshold Reference Line */}
            {staticThresh != null && (
              <ReferenceLine
                yAxisId="left"
                y={staticThresh}
                stroke="#FF2E4C"
                strokeDasharray="4 4"
                label={{
                  value: `THRESHOLD ${staticThresh}`,
                  fill: "#FF2E4C",
                  fontSize: 10,
                  fontFamily: "monospace",
                  position: "insideTopLeft",
                }}
              />
            )}
            {/* Primary Metric Line */}
            <Line
              yAxisId="left"
              type="monotone"
              dataKey="primaryValue"
              stroke="#FF2E4C"
              strokeWidth={3}
              isAnimationActive={false}
              dot={{ fill: "#FF2E4C", stroke: "#000", strokeWidth: 1, r: 4 }}
              activeDot={{ r: 6, fill: "#FFF", stroke: "#FF2E4C", strokeWidth: 2 }}
            />
            {/* EWMA Smoothing Line */}
            <Line
              yAxisId="left"
              type="monotone"
              dataKey="primaryEwma"
              stroke="#FFB800"
              strokeWidth={2}
              strokeDasharray="4 3"
              isAnimationActive={false}
              dot={false}
            />
            {/* Downstream Correlated Metric (Lag delay) */}
            <Line
              yAxisId="right"
              type="monotone"
              dataKey="downstreamValue"
              stroke="#00E5FF"
              strokeWidth={2}
              isAnimationActive={false}
              dot={{ fill: "#00E5FF", stroke: "#000", strokeWidth: 1, r: 3 }}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
