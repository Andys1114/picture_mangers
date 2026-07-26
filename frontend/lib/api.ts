// The only module that knows URLs. Components/hooks import typed functions
// from here and never hardcode /api/... (frontend quality-guidelines).
//
// All calls go same-origin via the Next.js rewrite (/api/*, /media/* →
// backend), so the HttpOnly session cookie travels automatically.

import type {
  ApiErrorBody,
  Me,
  Paginated,
  PostDetail,
  PostSummary,
  PostsParams,
  User,
} from "./types";

export class ApiError extends Error {
  code: string;
  status: number;
  constructor(code: string, message: string, status: number) {
    super(message);
    this.code = code;
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });
  if (!res.ok) {
    let code = "error";
    let message = `请求失败 (${res.status})`;
    try {
      const body = (await res.json()) as ApiErrorBody;
      if (body?.error) {
        code = body.error.code;
        message = body.error.message;
      }
    } catch {
      // Non-JSON error; keep defaults.
    }
    throw new ApiError(code, message, res.status);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

function withQuery(params: Record<string, string | number | undefined>): string {
  const s = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== "") s.set(k, String(v));
  }
  const str = s.toString();
  return str ? `?${str}` : "";
}

export const api = {
  status: () => request<{ setup_required: boolean }>("/api/auth/status"),
  setup: (body: { username: string; password: string }) =>
    request<User>("/api/auth/setup", { method: "POST", body: JSON.stringify(body) }),
  login: (body: { username: string; password: string }) =>
    request<User>("/api/auth/login", { method: "POST", body: JSON.stringify(body) }),
  logout: () => request<void>("/api/auth/logout", { method: "POST" }),
  me: () => request<Me>("/api/auth/me"),
  updateSettings: (body: { safe_mode: boolean }) =>
    request<Me>("/api/auth/me/settings", { method: "PATCH", body: JSON.stringify(body) }),
  listPosts: (params: PostsParams) =>
    request<Paginated<PostSummary>>(
      `/api/posts${withQuery({
        tags: params.tags,
        page: params.page,
        limit: params.limit,
        order: params.order,
        ratings: params.ratings,
      })}`,
    ),
  getPost: (id: number) => request<PostDetail>(`/api/posts/${id}`),
};

/** Build a same-origin /media URL from a stored relative path. */
export function mediaUrl(path: string): string {
  return `/media/${path.replace(/^\/+/, "")}`;
}
