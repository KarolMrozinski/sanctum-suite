export type SanitizedApiOperation = {
  method: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  summary: string;
  path: string;
  auth: "Bearer" | "API-Key" | "None";
  description: string;
  response: string;
};

export type SanctumCtiApiContract = {
  openapi: "3.0.0";
  info: {
    title: string;
    version: string;
    description: string;
  };
  servers: {
    url: string;
    description: string;
  }[];
  security: Array<{ bearerAuth?: string[]; apiKeyAuth?: string[] }>;
  paths: Record<string, Record<string, SanitizedApiOperation>>;
  schemas: {
    DashboardSnapshot: Record<string, unknown>;
    Threat: Record<string, unknown>;
    Incident: Record<string, unknown>;
    Investigation: Record<string, unknown>;
    Alert: Record<string, unknown>;
    Entity: Record<string, unknown>;
  };
};

export function getSanctumCtiApiContract(): SanctumCtiApiContract {
  const baseUrl = process.env.SANCTUM_API_BASE_URL ?? process.env.NEXT_PUBLIC_SANCTUM_API_URL ?? "http://localhost:3000";

  return {
    openapi: "3.0.0",
    info: {
      title: "Sanctum Suite CTI API",
      version: "1.5.0",
      description:
        "Formal contract for the Sanctum Suite cyber threat intelligence backend, designed for live production wiring while remaining compatible with local/mock datasets.",
    },
    servers: [
      {
        url: baseUrl.replace(/\/$/, ""),
        description: "Primary backend endpoint",
      },
      {
        url: "http://localhost:3000",
        description: "Local Next.js dashboard runtime",
      },
    ],
    security: [{ bearerAuth: [] }, { apiKeyAuth: [] }],
    paths: {
      "/api/dashboard": {
        GET: {
          method: "GET",
          summary: "Fetch the current CTI dashboard snapshot",
          path: "/api/dashboard",
          auth: "Bearer",
          description:
            "Returns the active operational overview including stats, alerts, entities, investigations, threats, incidents, and integrations. Supports live backend and mock fallback.",
          response: "DashboardSnapshot",
        },
      },
      "/api/graphql": {
        POST: {
          method: "POST",
          summary: "Execute a GraphQL-like CTI query",
          path: "/api/graphql",
          auth: "API-Key",
          description:
            "Accepts a query payload and returns a normalized dashboard result for threat intel workflows without requiring a dedicated GraphQL service.",
          response: "DashboardSnapshot",
        },
      },
      "/api/v1/dashboard": {
        GET: {
          method: "GET",
          summary: "Production CTI dashboard contract",
          path: "/api/v1/dashboard",
          auth: "Bearer",
          description:
            "Canonical live endpoint for dashboard state. The backend should return the same normalized envelope used by the UI model.",
          response: "DashboardSnapshot",
        },
      },
      "/api/v1/incidents": {
        GET: {
          method: "GET",
          summary: "List incidents",
          path: "/api/v1/incidents",
          auth: "Bearer",
          description: "Returns all incidents with workflow state, owner, confidence, impacted systems, and evidence.",
          response: "Incident[]",
        },
      },
      "/api/v1/investigations": {
        GET: {
          method: "GET",
          summary: "List investigations",
          path: "/api/v1/investigations",
          auth: "Bearer",
          description: "Returns investigation records, stage, priority, linked threats, and timeline.",
          response: "Investigation[]",
        },
      },
      "/api/v1/alerts": {
        GET: {
          method: "GET",
          summary: "List alerts",
          path: "/api/v1/alerts",
          auth: "Bearer",
          description: "Returns active and historical alert records with severity, source, and entity relation.",
          response: "Alert[]",
        },
      },
    },
    schemas: {
      DashboardSnapshot: {
        type: "object",
        required: ["section", "stats", "threats", "entities", "alerts", "incidents", "investigations"],
        properties: {
          section: { type: "string", enum: ["overview", "threats", "entities", "investigations", "alerts", "incidents", "integrations"] },
          stats: { type: "array", items: { type: "object" } },
          detection: { type: "array", items: { type: "object" } },
          events: { type: "array", items: { type: "object" } },
          threats: { type: "array", items: { type: "object" } },
          entities: { type: "array", items: { type: "object" } },
          investigations: { type: "array", items: { type: "object" } },
          alerts: { type: "array", items: { type: "object" } },
          incidents: { type: "array", items: { type: "object" } },
          integrations: { type: "array", items: { type: "object" } },
        },
      },
      Threat: {
        type: "object",
        properties: {
          id: { type: "string" },
          title: { type: "string" },
          actor: { type: "string" },
          severity: { type: "string", enum: ["Critical", "High", "Medium", "Low"] },
          source: { type: "string" },
          status: { type: "string", enum: ["Active", "Monitoring", "Contained"] },
          confidence: { type: "number" },
          description: { type: "string" },
          indicators: { type: "array", items: { type: "string" } },
          relations: { type: "array", items: { type: "string" } },
        },
      },
      Incident: {
        type: "object",
        properties: {
          id: { type: "string" },
          title: { type: "string" },
          severity: { type: "string", enum: ["Critical", "High", "Medium", "Low"] },
          status: { type: "string", enum: ["Open", "Investigating", "Contained", "Resolved"] },
          summary: { type: "string" },
          owner: { type: "string" },
          confidence: { type: "number" },
          impactedSystems: { type: "array", items: { type: "string" } },
          relatedThreats: { type: "array", items: { type: "string" } },
          relatedEntities: { type: "array", items: { type: "string" } },
          evidence: { type: "array", items: { type: "string" } },
        },
      },
      Investigation: {
        type: "object",
        properties: {
          id: { type: "string" },
          name: { type: "string" },
          owner: { type: "string" },
          progress: { type: "number" },
          priority: { type: "string", enum: ["P1", "P2", "P3"] },
          stage: { type: "string" },
          status: { type: "string", enum: ["In progress", "Monitoring", "Closed"] },
          linkedThreats: { type: "array", items: { type: "string" } },
        },
      },
      Alert: {
        type: "object",
        properties: {
          id: { type: "string" },
          title: { type: "string" },
          severity: { type: "string", enum: ["Critical", "High", "Medium", "Low"] },
          source: { type: "string" },
          status: { type: "string", enum: ["Open", "Dismissed", "Investigating"] },
          category: { type: "string" },
          relatedEntity: { type: "string" },
        },
      },
      Entity: {
        type: "object",
        properties: {
          id: { type: "string" },
          type: { type: "string" },
          value: { type: "string" },
          risk: { type: "string", enum: ["Critical", "High", "Medium", "Low"] },
          status: { type: "string", enum: ["Observed", "Monitored", "Contained"] },
          tags: { type: "array", items: { type: "string" } },
          description: { type: "string" },
          confidence: { type: "number" },
        },
      },
    },
  };
}
