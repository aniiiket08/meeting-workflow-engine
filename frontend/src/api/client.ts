import { getAuthToken } from "../lib/theme";

// In dev, Vite proxy rewrites /api → localhost:8000 (see vite.config.ts).
// In production (Vercel), VITE_API_URL must point to your deployed backend URL.
const BASE_URL = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/api/v1`
  : "/api/v1";

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = getAuthToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    // AppError shape: { error: { message } }, HTTPException: { detail: string | object[] }
    let message = errorData?.error?.message;
    if (!message) {
      const detail = errorData?.detail;
      if (typeof detail === "string") {
        message = detail;
      } else if (Array.isArray(detail)) {
        // Pydantic validation errors: [{"msg": "...", "loc": [...]}]
        message = detail
          .map((e: any) => {
            const field = Array.isArray(e.loc) ? e.loc.filter((s: any) => s !== "body").join(".") : "";
            return field ? `${field}: ${e.msg}` : e.msg;
          })
          .join("; ");
      } else if (detail && typeof detail === "object") {
        message = (detail as any).message || JSON.stringify(detail);
      }
    }
    throw new Error(message || `Request failed (${response.status})`);
  }

  return response.json();
}

export const api = {
  get: <T>(endpoint: string) => request<T>(endpoint, { method: "GET" }),
  post: <T>(endpoint: string, data: any) =>
    request<T>(endpoint, { method: "POST", body: JSON.stringify(data) }),
  put: <T>(endpoint: string, data: any) =>
    request<T>(endpoint, { method: "PUT", body: JSON.stringify(data) }),
};
