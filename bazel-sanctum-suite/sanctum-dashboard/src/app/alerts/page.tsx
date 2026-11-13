import { SectionDetailPage } from "@/components/dashboard/section-detail-page";
import { getDashboardSnapshot } from "@/lib/dashboard-data";

export default function AlertsPage() {
  return <SectionDetailPage section="alerts" snapshot={getDashboardSnapshot("alerts")} />;
}
