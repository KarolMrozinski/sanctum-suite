import { notFound } from "next/navigation";
import { DashboardShell } from "@/components/dashboard/dashboard-shell";
import { DetailPanel } from "@/components/dashboard/detail-panel";
import { getDashboardSnapshot } from "@/lib/dashboard-data";

export function generateStaticParams() {
  return ["ENT-91", "ENT-125", "ENT-214", "ENT-302"].map((id) => ({ id }));
}

export default async function EntityDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const snapshot = getDashboardSnapshot("entities");
  const entity = snapshot.entities.find((item) => item.id === id);

  if (!entity) {
    notFound();
  }

  return (
    <DashboardShell section="entities">
      <div className="grid gap-6 xl:grid-cols-[1fr_420px]">
        <div className="rounded-2xl border border-slate-800 bg-[#0d1b2b] p-5">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <div className="text-[10px] uppercase tracking-[0.2em] text-slate-400">Entity</div>
              <h1 className="mt-1 text-2xl font-semibold text-white">{entity.value}</h1>
            </div>
            <a href="/entities" className="rounded-full border border-slate-700 bg-slate-900/80 px-3 py-1.5 text-xs uppercase tracking-[0.18em] text-slate-200">
              Back
            </a>
          </div>

          <div className="rounded-xl border border-slate-800 bg-[#0f2237] p-4">
            <div className="text-[10px] uppercase tracking-[0.2em] text-slate-400">Description</div>
            <p className="mt-2 text-sm leading-6 text-slate-300">{entity.description}</p>
          </div>

          <div className="mt-4 grid gap-4 md:grid-cols-2">
            <div className="rounded-xl border border-slate-800 bg-[#0f2237] p-4">
              <div className="text-[10px] uppercase tracking-[0.2em] text-slate-400">Tags</div>
              <div className="mt-3 flex flex-wrap gap-2">
                {entity.tags.map((tag) => (
                  <span key={tag} className="rounded-full border border-slate-700 bg-slate-950/80 px-2 py-1 text-[10px] uppercase tracking-[0.12em] text-slate-200">
                    {tag}
                  </span>
                ))}
              </div>
            </div>

            <div className="rounded-xl border border-slate-800 bg-[#0f2237] p-4">
              <div className="text-[10px] uppercase tracking-[0.2em] text-slate-400">Relationships</div>
              <div className="mt-3 space-y-2 text-sm text-slate-300">
                {entity.relationships.map((relationship) => (
                  <div key={`${relationship.type}-${relationship.value}`} className="flex justify-between gap-3">
                    <span className="text-slate-400">{relationship.type}</span>
                    <span>{relationship.value}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        <DetailPanel item={entity} itemType="entity" />
      </div>
    </DashboardShell>
  );
}
