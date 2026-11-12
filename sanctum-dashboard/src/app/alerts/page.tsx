import { DashboardShell } from "@/components/dashboard/dashboard-shell";
import { AlertsSection } from "@/components/dashboard/overview-section";
import { getDashboardSnapshot } from "@/lib/dashboard-data";

export default function AlertsPage() {
  return (
    <DashboardShell section="alerts">
      <AlertsSection snapshot={getDashboardSnapshot("alerts")} />
    </DashboardShell>
  );
}
