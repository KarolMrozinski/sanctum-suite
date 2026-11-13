import { SectionDetailPage } from "@/components/dashboard/section-detail-page";
import { getDashboardSnapshot } from "@/lib/dashboard-data";

export default function ThreatsPage() {
  return <SectionDetailPage section="threats" snapshot={getDashboardSnapshot("threats")} />;
}
