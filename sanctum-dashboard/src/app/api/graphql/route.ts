import { getDashboardSnapshot } from "@/lib/dashboard-data";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const section = searchParams.get("section") ?? "overview";
  const id = searchParams.get("id");
  const snapshot = getDashboardSnapshot(section);

  const selectedThreat = id ? snapshot.threats.find((item) => item.id === id) ?? null : null;
  const selectedEntity = id ? snapshot.entities.find((item) => item.id === id) ?? null : null;
  const selectedAlert = id ? snapshot.alerts.find((item) => item.id === id) ?? null : null;

  return Response.json(
    {
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
          selected: selectedThreat ?? selectedEntity ?? selectedAlert,
          selectedId: id,
          query: {
            section,
            id,
          },
        },
      },
    },
    {
      headers: {
        "Content-Type": "application/json",
        "Cache-Control": "no-store",
      },
    },
  );
}
