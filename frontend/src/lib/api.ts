const JSON_HEADERS = { "Content-Type": "application/json" };

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(path, {
    credentials: "include",
    ...options,
    headers: {
      ...(options.body instanceof FormData ? {} : JSON_HEADERS),
      ...options.headers,
    },
  });
  if (!response.ok) {
    let message = `请求失败 (${response.status})`;
    try {
      const payload = await response.json();
      message = payload.detail || message;
    } catch {
      // Keep the HTTP fallback message for non-JSON errors.
    }
    throw new ApiError(message, response.status);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "-";
  return new Date(value).toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatBytes(value: number): string {
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / 1024 / 1024).toFixed(1)} MB`;
}
