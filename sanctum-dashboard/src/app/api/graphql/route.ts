import { getDashboardSnapshot } from "@/lib/dashboard-data";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const section = searchParams.get("section") ?? "overview";
  const snapshot = getDashboardSnapshot(section);

  return Response.json({
    data: {
      dashboard: {
        section,
        generatedAt: new Date().toISOString(),
        stats: snapshot.stats,
        detection: snapshot.detection,
        events: snapshot.events,
        entities: snapshot.entities,
        threats: snapshot.threats,
        investigations: snapshot.investigations,
        alerts: snapshot.alerts,
      },
    },
  }, {
    headers: {
      "Content-Type": "application/json",
      "Cache-Control": "no-store",
    },
  });
}
