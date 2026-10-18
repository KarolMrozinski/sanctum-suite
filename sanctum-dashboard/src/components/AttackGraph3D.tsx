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
  const nodes = data?.nodes ?? [];
  const edges = data?.edges ?? [];

  return (
    <div className="bg-slate-900 border border-slate-800 p-6 rounded-lg font-mono">
      <h3 className="text-xs text-slate-400 uppercase tracking-wider mb-4 flex items-center justify-between">
        <span>🕸️ Attack Graph Topology (NetworkX Engine)</span>
        <span className="text-cyan-400 text-[10px] bg-cyan-950/50 px-2 py-0.5 rounded border border-cyan-800">
          {nodes.length} Nodes / {edges.length} Edges
        </span>
      </h3>

      {nodes.length === 0 ? (
        <p className="mb-4 rounded border border-slate-800 bg-slate-950 p-4 text-xs text-slate-500">
          No attack graph data is connected. Graph details will appear here when supplied by an authorized data source.
        </p>
      ) : (
        <div className="mb-4 grid grid-cols-1 gap-4 md:grid-cols-3">
          {nodes.map((node) => (
            <div
              key={node.id}
              className={`rounded border p-3 text-xs ${
                node.type === "TARGET_HOST"
                  ? "border-cyan-500/50 bg-slate-950 text-cyan-300"
                  : node.type === "OPEN_PORT"
                    ? "border-indigo-500/50 bg-slate-950 text-indigo-300"
                    : "border-rose-500/50 bg-slate-950 text-rose-300"
              }`}
            >
              <div className="font-bold">{node.id}</div>
              <div className="mt-1 text-[10px] text-slate-400">Type: {node.type}</div>
              {node.service && <div className="text-[10px] text-slate-500">Service: {node.service}</div>}
              {node.severity && <div className="text-[10px] font-semibold text-rose-400">Severity: {node.severity}</div>}
            </div>
          ))}
        </div>
      )}

      <div className="bg-slate-950 p-3 rounded border border-slate-800 text-[11px] space-y-1">
        <div className="mb-1 font-semibold text-slate-400">Attack graph relationships:</div>
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