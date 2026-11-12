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
        timeline: threat.timeline,
        relationList: threat.relations,
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
        timeline: [],
        relationList: entity.relationships.map((r) => `${r.type} • ${r.value}`),
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
      timeline: [],
      relationList: [alert.relatedEntity, alert.category, alert.source],
    };
  }, [item, itemType]);

  return (
    <aside className="panel-surface rounded-2xl p-5 shadow-[0_0_0_1px_rgba(148,163,184,0.06)]">
      <div className="mb-5 flex items-center justify-between gap-3">
        <div>
          <div className="text-[10px] uppercase tracking-[0.22em] text-slate-400">{meta.subtitle}</div>
          <h3 className="mt-1 text-xl font-semibold text-white">{meta.title}</h3>
        </div>
        <span className={`inline-flex rounded-full border px-2.5 py-1 text-[10px] uppercase tracking-[0.12em] ${getSeverityTone(meta.severity)}`}>
          {meta.severity}
        </span>
      </div>

      <div className="mb-5 flex items-center justify-between rounded-xl border border-slate-800 bg-[#0b1219] px-3 py-2">
        <span className="text-[10px] uppercase tracking-[0.14em] text-slate-400">Status</span>
        <span className="text-sm font-medium text-[#8feccc]">{meta.status}</span>
      </div>

      <div className="mb-5 overflow-hidden rounded-xl border border-slate-800 bg-[#0b1219] p-3">
        <div className="mb-2 flex items-center justify-between text-[10px] uppercase tracking-[0.18em] text-slate-400">
          <span>Confidence</span>
          <span>{itemType === "threat" ? (item as Threat).confidence : itemType === "entity" ? (item as Entity).confidence : 86}%</span>
        </div>
        <div className="h-2 overflow-hidden rounded-full bg-slate-800">
          <div
            className="h-full rounded-full bg-gradient-to-r from-[#6ee7b7] via-[#82d7ff] to-[#bcd3ff]"
            style={{ width: `${itemType === "threat" ? (item as Threat).confidence : itemType === "entity" ? (item as Entity).confidence : 86}%` }}
          />
        </div>
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

      {meta.relationList.length > 0 && (
        <div className="mt-6 rounded-2xl border border-slate-800 bg-[#0a1117] p-4">
          <div className="mb-3 text-[10px] uppercase tracking-[0.18em] text-slate-400">Relations</div>
          <div className="flex flex-wrap gap-2">
            {meta.relationList.map((relation) => (
              <span key={relation} className="rounded-full border border-[#7ef7d3]/20 bg-[#0f201d] px-2.5 py-1 text-[10px] uppercase tracking-[0.12em] text-[#aaf7e2]">
                {relation}
              </span>
            ))}
          </div>
        </div>
      )}

      {meta.timeline.length > 0 && (
        <div className="mt-6 rounded-2xl border border-slate-800 bg-[#0a1117] p-4">
          <div className="mb-3 text-[10px] uppercase tracking-[0.18em] text-slate-400">Timeline</div>
          <div className="space-y-3">
            {meta.timeline.map((event) => (
              <div key={event.id} className="flex gap-3 border-l border-slate-700 pl-3">
                <div className="mt-1 h-2.5 w-2.5 rounded-full bg-[#7ef7d3] shadow-[0_0_12px_rgba(126,247,211,0.7)]" />
                <div className="flex-1">
                  <div className="flex items-center justify-between gap-3 text-xs uppercase tracking-[0.12em] text-slate-400">
                    <span>{event.title}</span>
                    <span>{event.time}</span>
                  </div>
                  <div className="mt-1 text-sm text-slate-300">{event.detail}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </aside>
  );
}
