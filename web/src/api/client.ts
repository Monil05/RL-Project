import { ApiRequestError } from "../types";

const BASE = import.meta.env.VITE_API_BASE ?? "";

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${BASE}${path}`, {
      ...init,
      headers: {
        ...(init?.body ? { "Content-Type": "application/json" } : {}),
        ...(init?.headers ?? {}),
      },
    });
  } catch {
    throw new ApiRequestError(0, "The API is unreachable.");
  }
  if (!response.ok) {
    let detail = response.statusText || "Request failed";
    try {
      const body = (await response.json()) as { detail?: string };
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      detail = await response.text();
    }
    throw new ApiRequestError(response.status, detail);
  }
  if (response.headers.get("content-type")?.includes("text/csv")) {
    return (await response.text()) as T;
  }
  return (await response.json()) as T;
}

export function exportUrl(params: Record<string, string>): string {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value) query.set(key, value);
  });
  const suffix = query.toString();
  return `${BASE}/api/results/export${suffix ? `?${suffix}` : ""}`;
}
