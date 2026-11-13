import { getSeverityTone, type Threat } from "@/lib/dashboard-data";

export function ThreatDetail({ threat }: { threat: Threat }) {
  return (
    <aside className="rounded-2xl border border-slate-800 bg-[#0d1b2b] p-5">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <div className="text-[10px] uppercase tracking-[0.2em] text-slate-400">Threat detail</div>
          <h3 className="mt-1 text-xl font-semibold text-white">{threat.title}</h3>
        </div>
        <span className={`inline-flex rounded-full border px-2.5 py-1 text-[10px] uppercase tracking-[0.12em] ${getSeverityTone(threat.severity)}`}>
          {threat.severity}
        </span>
      </div>

      <div className="space-y-3 text-sm text-slate-300">
        <div className="flex justify-between"><span className="text-slate-400">Threat ID</span><span>{threat.id}</span></div>
        <div className="flex justify-between"><span className="text-slate-400">Actor</span><span>{threat.actor}</span></div>
        <div className="flex justify-between"><span className="text-slate-400">Source</span><span>{threat.source}</span></div>
        <div className="flex justify-between"><span className="text-slate-400">Status</span><span>{threat.status}</span></div>
        <div className="flex justify-between"><span className="text-slate-400">Confidence</span><span>{threat.confidence}%</span></div>
      </div>

      <p className="mt-5 text-sm leading-6 text-slate-300">{threat.description}</p>

      <div className="mt-5 rounded-xl border border-slate-800 bg-[#0f2237] p-4">
        <div className="text-[10px] uppercase tracking-[0.18em] text-slate-400">Relations</div>
        <div className="mt-3 flex flex-wrap gap-2 text-[10px] uppercase tracking-[0.12em] text-slate-300">
          {threat.relations.map((relation) => (
            <span key={relation} className="rounded-full border border-slate-700 bg-slate-950/80 px-2 py-1">
              {relation}
            </span>
          ))}
        </div>
      </div>
    </aside>
  );
}
