"use client";

import React from "react";

interface NodeData {
  id: string;
  kind: string;
  label: string;
  provider: string;
  chain: string;
  block_hash: string;
  block_height: number;
  observed_at: string;
  confidence: string;
  provider_rating?: string;
  report_reference?: string;
  value_atomic?: string;
  unit?: string;
}

interface EdgeData {
  provider: string;
  target: string;
  relation: string;
  source: string;
  observed_at: string;
  confidence: string;
  provider_rating?: string;
  category?: string;
  report_reference?: string;
  report_sha256?: string;
  assessed_at?: string;
  value_atomic?: string;
  unit?: string;
}

interface AttackGraphProps {
  data?: {
    chain: string;
    block_hash: string;
    block_height: number;
    source: string;
    observed_at: string;
    nodes: NodeData[];
    edges: EdgeData[];
    limitations: string[];
  };
}

export default function AttackGraphVisualizer({ data }: AttackGraphProps) {
  const nodes = data?.nodes ?? [];
  const edges = data?.edges ?? [];

  return (
    <div className="bg-slate-900 border border-slate-800 p-6 rounded-lg font-mono">
      <h3 className="text-xs text-slate-400 uppercase tracking-wider mb-4 flex items-center justify-between">
        <span>On-chain transaction graph · {data?.chain ?? "no source selected"}</span>
        <span className="text-cyan-400 text-[10px] bg-cyan-950/50 px-2 py-0.5 rounded border border-cyan-800">
          {nodes.length} Nodes / {edges.length} Edges
        </span>
      </h3>

      {nodes.length === 0 ? (
        <p className="mb-4 rounded border border-slate-800 bg-slate-950 p-4 text-xs text-slate-500">
          No graph loaded. Select a case, chain, and block to query an operator-configured read-only RPC node.
        </p>
      ) : (
        <>
          <div className="mb-3 rounded border border-slate-800 bg-slate-950 p-3 text-[11px] text-slate-400">
            Block <span className="text-slate-200">{data?.block_height}</span>
            {" · "}<span className="break-all text-slate-300">{data?.block_hash}</span>
            {" · "}source <span className="text-cyan-300">{data?.source}</span>
            {" · "}observed {data?.observed_at}
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            <section className="max-h-96 space-y-2 overflow-y-auto" aria-label="Graph nodes">
              <h4 className="font-semibold text-slate-300">Nodes</h4>
              {nodes.map((node) => (
                <div key={node.id} className="rounded border border-slate-800 bg-slate-950 p-3 text-xs">
                  <div className="font-bold text-cyan-200">{node.label}</div>
                  <div className="mt-1 text-[10px] text-slate-400">
                    {node.kind} · {node.chain}
                    {node.provider_rating ? ` · provider rating: ${node.provider_rating}` : ""}
                    {node.value_atomic !== undefined && node.unit
                      ? ` · ${node.value_atomic} ${node.unit}`
                      : ""}
                  </div>
                  <div className="mt-1 break-all text-[10px] text-slate-500">
                    {node.provider} · block {node.block_height} · {node.confidence} · {node.observed_at}
                  </div>
                  {node.report_reference && (
                    <div className="mt-1 break-all text-[10px] text-amber-300">
                      {node.report_reference}
                    </div>
                  )}
                </div>
              ))}
            </section>
            <section className="max-h-96 space-y-2 overflow-y-auto" aria-label="Graph relationships">
              <h4 className="font-semibold text-slate-300">Observed relationships</h4>
              {edges.map((edge, index) => (
                <div key={`${edge.source}-${edge.target}-${edge.relation}-${index}`} className="rounded border border-slate-800 bg-slate-950 p-3 text-[11px]">
                  <div className="break-all">
                    <span className="text-cyan-300">{edge.source}</span>
                    <span className="px-2 font-bold text-rose-300">{edge.relation}</span>
                    <span className="text-indigo-300">{edge.target}</span>
                  </div>
                  {edge.value_atomic !== undefined && edge.unit && (
                    <div className="mt-1 text-slate-300">{edge.value_atomic} {edge.unit}</div>
                  )}
                  {edge.provider_rating && (
                    <div className="mt-1 text-amber-200">
                      {edge.provider_rating} · {edge.category}
                    </div>
                  )}
                  <div className="mt-1 text-[10px] text-slate-500">
                    {edge.provider} · {edge.confidence} · {edge.observed_at}
                  </div>
                </div>
              ))}
            </section>
          </div>
          <ul className="mt-4 list-disc space-y-1 pl-5 text-[10px] text-amber-200">
            {data?.limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}
          </ul>
        </>
      )}
    </div>
  );
}