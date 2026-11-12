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
      ...snapshot,
      section,
      selectedId: id,
      selected,
    },
    {
      headers: {
        "Cache-Control": "no-store",
      },
    },
  );
}
