// Thin fetch wrapper for the FastAPI Backend Wrapper (Section C/F). Defaults
// to same-origin `/api/*` routes (served by the mock handlers in
// src/app/api during development). Point NEXT_PUBLIC_API_BASE_URL at the
// real backend wrapper in production -- no other frontend code changes.

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(
      body?.message ?? `Request failed with status ${res.status}`,
      res.status,
    );
  }

  return res.json() as Promise<T>;
}

export const apiClient = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, data?: unknown) =>
    request<T>(path, { method: "POST", body: data ? JSON.stringify(data) : undefined }),
};
