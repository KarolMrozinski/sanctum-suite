"use client";

import React, { useState, useEffect } from "react";
import AttackGraphVisualizer from "@/components/AttackGraph3D";

interface IncidentEvent {
  event: string;
  source: string;
  severity: string;
  details: string;
}

export default function SanctumDashboard() {
  const [incidents, setIncidents] = useState<IncidentEvent[]>([]);
  const [status, setStatus] = useState<string>("CONNECTING");

  useEffect(() => {
    const ws = new WebSocket("ws://127.0.0.1:8000/ws/incidents");

    ws.onopen = () => setStatus("CONNECTED");
    ws.onclose = () => setStatus("DISCONNECTED");
    ws.onmessage = (event) => {
      const data: IncidentEvent = JSON.parse(event.data);
      setIncidents((prev) => [data, ...prev.slice(0, 9)]);
    };

    return () => ws.close();
  }, []);

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 p-8 font-mono">
      {/* Header */}
      <header className="flex justify-between items-center border-b border-slate-800 pb-4 mb-8">
        <div>
          <h1 className="text-2xl font-bold text-cyan-400">🏛️ SANCTUM-SUITE SOC Workbench</h1>
          <p className="text-xs text-slate-400">Enterprise Cyber Resilience & AI Safety Platform</p>
        </div>
        <div className="flex items-center space-x-2">
          <span className={`h-3 w-3 rounded-full ${status === "CONNECTED" ? "bg-emerald-500 animate-pulse" : "bg-rose-500"}`} />
          <span className="text-xs font-semibold">{status}</span>
        </div>
      </header>

      {/* Grid Layout */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Metric Cards */}
        <div className="bg-slate-900 border border-slate-800 p-6 rounded-lg">
          <h3 className="text-xs text-slate-400 uppercase tracking-wider">Overall Score</h3>
          <p className="text-4xl font-extrabold text-cyan-400 mt-2">87.5 / 100</p>
          <span className="inline-block mt-3 text-xs text-emerald-400 bg-emerald-950/50 px-2 py-1 rounded border border-emerald-800">OPTIMAL</span>
        </div>

        <div className="bg-slate-900 border border-slate-800 p-6 rounded-lg">
          <h3 className="text-xs text-slate-400 uppercase tracking-wider">Active Guardrails</h3>
          <p className="text-4xl font-extrabold text-indigo-400 mt-2">ENABLED</p>
          <span className="inline-block mt-3 text-xs text-indigo-400 bg-indigo-950/50 px-2 py-1 rounded border border-indigo-800">LLM Proxy Active</span>
        </div>

        <div className="bg-slate-900 border border-slate-800 p-6 rounded-lg">
          <h3 className="text-xs text-slate-400 uppercase tracking-wider">MITRE ATT&CK Mapping</h3>
          <p className="text-4xl font-extrabold text-rose-400 mt-2">2 Tactics</p>
          <span className="inline-block mt-3 text-xs text-rose-400 bg-rose-950/50 px-2 py-1 rounded border border-rose-800">AML.T0051 / T1190</span>
        </div>

        <div className="md:col-span-3 mt-4">
          <AttackGraphVisualizer />
        </div>

        {/* Live Event Stream */}
        <div className="md:col-span-3 bg-slate-900 border border-slate-800 p-6 rounded-lg mt-4">
          <h2 className="text-sm font-semibold text-slate-300 mb-4 flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-cyan-400 animate-ping" />
            Live WebSockets Event Stream (GHOST-COMM Telemetry)
          </h2>
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {incidents.length === 0 ? (
              <p className="text-xs text-slate-500">Waiting for live security events...</p>
            ) : (
              incidents.map((item, idx) => (
                <div key={idx} className="flex justify-between items-center text-xs p-3 bg-slate-950 rounded border border-slate-800">
                  <span className="text-rose-400 font-bold">[{item.severity}] {item.event}</span>
                  <span className="text-slate-400">{item.details}</span>
                  <span className="text-cyan-500">{item.source}</span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </main>
  );
}