import { notFound } from "next/navigation";
import { DashboardShell } from "@/components/dashboard/dashboard-shell";
import { DetailPanel } from "@/components/dashboard/detail-panel";
import { getDashboardSnapshot } from "@/lib/dashboard-data";

export function generateStaticParams() {
  return ["ALT-180", "ALT-181", "ALT-182", "ALT-183"].map((id) => ({ id }));
}

export default async function AlertDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const snapshot = getDashboardSnapshot("alerts");
  const alert = snapshot.alerts.find((item) => item.id === id);

  if (!alert) {
    notFound();
  }

  return (
    <DashboardShell section="alerts">
      <div className="grid gap-6 xl:grid-cols-[1fr_420px]">
        <div className="rounded-2xl border border-slate-800 bg-[#0d1b2b] p-5">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <div className="text-[10px] uppercase tracking-[0.2em] text-slate-400">Alert</div>
              <h1 className="mt-1 text-2xl font-semibold text-white">{alert.title}</h1>
            </div>
            <a href="/alerts" className="rounded-full border border-slate-700 bg-slate-900/80 px-3 py-1.5 text-xs uppercase tracking-[0.18em] text-slate-200">
              Back
            </a>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div className="rounded-xl border border-slate-800 bg-[#0f2237] p-4">
              <div className="text-[10px] uppercase tracking-[0.2em] text-slate-400">Description</div>
              <p className="mt-2 text-sm leading-6 text-slate-300">{alert.description}</p>
            </div>

            <div className="rounded-xl border border-slate-800 bg-[#0f2237] p-4">
              <div className="text-[10px] uppercase tracking-[0.2em] text-slate-400">Source</div>
              <div className="mt-3 text-sm text-slate-300">{alert.source}</div>
              <div className="mt-3 text-sm text-slate-300">Category: {alert.category}</div>
              <div className="mt-3 text-sm text-slate-300">Related entity: {alert.relatedEntity}</div>
            </div>
          </div>
        </div>

        <DetailPanel item={alert} itemType="alert" />
      </div>
    </DashboardShell>
  );
}
