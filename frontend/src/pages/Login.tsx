import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { ThemeToggle } from "../components/ThemeToggle";
import "./Login.css";

const API_BASE_URL = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL.replace(/\/$/, "")}/api/v1`
  : "/api/v1";

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

export const Login: React.FC = () => {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const { login } = useAuth();
  const navigate = useNavigate();

  const completeLogin = async (token: string) => {
    const meRes = await fetch(`${API_BASE_URL}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!meRes.ok) throw new Error("Could not load profile after sign in.");
    const userData = await meRes.json();
    login(token, userData);
    navigate("/");
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData?.detail || "Invalid username or password.");
      }
      const data = await res.json();
      await completeLogin(data.access_token);
    } catch (err: any) {
      setError(err.message || "The authentication service could not be reached.");
    } finally {
      setLoading(false);
    }
  };

  const handleQuickLogin = async (devUsername: string) => {
    setError(null);
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/auth/dev/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: devUsername }),
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData?.detail || "Could not start a development session.");
      }
      const data = await res.json();
      await completeLogin(data.access_token);
    } catch (err: any) {
      setError(err.message || "The authentication service could not be reached.");
    } finally {
      setLoading(false);
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
                <span>{loading ? "Signing in…" : "Sign in"}</span>
                <span aria-hidden="true">↗</span>
              </button>
            </form>

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
