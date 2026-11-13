const MAX_BODY_BYTES = 8_192;
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

type LeadSubmission = {
  email?: unknown;
  organization?: unknown;
  message?: unknown;
  website?: unknown;
};

function configuredWebhook(): URL | null {
  const configuredUrl = process.env.SANCTUM_LEAD_WEBHOOK_URL;
  if (!configuredUrl) return null;

  try {
    const webhook = new URL(configuredUrl);
    const isSecure = webhook.protocol === "https:"
      || (webhook.protocol === "http:" && ["localhost", "127.0.0.1"].includes(webhook.hostname));
    if (!isSecure || webhook.username || webhook.password) return null;
    return webhook;
  } catch {
    return null;
  }
}

export async function GET(request: Request) {
  const origin = request.headers.get("origin");
  if (origin) {
    try {
      if (new URL(origin).host !== new URL(request.url).host) {
        return Response.json({ error: "Invalid request origin." }, { status: 403 });
      }
    } catch {
      return Response.json({ error: "Invalid request origin." }, { status: 403 });
    }
  }
  return Response.json(
    { available: configuredWebhook() !== null },
    { headers: { "Cache-Control": "no-store" } },
  );
}

function isBoundedString(value: unknown, maxLength: number): value is string {
  return typeof value === "string" && value.trim().length > 0 && value.length <= maxLength;
}

export async function POST(request: Request) {
  const origin = request.headers.get("origin");
  if (origin) {
    try {
      if (new URL(origin).host !== new URL(request.url).host) {
        return Response.json({ error: "Invalid request origin." }, { status: 403 });
      }
    } catch {
      return Response.json({ error: "Invalid request origin." }, { status: 403 });
    }
  }

  const contentLength = Number(request.headers.get("content-length") ?? 0);
  if (contentLength > MAX_BODY_BYTES) {
    return Response.json({ error: "Request is too large." }, { status: 413 });
  }

  if (!request.headers.get("content-type")?.toLowerCase().includes("application/json")) {
    return Response.json({ error: "Content-Type must be application/json." }, { status: 415 });
  }

  const reader = request.body?.getReader();
  if (!reader) {
    return Response.json({ error: "Request body is required." }, { status: 400 });
  }

  const chunks: Uint8Array[] = [];
  let bodySize = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      bodySize += value.byteLength;
      if (bodySize > MAX_BODY_BYTES) {
        await reader.cancel();
        return Response.json({ error: "Request is too large." }, { status: 413 });
      }
      chunks.push(value);
    }
  } catch {
    return Response.json({ error: "Unable to read request body." }, { status: 400 });
  }

  let submission: LeadSubmission;
  try {
    const body = new Uint8Array(bodySize);
    let offset = 0;
    for (const chunk of chunks) {
      body.set(chunk, offset);
      offset += chunk.byteLength;
    }
    const parsed: unknown = JSON.parse(new TextDecoder().decode(body));
    if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
      return Response.json({ error: "Expected a JSON object." }, { status: 400 });
    }
    submission = parsed as LeadSubmission;
  } catch {
    return Response.json({ error: "Invalid JSON body." }, { status: 400 });
  }

  if (typeof submission.website === "string" && submission.website.trim()) {
    return Response.json({ accepted: true }, { status: 202 });
  }

  const email = typeof submission.email === "string" ? submission.email.trim() : "";
  const organization = typeof submission.organization === "string" ? submission.organization.trim() : "";
  const message = typeof submission.message === "string" ? submission.message.trim() : "";

  if (
    !isBoundedString(email, 254) ||
    !EMAIL_PATTERN.test(email) ||
    !isBoundedString(organization, 120) ||
    !isBoundedString(message, 2_000)
  ) {
    return Response.json({ error: "Please provide a valid email, organization, and message." }, { status: 400 });
  }

  const webhook = configuredWebhook();
  if (!webhook) {
    if (process.env.SANCTUM_LEAD_WEBHOOK_URL) {
      console.error("SANCTUM_LEAD_WEBHOOK_URL must be HTTPS and must not contain embedded credentials.");
      return Response.json({ error: "Lead submission is not configured securely." }, { status: 503 });
    }
    return Response.json({ error: "Lead submission is not configured." }, { status: 503 });
  }

  const headers = new Headers({ "Content-Type": "application/json" });
  const webhookToken = process.env.SANCTUM_LEAD_WEBHOOK_TOKEN;
  if (webhookToken) {
    headers.set("Authorization", `Bearer ${webhookToken}`);
  }

  let upstream: Response;
  try {
    upstream = await fetch(webhook, {
      method: "POST",
      headers,
      body: JSON.stringify({
        email,
        organization,
        message,
        submittedAt: new Date().toISOString(),
      }),
      signal: AbortSignal.timeout(10_000),
      cache: "no-store",
      redirect: "manual",
    });
  } catch (error) {
    console.error("Lead webhook request failed.", error);
    return Response.json({ error: "Lead service is temporarily unavailable." }, { status: 502 });
  }

  if (!upstream.ok) {
    console.error(`Lead webhook returned HTTP ${upstream.status}.`);
    return Response.json({ error: "Lead service could not accept the inquiry." }, { status: 502 });
  }

  return Response.json({ accepted: true }, { status: 201 });
}
