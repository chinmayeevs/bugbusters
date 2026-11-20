"use client";

import React from "react";
import { ServiceHealth } from "../lib/api";
import { Server, Activity, CheckCircle, AlertOctagon, AlertTriangle } from "lucide-react";

interface ServiceHealthGridProps {
  services: ServiceHealth[];
}

export const ServiceHealthGrid: React.FC<ServiceHealthGridProps> = ({ services }) => {
  return (
    <div className="bg-charcoal border-b-2 border-borderStructural p-4">
      <div className="flex items-center gap-2 mb-3">
        <Server className="w-4 h-4 text-signal-cyan" />
        <h3 className="text-xs font-mono font-black uppercase tracking-wider text-primaryText">
          TOPOLOGICAL MICROSERVICE FLEET STATUS // E-COMMERCE CHECKOUT STACK
        </h3>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        {services.map((svc) => {
          const isDegraded = svc.status === "DEGRADED" || svc.status === "OUTAGE";
          return (
            <div
              key={svc.service}
              className={`p-3 border-2 flex flex-col justify-between ${
                svc.status === "OUTAGE"
                  ? "bg-obsidian border-signal-crimson shadow-neo-crimson"
                  : svc.status === "DEGRADED"
                  ? "bg-obsidian border-signal-amber shadow-neo-amber"
                  : "bg-obsidian border-borderStructural shadow-neo-sm"
              }`}
            >
              <div>
                <div className="flex items-center justify-between">
                  <span
                    className={`text-[9px] font-mono font-bold px-1.5 py-0.2 uppercase ${
                      svc.status === "OUTAGE"
                        ? "bg-signal-crimson text-obsidian"
                        : svc.status === "DEGRADED"
                        ? "bg-signal-amber text-obsidian"
                        : "bg-signal-lime text-obsidian"
                    }`}
                  >
                    {svc.status}
                  </span>
                </div>
                <h4 className="font-mono text-xs font-bold text-primaryText mt-1.5 truncate">
                  {svc.service}
                </h4>
              </div>

              <div className="mt-2.5 pt-2 border-t border-borderStructural space-y-0.5 text-[10px] font-mono text-mutedLabel">
                <div className="flex justify-between">
                  <span>p99 Lat:</span>
                  <span className="text-primaryText font-bold">{svc.latencyP99Ms}ms</span>
                </div>
                <div className="flex justify-between">
                  <span>5xx Err:</span>
                  <span className={svc.errorRate5xx > 1.0 ? "text-signal-crimson font-bold" : "text-primaryText"}>
                    {svc.errorRate5xx}%
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>CPU:</span>
                  <span className="text-primaryText">{svc.cpuUtilizationPct}%</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
