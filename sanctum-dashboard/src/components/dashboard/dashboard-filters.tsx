"use client";

import { useState } from "react";

const filters = [
  { label: "All", value: "all" },
  { label: "Critical", value: "critical" },
  { label: "High", value: "high" },
  { label: "Monitoring", value: "monitoring" },
  { label: "Investigations", value: "investigations" },
];

export function DashboardFilters() {
  const [activeFilter, setActiveFilter] = useState("all");

  return (
    <div className="rounded-2xl border border-slate-800 bg-[#0d1b2b] p-4">
      <div className="mb-3 flex items-center justify-between">
        <div>
          <div className="text-[10px] uppercase tracking-[0.2em] text-slate-400">Filter view</div>
          <div className="mt-1 text-lg font-semibold text-white">Operational filters</div>
        </div>
        <div className="rounded-full border border-slate-700 bg-slate-900/80 px-2.5 py-1 text-[10px] uppercase tracking-[0.18em] text-slate-300">
          Live
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        {filters.map((filter) => (
          <button
            key={filter.value}
            type="button"
            onClick={() => setActiveFilter(filter.value)}
            className={[
              "rounded-full border px-3 py-1.5 text-xs font-medium transition",
              activeFilter === filter.value
                ? "border-[#1de9b6]/30 bg-[#113d35] text-[#8feccc]"
                : "border-slate-700 bg-slate-950/60 text-slate-300 hover:border-slate-600 hover:text-white",
            ].join(" ")}
          >
            {filter.label}
          </button>
        ))}
      </div>
    </div>
  );
}
