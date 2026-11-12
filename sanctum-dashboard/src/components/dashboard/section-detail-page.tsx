"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { DetailPanel } from "@/components/dashboard/detail-panel";
import { DashboardShell } from "@/components/dashboard/dashboard-shell";
import { getSeverityTone, type DashboardSnapshot, type Entity, type Threat } from "@/lib/dashboard-data";

export function SectionDetailPage({
  snapshot,
  section,
}: {
  snapshot: DashboardSnapshot;
  section: "threats" | "entities" | "alerts";
}) {
  const [selectedThreatId, setSelectedThreatId] = useState(snapshot.threats[0]?.id ?? "");
  const [selectedEntityId, setSelectedEntityId] = useState(snapshot.entities[0]?.id ?? "");
  const [selectedAlertId, setSelectedAlertId] = useState(snapshot.alerts[0]?.id ?? "");

  const selectedThreat = useMemo(
    () => snapshot.threats.find((item) => item.id === selectedThreatId) ?? snapshot.threats[0],
    [selectedThreatId, snapshot],
  );

  const selectedEntity = useMemo(
    () => snapshot.entities.find((item) => item.id === selectedEntityId) ?? snapshot.entities[0],
    [selectedEntityId, snapshot],
  );

  const selectedAlert = useMemo(
    () => snapshot.alerts.find((item) => item.id === selectedAlertId) ?? snapshot.alerts[0],
    [selectedAlertId, snapshot],
  );

  const renderThreats = () => (
    <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
      <div className="space-y-4">
        {snapshot.threats.map((threat) => (
          <button
            key={threat.id}
            type="button"
            onClick={() => setSelectedThreatId(threat.id)}
            className={[
              "w-full rounded-2xl border bg-[#0d1b2b] p-4 text-left transition",
              selectedThreat?.id === threat.id
                ? "border-[#1de9b6]/40 bg-[#102739] shadow-[inset_0_0_0_1px_rgba(29,233,182,0.1)]"
                : "border-slate-800 hover:border-slate-700",
            ].join(" ")}
          >
            <div className="flex items-center justify-between gap-4">
              <div>
                <div className="text-[10px] uppercase tracking-[0.2em] text-slate-400">{threat.id}</div>
                <div className="mt-1 text-lg font-semibold text-white">{threat.title}</div>
              </div>
              <span className={`inline-flex rounded-full border px-2.5 py-1 text-[10px] uppercase tracking-[0.12em] ${getSeverityTone(threat.severity)}`}>
                {threat.severity}
              </span>
            </div>
            <div className="mt-3 flex items-center justify-between text-sm text-slate-300">
              <span>{threat.actor}</span>
              <span>{threat.status}</span>
            </div>
          </button>
        ))}
      </div>

      <DetailPanel item={selectedThreat} itemType="threat" />
    </div>
  );

  const renderEntities = () => (
    <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
      <div className="grid gap-4 md:grid-cols-2">
        {(snapshot.entities as Entity[]).map((entity) => (
          <button
            key={entity.id}
            type="button"
            onClick={() => setSelectedEntityId(entity.id)}
            className={[
              "rounded-2xl border bg-[#0d1b2b] p-5 text-left transition",
              selectedEntity?.id === entity.id
                ? "border-[#1de9b6]/40 bg-[#102739]"
                : "border-slate-800 hover:border-slate-700",
            ].join(" ")}
          >
            <div className="mb-3 flex items-center justify-between">
              <div>
                <div className="text-[10px] uppercase tracking-[0.2em] text-slate-400">{entity.type}</div>
                <div className="mt-1 text-lg font-semibold text-white">{entity.value}</div>
              </div>
              <span className={`inline-flex rounded-full border px-2.5 py-1 text-[10px] uppercase tracking-[0.12em] ${getSeverityTone(entity.risk)}`}>
                {entity.risk}
              </span>
            </div>
            <div className="text-sm text-slate-300">{entity.status}</div>
          </button>
        ))}
      </div>

      <DetailPanel item={selectedEntity} itemType="entity" />
    </div>
  );

  const renderAlerts = () => (
    <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
      <div className="space-y-4">
        {snapshot.alerts.map((alert) => (
          <button
            key={alert.id}
            type="button"
            onClick={() => setSelectedAlertId(alert.id)}
            className={[
              "w-full rounded-2xl border bg-[#0d1b2b] p-4 text-left transition",
              selectedAlert?.id === alert.id
                ? "border-[#1de9b6]/40 bg-[#102739]"
                : "border-slate-800 hover:border-slate-700",
            ].join(" ")}
          >
            <div className="flex items-center justify-between gap-4">
              <div>
                <div className="text-[10px] uppercase tracking-[0.2em] text-slate-400">{alert.id}</div>
                <div className="mt-1 text-lg font-semibold text-white">{alert.title}</div>
              </div>
              <span className={`inline-flex rounded-full border px-2.5 py-1 text-[10px] uppercase tracking-[0.12em] ${getSeverityTone(alert.severity)}`}>
                {alert.severity}
              </span>
            </div>
            <div className="mt-3 text-sm text-slate-300">{alert.category}</div>
          </button>
        ))}
      </div>

      <DetailPanel item={selectedAlert} itemType="alert" />
    </div>
  );

  return (
    <DashboardShell section={section}>
      <div className="rounded-2xl border border-slate-800 bg-[#0d1b2b] p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="text-[10px] uppercase tracking-[0.2em] text-slate-400">OpenCTI style</div>
            <h2 className="mt-1 text-xl font-semibold text-white">Detailed intelligence view</h2>
          </div>
          <Link href="/" className="rounded-full border border-[#1de9b6]/30 bg-[#113d35] px-4 py-2 text-sm font-medium text-[#8feccc] hover:bg-[#174c42]">
            Back to overview
          </Link>
        </div>
      </div>

      {section === "threats" && renderThreats()}
      {section === "entities" && renderEntities()}
      {section === "alerts" && renderAlerts()}
    </DashboardShell>
  );
}
