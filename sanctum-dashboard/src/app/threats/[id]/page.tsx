import { notFound } from "next/navigation";
import { DashboardShell } from "@/components/dashboard/dashboard-shell";
import { DetailPanel } from "@/components/dashboard/detail-panel";
import { getDashboardSnapshot } from "@/lib/dashboard-data";

export function generateStaticParams() {
  return ["THR-421", "THR-612", "THR-118", "THR-204"].map((id) => ({ id }));
}

export default async function ThreatDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const snapshot = getDashboardSnapshot("threats");
  const threat = snapshot.threats.find((item) => item.id === id);

  if (!threat) {
    notFound();
  }

  return (
    <DashboardShell section="threats">
      <div className="grid gap-6 xl:grid-cols-[1fr_420px]">
        <div className="rounded-2xl border border-slate-800 bg-[#0d1b2b] p-5">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <div className="text-[10px] uppercase tracking-[0.2em] text-slate-400">Threat intelligence</div>
              <h1 className="mt-1 text-2xl font-semibold text-white">{threat.title}</h1>
            </div>
            <a href="/threats" className="rounded-full border border-slate-700 bg-slate-900/80 px-3 py-1.5 text-xs uppercase tracking-[0.18em] text-slate-200">
              Back
            </a>
          </div>

          <div className="space-y-4">
            <div className="rounded-xl border border-slate-800 bg-[#0f2237] p-4">
              <div className="text-[10px] uppercase tracking-[0.2em] text-slate-400">Summary</div>
              <p className="mt-2 text-sm leading-6 text-slate-300">{threat.description}</p>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div className="rounded-xl border border-slate-800 bg-[#0f2237] p-4">
                <div className="text-[10px] uppercase tracking-[0.2em] text-slate-400">Indicators</div>
                <div className="mt-3 flex flex-wrap gap-2">
                  {threat.indicators.map((indicator) => (
                    <span key={indicator} className="rounded-full border border-slate-700 bg-slate-950/80 px-2 py-1 text-[10px] uppercase tracking-[0.12em] text-slate-200">
                      {indicator}
                    </span>
                  ))}
                </div>
              </div>

              <div className="rounded-xl border border-slate-800 bg-[#0f2237] p-4">
                <div className="text-[10px] uppercase tracking-[0.2em] text-slate-400">Relationships</div>
                <div className="mt-3 flex flex-wrap gap-2">
                  {threat.relations.map((relation) => (
                    <span key={relation} className="rounded-full border border-slate-700 bg-slate-950/80 px-2 py-1 text-[10px] uppercase tracking-[0.12em] text-slate-200">
                      {relation}
                    </span>
                  ))}
                </div>
              </div>
            </div>

            <div className="rounded-xl border border-slate-800 bg-[#0f2237] p-4">
              <div className="mb-3 text-[10px] uppercase tracking-[0.2em] text-slate-400">Timeline</div>
              <div className="space-y-4">
                {threat.timeline.map((event) => (
                  <div key={event.id} className="flex gap-3">
                    <div className="mt-1 h-2.5 w-2.5 rounded-full bg-[#1de9b6]" />
                    <div className="flex-1 rounded-xl border border-slate-700 bg-[#0d1b2b] p-3">
                      <div className="flex items-center justify-between gap-3 text-[10px] uppercase tracking-[0.12em] text-slate-400">
                        <span>{event.title}</span>
                        <span>{event.time}</span>
                      </div>
                      <p className="mt-2 text-sm text-slate-300">{event.detail}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        <DetailPanel item={threat} itemType="threat" />
      </div>
    </DashboardShell>
  );
}
