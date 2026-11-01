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

  const controller = new AbortController();
  const wakeTimer = setTimeout(() => _setWaking(true), WAKE_UP_THRESHOLD_MS);

  try {
    const response = await fetch(`${BASE_URL}${endpoint}`, {
      ...options,
      headers,
      signal: controller.signal,
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
      throw new Error(message || `Request failed (${response.status})`);
    }

    return response.json();
  } catch (err) {
    clearTimeout(wakeTimer);
    _setWaking(false);
    throw err;
  }
}

export const api = {
  get: <T,>(endpoint: string) => request<T>(endpoint, { method: "GET" }),
  post: <T,>(endpoint: string, data: any) =>
    request<T>(endpoint, { method: "POST", body: JSON.stringify(data) }),
  put: <T,>(endpoint: string, data: any) =>
    request<T>(endpoint, { method: "PUT", body: JSON.stringify(data) }),
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
