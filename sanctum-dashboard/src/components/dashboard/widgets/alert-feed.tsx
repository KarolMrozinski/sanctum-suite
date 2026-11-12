import type { Alert } from "@/lib/dashboard-data";

export function AlertFeed({ alerts }: { alerts: Alert[] }) {
  return (
    <section className="rounded-2xl border border-slate-800 bg-[#0d1b2b] p-5">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <div className="text-[10px] uppercase tracking-[0.2em] text-slate-400">Alert feed</div>
          <h3 className="mt-1 text-xl font-semibold text-white">Latest detections</h3>
        </div>
        <span className="rounded-full border border-slate-700 bg-slate-900/80 px-2.5 py-1 text-[10px] uppercase tracking-[0.12em] text-slate-300">
          {alerts.length} active
        </span>
      </div>

      <div className="space-y-3">
        {alerts.map((alert) => (
          <div key={alert.id} className="rounded-xl border border-slate-800 bg-[#0f2237] p-3">
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="text-sm font-medium text-white">{alert.title}</div>
                <div className="mt-1 text-xs text-slate-400">{alert.category}</div>
              </div>
              <span className="rounded-full border border-[#ff6b6b]/30 bg-[#2f1e2a] px-2 py-1 text-[10px] uppercase tracking-[0.12em] text-[#ff9aa2]">
                {alert.severity}
              </span>
            </div>
            <p className="mt-2 text-sm text-slate-300">{alert.description}</p>
            <div className="mt-3 flex items-center justify-between text-[10px] uppercase tracking-[0.12em] text-slate-400">
              <span>{alert.status}</span>
              <span>{alert.timestamp}</span>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
