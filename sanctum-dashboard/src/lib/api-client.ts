export type ApiClientConfig = {
  baseUrl?: string;
  apiKey?: string;
  token?: string;
  useRealData?: boolean;
};

export function buildSanctumHeaders(config: ApiClientConfig = {}) {
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

export function shouldUseRealApiData() {
  return process.env.NEXT_PUBLIC_SANCTUM_USE_REAL_DATA !== "false" && Boolean(getSanctumApiBaseUrl());
}
