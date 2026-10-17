"use client";

import React from "react";

interface NodeData {
  id: string;
  type: string;
  severity?: string;
  service?: string;
}

interface EdgeData {
  source: string;
  target: string;
  relation: string;
}

interface AttackGraphProps {
  data?: {
    nodes: NodeData[];
    edges: EdgeData[];
  };
}

export default function AttackGraphVisualizer({ data }: AttackGraphProps) {
  const nodes = data?.nodes || [
    { id: "enterprise-core.com", type: "TARGET_HOST" },
    { id: "Port:11434", type: "OPEN_PORT", service: "Ollama LLM API" },
    { id: "Vuln:PROMPT_INJECTION_RISK", type: "VULNERABILITY", severity: "HIGH" },
  ];

  const edges = data?.edges || [
    { source: "enterprise-core.com", target: "Port:11434", relation: "EXPOSES" },
    { source: "Port:11434", target: "Vuln:PROMPT_INJECTION_RISK", relation: "EXPLOITS" },
  ];

  return (
    <div className="bg-slate-900 border border-slate-800 p-6 rounded-lg font-mono">
      <h3 className="text-xs text-slate-400 uppercase tracking-wider mb-4 flex items-center justify-between">
        <span>🕸️ Attack Graph Topology (NetworkX Engine)</span>
        <span className="text-cyan-400 text-[10px] bg-cyan-950/50 px-2 py-0.5 rounded border border-cyan-800">
          {nodes.length} Nodes / {edges.length} Edges
        </span>
      </h3>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
        {nodes.map((node, idx) => (
          <div
            key={idx}
            className={`p-3 rounded border text-xs ${
              node.type === "TARGET_HOST"
                ? "bg-slate-950 border-cyan-500/50 text-cyan-300"
                : node.type === "OPEN_PORT"
                ? "bg-slate-950 border-indigo-500/50 text-indigo-300"
                : "bg-slate-950 border-rose-500/50 text-rose-300 animate-pulse"
            }`}
          >
            <div className="font-bold">{node.id}</div>
            <div className="text-[10px] text-slate-400 mt-1">Type: {node.type}</div>
            {node.service && <div className="text-[10px] text-slate-500">Service: {node.service}</div>}
            {node.severity && <div className="text-[10px] text-rose-400 font-semibold">Severity: {node.severity}</div>}
          </div>
        ))}
      </div>

      <div className="bg-slate-950 p-3 rounded border border-slate-800 text-[11px] space-y-1">
        <div className="text-slate-400 font-semibold mb-1">Detected Attack Vector Edges:</div>
        {edges.map((edge, idx) => (
          <div key={idx} className="flex items-center space-x-2 text-slate-300">
            <span className="text-cyan-400">{edge.source}</span>
            <span className="text-rose-400 font-bold">───[{edge.relation}]───►</span>
            <span className="text-indigo-400">{edge.target}</span>
          </div>
        ))}
      </div>
    </div>
  );
}