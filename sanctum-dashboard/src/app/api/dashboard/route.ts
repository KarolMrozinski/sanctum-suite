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

  return Response.json(
    {
      data: {
        dashboard: {
          ...snapshot,
          section,
          selectedId: id,
          selected,
          mode: process.env.NEXT_PUBLIC_SANCTUM_USE_REAL_DATA === "false" ? "live-like" : "live",
          generatedAt: new Date().toISOString(),
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
