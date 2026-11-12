import { DashboardShell } from "@/components/dashboard/dashboard-shell";
import { InvestigationsSection } from "@/components/dashboard/overview-section";
import { getDashboardSnapshot } from "@/lib/dashboard-data";

export default function InvestigationsPage() {
  return (
    <DashboardShell section="investigations">
      <InvestigationsSection snapshot={getDashboardSnapshot("investigations")} />
    </DashboardShell>
  );
}
