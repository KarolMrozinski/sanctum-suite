"use client";

import { useEffect, useState } from "react";
import AttackGraphVisualizer from "@/components/AttackGraph3D";

interface IncidentEvent {
  event: string;
  source: string;
  severity?: string;
  details?: string;
}

interface IncidentTimelineEntry {
  event_id: string;
  event_type: string;
  source: string | null;
  observed_at: string | null;
  reported_severity: string | null;
}

interface CorrelatedIncident {
  correlation_id: string;
  event_count: number;
  priority: string;
  priority_reasons: string[];
  timeline: IncidentTimelineEntry[];
}

type WorkbenchIncident = IncidentEvent | CorrelatedIncident;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isCorrelatedIncident(value: unknown): value is CorrelatedIncident {
  if (!isRecord(value)) return false;
  return (
    typeof value.correlation_id === "string" &&
    typeof value.event_count === "number" &&
    typeof value.priority === "string" &&
    Array.isArray(value.priority_reasons) &&
    value.priority_reasons.every((reason) => typeof reason === "string") &&
    Array.isArray(value.timeline) &&
    value.timeline.every(
      (entry) =>
        isRecord(entry) &&
        typeof entry.event_id === "string" &&
        typeof entry.event_type === "string" &&
        (typeof entry.source === "string" || entry.source === null) &&
        (typeof entry.observed_at === "string" || entry.observed_at === null) &&
        (typeof entry.reported_severity === "string" || entry.reported_severity === null),
    )
  );
}

export default function WorkbenchPage() {
  const [incidents, setIncidents] = useState<WorkbenchIncident[]>([]);
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
        if (!isRecord(data)) return;
        let incident: WorkbenchIncident;
        if (isCorrelatedIncident(data)) {
          incident = data;
        } else if (typeof data.event === "string" && typeof data.source === "string") {
          incident = {
            event: data.event,
            source: data.source,
            severity: typeof data.severity === "string" ? data.severity : undefined,
            details: typeof data.details === "string" ? data.details : undefined,
          };
        } else {
          return;
        }
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
            ) : incidents.map((item, index) => "timeline" in item ? (
              <article key={`${item.correlation_id}-${index}`} className="rounded border border-slate-800 bg-slate-950 p-4 text-xs">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <h3 className="font-bold text-cyan-300">Correlated incident · {item.correlation_id}</h3>
                  <span className="font-semibold text-amber-300">Reported priority: {item.priority}</span>
                </div>
                <ul className="mt-3 space-y-1 text-slate-400">
                  {item.priority_reasons.map((reason) => <li key={reason}>• {reason}</li>)}
                </ul>
                <ol className="mt-4 space-y-2 border-l border-slate-700 pl-4">
                  {item.timeline.map((entry) => (
                    <li key={entry.event_id} className="relative">
                      <span className="font-semibold text-slate-200">{entry.event_type}</span>
                      <span className="ml-2 text-slate-500">{entry.observed_at ?? "Time not provided"}</span>
                      <div className="mt-1 text-slate-400">
                        {entry.source ?? "Source not provided"} · {entry.reported_severity ?? "Severity not reported"}
                      </div>
                    </li>
                  ))}
                </ol>
              </article>
            ) : (
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
