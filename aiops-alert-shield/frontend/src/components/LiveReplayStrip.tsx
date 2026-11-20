"use client";

import React, { useEffect, useState, useRef } from "react";
import { fetchReplayStatus, startStreamReplay, ReplayStatus } from "@/lib/api";

interface LiveReplayStripProps {
  onIncidentTriggered?: () => void;
}

export default function LiveReplayStrip({ onIncidentTriggered }: LiveReplayStripProps) {
  const [status, setStatus] = useState<ReplayStatus>({
    replayId: "",
    isRunning: false,
    progressPct: 0.0,
    rawCount: 0,
    collapsedCount: 0,
    suppressedBlips: 0,
    verifiedCount: 0,
    currentScenario: "IDLE",
    latestMessage: "Telemetry ingestion stream ready.",
  });
  const [starting, setStarting] = useState(false);
  const pollTimerRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    // Initial fetch
    checkStatus();
    return () => {
      if (pollTimerRef.current) clearInterval(pollTimerRef.current);
    };
  }, []);

  async function checkStatus() {
    try {
      const st = await fetchReplayStatus();
      setStatus(st);
      if (st.isRunning) {
        startPolling();
      }
    } catch {
      // ignore offline errors
    }
  }

  function startPolling() {
    if (pollTimerRef.current) clearInterval(pollTimerRef.current);
    pollTimerRef.current = setInterval(async () => {
      try {
        const st = await fetchReplayStatus();
        setStatus(st);
        if (!st.isRunning) {
          if (pollTimerRef.current) clearInterval(pollTimerRef.current);
          if (onIncidentTriggered) onIncidentTriggered();
        }
      } catch {
        // ignore
      }
    }, 700);
  }

  async function handleStartReplay() {
    setStarting(true);
    try {
      await startStreamReplay(8.0, true);
      startPolling();
    } catch (e: any) {
      alert("Failed to start stream replay: " + e.message);
    } finally {
      setStarting(false);
    }
  }

  const compressionRatio =
    status.rawCount > 0
      ? Math.round((status.collapsedCount / status.rawCount) * 100)
      : 0;

  return (
    <div className="border-b-2 border-[#27272A] bg-[#0E0E12] px-4 py-2 font-mono text-xs">
      <div className="flex flex-wrap items-center justify-between gap-3">
        {/* Stream Status & Controls */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <span
              className={`h-2.5 w-2.5 rounded-none ${
                status.isRunning
                  ? "bg-[#00FF66] shadow-[0_0_8px_#00FF66]"
                  : "bg-[#71717A]"
              }`}
            />
            <span className="text-[11px] font-black uppercase tracking-wider text-[#F4F4F5]">
              {status.isRunning ? "LIVE TELEMETRY STREAM" : "INGESTION STREAM IDLE"}
            </span>
          </div>

          <button
            onClick={handleStartReplay}
            disabled={status.isRunning || starting}
            className={`px-3 py-1 text-[10px] font-black uppercase tracking-wider border-2 border-black transition-all ${
              status.isRunning
                ? "bg-[#27272A] text-[#71717A] cursor-not-allowed"
                : "bg-[#00FF66] text-black shadow-[2px_2px_0px_#000] hover:translate-x-[1px] hover:translate-y-[1px] hover:shadow-[1px_1px_0px_#000]"
            }`}
          >
            {status.isRunning
              ? "[ STREAM IN PROGRESS... ]"
              : starting
              ? "[ STARTING... ]"
              : "[ ▶ LIVE REPLAY (400+ ALERTS) ]"}
          </button>
        </div>

        {/* Real-Time Monospace Metric Counters */}
        <div className="flex items-center gap-4 text-[11px]">
          <div className="flex items-center gap-1.5 bg-[#141418] border border-[#27272A] px-2 py-0.5">
            <span className="text-[#71717A]">RAW:</span>
            <span className="font-bold text-[#F4F4F5]">{status.rawCount}</span>
          </div>

          <div className="flex items-center gap-1.5 bg-[#141418] border border-[#27272A] px-2 py-0.5">
            <span className="text-[#71717A]">COLLAPSED:</span>
            <span className="font-bold text-[#00FF66]">
              {status.collapsedCount} ({compressionRatio}%)
            </span>
          </div>

          <div className="flex items-center gap-1.5 bg-[#141418] border border-[#27272A] px-2 py-0.5">
            <span className="text-[#71717A]">BLIPS DROPPED:</span>
            <span className="font-bold text-[#FFCC00]">{status.suppressedBlips}</span>
          </div>

          <div className="flex items-center gap-1.5 bg-[#141418] border border-[#27272A] px-2 py-0.5">
            <span className="text-[#71717A]">INCIDENTS:</span>
            <span className="font-bold text-[#FF0055]">{status.verifiedCount}</span>
          </div>
        </div>
      </div>

      {/* Progress Bar & Live Ticker */}
      <div className="mt-2 flex items-center gap-3">
        {/* Progress Bar */}
        <div className="w-32 bg-[#1C1C22] h-2 border border-[#27272A] overflow-hidden">
          <div
            className="bg-[#00FF66] h-full transition-all duration-300"
            style={{ width: `${Math.min(100, status.progressPct)}%` }}
          />
        </div>

        {/* Progress Percentage */}
        <span className="text-[10px] text-[#A1A1AA] w-10">
          {Math.round(status.progressPct)}%
        </span>

        {/* Monospace Scrolling Ticker */}
        <div className="flex-1 overflow-hidden whitespace-nowrap bg-[#08080A] border border-[#27272A] px-2 py-0.5 text-[10px] text-[#A1A1AA]">
          <span className="text-[#00FF66] font-bold mr-2">[{status.currentScenario}]</span>
          <span>{status.latestMessage}</span>
        </div>
      </div>
    </div>
  );
}
