"use client";

import React, { useState, useEffect } from "react";
import { fetchSeaCasebook, SeaCasebookDetail } from "@/lib/api";

export default function SeaCasebookExplorer() {
  const [cases, setCases] = useState<SeaCasebookDetail[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedCase, setSelectedCase] = useState<SeaCasebookDetail | null>(null);

  useEffect(() => {
    loadCasebook();
  }, []);

  async function loadCasebook() {
    setLoading(true);
    try {
      const data = await fetchSeaCasebook(50);
      setCases(data);
      if (data.length > 0 && !selectedCase) {
        setSelectedCase(data[0]);
      }
    } catch (e: any) {
      console.error("Failed to load SEA casebook:", e);
    } finally {
      setLoading(false);
    }
  }

  const filteredCases = cases.filter((c) => {
    if (!searchTerm) return true;
    const term = searchTerm.toLowerCase();
    return (
      c.title.toLowerCase().includes(term) ||
      c.symptomSignature.toLowerCase().includes(term) ||
      c.caseId.toLowerCase().includes(term)
    );
  });

  return (
    <div className="space-y-4 font-mono text-xs">
      {/* Top Banner explaining SEA Memory Architecture */}
      <div className="border-2 border-[#27272A] bg-[#141418] p-4 flex flex-col md:flex-row justify-between items-start md:items-center gap-3 shadow-[4px_4px_0px_#000]">
        <div>
          <div className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 bg-[#00FF66]" />
            <h2 className="text-sm font-black uppercase tracking-wider text-[#F4F4F5]">
              Self-Evolving Agent (SEA) Versioned Casebook Memory
            </h2>
            <span className="border border-[#00FF66] bg-[#00FF66]/10 px-2 py-0.5 text-[10px] font-bold text-[#00FF66]">
              {cases.length} HISTORICAL CASES
            </span>
          </div>
          <p className="text-[11px] text-[#71717A] mt-1">
            Zero auto-remediation. Casebook memory learns strictly from human-verified resolutions and maker-checker validation outcomes with end-to-end provenance.
          </p>
        </div>

        <button
          onClick={loadCasebook}
          className="px-3 py-1.5 bg-[#27272A] text-[#F4F4F5] text-[11px] font-bold uppercase tracking-wider border border-[#3F3F46] hover:bg-[#3F3F46]"
        >
          [ REFRESH CASEBOOK ]
        </button>
      </div>

      {/* Main Split View: Left List, Right Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Left Column: Search & Case List */}
        <div className="lg:col-span-5 space-y-3">
          <input
            type="text"
            placeholder="Search cases by title or signature..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-[#141418] border border-[#27272A] px-3 py-2 text-xs text-[#F4F4F5] placeholder-[#71717A] focus:outline-none focus:border-[#00FF66]"
          />

          <div className="space-y-2 max-h-[70vh] overflow-y-auto pr-1">
            {loading ? (
              <div className="p-8 text-center text-[#71717A] bg-[#0E0E12] border border-[#27272A]">
                Loading versioned casebook memory...
              </div>
            ) : filteredCases.length === 0 ? (
              <div className="p-8 text-center text-[#71717A] bg-[#0E0E12] border border-[#27272A]">
                No cases match the search criteria.
              </div>
            ) : (
              filteredCases.map((c) => {
                const isSelected = selectedCase?.caseId === c.caseId;
                return (
                  <div
                    key={c.caseId}
                    onClick={() => setSelectedCase(c)}
                    className={`cursor-pointer p-3 border-2 transition-all ${
                      isSelected
                        ? "border-[#00FF66] bg-[#141418] shadow-[3px_3px_0px_#000]"
                        : "border-[#27272A] bg-[#0E0E12] hover:border-[#3F3F46]"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] font-bold text-[#A1A1AA]">{c.caseId}</span>
                      <div className="flex items-center gap-1.5">
                        <span className="border border-[#3F3F46] bg-[#18181C] px-1.5 py-0.5 text-[9px] text-[#A1A1AA]">
                          v{c.version}
                        </span>
                        <span
                          className={`px-1.5 py-0.5 text-[9px] font-bold border ${
                            c.provenance === "HUMAN_CONFIRMED"
                              ? "border-[#00FF66] text-[#00FF66] bg-[#00FF66]/10"
                              : c.provenance === "SEED"
                              ? "border-[#71717A] text-[#A1A1AA] bg-[#27272A]"
                              : "border-[#FFCC00] text-[#FFCC00] bg-[#FFCC00]/10"
                          }`}
                        >
                          {c.provenance}
                        </span>
                      </div>
                    </div>

                    <h4 className="text-xs font-bold text-[#F4F4F5] mt-1.5 leading-snug">
                      {c.title}
                    </h4>

                    <div className="mt-2 text-[10px] text-[#71717A] truncate">
                      Sig: {c.symptomSignature}
                    </div>

                    <div className="mt-2 flex items-center justify-between text-[10px]">
                      <span
                        className={`font-bold ${
                          c.historicalOutcome === "VERIFIED_INCIDENT"
                            ? "text-[#FF0055]"
                            : c.historicalOutcome === "BENIGN_NOISE"
                            ? "text-[#FFCC00]"
                            : "text-[#00FF66]"
                        }`}
                      >
                        {c.historicalOutcome}
                      </span>
                      <span className="text-[#71717A]">{c.category}</span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Right Column: Casebook Detail Inspector */}
        <div className="lg:col-span-7">
          {selectedCase ? (
            <div className="border-2 border-[#27272A] bg-[#0E0E12] p-5 space-y-5 shadow-[6px_6px_0px_#000]">
              {/* Header */}
              <div className="border-b border-[#27272A] pb-3 flex justify-between items-start">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-black text-[#F4F4F5]">{selectedCase.caseId}</span>
                    <span className="border border-[#3F3F46] bg-[#18181C] px-2 py-0.5 text-[10px] text-[#A1A1AA]">
                      Version {selectedCase.version}
                    </span>
                    <span className="border border-[#00FF66] bg-[#00FF66]/10 px-2 py-0.5 text-[10px] font-bold text-[#00FF66]">
                      {selectedCase.provenance}
                    </span>
                  </div>
                  <h3 className="text-base font-bold text-[#F4F4F5] mt-1">
                    {selectedCase.title}
                  </h3>
                </div>

                <span
                  className={`px-2 py-1 text-[11px] font-black border ${
                    selectedCase.historicalOutcome === "VERIFIED_INCIDENT"
                      ? "border-[#FF0055] text-[#FF0055] bg-[#FF0055]/10"
                      : selectedCase.historicalOutcome === "BENIGN_NOISE"
                      ? "border-[#FFCC00] text-[#FFCC00] bg-[#FFCC00]/10"
                      : "border-[#00FF66] text-[#00FF66] bg-[#00FF66]/10"
                  }`}
                >
                  {selectedCase.historicalOutcome}
                </span>
              </div>

              {/* Symptom Signature */}
              <div>
                <label className="text-[10px] font-bold uppercase tracking-wider text-[#71717A] block mb-1">
                  Deterministic Symptom Signature
                </label>
                <div className="bg-[#141418] border border-[#27272A] p-2 text-xs text-[#00FF66] font-mono break-all">
                  {selectedCase.symptomSignature}
                </div>
              </div>

              {/* Context Conditions (The Key to Divergence Protection) */}
              <div>
                <label className="text-[10px] font-bold uppercase tracking-wider text-[#71717A] block mb-1">
                  Historical Context Conditions (Ground Truth Baseline)
                </label>
                <pre className="bg-[#141418] border border-[#27272A] p-3 text-[11px] text-[#A1A1AA] font-mono overflow-x-auto whitespace-pre-wrap">
                  {(() => {
                    try {
                      return JSON.stringify(JSON.parse(selectedCase.contextConditions), null, 2);
                    } catch {
                      return selectedCase.contextConditions;
                    }
                  })()}
                </pre>
              </div>

              {/* Remediation & Diagnostics */}
              <div>
                <label className="text-[10px] font-bold uppercase tracking-wider text-[#71717A] block mb-1">
                  Verified Remediation Recommendation
                </label>
                <div className="bg-[#141418] border border-[#27272A] p-3 text-xs text-[#F4F4F5] leading-relaxed">
                  {selectedCase.remediationRecommendation || "No formal remediation prescribed."}
                </div>
              </div>

              {/* Diagnostic Runbook */}
              {selectedCase.diagnosticRunbook && selectedCase.diagnosticRunbook.length > 0 && (
                <div>
                  <label className="text-[10px] font-bold uppercase tracking-wider text-[#71717A] block mb-1">
                    Prescribed Diagnostic Runbook
                  </label>
                  <div className="space-y-1.5">
                    {selectedCase.diagnosticRunbook.map((cmd, idx) => (
                      <div
                        key={idx}
                        className="bg-[#08080A] border border-[#27272A] p-2 text-[11px] font-mono text-[#00FF66] flex items-center justify-between"
                      >
                        <span className="truncate">{cmd}</span>
                        <span className="text-[9px] text-[#71717A] ml-2">STEP {idx + 1}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Timestamps */}
              <div className="border-t border-[#27272A] pt-3 flex justify-between text-[10px] text-[#71717A]">
                <span>Created: {selectedCase.createdAt || "N/A"}</span>
                <span>Last Updated: {selectedCase.updatedAt || "N/A"}</span>
              </div>
            </div>
          ) : (
            <div className="border-2 border-[#27272A] bg-[#0E0E12] p-12 text-center text-[#71717A]">
              Select a case from the casebook list to inspect historical conditions and diagnostics.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
