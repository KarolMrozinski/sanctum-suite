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
      <OverviewSection snapshot={snapshot} />

      <section className="grid gap-6 xl:grid-cols-[1.3fr_0.7fr]">
        <ThreatDetail threat={snapshot.threats[0]} />
        <AlertFeed alerts={snapshot.alerts} />
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
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
