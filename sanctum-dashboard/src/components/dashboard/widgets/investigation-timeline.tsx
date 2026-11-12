import type { Investigation } from "@/lib/dashboard-data";

export function InvestigationTimeline({ investigation }: { investigation: Investigation }) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-[#0d1b2b] p-5">
      <div className="mb-5 flex items-center justify-between">
        <div>
          <div className="text-[10px] uppercase tracking-[0.2em] text-slate-400">Investigation</div>
          <h3 className="mt-1 text-xl font-semibold text-white">{investigation.name}</h3>
        </div>
        <span className="rounded-full border border-slate-700 bg-slate-900/80 px-2.5 py-1 text-[10px] uppercase tracking-[0.12em] text-slate-200">
          {investigation.status}
        </span>
      </div>

      <div className="space-y-4">
        {investigation.timeline.map((event) => (
          <div key={event.id} className="flex gap-3">
            <div className="mt-1 flex flex-col items-center">
              <span className="block h-2.5 w-2.5 rounded-full bg-[#1de9b6]" />
              <span className="mt-2 block h-full w-px bg-slate-700" />
            </div>
            <div className="flex-1 rounded-xl border border-slate-800 bg-[#0f2237] p-3">
              <div className="flex items-center justify-between gap-3 text-xs uppercase tracking-[0.12em] text-slate-400">
                <span>{event.type}</span>
                <span>{event.time}</span>
              </div>
              <p className="mt-2 text-sm text-slate-200">{event.description}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
