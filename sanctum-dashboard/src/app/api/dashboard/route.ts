import { getDashboardSnapshot } from "@/lib/dashboard-data";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const section = searchParams.get("section") ?? "overview";

  return Response.json(getDashboardSnapshot(section), {
    headers: {
      "Cache-Control": "no-store",
    },
  });
}
