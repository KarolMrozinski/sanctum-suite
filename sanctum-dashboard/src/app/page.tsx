import { DashboardFilters } from "@/components/dashboard/dashboard-filters";
import { DashboardShell } from "@/components/dashboard/dashboard-shell";
import { OverviewSection } from "@/components/dashboard/overview-section";
import { AlertFeed } from "@/components/dashboard/widgets/alert-feed";
import { EntityCard } from "@/components/dashboard/widgets/entity-card";
import { InvestigationTimeline } from "@/components/dashboard/widgets/investigation-timeline";
import { ThreatDetail } from "@/components/dashboard/widgets/threat-detail";
import { getDashboardSnapshot } from "@/lib/dashboard-data";

export default function HomePage() {
  const snapshot = getDashboardSnapshot("overview");

  return (
    <DashboardShell section="overview">
      <DashboardFilters />

      <section className="grid gap-6 xl:grid-cols-[1.45fr_0.55fr]">
        <div className="panel-surface rounded-3xl p-5">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <p className="text-[10px] uppercase tracking-[0.22em] text-slate-400">Exec summary</p>
              <h2 className="mt-2 text-xl font-semibold text-white">Mission posture</h2>
            </div>
            <div className="rounded-full border border-[#7ef7d3]/30 bg-[#0f1b1a] px-3 py-1 text-[10px] uppercase tracking-[0.18em] text-[#9ee7d6]">
              Live signal
            </div>
          </div>
          <OverviewSection snapshot={snapshot} />
        </div>

        <div className="panel-surface rounded-3xl p-5">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <p className="text-[10px] uppercase tracking-[0.22em] text-slate-400">Operations</p>
              <h2 className="mt-2 text-xl font-semibold text-white">Operator notes</h2>
            </div>
          </div>
          <div className="space-y-4">
            {[
              { label: "Priority queue", value: "06 active cases", tone: "text-[#9ee7d6]" },
              { label: "Threat drift", value: "+18.4% vs last run", tone: "text-[#8ad8ff]" },
              { label: "Containment", value: "4 mitigations deployed", tone: "text-[#c7d2fe]" },
            ].map((item) => (
              <div key={item.label} className="rounded-2xl border border-slate-800 bg-[#0d1419] p-3.5">
                <div className="text-[10px] uppercase tracking-[0.2em] text-slate-400">{item.label}</div>
                <div className={`mt-2 text-sm font-medium ${item.tone}`}>{item.value}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.35fr_0.65fr]">
        <ThreatDetail threat={snapshot.threats[0]} />
        <AlertFeed alerts={snapshot.alerts} />
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.12fr_0.88fr]">
        <div className="grid gap-5 md:grid-cols-2">
          {snapshot.entities.slice(0, 2).map((entity) => (
            <EntityCard key={entity.id} entity={entity} />
          ))}
        </div>
        <InvestigationTimeline investigation={snapshot.investigations[0]} />
      </section>
    </DashboardShell>
  );
}
