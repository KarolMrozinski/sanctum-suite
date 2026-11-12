import { DashboardShell } from "@/components/dashboard/dashboard-shell";
import { ThreatsSection } from "@/components/dashboard/overview-section";
import { getDashboardSnapshot } from "@/lib/dashboard-data";

export default function ThreatsPage() {
  return (
    <DashboardShell section="threats">
      <ThreatsSection snapshot={getDashboardSnapshot("threats")} />
    </DashboardShell>
  );
}
