import { fetchDashboardSnapshot } from "@/lib/dashboard-data";
import { getSanctumApiRuntimeMeta } from "@/lib/api-client";

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

  const runtimeMeta = getSanctumApiRuntimeMeta();
  const dashboard = {
    ...snapshot,
    section,
    selectedId: id,
    selected,
    mode: runtimeMeta.mode,
    generatedAt: new Date().toISOString(),
  };

  return Response.json(
    {
      ...dashboard,
      data: {
        dashboard,
      },
      meta: {
        source: runtimeMeta.source,
        mode: runtimeMeta.mode,
        ready: runtimeMeta.ready,
        baseUrl: runtimeMeta.baseUrl,
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
