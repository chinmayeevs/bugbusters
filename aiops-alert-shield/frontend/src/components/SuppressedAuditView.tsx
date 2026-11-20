"use client";

import React, { useState, useEffect } from "react";
import {
  fetchSuppressedEvents,
  escalateSuppressedEvent,
  SuppressedEvent,
} from "@/lib/api";

interface SuppressedAuditViewProps {
  onSelectIncident?: (incidentId: string) => void;
}

export default function SuppressedAuditView({ onSelectIncident }: SuppressedAuditViewProps = {}) {
  const [events, setEvents] = useState<SuppressedEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState<string>("ALL");
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedEvent, setSelectedEvent] = useState<SuppressedEvent | null>(null);
  const [escalateReason, setEscalateReason] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [feedbackMsg, setFeedbackMsg] = useState<string | null>(null);

  useEffect(() => {
    loadEvents();
  }, [selectedCategory]);

  async function loadEvents() {
    setLoading(true);
    try {
      const data = await fetchSuppressedEvents(100, selectedCategory === "ALL" ? undefined : selectedCategory);
      setEvents(data);
    } catch (e: any) {
      console.error("Failed to load suppressed audit events:", e);
    } finally {
      setLoading(false);
    }
  }

  async function handleEscalate() {
    if (!selectedEvent || !escalateReason.trim()) return;
    setSubmitting(true);
    try {
      const updated = await escalateSuppressedEvent(selectedEvent.eventId, escalateReason.trim(), "lead-sre");
      const incId = updated.escalatedIncidentId || `INC-ESCALATED-${selectedEvent.eventId.replace("SUP-", "").substring(0, 8)}`;
      setEvents((prev) =>
        prev.map((ev) => (ev.eventId === updated.eventId ? { ...ev, status: "ESCALATED", escalatedBy: "lead-sre", escalatedIncidentId: incId } : ev))
      );
      setFeedbackMsg(`Event ${selectedEvent.eventId} successfully escalated to ${incId} (NEEDS_HUMAN_REVIEW).`);
      setSelectedEvent(null);
      setEscalateReason("");
      setTimeout(() => setFeedbackMsg(null), 6000);
    } catch (e: any) {
      alert("Failed to escalate event: " + e.message);
    } finally {
      setSubmitting(false);
    }
  }

  const filteredEvents = events.filter((ev) => {
    if (!searchTerm) return true;
    const term = searchTerm.toLowerCase();
    return (
      ev.service.toLowerCase().includes(term) ||
      ev.metric.toLowerCase().includes(term) ||
      ev.eventId.toLowerCase().includes(term) ||
      ev.suppressionReason.toLowerCase().includes(term)
    );
  });

  return (
    <div className="space-y-4 font-mono text-xs">
      {/* Top Banner explaining No Silent Suppression */}
      <div className="border-2 border-[#27272A] bg-[#141418] p-4 flex flex-col md:flex-row justify-between items-start md:items-center gap-3 shadow-[4px_4px_0px_#000]">
        <div>
          <div className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 bg-[#FFCC00]" />
            <h2 className="text-sm font-black uppercase tracking-wider text-[#F4F4F5]">
              No Silent Suppression Audit Log
            </h2>
            <span className="border border-[#3F3F46] bg-[#27272A] px-2 py-0.5 text-[10px] text-[#A1A1AA]">
              {events.length} LOGGED SUPPRESSIONS
            </span>
          </div>
          <p className="text-[11px] text-[#71717A] mt-1">
            Zero telemetry signals are silently dropped. Every deduplicated alert, transient blip, and benign repeat pattern is mathematically proven and auditable here.
          </p>
        </div>

        <button
          onClick={loadEvents}
          className="px-3 py-1.5 bg-[#27272A] text-[#F4F4F5] text-[11px] font-bold uppercase tracking-wider border border-[#3F3F46] hover:bg-[#3F3F46]"
        >
          [ REFRESH AUDIT LOG ]
        </button>
      </div>

      {feedbackMsg && (
        <div className="border border-[#00FF66] bg-[#00FF66]/10 p-3 text-[11px] text-[#00FF66]">
          {feedbackMsg}
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-[#0E0E12] border border-[#27272A] p-3">
        <div className="flex flex-wrap items-center gap-2">
          {["ALL", "DUPLICATES", "TRANSIENT_BLIPS", "SEA_BENIGN_REPEAT"].map((cat) => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              className={`px-3 py-1 text-[10px] font-black uppercase tracking-wider border transition-all ${
                selectedCategory === cat
                  ? "bg-[#F4F4F5] text-black border-white shadow-[2px_2px_0px_#000]"
                  : "bg-[#18181C] text-[#A1A1AA] border-[#27272A] hover:text-white"
              }`}
            >
              {cat.replace(/_/g, " ")}
            </button>
          ))}
        </div>

        <div className="w-full md:w-72">
          <input
            type="text"
            placeholder="Search service, metric, event ID..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-[#141418] border border-[#27272A] px-3 py-1 text-[11px] text-[#F4F4F5] placeholder-[#71717A] focus:outline-none focus:border-[#00FF66]"
          />
        </div>
      </div>

      {/* Audit Log Table */}
      <div className="border border-[#27272A] bg-[#0E0E12] overflow-x-auto">
        <table className="w-full text-left border-collapse text-xs font-mono">
          <thead>
            <tr className="border-b border-[#27272A] text-[#71717A] bg-[#141418]">
              <th className="p-3">Event ID</th>
              <th className="p-3">Timestamp</th>
              <th className="p-3">Service & Metric</th>
              <th className="p-3">Category</th>
              <th className="p-3">Collapsed</th>
              <th className="p-3">Mathematical Justification</th>
              <th className="p-3">Status</th>
              <th className="p-3 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#27272A]">
            {loading ? (
              <tr>
                <td colSpan={8} className="p-8 text-center text-[#71717A]">
                  Loading suppressed event audit trail...
                </td>
              </tr>
            ) : filteredEvents.length === 0 ? (
              <tr>
                <td colSpan={8} className="p-8 text-center text-[#71717A]">
                  No suppressed events match the current filter.
                </td>
              </tr>
            ) : (
              filteredEvents.map((ev) => (
                <tr key={ev.eventId} className="hover:bg-[#141418] transition-colors">
                  <td className="p-3 font-bold text-[#A1A1AA]">{ev.eventId}</td>
                  <td className="p-3 text-[#71717A] text-[10px]">
                    {ev.timestamp ? ev.timestamp.replace("T", " ").replace("Z", "") : "--"}
                  </td>
                  <td className="p-3">
                    <span className="font-bold text-[#F4F4F5]">{ev.service}</span>
                    <span className="block text-[10px] text-[#71717A]">{ev.metric}</span>
                  </td>
                  <td className="p-3">
                    <span className="border border-[#27272A] bg-[#18181C] px-2 py-0.5 text-[10px] font-bold text-[#A1A1AA]">
                      {ev.category}
                    </span>
                  </td>
                  <td className="p-3">
                    <span className="font-bold text-[#00FF66]">
                      +{ev.collapsedCount} alerts
                    </span>
                  </td>
                  <td className="p-3 max-w-xs text-[11px] text-[#A1A1AA]">
                    <div>{ev.suppressionReason}</div>
                    {ev.madZScore > 0 && (
                      <span className="text-[9px] text-[#71717A]">
                        (MAD Z={ev.madZScore.toFixed(2)})
                      </span>
                    )}
                  </td>
                  <td className="p-3">
                    {ev.status === "ESCALATED" ? (
                      <span className="border border-[#FF0055] bg-[#FF0055]/10 px-2 py-0.5 text-[10px] font-bold text-[#FF0055]">
                        ESCALATED
                      </span>
                    ) : (
                      <span className="border border-[#3F3F46] bg-[#27272A] px-2 py-0.5 text-[10px] font-bold text-[#A1A1AA]">
                        SUPPRESSED
                      </span>
                    )}
                  </td>
                  <td className="p-3 text-right">
                    {ev.status === "ESCALATED" || ev.escalatedIncidentId ? (
                      (() => {
                        const targetIncId = ev.escalatedIncidentId || `INC-ESCALATED-${ev.eventId.replace("SUP-", "").substring(0, 8)}`;
                        return (
                          <button
                            type="button"
                            onClick={() => onSelectIncident?.(targetIncId)}
                            title={`Jump to escalated incident ${targetIncId} in Incident Queue`}
                            className="px-2 py-1 bg-[#00E5FF]/20 text-[#00E5FF] hover:bg-[#00E5FF] hover:text-black border border-[#00E5FF] text-[10px] font-black uppercase tracking-wider transition-all shadow-[2px_2px_0px_#000]"
                          >
                            [ ESCALATED -&gt; {targetIncId} ]
                          </button>
                        );
                      })()
                    ) : (
                      <button
                        type="button"
                        onClick={() => setSelectedEvent(ev)}
                        className="px-2 py-1 bg-[#27272A] hover:bg-[#FF0055] hover:text-white border border-[#3F3F46] text-[10px] font-bold uppercase transition-colors"
                      >
                        [ ESCALATE ]
                      </button>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Escalation Modal */}
      {selectedEvent && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4">
          <div className="w-full max-w-lg bg-[#0C0C0E] border-2 border-[#FF0055] p-6 shadow-[8px_8px_0px_#000] space-y-4">
            <div className="flex items-center justify-between border-b border-[#27272A] pb-3">
              <div className="flex items-center gap-2">
                <span className="h-2.5 w-2.5 bg-[#FF0055]" />
                <h3 className="text-sm font-black uppercase text-[#F4F4F5]">
                  Escalate Suppressed Event
                </h3>
              </div>
              <button
                onClick={() => setSelectedEvent(null)}
                className="text-[#71717A] hover:text-white text-xs"
              >
                [ CLOSE ]
              </button>
            </div>

            <div className="bg-[#141418] border border-[#27272A] p-3 space-y-1 text-[11px]">
              <div>
                <span className="text-[#71717A]">Event ID: </span>
                <span className="font-bold text-[#F4F4F5]">{selectedEvent.eventId}</span>
              </div>
              <div>
                <span className="text-[#71717A]">Target Service: </span>
                <span className="font-bold text-[#F4F4F5]">{selectedEvent.service}</span>
              </div>
              <div>
                <span className="text-[#71717A]">Suppression Reason: </span>
                <span className="text-[#A1A1AA]">{selectedEvent.suppressionReason}</span>
              </div>
            </div>

            <div className="space-y-1">
              <label className="text-[11px] font-bold uppercase text-[#A1A1AA]">
                Engineer Escalation Justification:
              </label>
              <textarea
                rows={3}
                placeholder="Explain why this suppressed noise represents a genuine incident or requires human investigation..."
                value={escalateReason}
                onChange={(e) => setEscalateReason(e.target.value)}
                className="w-full bg-[#141418] border border-[#27272A] p-2 text-xs text-[#F4F4F5] focus:outline-none focus:border-[#FF0055]"
              />
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <button
                onClick={() => setSelectedEvent(null)}
                className="px-4 py-1.5 bg-[#27272A] text-[#F4F4F5] text-xs font-bold uppercase border border-[#3F3F46]"
              >
                Cancel
              </button>
              <button
                onClick={handleEscalate}
                disabled={submitting || !escalateReason.trim()}
                className="px-4 py-1.5 bg-[#FF0055] text-white text-xs font-black uppercase border-2 border-black shadow-[3px_3px_0px_#000] disabled:opacity-50"
              >
                {submitting ? "[ ESCALATING... ]" : "[ CONFIRM ESCALATION ]"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
