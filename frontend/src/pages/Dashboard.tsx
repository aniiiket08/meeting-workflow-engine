import React, { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ExternalLink, Plus } from "lucide-react";
import { api } from "../api/client";
import { AppShell } from "../components/AppShell";
import { useAuth, User } from "../lib/auth";

type HomeRole = "admin" | "approver" | "coordinator" | "attendee";

interface Meeting {
  id: number;
  title: string;
  duration_minutes: number;
  start_time: string | null;
  end_time: string | null;
  status: string;
  created_at: string;
  created_by_id: number | null;
}

interface ActionItem {
  id: number;
  meeting_id: number;
  description: string;
  owner_email: string | null;
  owner_name: string | null;
  due_date: string | null;
  priority: string;
  status: string;
  created_at: string | null;
}

function roleKind(role: User["role"]): HomeRole {
  switch (role) {
    case "chairman":
      return "admin";
    case "principal":
    case "hod":
      return "approver";
    case "teacher":
      return "coordinator";
    case "student":
      return "attendee";
  }
}

function parseDate(iso: string | null): Date | null {
  if (!iso) return null;
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? null : d;
}

function isSameWeek(d: Date, now: Date): boolean {
  const start = new Date(now);
  const dow = (start.getDay() + 6) % 7;
  start.setDate(start.getDate() - dow);
  start.setHours(0, 0, 0, 0);
  const end = new Date(start);
  end.setDate(end.getDate() + 7);
  return d >= start && d < end;
}

function isSameMonth(d: Date, now: Date): boolean {
  return d.getFullYear() === now.getFullYear() && d.getMonth() === now.getMonth();
}

function formatMeetDate(iso: string | null): string {
  const d = parseDate(iso);
  if (!d) return "Unscheduled";
  return d
    .toLocaleString("en-GB", {
      weekday: "short",
      day: "numeric",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
    })
    .replace(",", "");
}

function formatDueLabel(
  due: Date | null,
  now: Date
): { label: string; tone: "warn" | "ok" | "accent" | "faint" } {
  if (!due) return { label: "No date", tone: "faint" };
  const days = Math.floor((due.getTime() - now.getTime()) / 86400000);
  if (days < 0) return { label: `${Math.abs(days)}d overdue`, tone: "accent" };
  if (days === 0) return { label: "Today", tone: "warn" };
  if (days <= 7) return { label: `${days}d`, tone: "warn" };
  return {
    label: due.toLocaleDateString("en-GB", { day: "numeric", month: "short" }),
    tone: "faint",
  };
}

export const Dashboard: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [actions, setActions] = useState<ActionItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const now = useMemo(() => new Date(), []);
  const role = user ? roleKind(user.role) : "attendee";

  useEffect(() => {
    setLoading(true);
    Promise.all([
      api.get<Meeting[]>("/meetings").catch(() => []),
      api.get<ActionItem[]>("/actions").catch(() => []),
    ])
      .then(([m, a]) => {
        setMeetings(m);
        setActions(a);
      })
      .catch((err) => setError(err.message || "Failed to load dashboard data."))
      .finally(() => setLoading(false));
  }, []);

  // Filtered sets
  const waitingMeetings = useMemo(() => {
    return meetings.filter((m) =>
      ["requested", "slots_proposed", "agenda_drafted"].includes(m.status)
    );
  }, [meetings]);

  const thisWeekMeetings = useMemo(() => {
    return meetings.filter((m) => {
      const d = parseDate(m.start_time);
      return d && isSameWeek(d, now) && m.status !== "discarded";
    });
  }, [meetings, now]);

  const overdueActions = useMemo(() => {
    return actions.filter((a) => {
      if (a.status === "completed") return false;
      const due = parseDate(a.due_date);
      return due && due.getTime() < now.getTime();
    });
  }, [actions, now]);

  const myActions = useMemo(() => {
    if (!user) return [];
    return actions.filter(
      (a) =>
        a.owner_email?.toLowerCase() === user.email.toLowerCase() &&
        a.status !== "completed"
    );
  }, [actions, user]);

  // Statistics
  const meetingsThisMonth = useMemo(() => {
    return meetings.filter((m) => {
      const d = parseDate(m.start_time);
      return d && isSameMonth(d, now) && m.status !== "discarded";
    }).length;
  }, [meetings, now]);

  const tasksOnTime = useMemo(() => {
    const closed = actions.filter((a) => a.status === "completed").length;
    const total = actions.length;
    return total > 0 ? Math.round((closed / total) * 100) : 100;
  }, [actions]);

  const greetingTitle = useMemo(() => {
    if (!user) return "Dashboard";
    switch (user.role) {
      case "chairman":
        return `Chairman's Dispatch`;
      case "principal":
        return `Principal's Executive Desk`;
      case "hod":
        return `Department Coordination`;
      case "teacher":
        return `Faculty Workspace`;
      case "student":
        return `Student Dashboard`;
    }
  }, [user]);

  return (
    <AppShell
      pageTitle={greetingTitle}
      pageSubtitle={`Welcome, ${user?.name || "Member"}. Here are your university priorities.`}
      actionButton={
        ["admin", "approver", "coordinator"].includes(role) ? (
          <button
            type="button"
            onClick={() => navigate("/meetings/new")}
            className="btn-primary flex items-center gap-1.5"
          >
            <Plus size={14} />
            <span>New Meeting</span>
          </button>
        ) : undefined
      }
    >
      <div className="space-y-8">
        {loading && <div className="loading-bar" aria-hidden="true" />}
        {/* Error */}
        {error && (
          <div className="error-banner mb-4" role="alert">
            {error}
          </div>
        )}

        {/* ── Key Metrics Strip (Spatial elevated cards) ────────────────────── */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="editorial-card-raised p-5 flex flex-col justify-between">
            <div>
              <span className="label text-ink-faint block mb-1.5 text-10">Meetings This Month</span>
              <div className="font-serif text-ink tracking-tight text-32 sm:text-36 font-normal leading-none">{meetingsThisMonth}</div>
            </div>
            <div className="font-mono text-11 text-ink-faint pt-3 border-t border-rule/60 mt-3">
              Scheduled across faculty
            </div>
          </div>

          <div className="editorial-card-raised p-5 flex flex-col justify-between">
            <div>
              <span className="label text-ink-faint block mb-1.5 text-10">Tasks Closed</span>
              <div className="font-serif text-ok tracking-tight text-32 sm:text-36 font-normal leading-none">{tasksOnTime}%</div>
            </div>
            <div className="font-mono text-11 text-ink-faint pt-3 border-t border-rule/60 mt-3">
              On-time resolution rate
            </div>
          </div>

          <div className="editorial-card-raised p-5 flex flex-col justify-between">
            <div>
              <span className="label text-ink-faint block mb-1.5 text-10">Pending Approvals</span>
              <div
                className={`font-serif tracking-tight text-32 sm:text-36 font-normal leading-none ${
                  waitingMeetings.length > 0 ? "text-warn" : "text-ink"
                }`}
              >
                {waitingMeetings.length}
              </div>
            </div>
            <div className="font-mono text-11 text-ink-faint pt-3 border-t border-rule/60 mt-3">
              Awaiting gate validation
            </div>
          </div>

          <div className="editorial-card-raised p-5 flex flex-col justify-between">
            <div>
              <span className="label text-ink-faint block mb-1.5 text-10">Open Action Items</span>
              <div className="font-serif text-ink tracking-tight text-32 sm:text-36 font-normal leading-none">
                {actions.filter((a) => a.status !== "completed").length}
              </div>
            </div>
            <div className="font-mono text-11 text-ink-faint pt-3 border-t border-rule/60 mt-3">
              Active commitments
            </div>
          </div>
        </div>

        {/* ── Main Two-Column Layout ──────────────────────────── */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* Left Column: Work Queues (8 cols) */}
          <div className="lg:col-span-8 space-y-8">
            {/* Section 01: Waiting for approval */}
            {["admin", "approver"].includes(role) && (
              <section className="editorial-card">
                <div className="flex items-center justify-between pb-3 mb-3 border-b border-rule">
                  <div>
                    <span className="label text-accent font-semibold block mb-0.5">
                      01 — Immediate Attention
                    </span>
                    <h3 className="font-serif text-18 text-ink">
                      Sessions Awaiting Approval
                    </h3>
                  </div>
                  <span className="editorial-tag editorial-tag-warn">
                    {waitingMeetings.length} PENDING
                  </span>
                </div>

                {waitingMeetings.length === 0 ? (
                  <p className="font-serif italic text-ink-soft text-13 py-3">
                    No pending meeting requests or minutes awaiting your sign-off.
                  </p>
                ) : (
                  <div className="divide-y divide-rule font-sans text-13">
                    {waitingMeetings.map((m) => (
                      <div
                        key={m.id}
                        className="py-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2 hover:bg-tint/40 px-2 rounded-sm transition-colors"
                      >
                        <div>
                          <Link
                            to={`/meetings/${m.id}`}
                            className="font-serif text-15 font-medium text-ink hover:text-accent transition-colors"
                          >
                            {m.title}
                          </Link>
                          <div className="font-mono text-11 text-ink-faint mt-0.5">
                            Meeting #{m.id} · {m.duration_minutes}m · {m.status.replace("_", " ")}
                          </div>
                        </div>

                        <div className="flex items-center gap-2">
                          <Link
                            to={`/meetings/${m.id}/agenda`}
                            className="text-11 font-sans px-2 py-1 border border-rule hover:border-ink rounded-sm text-ink-soft hover:text-ink transition-colors"
                          >
                            Review Agenda
                          </Link>
                          <Link
                            to={`/meetings/${m.id}/minutes`}
                            className="btn-primary text-11 py-1 px-3"
                          >
                            Review Minutes
                          </Link>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </section>
            )}

            {/* Coordinator Section */}
            {role === "coordinator" && (
              <section className="editorial-card space-y-3">
                <div className="flex items-center justify-between pb-3 border-b border-rule">
                  <h3 className="font-serif text-18 text-ink">Faculty Fast Actions</h3>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
                  <Link
                    to="/meetings/new"
                    className="p-4 bg-paper border border-rule rounded-sm hover:border-ink transition-colors block"
                  >
                    <div className="font-serif text-15 font-medium text-ink">
                      + Propose New Meeting
                    </div>
                    <p className="font-sans text-12 text-ink-soft mt-1">
                      Check room availability and let the scheduling agent rank conflict-free slots.
                    </p>
                  </Link>

                  <Link
                    to="/schedule"
                    className="p-4 bg-paper border border-rule rounded-sm hover:border-ink transition-colors block"
                  >
                    <div className="font-serif text-15 font-medium text-ink">
                      Weekly Calendar &amp; Timetable
                    </div>
                    <p className="font-sans text-12 text-ink-soft mt-1">
                      Find common-availability hours across students and faculty members.
                    </p>
                  </Link>
                </div>
              </section>
            )}

            {/* Section 02: This Week's Sessions */}
            <section className="editorial-card">
              <div className="flex items-center justify-between pb-3 mb-3 border-b border-rule">
                <div>
                  <span className="label text-ink-faint block mb-0.5">
                    02 — Schedule
                  </span>
                  <h3 className="font-serif text-18 text-ink">This Week's Sessions</h3>
                </div>
                <Link to="/meetings" className="text-11 font-sans text-ink-soft hover:underline">
                  View All ({meetings.length})
                </Link>
              </div>

              {thisWeekMeetings.length === 0 ? (
                <p className="font-serif italic text-ink-soft text-13 py-3">
                  No meetings scheduled for the rest of this week.
                </p>
              ) : (
                <div className="divide-y divide-rule font-sans text-13">
                  {thisWeekMeetings.slice(0, 5).map((m) => (
                    <div
                      key={m.id}
                      onClick={() => navigate(`/meetings/${m.id}`)}
                      className="py-3 flex items-center justify-between hover:bg-tint/40 px-2 rounded-sm cursor-pointer transition-colors"
                    >
                      <div className="min-w-0 pr-4">
                        <div className="font-serif text-14 font-medium text-ink truncate">
                          {m.title}
                        </div>
                        <div className="font-mono text-11 text-ink-faint mt-0.5">
                          {formatMeetDate(m.start_time)}
                        </div>
                      </div>

                      <span className="editorial-tag editorial-tag-default shrink-0 text-10">
                        {m.duration_minutes}m
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </section>

            {/* Section 03: Overdue or My Action Items */}
            <section className="editorial-card">
              <div className="flex items-center justify-between pb-3 mb-3 border-b border-rule">
                <div>
                  <span className="label text-ink-faint block mb-0.5">
                    03 — Commitments
                  </span>
                  <h3 className="font-serif text-18 text-ink">
                    {role === "attendee" ? "My Assigned Tasks" : "Critical & Overdue Tasks"}
                  </h3>
                </div>
                <Link to="/actions" className="text-11 font-sans text-ink-soft hover:underline">
                  Action Tracker
                </Link>
              </div>

              {(role === "attendee" ? myActions : overdueActions).length === 0 ? (
                <p className="font-serif italic text-ink-soft text-13 py-3">
                  All action items are up to date with no overdue deadlines.
                </p>
              ) : (
                <div className="divide-y divide-rule font-sans text-13">
                  {(role === "attendee" ? myActions : overdueActions).slice(0, 5).map((a) => {
                    const due = parseDate(a.due_date);
                    const dueBadge = formatDueLabel(due, now);

                    return (
                      <div
                        key={a.id}
                        className="py-2.5 flex items-center justify-between gap-3 hover:bg-tint/40 px-2 rounded-sm"
                      >
                        <div className="min-w-0 flex-1">
                          <div className="font-serif text-14 text-ink truncate">
                            {a.description}
                          </div>
                          <div className="font-mono text-10 text-ink-faint">
                            Owner: {a.owner_name || a.owner_email || "Unassigned"}
                          </div>
                        </div>

                        <span
                          className={`editorial-tag ${
                            dueBadge.tone === "accent"
                              ? "editorial-tag-accent"
                              : dueBadge.tone === "warn"
                              ? "editorial-tag-warn"
                              : "editorial-tag-default"
                          } shrink-0 text-10`}
                        >
                          {dueBadge.label}
                        </span>
                      </div>
                    );
                  })}
                </div>
              )}
            </section>
          </div>

          {/* Right Rail: Quick Telemetry & Shortcuts (4 cols) */}
          <div className="lg:col-span-4 space-y-6">
            {/* Quick Links */}
            <div className="editorial-card space-y-3">
              <span className="label text-ink-faint block">Quick Workflows</span>
              <div className="space-y-1 font-sans text-13">
                <Link
                  to="/memory"
                  className="p-2.5 rounded-sm hover:bg-tint flex items-center justify-between text-ink transition-colors block"
                >
                  <span className="font-serif">Search Meeting Memory</span>
                  <ExternalLink size={13} className="text-ink-faint" />
                </Link>
                <Link
                  to="/actions"
                  className="p-2.5 rounded-sm hover:bg-tint flex items-center justify-between text-ink transition-colors block"
                >
                  <span className="font-serif">Kanban Action Board</span>
                  <ExternalLink size={13} className="text-ink-faint" />
                </Link>
                <Link
                  to="/evaluations"
                  className="p-2.5 rounded-sm hover:bg-tint flex items-center justify-between text-ink transition-colors block"
                >
                  <span className="font-serif">System Quality &amp; WER</span>
                  <ExternalLink size={13} className="text-ink-faint" />
                </Link>
                {["chairman", "principal", "hod"].includes(user?.role || "") && (
                  <Link
                    to="/traces"
                    className="p-2.5 rounded-sm hover:bg-tint flex items-center justify-between text-ink transition-colors block"
                  >
                    <span className="font-serif">Agent Execution Traces</span>
                    <ExternalLink size={13} className="text-ink-faint" />
                  </Link>
                )}
              </div>
            </div>

            {/* Autonomous System Status */}
            <div className="editorial-card space-y-3">
              <span className="label text-ink-faint block">Autonomous Agent Loop</span>
              <div className="space-y-2 text-12 font-sans text-ink-soft">
                <div className="flex items-center justify-between">
                  <span>Scheduler Agent:</span>
                  <span className="editorial-tag editorial-tag-ok text-9">ONLINE</span>
                </div>
                <div className="flex items-center justify-between">
                  <span>Agenda Summarizer:</span>
                  <span className="editorial-tag editorial-tag-ok text-9">ONLINE</span>
                </div>
                <div className="flex items-center justify-between">
                  <span>Grounding Verifier:</span>
                  <span className="editorial-tag editorial-tag-ok text-9">ONLINE</span>
                </div>
                <div className="flex items-center justify-between">
                  <span>Human Gate:</span>
                  <span className="editorial-tag editorial-tag-accent text-9">ENFORCED</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
};
