import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Shield } from "lucide-react";
import { AppShell } from "../components/AppShell";
import { useAuth, User } from "../lib/auth";

function roleLabel(role: User["role"]): string {
  switch (role) {
    case "chairman":
      return "Chairman";
    case "principal":
      return "Principal";
    case "hod":
      return "HOD";
    case "teacher":
      return "Teacher";
    case "student":
      return "Student";
  }
}

function initials(name: string): string {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0].toUpperCase())
    .join("");
}

const DEV_ACCOUNTS = [
  { username: "chairman", label: "Chairman", role: "chairman" },
  { username: "principal", label: "Principal", role: "principal" },
  { username: "hod", label: "HOD", role: "hod" },
  { username: "teacher", label: "Teacher", role: "teacher" },
  { username: "aniket", label: "Aniket", role: "student" },
  { username: "sujal", label: "Sujal", role: "student" },
];

export const Profile: React.FC = () => {
  const navigate = useNavigate();
  const { user, login, logout } = useAuth();
  const [switching, setSwitching] = useState(false);

  const handleSignOut = () => {
    logout();
    navigate("/login", { replace: true });
  };

  const handleQuickSwitch = async (username: string) => {
    setSwitching(true);
    try {
      const res = await fetch("/api/v1/auth/dev/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username }),
      });
      if (res.ok) {
        const data = await res.json();
        const meRes = await fetch("/api/v1/auth/me", {
          headers: { Authorization: `Bearer ${data.access_token}` },
        });
        if (meRes.ok) {
          const userData = await meRes.json();
          login(data.access_token, userData);
          navigate("/");
        }
      }
    } catch {
      alert("Failed to switch development role.");
    } finally {
      setSwitching(false);
    }
  };

  return (
    <AppShell
      pageTitle="Account &amp; Role"
      pageSubtitle="University identity, access permissions, and session credentials."
    >
      {!user ? (
        <div className="py-12 font-serif italic text-ink-soft text-center text-15">
          Loading account profile…
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left: Account details (7 cols) */}
          <div className="lg:col-span-7 space-y-6">
            <div className="editorial-card-raised p-6 space-y-5">
              <div className="flex items-center gap-4 pb-4 border-b border-rule">
                <div className="monogram w-12 h-12 rounded-sm bg-tint text-ink border border-rule font-serif text-18 font-medium">
                  {initials(user.name)}
                </div>
                <div>
                  <h3 className="font-serif text-20 text-ink">{user.name}</h3>
                  <div className="editorial-tag editorial-tag-accent mt-1 text-9 px-2 py-0.5">
                    {roleLabel(user.role).toUpperCase()}
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-13 font-sans">
                <div className="p-3 bg-paper border border-rule rounded-sm">
                  <span className="label text-ink-faint block mb-1 text-10">Email Address</span>
                  <span className="font-serif text-ink text-14">{user.email}</span>
                </div>
                <div className="p-3 bg-paper border border-rule rounded-sm">
                  <span className="label text-ink-faint block mb-1 text-10">System User ID</span>
                  <span className="font-mono text-ink text-14">#{user.id}</span>
                </div>
                <div className="p-3 bg-paper border border-rule rounded-sm">
                  <span className="label text-ink-faint block mb-1 text-10">Institution Domain</span>
                  <span className="font-serif text-ink text-14">
                    {user.email.split("@")[1] || "university.com"}
                  </span>
                </div>
                <div className="p-3 bg-paper border border-rule rounded-sm">
                  <span className="label text-ink-faint block mb-1 text-10">Account Authority</span>
                  <span className="font-serif text-ink text-14">{roleLabel(user.role)}</span>
                </div>
              </div>
            </div>

            {/* Role Permissions Matrix */}
            <div className="editorial-card-raised p-6 space-y-4">
              <div className="flex items-center gap-2 border-b border-rule pb-3">
                <Shield size={16} className="text-accent" />
                <h3 className="font-serif text-16 text-ink">
                  Role Authority Matrix: {roleLabel(user.role)}
                </h3>
              </div>

              <div className="space-y-2.5 text-13 font-sans divide-y divide-rule/60">
                <div className="pt-2.5 flex items-center justify-between">
                  <span className="text-ink">Create Meeting Requests</span>
                  {["chairman", "principal", "hod", "teacher"].includes(user.role) ? (
                    <span className="editorial-tag editorial-tag-ok text-9 px-1.5 py-0.5">AUTHORIZED</span>
                  ) : (
                    <span className="editorial-tag editorial-tag-default text-9 px-1.5 py-0.5">RESTRICTED</span>
                  )}
                </div>

                <div className="pt-2.5 flex items-center justify-between">
                  <span className="text-ink">Approve Agendas &amp; Meeting Minutes</span>
                  {["chairman", "principal", "hod"].includes(user.role) ? (
                    <span className="editorial-tag editorial-tag-ok text-9 px-1.5 py-0.5">AUTHORIZED</span>
                  ) : (
                    <span className="editorial-tag editorial-tag-default text-9 px-1.5 py-0.5">RESTRICTED</span>
                  )}
                </div>

                <div className="pt-2.5 flex items-center justify-between">
                  <span className="text-ink">Inspect Autonomous Agent Traces</span>
                  {["chairman", "principal", "hod"].includes(user.role) ? (
                    <span className="editorial-tag editorial-tag-ok text-9 px-1.5 py-0.5">AUTHORIZED</span>
                  ) : (
                    <span className="editorial-tag editorial-tag-default text-9 px-1.5 py-0.5">RESTRICTED</span>
                  )}
                </div>

                <div className="pt-2.5 flex items-center justify-between">
                  <span className="text-ink">Campus Facility Administration</span>
                  {["chairman", "principal"].includes(user.role) ? (
                    <span className="editorial-tag editorial-tag-ok text-9 px-1.5 py-0.5">AUTHORIZED</span>
                  ) : (
                    <span className="editorial-tag editorial-tag-default text-9 px-1.5 py-0.5">RESTRICTED</span>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Right: Quick Role Switcher (5 cols) */}
          <div className="lg:col-span-5 space-y-6">
            <div className="editorial-card-raised p-6 space-y-3">
              <span className="label text-ink-faint block text-10">Developer Role Switcher</span>
              <p className="font-sans text-12 text-ink-soft leading-relaxed">
                Instantly switch accounts in development to test role-based permissions:
              </p>

              <div className="space-y-1.5 pt-1">
                {DEV_ACCOUNTS.map((acc) => (
                  <button
                    key={acc.username}
                    type="button"
                    disabled={switching || user.email.startsWith(acc.username)}
                    onClick={() => handleQuickSwitch(acc.username)}
                    className={`w-full p-2.5 rounded-sm text-left flex items-center justify-between text-12 font-sans border transition-all ${
                      user.email.startsWith(acc.username)
                        ? "bg-tint border-ink text-ink font-medium shadow-sm"
                        : "bg-paper border-rule text-ink-soft hover:border-ink hover:text-ink hover:bg-tint/30"
                    }`}
                  >
                    <span>{acc.label}</span>
                    <span className="editorial-tag editorial-tag-default text-9 px-1.5 py-0.5">
                      {acc.role.toUpperCase()}
                    </span>
                  </button>
                ))}
              </div>
            </div>

            <div className="editorial-card-raised p-6 space-y-3">
              <span className="label text-ink-faint block text-10">Session Actions</span>
              <p className="font-sans text-12 text-ink-soft leading-relaxed">
                End your authenticated session on this workstation.
              </p>
              <button
                type="button"
                onClick={handleSignOut}
                className="btn-secondary text-12 text-accent py-2 px-3"
              >
                Sign out of account
              </button>
            </div>
          </div>
        </div>
      )}
    </AppShell>
  );
};
