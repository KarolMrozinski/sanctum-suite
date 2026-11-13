export type ApiClientConfig = {
  baseUrl?: string;
  apiKey?: string;
  token?: string;
  useRealData?: boolean;
};

export type SanctumApiEndpoint = {
  url: string;
  method?: "GET" | "POST" | "PUT" | "DELETE";
  params?: Record<string, string>;
};

export function buildSanctumHeaders(config: ApiClientConfig = {}): HeadersInit {
  const hasToken = Boolean(config.token || config.apiKey);

  if (!hasToken) {
    return { Accept: "application/json" };
  }

  if (config.token) {
    return {
      Accept: "application/json",
      Authorization: `Bearer ${config.token}`,
    };
  }

  return {
    Accept: "application/json",
    "X-API-Key": config.apiKey ?? "",
  };
}

export function getSanctumApiBaseUrl() {
  return (process.env.SANCTUM_API_BASE_URL ?? process.env.NEXT_PUBLIC_SANCTUM_API_URL ?? "").replace(/\/$/, "");
}

export function getSanctumApiConfig() {
  const baseUrl = getSanctumApiBaseUrl();
  const useRealData = (process.env.SANCTUM_USE_REAL_DATA ?? process.env.NEXT_PUBLIC_SANCTUM_USE_REAL_DATA ?? "true") !== "false";

  return {
    baseUrl,
    apiKey: process.env.SANCTUM_API_KEY ?? process.env.NEXT_PUBLIC_SANCTUM_API_KEY ?? "",
    token: process.env.SANCTUM_API_TOKEN ?? process.env.NEXT_PUBLIC_SANCTUM_API_TOKEN ?? "",
    useRealData: useRealData && Boolean(baseUrl),
  } satisfies ApiClientConfig;
}

export function shouldUseRealApiData() {
  const { baseUrl, useRealData } = getSanctumApiConfig();
  return useRealData && Boolean(baseUrl);
}

export function getSanctumApiEndpoints(baseUrl: string, section?: string, id?: string | null): SanctumApiEndpoint[] {
  const normalizedSection = section || "overview";
  const targetEndpoints = [
    `${baseUrl}/api/v1/dashboard`,
    `${baseUrl}/api/dashboard`,
    `${baseUrl}/api/v1/cti/dashboard`,
  ];

  return targetEndpoints.map((endpoint) => ({
    url: endpoint,
    method: "GET",
    params: {
      section: normalizedSection,
      ...(id ? { id } : {}),
    },
  }));
}

export async function fetchSanctumApi<T>(
  endpoint: SanctumApiEndpoint,
  config: ApiClientConfig = {},
  init: RequestInit = {},
): Promise<T | null> {
  const url = new URL(endpoint.url);

  Object.entries(endpoint.params ?? {}).forEach(([key, value]) => {
    if (value) {
      url.searchParams.set(key, value);
    }
  });

  const mergedHeaders = new Headers(buildSanctumHeaders(config));

  if (init.headers) {
    const requestHeaders = new Headers(init.headers);
    requestHeaders.forEach((value, key) => mergedHeaders.set(key, value));
  }

  try {
    const response = await fetch(url.toString(), {
      ...init,
      method: endpoint.method ?? "GET",
      headers: mergedHeaders,
    });

    if (!response.ok) {
      return null;
    }

    return (await response.json()) as T;
  } catch {
    return null;
  }
}
