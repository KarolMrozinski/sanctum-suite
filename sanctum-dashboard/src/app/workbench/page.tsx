"use client";

import { useEffect, useState } from "react";
import AttackGraphVisualizer from "@/components/AttackGraph3D";

interface IncidentEvent {
  event?: string;
  source?: string;
  severity?: string;
  details?: string;
}

export default function WorkbenchPage() {
  const [incidents, setIncidents] = useState<IncidentEvent[]>([]);
  const [status, setStatus] = useState("CONNECTING");

  useEffect(() => {
    const configuredUrl = process.env.NEXT_PUBLIC_SANCTUM_WS_URL;
    const url = configuredUrl ?? `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.hostname}:8000/ws/incidents`;
    let socket: WebSocket;

    try {
      socket = new WebSocket(url);
    } catch {
      const errorTimer = window.setTimeout(() => setStatus("INVALID CONFIGURATION"), 0);
      return () => window.clearTimeout(errorTimer);
    }

    socket.onopen = () => setStatus("CONNECTED");
    socket.onclose = () => setStatus("DISCONNECTED");
    socket.onerror = () => setStatus("CONNECTION ERROR");
    socket.onmessage = (event: MessageEvent<string>) => {
      try {
        const data: unknown = JSON.parse(event.data);
        if (!data || typeof data !== "object") return;
        const incident = data as IncidentEvent;
        if (typeof incident.event !== "string" || typeof incident.source !== "string") return;
        setIncidents((previous) => [incident, ...previous].slice(0, 10));
      } catch {
        setStatus("INVALID EVENT");
      }
    };

    return () => socket.close();
  }, []);

  const connected = status === "CONNECTED";

  return (
    <main className="min-h-screen bg-slate-950 p-6 font-mono text-slate-100 md:p-8">
      <header className="mb-8 flex items-center justify-between border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-2xl font-bold text-cyan-400">SANCTUM-SUITE SOC Workbench</h1>
          <p className="text-xs text-slate-400">Operational dashboard preview</p>
        </div>
        <div className="flex items-center gap-2" role="status" aria-live="polite">
          <span className={`h-3 w-3 rounded-full ${connected ? "animate-pulse bg-emerald-500" : "bg-rose-500"}`} />
          <span className="text-xs font-semibold">{status}</span>
        </div>
      </header>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
        {[
          ["Overall Score", "No live score configured"],
          ["Guardrails", "View module configuration"],
          ["MITRE Mapping", "Based on available events"],
        ].map(([label, value]) => (
          <section key={label} className="rounded-lg border border-slate-800 bg-slate-900 p-6">
            <h2 className="text-xs uppercase tracking-wider text-slate-400">{label}</h2>
            <p className="mt-3 text-lg font-bold text-cyan-300">{value}</p>
          </section>
        ))}
        <section className="md:col-span-3">
          <AttackGraphVisualizer />
          <p className="mt-2 text-xs text-slate-500">No live graph integration is configured by default.</p>
        </section>
        <section className="mt-4 rounded-lg border border-slate-800 bg-slate-900 p-6 md:col-span-3">
          <h2 className="mb-4 text-sm font-semibold text-slate-300">Live incident stream</h2>
          <div className="max-h-72 space-y-2 overflow-y-auto">
            {incidents.length === 0 ? (
              <p className="text-xs text-slate-500">No incident events received. Check the API WebSocket endpoint and connection status.</p>
            ) : incidents.map((item, index) => (
              <div key={`${item.source}-${item.event}-${index}`} className="flex flex-wrap items-center justify-between gap-3 rounded border border-slate-800 bg-slate-950 p-3 text-xs">
                <span className="font-bold text-rose-300">[{item.severity ?? "UNKNOWN"}] {item.event}</span>
                <span className="text-slate-400">{item.details ?? ""}</span>
                <span className="text-cyan-400">{item.source}</span>
              </div>
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}
