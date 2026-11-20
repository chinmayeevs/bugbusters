"use client";

import React, { useState } from "react";
import { Play, Flame, Moon, Compass, Radio, ShieldX, Check } from "lucide-react";
import { triggerPipeline } from "../lib/api";

interface SimulationControlsProps {
  onSimulationComplete: () => void;
}

export const SimulationControls: React.FC<SimulationControlsProps> = ({ onSimulationComplete }) => {
  const [activeScenario, setActiveScenario] = useState<string | null>(null);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);

  const handleRun = async (scenarioName: string, forceAiFailure: boolean = false, label: string) => {
    setActiveScenario(scenarioName);
    setStatusMsg(`EXECUTING: ${label}...`);
    try {
      const res = await triggerPipeline(scenarioName, forceAiFailure);
      setStatusMsg(`SUCCESS: Incident ${res.incidentId} published with status ${res.status}!`);
      onSimulationComplete();
    } catch (err: any) {
      setStatusMsg(`ERROR: ${err.message}`);
    } finally {
      setTimeout(() => {
        setActiveScenario(null);
      }, 1000);
    }
  };

  return (
    <div className="bg-charcoal border-b-2 border-borderStructural p-4">
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-3 mb-3">
        <div className="flex items-center gap-2">
          <Play className="w-4 h-4 text-signal-lime fill-signal-lime" />
          <h3 className="text-xs font-mono font-black uppercase tracking-wider text-primaryText">
            BENCHMARK SCENARIO SIMULATOR // LIVE INJECTION CONTROLS
          </h3>
        </div>
        {statusMsg && (
          <span className="text-xs font-mono text-signal-lime bg-obsidian border border-signal-lime px-2 py-0.5">
            {statusMsg}
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-2.5">
        {/* Scenario 1: P0 Cascade */}
        <button
          onClick={() => handleRun("scenario_1_postgres_cascade", false, "P0 Lock Cascade")}
          disabled={activeScenario !== null}
          className="neo-btn bg-obsidian hover:bg-signal-crimson hover:text-obsidian text-primaryText border-2 border-signal-crimson p-2.5 text-left flex flex-col justify-between shadow-neo-sm group"
        >
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-mono text-signal-crimson group-hover:text-obsidian font-bold">
              SCENARIO 1 // P0
            </span>
            <Flame className="w-4 h-4 text-signal-crimson group-hover:text-obsidian" />
          </div>
          <span className="text-xs font-black uppercase mt-1 leading-tight">
            Postgres Lock Cascade
          </span>
          <span className="text-[10px] font-mono text-mutedLabel group-hover:text-obsidian mt-1">
            DB pool exhaustion & 504 timeouts
          </span>
        </button>

        {/* Scenario 2: Benign pg_dump */}
        <button
          onClick={() => handleRun("scenario_2_benign_backup", false, "Case A Benign Backup")}
          disabled={activeScenario !== null}
          className="neo-btn bg-obsidian hover:bg-signal-lime hover:text-obsidian text-primaryText border-2 border-signal-lime p-2.5 text-left flex flex-col justify-between shadow-neo-sm group"
        >
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-mono text-signal-lime group-hover:text-obsidian font-bold">
              SEA CASE A // BENIGN
            </span>
            <Moon className="w-4 h-4 text-signal-lime group-hover:text-obsidian" />
          </div>
          <span className="text-xs font-black uppercase mt-1 leading-tight">
            Nightly 02:00 pg_dump
          </span>
          <span className="text-[10px] font-mono text-mutedLabel group-hover:text-obsidian mt-1">
            High CPU, zero customer latency
          </span>
        </button>

        {/* Scenario 3: Context Divergence */}
        <button
          onClick={() => handleRun("scenario_3_context_divergence", false, "Case B Context Divergence")}
          disabled={activeScenario !== null}
          className="neo-btn bg-obsidian hover:bg-signal-amber hover:text-obsidian text-primaryText border-2 border-signal-amber p-2.5 text-left flex flex-col justify-between shadow-neo-sm group"
        >
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-mono text-signal-amber group-hover:text-obsidian font-bold">
              SEA CASE B // DIVERGENT
            </span>
            <Compass className="w-4 h-4 text-signal-amber group-hover:text-obsidian" />
          </div>
          <span className="text-xs font-black uppercase mt-1 leading-tight">
            Midday Lock Spike
          </span>
          <span className="text-[10px] font-mono text-mutedLabel group-hover:text-obsidian mt-1">
            Same CPU symptom, high latency!
          </span>
        </button>

        {/* Scenario 4: Redis Flap */}
        <button
          onClick={() => handleRun("scenario_4_transient_flap", false, "Redis Heartbeat Flap")}
          disabled={activeScenario !== null}
          className="neo-btn bg-obsidian hover:bg-signal-cyan hover:text-obsidian text-primaryText border-2 border-signal-cyan p-2.5 text-left flex flex-col justify-between shadow-neo-sm group"
        >
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-mono text-signal-cyan group-hover:text-obsidian font-bold">
              SCENARIO 4 // NOISE
            </span>
            <Radio className="w-4 h-4 text-signal-cyan group-hover:text-obsidian" />
          </div>
          <span className="text-xs font-black uppercase mt-1 leading-tight">
            Redis Flapping Noise
          </span>
          <span className="text-[10px] font-mono text-mutedLabel group-hover:text-obsidian mt-1">
            80 flapping alerts suppressed
          </span>
        </button>

        {/* Scenario 5: Fail-Open AI Down */}
        <button
          onClick={() => handleRun("fail_open", true, "Fail-Open Outage")}
          disabled={activeScenario !== null}
          className="neo-btn bg-obsidian hover:bg-signal-crimson hover:text-obsidian text-primaryText border-2 border-borderActive p-2.5 text-left flex flex-col justify-between shadow-neo-crimson group"
        >
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-mono text-signal-crimson group-hover:text-obsidian font-bold">
              FAIL-OPEN TEST
            </span>
            <ShieldX className="w-4 h-4 text-signal-crimson group-hover:text-obsidian" />
          </div>
          <span className="text-xs font-black uppercase mt-1 leading-tight">
            Simulate AI Failure
          </span>
          <span className="text-[10px] font-mono text-mutedLabel group-hover:text-obsidian mt-1">
            Ensures zero dropped P0 alerts
          </span>
        </button>
      </div>
    </div>
  );
};
