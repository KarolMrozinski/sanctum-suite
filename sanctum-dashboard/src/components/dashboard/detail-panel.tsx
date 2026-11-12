"use client";

import { useMemo } from "react";
import { getSeverityTone, type Alert, type Entity, type Threat } from "@/lib/dashboard-data";

export function DetailPanel({
  item,
  itemType,
}: {
  item: Threat | Entity | Alert;
  itemType: "threat" | "entity" | "alert";
}) {
  const meta = useMemo(() => {
    if (itemType === "threat") {
      const threat = item as Threat;
      return {
        title: threat.title,
        subtitle: "Threat detail",
        status: threat.status,
        severity: threat.severity,
        summary: threat.description,
        chips: threat.indicators,
        rows: [
          ["Actor", threat.actor],
          ["Source", threat.source],
          ["Confidence", `${threat.confidence}%`],
          ["Related entities", threat.relatedEntities.join(", ")],
        ],
      };
    }

    if (itemType === "entity") {
      const entity = item as Entity;
      return {
        title: entity.value,
        subtitle: entity.type,
        status: entity.status,
        severity: entity.risk,
        summary: entity.description,
        chips: entity.tags,
        rows: [
          ["Entity ID", entity.id],
          ["First seen", entity.firstSeen],
          ["Confidence", `${entity.confidence}%`],
          ["Relationships", entity.relationships.map((r) => `${r.type}: ${r.value}`).join(" | ")],
        ],
      };
    }

    const alert = item as Alert;
    return {
      title: alert.title,
      subtitle: "Alert",
      status: alert.status,
      severity: alert.severity,
      summary: alert.description,
      chips: [alert.category, alert.source],
      rows: [
        ["Alert ID", alert.id],
        ["Observed", alert.observed],
        ["Related entity", alert.relatedEntity],
        ["Timestamp", alert.timestamp],
      ],
    };
  }, [item, itemType]);

  return (
    <aside className="rounded-2xl border border-slate-800 bg-[#0d1b2b] p-5 shadow-[0_0_0_1px_rgba(148,163,184,0.06)]">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <div className="text-[10px] uppercase tracking-[0.22em] text-slate-400">{meta.subtitle}</div>
          <h3 className="mt-1 text-xl font-semibold text-white">{meta.title}</h3>
        </div>
        <span className={`inline-flex rounded-full border px-2.5 py-1 text-[10px] uppercase tracking-[0.12em] ${getSeverityTone(meta.severity)}`}>
          {meta.severity}
        </span>
      </div>

      <div className="mb-4 flex items-center justify-between">
        <span className="text-xs uppercase tracking-[0.14em] text-slate-400">Status</span>
        <span className="text-sm text-[#8feccc]">{meta.status}</span>
      </div>

      <p className="text-sm leading-6 text-slate-300">{meta.summary}</p>

      <div className="mt-5 flex flex-wrap gap-2">
        {meta.chips.map((chip) => (
          <span key={chip} className="rounded-full border border-slate-700 bg-slate-900/80 px-2 py-1 text-[10px] uppercase tracking-[0.12em] text-slate-200">
            {chip}
          </span>
        ))}
      </div>

      <div className="mt-6 space-y-3 border-t border-slate-800 pt-4">
        {meta.rows.map(([label, value]) => (
          <div key={label} className="flex items-start justify-between gap-4 text-sm">
            <span className="text-slate-400">{label}</span>
            <span className="text-right text-slate-200">{value}</span>
          </div>
        ))}
      </div>
    </aside>
  );
}
