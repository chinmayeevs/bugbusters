"use client";

import React, { useState } from "react";
import { BlastRadiusNode } from "@/lib/api";

interface InteractiveTopologyDAGProps {
  nodes?: BlastRadiusNode[];
  rootSuspect?: string;
  mermaidDiagram?: string;
}

export default function InteractiveTopologyDAG({
  nodes = [],
  rootSuspect = "orders-postgres-primary",
  mermaidDiagram = "",
}: InteractiveTopologyDAGProps) {
  const [selectedNode, setSelectedNode] = useState<BlastRadiusNode | null>(null);
  const [showMermaidModal, setShowMermaidModal] = useState<boolean>(false);
  const [copied, setCopied] = useState<boolean>(false);

  const nodeMap = new Map<string, BlastRadiusNode>();
  nodes.forEach((n) => nodeMap.set(n.service, n));

  const getNodeInfo = (svc: string) => {
    return (
      nodeMap.get(svc) || {
        service: svc,
        role: svc === rootSuspect ? "ROOT_SUSPECT" : "UNAFFECTED",
        hopDistance: 0,
        impactLevel: svc === rootSuspect ? "CRITICAL" : "NORMAL",
        trafficLossPct: 0.0,
      }
    );
  };

  const getNodeColor = (svc: string) => {
    const info = getNodeInfo(svc);
    if (info.role === "ROOT_SUSPECT" || info.impactLevel === "CRITICAL") {
      return { fill: "#FF2E4C", text: "#FFFFFF", border: "#000000", glow: "#FF2E4C" };
    }
    if (info.impactLevel === "DEGRADED") {
      return { fill: "#FFB800", text: "#000000", border: "#000000", glow: "#FFB800" };
    }
    return { fill: "#1C1C22", text: "#A1A1AA", border: "#3F3F46", glow: "#27272A" };
  };

  const copyMermaid = () => {
    const text = mermaidDiagram || "graph TD\n  api_gateway --> checkout_api";
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="bg-[#141418] border-2 border-black p-4 shadow-[4px_4px_0px_#FF2E4C]">
      <div className="flex items-center justify-between border-b-2 border-zinc-800 pb-2 mb-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 bg-[#FFB800] border border-black" />
            <h4 className="font-mono text-xs font-black uppercase text-white tracking-widest">
              CHECKOUT TOPOLOGY CASCADE GRAPH
            </h4>
          </div>
          <p className="font-mono text-[10px] text-zinc-400 mt-0.5">
            Click any service node to inspect blast radius & hop latency
          </p>
        </div>
        <button
          onClick={() => setShowMermaidModal(true)}
          className="px-2.5 py-1 bg-[#1C1C22] hover:bg-[#27272A] border-2 border-black text-[#00E5FF] font-mono text-[10px] font-black uppercase shadow-[2px_2px_0px_#00E5FF] transition-all active:translate-x-0.5 active:translate-y-0.5"
        >
          &lt; / &gt; MERMAID SOURCE
        </button>
      </div>

      {/* SVG Topology Graph */}
      <div className="w-full h-[280px] overflow-x-auto bg-[#09090B] border-2 border-zinc-800 p-3 flex items-center justify-center">
        <svg viewBox="0 0 540 260" className="w-full max-w-[540px] h-[240px] select-none">
          <defs>
            <marker
              id="arrowhead"
              markerWidth="8"
              markerHeight="6"
              refX="7"
              refY="3"
              orient="auto"
            >
              <polygon points="0 0, 8 3, 0 6" fill="#71717A" />
            </marker>
            <marker
              id="arrowhead-red"
              markerWidth="8"
              markerHeight="6"
              refX="7"
              refY="3"
              orient="auto"
            >
              <polygon points="0 0, 8 3, 0 6" fill="#FF2E4C" />
            </marker>
          </defs>

          {/* Edges */}
          {/* api-gateway -> checkout-api */}
          <line
            x1="270"
            y1="40"
            x2="270"
            y2="85"
            stroke="#FF2E4C"
            strokeWidth="2.5"
            strokeDasharray="4 2"
            markerEnd="url(#arrowhead-red)"
          />

          {/* checkout-api -> payment-service */}
          <line
            x1="230"
            y1="125"
            x2="80"
            y2="175"
            stroke="#FFB800"
            strokeWidth="2"
            markerEnd="url(#arrowhead)"
          />

          {/* checkout-api -> inventory-service */}
          <line
            x1="250"
            y1="125"
            x2="200"
            y2="175"
            stroke="#52525B"
            strokeWidth="1.5"
            markerEnd="url(#arrowhead)"
          />

          {/* checkout-api -> orders-postgres-primary */}
          <line
            x1="290"
            y1="125"
            x2="340"
            y2="175"
            stroke="#FF2E4C"
            strokeWidth="2.5"
            markerEnd="url(#arrowhead-red)"
          />

          {/* checkout-api -> redis-cache */}
          <line
            x1="310"
            y1="125"
            x2="460"
            y2="175"
            stroke="#52525B"
            strokeWidth="1.5"
            markerEnd="url(#arrowhead)"
          />

          {/* Node 1: api-gateway */}
          {(() => {
            const col = getNodeColor("api-gateway");
            return (
              <g
                className="cursor-pointer"
                onClick={() => setSelectedNode(getNodeInfo("api-gateway"))}
              >
                <rect
                  x="200"
                  y="10"
                  width="140"
                  height="34"
                  fill={col.fill}
                  stroke={col.border}
                  strokeWidth="2"
                  filter="drop-shadow(3px 3px 0px #000)"
                />
                <text
                  x="270"
                  y="31"
                  fill={col.text}
                  fontSize="11"
                  fontWeight="900"
                  fontFamily="monospace"
                  textAnchor="middle"
                >
                  api-gateway
                </text>
              </g>
            );
          })()}

          {/* Node 2: checkout-api */}
          {(() => {
            const col = getNodeColor("checkout-api");
            return (
              <g
                className="cursor-pointer"
                onClick={() => setSelectedNode(getNodeInfo("checkout-api"))}
              >
                <rect
                  x="200"
                  y="90"
                  width="140"
                  height="34"
                  fill={col.fill}
                  stroke={col.border}
                  strokeWidth="2"
                  filter="drop-shadow(3px 3px 0px #000)"
                />
                <text
                  x="270"
                  y="111"
                  fill={col.text}
                  fontSize="11"
                  fontWeight="900"
                  fontFamily="monospace"
                  textAnchor="middle"
                >
                  checkout-api
                </text>
              </g>
            );
          })()}

          {/* Node 3: payment-service */}
          {(() => {
            const col = getNodeColor("payment-service");
            return (
              <g
                className="cursor-pointer"
                onClick={() => setSelectedNode(getNodeInfo("payment-service"))}
              >
                <rect
                  x="20"
                  y="180"
                  width="115"
                  height="32"
                  fill={col.fill}
                  stroke={col.border}
                  strokeWidth="2"
                  filter="drop-shadow(2px 2px 0px #000)"
                />
                <text
                  x="77"
                  y="200"
                  fill={col.text}
                  fontSize="10"
                  fontWeight="900"
                  fontFamily="monospace"
                  textAnchor="middle"
                >
                  payment-svc
                </text>
              </g>
            );
          })()}

          {/* Node 4: inventory-service */}
          {(() => {
            const col = getNodeColor("inventory-service");
            return (
              <g
                className="cursor-pointer"
                onClick={() => setSelectedNode(getNodeInfo("inventory-service"))}
              >
                <rect
                  x="145"
                  y="180"
                  width="115"
                  height="32"
                  fill={col.fill}
                  stroke={col.border}
                  strokeWidth="2"
                  filter="drop-shadow(2px 2px 0px #000)"
                />
                <text
                  x="202"
                  y="200"
                  fill={col.text}
                  fontSize="10"
                  fontWeight="900"
                  fontFamily="monospace"
                  textAnchor="middle"
                >
                  inventory-svc
                </text>
              </g>
            );
          })()}

          {/* Node 5: orders-postgres-primary (Root suspect) */}
          {(() => {
            const col = getNodeColor("orders-postgres-primary");
            return (
              <g
                className="cursor-pointer"
                onClick={() => setSelectedNode(getNodeInfo("orders-postgres-primary"))}
              >
                <rect
                  x="270"
                  y="180"
                  width="145"
                  height="32"
                  fill={col.fill}
                  stroke={col.border}
                  strokeWidth="2"
                  filter="drop-shadow(2px 2px 0px #000)"
                />
                <text
                  x="342"
                  y="200"
                  fill={col.text}
                  fontSize="10"
                  fontWeight="900"
                  fontFamily="monospace"
                  textAnchor="middle"
                >
                  orders-postgres
                </text>
              </g>
            );
          })()}

          {/* Node 6: redis-cache */}
          {(() => {
            const col = getNodeColor("redis-cache");
            return (
              <g
                className="cursor-pointer"
                onClick={() => setSelectedNode(getNodeInfo("redis-cache"))}
              >
                <rect
                  x="425"
                  y="180"
                  width="105"
                  height="32"
                  fill={col.fill}
                  stroke={col.border}
                  strokeWidth="2"
                  filter="drop-shadow(2px 2px 0px #000)"
                />
                <text
                  x="477"
                  y="200"
                  fill={col.text}
                  fontSize="10"
                  fontWeight="900"
                  fontFamily="monospace"
                  textAnchor="middle"
                >
                  redis-cache
                </text>
              </g>
            );
          })()}
        </svg>
      </div>

      {/* Selected Node Details Bar */}
      {selectedNode && (
        <div className="mt-3 p-3 bg-[#09090B] border-2 border-black flex flex-wrap items-center justify-between gap-2 shadow-[2px_2px_0px_#000]">
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs font-black text-white uppercase">
                {selectedNode.service}
              </span>
              <span
                className={`font-mono text-[9px] font-black px-1.5 py-0.5 ${
                  selectedNode.impactLevel === "CRITICAL"
                    ? "bg-[#FF2E4C] text-white"
                    : selectedNode.impactLevel === "DEGRADED"
                    ? "bg-[#FFB800] text-black"
                    : "bg-zinc-700 text-zinc-300"
                }`}
              >
                {selectedNode.role} • {selectedNode.impactLevel}
              </span>
            </div>
            <div className="font-mono text-[10px] text-zinc-400 mt-1">
              Hop Distance: {selectedNode.hopDistance} | Traffic Loss:{" "}
              {selectedNode.trafficLossPct}%
            </div>
          </div>
          <button
            onClick={() => setSelectedNode(null)}
            className="text-zinc-500 hover:text-white font-mono text-xs font-black"
          >
            [CLOSE]
          </button>
        </div>
      )}

      {/* Modal: Raw Mermaid Source */}
      {showMermaidModal && (
        <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4">
          <div className="bg-[#141418] border-4 border-black p-5 max-w-xl w-full shadow-[8px_8px_0px_#00E5FF]">
            <div className="flex items-center justify-between border-b-2 border-zinc-800 pb-3 mb-4">
              <h3 className="font-mono text-sm font-black text-white uppercase tracking-wider">
                RAW MERMAID TOPOLOGY SPECIFICATION
              </h3>
              <button
                onClick={() => setShowMermaidModal(false)}
                className="px-2 py-1 bg-red-600 text-white font-mono text-xs font-black"
              >
                ✕
              </button>
            </div>
            <pre className="bg-[#09090B] p-4 border-2 border-zinc-800 text-[#CCFF00] font-mono text-xs overflow-x-auto whitespace-pre max-h-80">
              {mermaidDiagram ||
                `graph TD\n  api_gateway["api-gateway"] --> checkout_api["checkout-api"]\n  checkout_api --> orders_postgres["orders-postgres-primary"]\n  style orders_postgres fill:#FF2E4C,stroke:#000,stroke-width:2px`}
            </pre>
            <div className="mt-4 flex justify-end gap-2">
              <button
                onClick={copyMermaid}
                className="px-4 py-2 bg-[#00E5FF] hover:bg-[#33EAFF] text-black font-mono text-xs font-black uppercase border-2 border-black shadow-[3px_3px_0px_#000]"
              >
                {copied ? "COPIED TO CLIPBOARD!" : "COPY MERMAID CODE"}
              </button>
              <button
                onClick={() => setShowMermaidModal(false)}
                className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-white font-mono text-xs font-black uppercase border-2 border-black"
              >
                CLOSE
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
