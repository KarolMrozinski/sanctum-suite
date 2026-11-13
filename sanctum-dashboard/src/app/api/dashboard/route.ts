import { fetchDashboardSnapshot } from "@/lib/dashboard-data";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const section = searchParams.get("section") ?? "overview";
  const id = searchParams.get("id");

  const snapshot = await fetchDashboardSnapshot(section, id);

  const selected = id
    ? [
        ...snapshot.threats,
        ...snapshot.entities,
        ...snapshot.alerts,
        ...snapshot.incidents,
      ].find((entry) => ("id" in entry ? entry.id === id : false)) ?? null
    : null;

  const useRealData = (process.env.SANCTUM_USE_REAL_DATA ?? process.env.NEXT_PUBLIC_SANCTUM_USE_REAL_DATA ?? "true") !== "false";
  const dashboard = {
    ...snapshot,
    section,
    selectedId: id,
    selected,
    mode: useRealData ? "live" : "live-like",
    generatedAt: new Date().toISOString(),
  };

  return Response.json(
    {
      ...dashboard,
      data: {
        dashboard,
      },
      meta: {
        source: useRealData ? "live-api" : "mock-data",
        section,
        generatedAt: dashboard.generatedAt,
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
