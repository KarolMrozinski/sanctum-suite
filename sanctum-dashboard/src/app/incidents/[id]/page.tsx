import { notFound } from "next/navigation";
import { DashboardShell } from "@/components/dashboard/dashboard-shell";
import { DetailPanel } from "@/components/dashboard/detail-panel";
import { getDashboardSnapshot } from "@/lib/dashboard-data";

export function generateStaticParams() {
  return ["INC-1001", "INC-1002", "INC-1003"].map((id) => ({ id }));
}

export default async function IncidentDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const snapshot = getDashboardSnapshot("incidents");
  const incident = snapshot.incidents.find((item) => item.id === id);

  if (!incident) {
    notFound();
  }

  return (
    <DashboardShell section="incidents">
      <div className="grid gap-6 xl:grid-cols-[1fr_420px]">
        <div className="rounded-2xl border border-slate-800 bg-[#0d1b2b] p-5">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <div className="text-[10px] uppercase tracking-[0.2em] text-slate-400">Incident</div>
              <h1 className="mt-1 text-2xl font-semibold text-white">{incident.title}</h1>
            </div>
            <a href="/incidents" className="rounded-full border border-slate-700 bg-slate-900/80 px-3 py-1.5 text-xs uppercase tracking-[0.18em] text-slate-200">
              Back
            </a>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div className="rounded-xl border border-slate-800 bg-[#0f2237] p-4">
              <div className="text-[10px] uppercase tracking-[0.2em] text-slate-400">Summary</div>
              <p className="mt-2 text-sm leading-6 text-slate-300">{incident.summary}</p>
            </div>

            <div className="rounded-xl border border-slate-800 bg-[#0f2237] p-4">
              <div className="text-[10px] uppercase tracking-[0.2em] text-slate-400">Operational data</div>
              <div className="mt-3 text-sm text-slate-300">Owner: {incident.owner}</div>
              <div className="mt-3 text-sm text-slate-300">Category: {incident.category}</div>
              <div className="mt-3 text-sm text-slate-300">Updated: {incident.updatedAt}</div>
            </div>
          </div>

          <div className="mt-5 rounded-xl border border-slate-800 bg-[#0f2237] p-4">
            <div className="mb-3 text-[10px] uppercase tracking-[0.2em] text-slate-400">Workflow</div>
            <div className="space-y-4">
              {incident.workflow.map((step) => (
                <div key={step.id} className="rounded-xl border border-slate-700 bg-[#0d1b2b] p-3">
                  <div className="flex items-center justify-between gap-3">
                    <div className="text-sm font-medium text-white">{step.label}</div>
                    <span className="rounded-full border border-slate-600 bg-slate-900 px-2 py-1 text-[10px] uppercase tracking-[0.12em] text-slate-200">
                      {step.status}
                    </span>
                  </div>
                  <div className="mt-2 flex items-center justify-between text-xs uppercase tracking-[0.12em] text-slate-400">
                    <span>{step.owner}</span>
                    <span>{step.eta}</span>
                  </div>
                  <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-800">
                    <div className="h-full rounded-full bg-gradient-to-r from-[#1de9b6] via-[#7fe7d4] to-[#47c4ff]" style={{ width: `${step.progress}%` }} />
                  </div>
                  <p className="mt-2 text-sm text-slate-300">{step.notes}</p>
                </div>
              ))}
            </div>
          </div>
        </div>

        <DetailPanel item={incident} itemType="incident" />
      </div>
    </DashboardShell>
  );
}
