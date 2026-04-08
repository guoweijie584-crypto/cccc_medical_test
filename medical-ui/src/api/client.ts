// API Client — 统一请求封装
// 通过 nginx 代理，/api/ 已指向 :8001

const API_BASE = import.meta.env.VITE_API_BASE || '';

export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string,
  ) {
    super(detail);
    this.name = 'ApiError';
  }
}

export async function apiRequest<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 30000); // 30s timeout

  try {
    const response = await fetch(`${API_BASE}${path}`, {
      headers: { 'Content-Type': 'application/json' },
      signal: controller.signal,
      ...options,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new ApiError(response.status, error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  } catch (err) {
    if (err instanceof ApiError) throw err;
    if (err instanceof DOMException && err.name === 'AbortError') {
      throw new ApiError(408, '请求超时，请稍候重试');
    }
    throw new ApiError(0, '网络连接失败，请检查网络');
  } finally {
    clearTimeout(timeout);
  }
}

// Convenience methods
export const api = {
  get: <T>(path: string) => apiRequest<T>(path),

  post: <T>(path: string, body?: unknown) =>
    apiRequest<T>(path, {
      method: 'POST',
      body: body ? JSON.stringify(body) : undefined,
    }),

  put: <T>(path: string, body?: unknown) =>
    apiRequest<T>(path, {
      method: 'PUT',
      body: body ? JSON.stringify(body) : undefined,
    }),

  delete: <T>(path: string) =>
    apiRequest<T>(path, { method: 'DELETE' }),
};
