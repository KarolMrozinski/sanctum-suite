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
    <div className="panel-surface rounded-2xl p-4">
      <div className="mb-3 flex items-center justify-between">
        <div>
          <div className="section-kicker">Filter view</div>
          <div className="mt-1 text-lg font-semibold text-white">Operational filters</div>
        </div>
        <div className="status-pill rounded-full px-2.5 py-1 text-[10px] uppercase tracking-[0.18em]">
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
              "rounded-full border px-3 py-1.5 text-xs font-medium transition-all",
              activeFilter === filter.value
                ? "border-[#6ee7b7]/25 bg-[#11221f] text-[#a7f3d0] shadow-[0_0_0_1px_rgba(110,231,183,0.08)]"
                : "border-slate-700 bg-[#0d1217] text-slate-300 hover:border-slate-600 hover:text-white",
            ].join(" ")}
          >
            {filter.label}
          </button>
        ))}
      </div>
    </div>
  );
}
