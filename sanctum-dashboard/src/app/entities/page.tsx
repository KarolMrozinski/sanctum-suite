import { SectionDetailPage } from "@/components/dashboard/section-detail-page";
import { getDashboardSnapshot } from "@/lib/dashboard-data";

export default function EntitiesPage() {
  return <SectionDetailPage section="entities" snapshot={getDashboardSnapshot("entities")} />;
}
