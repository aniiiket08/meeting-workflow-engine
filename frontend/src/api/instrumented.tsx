/**
 * Wraps the base API client with:
 * 1. "Server is waking up..." banner when any request takes > 3 s.
 * 2. Progress-message utilities that callers can use while waiting for
 *    long-running backend operations (transcription, agenda, minutes, email).
 *
 * This module re-exports a `requestWithProgress` helper and a
 * `ServerWakeUpBanner` React component. The core `api` object from
 * client.ts is re-exported unchanged so existing imports keep working.
 */

import React, { useCallback, useEffect, useState } from "react";
import { getAuthToken } from "../lib/theme";

// ── Shared wake-up state (module-level so any component can observe it) ───────
type WakeUpListener = (waking: boolean) => void;
const _listeners = new Set<WakeUpListener>();
let _waking = false;

function _setWaking(value: boolean) {
  if (_waking === value) return;
  _waking = value;
  _listeners.forEach((fn) => fn(value));
}

export function useServerWakeUp(): boolean {
  const [waking, setWaking] = useState(_waking);
  useEffect(() => {
    _listeners.add(setWaking);
    return () => { _listeners.delete(setWaking); };
  }, []);
  return waking;
}

// ── Banner component ──────────────────────────────────────────────────────────
export const ServerWakeUpBanner: React.FC = () => {
  const waking = useServerWakeUp();
  if (!waking) return null;
  return (
    <div
      role="status"
      aria-live="polite"
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        zIndex: 9999,
        background: "var(--color-accent, #d97706)",
        color: "#fff",
        fontSize: "0.75rem",
        fontFamily: "var(--font-mono, monospace)",
        textAlign: "center",
        padding: "6px 16px",
        letterSpacing: "0.05em",
      }}
    >
      Server is waking up... please wait
    </div>
  );
};

// ── Progress messages ─────────────────────────────────────────────────────────
export const PROGRESS_MESSAGES = {
  agenda: "Drafting agenda...",
  transcribe: "Transcribing audio...",
  minutes: "Generating meeting minutes...",
  tasks: "Extracting tasks...",
  distribution: "Sending distribution...",
  approval: "Saving approval...",
} as const;

export type ProgressKey = keyof typeof PROGRESS_MESSAGES;

// ── Instrumented fetch ────────────────────────────────────────────────────────
const WAKE_UP_THRESHOLD_MS = 3000;
const configuredApiOrigin = import.meta.env.VITE_API_URL?.trim().replace(/\/+$/, "");
const BASE_URL = configuredApiOrigin
  ? `${configuredApiOrigin}/api/v1`
  : import.meta.env.PROD
    ? null
    : "/api/v1";
const RETRY_DELAYS_MS = [500, 1000, 2000];
const GET_CACHE_TTL_MS = 1500;
export const API_CONFIGURATION_ERROR =
  "The API endpoint is not configured. Set VITE_API_URL to the backend origin.";
const getCache = new Map<string, { expiresAt: number; value: unknown }>();
const inFlightGets = new Map<string, Promise<unknown>>();
let cacheGeneration = 0;

export function apiUrl(endpoint: string): string {
  if (!BASE_URL) throw new Error(API_CONFIGURATION_ERROR);
  return `${BASE_URL}${endpoint}`;
}

const isSafeToRetry = (method: string) => ["GET", "HEAD", "OPTIONS"].includes(method);

const isProxyConnectionFailure = async (response: Response): Promise<boolean> => {
  if (response.status !== 500 || !response.headers.get("content-type")?.includes("text/plain")) {
    return false;
  }
  const body = await response.clone().text();
  return /http proxy error|ECONNREFUSED|ECONNRESET|ETIMEDOUT|socket hang up/i.test(body);
};

const waitBeforeRetry = (attempt: number) =>
  new Promise((resolve) => window.setTimeout(resolve, RETRY_DELAYS_MS[attempt]));

export async function fetchWithRetry(
  input: RequestInfo | URL,
  init: RequestInit = {},
  onRetry: () => void = () => {},
): Promise<Response> {
  const method = (init.method || (input instanceof Request ? input.method : "GET")).toUpperCase();
  const safeToRetryNetworkError = isSafeToRetry(method);

  for (let attempt = 0; ; attempt += 1) {
    let response: Response;
    try {
      response = await fetch(input, init);
    } catch (error) {
      if (error instanceof TypeError && safeToRetryNetworkError && attempt < RETRY_DELAYS_MS.length) {
        onRetry();
        await waitBeforeRetry(attempt);
        continue;
      }
      if (error instanceof TypeError && /fetch|network/i.test(error.message)) {
        throw new Error("The network request failed or was blocked. Check connectivity and API CORS settings.");
      }
      throw error;
    }

    const proxyFailure = await isProxyConnectionFailure(response);
    const retryableResponse =
      safeToRetryNetworkError && (proxyFailure || [502, 503, 504].includes(response.status));
    if (!retryableResponse) {
      if (!safeToRetryNetworkError && response.ok) {
        cacheGeneration += 1;
        getCache.clear();
        inFlightGets.clear();
      }
      return response;
    }
    if (attempt >= RETRY_DELAYS_MS.length) {
      throw new Error(`The backend is still unavailable (HTTP ${response.status}). Please try again.`);
    }
    onRetry();
    await waitBeforeRetry(attempt);
  }
}

async function requestUncached<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = getAuthToken();
  const headers: Record<string, string> = { ...(options.headers as Record<string, string>) };
  if (!(options.body instanceof FormData) && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const wakeTimer = setTimeout(() => _setWaking(true), WAKE_UP_THRESHOLD_MS);

  try {
    const response = await fetchWithRetry(apiUrl(endpoint), {
      ...options,
      headers,
    });
    clearTimeout(wakeTimer);
    _setWaking(false);

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      let message = errorData?.error?.message;
      if (!message) {
        const detail = errorData?.detail;
        if (typeof detail === "string") {
          message = detail;
        } else if (Array.isArray(detail)) {
          message = detail
            .map((e: any) => {
              const field = Array.isArray(e.loc)
                ? e.loc.filter((s: any) => s !== "body").join(".")
                : "";
              return field ? `${field}: ${e.msg}` : e.msg;
            })
            .join("; ");
        } else if (detail && typeof detail === "object") {
          message = (detail as any).message || JSON.stringify(detail);
        }
      }
      if (response.status === 401) {
        throw new Error(message || "Your session is invalid or has expired. Sign in again.");
      }
      if (response.status === 403) throw new Error(message || "You do not have permission to do that.");
      if (response.status >= 500) {
        throw new Error(`The server returned HTTP ${response.status}. Please try again later.`);
      }
      throw new Error(message || `Request failed (${response.status})`);
    }

    return response.json();
  } catch (err) {
    clearTimeout(wakeTimer);
    _setWaking(false);
    throw err;
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const method = (options.method || "GET").toUpperCase();
  if (method !== "GET" || endpoint.startsWith("/jobs/")) {
    return requestUncached<T>(endpoint, options);
  }

  const token = getAuthToken() || "anonymous";
  const key = `${token}:${endpoint}`;
  const cached = getCache.get(key);
  if (cached && cached.expiresAt > Date.now()) {
    return cached.value as T;
  }

  const pending = inFlightGets.get(key);
  if (pending) return pending as Promise<T>;

  const generation = cacheGeneration;
  const requestPromise = requestUncached<T>(endpoint, options)
    .then((value) => {
      if (generation === cacheGeneration) {
        getCache.set(key, { value, expiresAt: Date.now() + GET_CACHE_TTL_MS });
      }
      if (getCache.size > 100) {
        const oldestKey = getCache.keys().next().value;
        if (oldestKey) getCache.delete(oldestKey);
      }
      return value;
    })
    .finally(() => {
      if (inFlightGets.get(key) === requestPromise) inFlightGets.delete(key);
    });
  inFlightGets.set(key, requestPromise);
  return requestPromise;
}

export const api = {
  get: <T,>(endpoint: string) => request<T>(endpoint, { method: "GET" }),
  post: <T,>(endpoint: string, data: any) =>
    request<T>(endpoint, { method: "POST", body: JSON.stringify(data) }),
  put: <T,>(endpoint: string, data: any) =>
    request<T>(endpoint, { method: "PUT", body: JSON.stringify(data) }),
  upload: <T,>(endpoint: string, data: FormData) =>
    request<T>(endpoint, { method: "POST", body: data }),
};

export interface JobStatus<T = unknown> {
  id: number;
  type: string;
  status: "pending" | "running" | "completed" | "failed";
  progress_text: string;
  result: T | null;
  error: string | null;
}

export async function waitForJob<T>(
  jobId: number,
  onProgress?: (progress: string) => void,
): Promise<T> {
  for (;;) {
    const job = await api.get<JobStatus<T>>(`/jobs/${jobId}`);
    onProgress?.(job.progress_text);
    if (job.status === "completed" && job.result !== null) return job.result;
    if (job.status === "failed") {
      throw new Error(job.error || "Background job failed.");
    }
    await new Promise((resolve) => window.setTimeout(resolve, 600));
  }
}

// ── Progress hook ─────────────────────────────────────────────────────────────
/**
 * Returns [progressMessage, runWithProgress].
 * Call runWithProgress(key, asyncFn) to display a standard message while
 * awaiting a long-running operation.
 */
export function useProgress(): [string | null, <T,>(key: ProgressKey, fn: () => Promise<T>) => Promise<T>] {
  const [message, setMessage] = useState<string | null>(null);

  const run = useCallback(async <T,>(key: ProgressKey, fn: () => Promise<T>): Promise<T> => {
    setMessage(PROGRESS_MESSAGES[key]);
    try {
      return await fn();
    } finally {
      setMessage(null);
    }
  }, []);

  return [message, run];
}
