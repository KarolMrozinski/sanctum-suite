import { getDashboardSnapshot } from "@/lib/dashboard-data";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const section = searchParams.get("section") ?? "overview";
  const id = searchParams.get("id");
  const snapshot = getDashboardSnapshot(section);

  const selected = id
    ? [
        ...snapshot.threats,
        ...snapshot.entities,
        ...snapshot.alerts,
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
          mode: "live-like",
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
