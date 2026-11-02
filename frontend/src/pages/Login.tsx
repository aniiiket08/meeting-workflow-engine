import React, { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiUrl } from "../api/client";
import { useAuth } from "../lib/auth";
import type { User } from "../lib/auth";
import { ThemeToggle } from "../components/ThemeToggle";
import "./Login.css";

const DEV_LOGIN_ROLES = [
  { username: "chairman", label: "Chairman" },
  { username: "principal", label: "Principal" },
  { username: "hod", label: "HOD" },
  { username: "teacher", label: "Teacher" },
  { username: "aniket", label: "Aniket" },
  { username: "sujal", label: "Sujal" },
  { username: "viraj", label: "Viraj" },
  { username: "sarvesh", label: "Sarvesh" },
] as const;

const IS_DEV = import.meta.env?.VITE_APP_ENV === "development";
const READY_RETRY_DELAYS_MS = [500, 1000, 2000, 4000, 8000];
const READY_REQUEST_TIMEOUT_MS = 2500;
const LOGIN_REQUEST_TIMEOUT_MS = 15000;

interface LoginResponse {
  access_token: string;
  user?: User;
}

let readinessPromise: Promise<void> | null = null;
let backendReadyUntil = 0;

const getLoginErrorMessage = (error: unknown): string => {
  return error instanceof Error
    ? error.message
    : "The authentication request failed unexpectedly. Please try again.";
};

const isTransientReadinessError = (error: unknown): boolean =>
  error instanceof TypeError ||
  (error instanceof Error && error.message === "Backend readiness request timed out.");

const fetchWithTimeout = async (
  url: string,
  options: RequestInit,
  timeoutMs: number,
): Promise<Response> => {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } catch (error) {
    if (controller.signal.aborted) {
      throw new Error("Backend readiness request timed out.");
    }
    throw error;
  } finally {
    window.clearTimeout(timeoutId);
  }
};

const waitForBackendReady = async (onRetry: () => void): Promise<void> => {
  let lastError: Error = new Error("The backend did not become ready.");
  for (let attempt = 0; attempt <= READY_RETRY_DELAYS_MS.length; attempt += 1) {
    try {
      const response = await fetchWithTimeout(
        apiUrl("/ready"),
        { method: "GET", headers: { Accept: "application/json" } },
        READY_REQUEST_TIMEOUT_MS,
      );
      const contentType = response.headers.get("content-type") || "";
      if (response.status === 500 && contentType.includes("text/plain")) {
        const body = await response.clone().text();
        if (/http proxy error|ECONNREFUSED|ECONNRESET|ETIMEDOUT|socket hang up/i.test(body)) {
          lastError = new Error(`Backend connection failed (HTTP ${response.status}).`);
        } else {
          throw new Error(`Backend readiness check failed (HTTP ${response.status}).`);
        }
      } else if ([502, 503, 504].includes(response.status)) {
        lastError = new Error(`Backend is starting or unavailable (HTTP ${response.status}).`);
      } else if (!response.ok) {
        throw new Error(`Backend readiness check failed (HTTP ${response.status}).`);
      } else if (!contentType.includes("application/json")) {
        throw new Error("The configured API URL did not return the backend readiness endpoint. Check VITE_API_URL.");
      } else {
        let data: { status?: string };
        try {
          data = await response.json();
        } catch {
          throw new Error("The configured API URL returned an invalid readiness response. Check VITE_API_URL.");
        }
        if (data.status !== "ready") {
          throw new Error("The backend responded but is not ready yet.");
        }
        return;
      }
    } catch (error) {
      if (!isTransientReadinessError(error)) throw error;
      lastError = error instanceof Error
        ? error
        : new Error("The network request failed or was blocked by CORS.");
    }

    if (attempt === READY_RETRY_DELAYS_MS.length) break;
    onRetry();
    await new Promise((resolve) => window.setTimeout(resolve, READY_RETRY_DELAYS_MS[attempt]));
  }

  if (lastError.message === "Backend readiness request timed out.") {
    throw new Error("The backend did not become ready in time. No login request was sent; try again.");
  }
  if (lastError instanceof TypeError) {
    throw new Error("Could not reach the backend. Check the API URL, network connection, and CORS settings. No login request was sent.");
  }
  throw new Error(`${lastError.message} No login request was sent.`);
};

const prepareBackend = (onRetry: () => void): Promise<void> => {
  if (backendReadyUntil > Date.now()) return Promise.resolve();
  if (!readinessPromise) {
    const pending = waitForBackendReady(onRetry).then(() => {
      backendReadyUntil = Date.now() + 15000;
    });
    readinessPromise = pending.finally(() => {
      readinessPromise = null;
    });
  }
  return readinessPromise;
};

const fetchAuth = async (url: string, options: RequestInit): Promise<Response> => {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), LOGIN_REQUEST_TIMEOUT_MS);
  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } catch (error) {
    if (controller.signal.aborted) {
      throw new Error("The login request timed out. It was not retried; please try again.");
    }
    if (error instanceof TypeError) {
      throw new Error("The network request failed or was blocked by CORS. Check the API URL and connection.");
    }
    throw error;
  } finally {
    window.clearTimeout(timeoutId);
  }
};

export const Login: React.FC = () => {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [retrying, setRetrying] = useState(false);
  const [readinessMessage, setReadinessMessage] = useState<string | null>(null);
  const isSubmitting = useRef(false);

  const { login } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    let active = true;
    prepareBackend(() => {
      if (active) setRetrying(true);
    })
      .then(() => {
        if (active) setRetrying(false);
      })
      .catch((readinessError: unknown) => {
        if (active) {
          setRetrying(false);
          setReadinessMessage(getLoginErrorMessage(readinessError));
        }
      });
    return () => {
      active = false;
    };
  }, []);

  const completeLogin = async (token: string) => {
    const meRes = await fetchAuth(apiUrl("/auth/me"), {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!meRes.ok) throw new Error("Could not load profile after sign in.");
    const userData = await meRes.json();
    login(token, userData);
    navigate("/");
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isSubmitting.current) return;
    isSubmitting.current = true;
    setError(null);
    setReadinessMessage(null);
    setLoading(true);
    try {
      await prepareBackend(() => setRetrying(true));
      const res = await fetchAuth(
        apiUrl("/auth/login"),
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ username, password }),
        },
      );
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        if (res.status === 401) {
          throw new Error(errData?.detail || "Incorrect username or password.");
        }
        if (res.status === 403) {
          throw new Error(errData?.detail || "You are not allowed to sign in.");
        }
        if (res.status >= 500) {
          throw new Error(`The authentication service returned HTTP ${res.status}. Please try again later.`);
        }
        throw new Error(errData?.detail || `Sign in failed (HTTP ${res.status}).`);
      }
      const data: LoginResponse = await res.json();
      if (data.user) {
        login(data.access_token, data.user);
        navigate("/");
      } else {
        await completeLogin(data.access_token);
      }
    } catch (err: unknown) {
      setError(getLoginErrorMessage(err));
    } finally {
      setLoading(false);
      setRetrying(false);
      isSubmitting.current = false;
    }
  };

  const handleQuickLogin = async (devUsername: string) => {
    if (isSubmitting.current) return;
    isSubmitting.current = true;
    setError(null);
    setReadinessMessage(null);
    setLoading(true);
    try {
      await prepareBackend(() => setRetrying(true));
      const res = await fetchAuth(
        apiUrl("/auth/dev/login"),
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ username: devUsername }),
        },
      );
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData?.detail || "Could not start a development session.");
      }
      const data: LoginResponse = await res.json();
      if (data.user) {
        login(data.access_token, data.user);
        navigate("/");
      } else {
        await completeLogin(data.access_token);
      }
    } catch (err: unknown) {
      setError(getLoginErrorMessage(err));
    } finally {
      setLoading(false);
      setRetrying(false);
      isSubmitting.current = false;
    }
  };

  return (
    <div className="login-shell">
      <header className="login-topbar">
        <span className="login-brand">WORKLET 04</span>
        <ThemeToggle />
      </header>

      <main className="login-main">
        <section className="login-intro" aria-labelledby="login-intro-title">
          <h1 id="login-intro-title">
            Meeting
            <br />
            Workflow
            <br />
            Engine
          </h1>
          <p className="login-intro-description">
            Meetings, minuted and followed through.
          </p>
        </section>

        <section className="login-access" aria-labelledby="login-title">
          <div className="login-access-inner">
            <p className="login-kicker">YOUR WORKSPACE</p>
            <h2 id="login-title">Welcome back.</h2>
            <p className="login-access-description">
              Sign in with your organization account to continue.
            </p>

            {error && (
              <div className="login-error" role="alert" aria-live="polite">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="login-form" noValidate>
              <div className="login-field">
                <label htmlFor="login-username">Username or email</label>
                <input
                  id="login-username"
                  type="text"
                  required
                  autoComplete="username"
                  autoCapitalize="none"
                  spellCheck={false}
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                />
              </div>

              <div className="login-field">
                <label htmlFor="login-password">Password</label>
                <input
                  id="login-password"
                  type="password"
                  required
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </div>

              <button type="submit" disabled={loading} className="login-submit">
                <span>{loading ? (retrying ? "Reconnecting…" : "Signing in…") : "Sign in"}</span>
                <span aria-hidden="true">↗</span>
              </button>
            </form>

            {(retrying || readinessMessage) && (
              <p className="login-retry-status" role="status" aria-live="polite">
                {retrying
                  ? "Waiting for the backend to become ready. Sign-in will only be sent once."
                  : `${readinessMessage} Sign-in will check again when submitted.`}
              </p>
            )}

            {IS_DEV && (
              <div className="login-dev-access">
                <p className="login-dev-heading">DEVELOPMENT ACCESS</p>
                <div className="login-dev-roles">
                  {DEV_LOGIN_ROLES.map((role) => (
                    <button
                      key={role.username}
                      type="button"
                      disabled={loading}
                      onClick={() => handleQuickLogin(role.username)}
                    >
                      {role.label}
                    </button>
                  ))}
                </div>
              </div>
            )}

            <p className="login-access-note">
              Access is managed by your organization administrator.
            </p>
          </div>
        </section>
      </main>

      <footer className="login-bottom">
        <span>MEETINGS · DECISIONS · FOLLOW-THROUGH</span>
      </footer>
    </div>
  );
};
