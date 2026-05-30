/**
 * API 客户端封装 —— 统一响应壳解析 + 错误处理。
 * 后端统一返回 { code, message, data, meta }。
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_PREFIX = "/api/v1";

/** 统一响应壳 */
export interface ApiEnvelope<T> {
  code: number;
  message: string;
  data: T;
  meta?: { page?: number; page_size?: number; total?: number } | null;
}

export class ApiError extends Error {
  code: number;
  status: number;
  constructor(message: string, code: number, status: number) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<ApiEnvelope<T>> {
  const url = `${API_BASE}${API_PREFIX}${path}`;
  const resp = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });

  let body: ApiEnvelope<T>;
  try {
    body = await resp.json();
  } catch {
    throw new ApiError(`响应解析失败 (HTTP ${resp.status})`, -1, resp.status);
  }

  // 业务错误码或 HTTP 错误
  if (!resp.ok || (body.code !== undefined && body.code !== 0)) {
    throw new ApiError(body.message || `请求失败 (HTTP ${resp.status})`, body.code ?? -1, resp.status);
  }
  return body;
}

export const api = {
  get: <T>(path: string) => request<T>(path, { method: "GET" }),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
  patch: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "PATCH", body: body ? JSON.stringify(body) : undefined }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
};
