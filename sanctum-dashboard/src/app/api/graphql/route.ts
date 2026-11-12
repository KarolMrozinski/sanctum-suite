import { getGraphQLDashboardPayload } from "@/lib/dashboard-data";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const section = searchParams.get("section") ?? "overview";
  const id = searchParams.get("id");
  const payload = getGraphQLDashboardPayload(section, id);

  return Response.json(
    {
      data: payload,
      meta: {
        source: "mock-graphql",
        version: "1.5.0",
        generatedAt: new Date().toISOString(),
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

export async function POST(request: Request) {
  const body = (await request.json()) as {
    query?: string;
    variables?: { section?: string; id?: string };
  };

  const section = body?.variables?.section ?? "overview";
  const id = body?.variables?.id ?? null;
  const payload = getGraphQLDashboardPayload(section, id);

  return Response.json(
    {
      data: payload,
      meta: {
        source: "mock-graphql",
        operation: body?.query?.includes("query") ? "query" : "mutation",
        status: "ok",
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
