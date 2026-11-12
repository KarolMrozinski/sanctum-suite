import { DashboardShell } from "@/components/dashboard/dashboard-shell";
import { EntitiesSection } from "@/components/dashboard/overview-section";
import { getDashboardSnapshot } from "@/lib/dashboard-data";

export default function EntitiesPage() {
  return (
    <DashboardShell section="entities">
      <EntitiesSection snapshot={getDashboardSnapshot("entities")} />
    </DashboardShell>
  );
}
