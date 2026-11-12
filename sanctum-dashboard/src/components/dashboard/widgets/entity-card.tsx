import { getSeverityTone, type Entity } from "@/lib/dashboard-data";

export function EntityCard({ entity }: { entity: Entity }) {
  return (
    <article className="rounded-2xl border border-slate-800 bg-[#0d1b2b] p-5">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <div className="text-[10px] uppercase tracking-[0.2em] text-slate-400">{entity.type}</div>
          <h3 className="mt-1 text-xl font-semibold text-white">{entity.value}</h3>
        </div>
        <span className={`inline-flex rounded-full border px-2.5 py-1 text-[10px] uppercase tracking-[0.12em] ${getSeverityTone(entity.risk)}`}>
          {entity.risk}
        </span>
      </div>

      <dl className="space-y-3 text-sm text-slate-300">
        <div className="flex justify-between"><dt className="text-slate-400">Entity ID</dt><dd>{entity.id}</dd></div>
        <div className="flex justify-between"><dt className="text-slate-400">First seen</dt><dd>{entity.firstSeen}</dd></div>
      </dl>

      <div className="mt-4 flex flex-wrap gap-2">
        {entity.tags.map((tag) => (
          <span key={tag} className="rounded-full border border-slate-700 bg-slate-900/80 px-2 py-1 text-[10px] uppercase tracking-[0.12em] text-slate-300">
            {tag}
          </span>
        ))}
      </div>
    </article>
  );
}
