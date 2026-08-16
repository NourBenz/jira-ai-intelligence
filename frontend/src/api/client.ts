const API_BASE_URL = import.meta.env.VITE_API_URL ?? "";
const TOKEN_KEY = "jira-ai-intelligence-token";

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
  }
}

export function getStoredToken(): string | null {
  return sessionStorage.getItem(TOKEN_KEY);
}

export function storeToken(token: string): void {
  sessionStorage.setItem(TOKEN_KEY, token);
}

export function clearStoredToken(): void {
  sessionStorage.removeItem(TOKEN_KEY);
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const demoResponse = await getDemoResponse(path, options);
  if (demoResponse !== DEMO_UNHANDLED) return demoResponse as T;
  const token = getStoredToken();
  const headers = new Headers(options.headers);
  headers.set("Accept", "application/json");
  if (options.body) headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
  if (response.status === 401 && token) {
    clearStoredToken();
    window.dispatchEvent(new Event("jira-auth-expired"));
  }
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    const detail = payload?.detail;
    const message =
      typeof detail === "string"
        ? detail
        : response.status === 422
          ? "Please check the submitted values."
          : `Request failed with status ${response.status}.`;
    throw new ApiError(message, response.status);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}
import { DEMO_UNHANDLED, getDemoResponse } from "./demo";
