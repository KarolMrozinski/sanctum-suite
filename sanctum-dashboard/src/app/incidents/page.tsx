import { SectionDetailPage } from "@/components/dashboard/section-detail-page";
import { getDashboardSnapshot } from "@/lib/dashboard-data";

export default function IncidentsPage() {
  return <SectionDetailPage section="incidents" snapshot={getDashboardSnapshot("incidents")} />;
}
