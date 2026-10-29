import React, { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Calendar, Plus, Search, Trash2 } from "lucide-react";
import { api } from "../api/client";
import { AppShell } from "../components/AppShell";
import { StageTracker } from "../components/StageTracker";
import { useAuth } from "../lib/auth";

interface Meeting {
  id: number;
  title: string;
  description: string | null;
  duration_minutes: number;
  start_time: string | null;
  end_time: string | null;
  status: string;
  created_at: string;
}

function formatDateHuman(iso: string | null): string {
  if (!iso) return "Unscheduled";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "Unscheduled";
  return d
    .toLocaleString("en-GB", {
      weekday: "short",
      day: "numeric",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    })
    .replace(",", "");
}

function statusBadge(status: string) {
  switch (status) {
    case "minutes_approved":
    case "agenda_approved":
      return (
        <span className="editorial-tag editorial-tag-ok">
          <span className="status-marker bg-ok" />
          {status.replace(/_/g, " ")}
        </span>
      );
    case "requested":
    case "slots_proposed":
      return (
        <span className="editorial-tag editorial-tag-warn">
          <span className="status-marker bg-warn" />
          {status.replace(/_/g, " ")}
        </span>
      );
    case "discarded":
      return (
        <span className="editorial-tag editorial-tag-accent">
          <span className="status-marker bg-accent" />
          discarded
        </span>
      );
    default:
      return (
        <span className="editorial-tag editorial-tag-default">
          <span className="status-marker bg-ink-faint" />
          {status.replace(/_/g, " ")}
        </span>
      );
  }
}

export const MeetingsList: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const canCreate = user && ["chairman", "principal", "hod", "teacher"].includes(user.role);
  const canDiscard = user && ["chairman", "principal", "hod"].includes(user.role);

  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters & Search
  const [search, setSearch] = useState("");
  const [tabFilter, setTabFilter] = useState<"all" | "pending" | "scheduled" | "completed" | "discarded">("all");

  useEffect(() => {
    fetchMeetings();
  }, []);

  const fetchMeetings = () => {
    setLoading(true);
    api
      .get<Meeting[]>("/meetings")
      .then((data) => setMeetings(data))
      .catch((err) => setError(err.message || "Could not load meetings."))
      .finally(() => setLoading(false));
  };

  const handleDiscard = async (e: React.MouseEvent, meetingId: number) => {
    e.stopPropagation();
    if (!window.confirm("Are you sure you want to discard this meeting?")) return;
    try {
      await api.post(`/meetings/${meetingId}/discard`, {});
      setMeetings((prev) =>
        prev.map((m) => (m.id === meetingId ? { ...m, status: "discarded" } : m))
      );
    } catch (err: any) {
      alert(err.message || "Failed to discard meeting.");
    }
  };

  const filteredMeetings = useMemo(() => {
    return meetings.filter((m) => {
      // Tab filter
      if (tabFilter === "pending") {
        if (!["requested", "slots_proposed", "agenda_drafted"].includes(m.status)) return false;
      } else if (tabFilter === "scheduled") {
        if (!["agenda_approved", "room_booked"].includes(m.status)) return false;
      } else if (tabFilter === "completed") {
        if (m.status !== "minutes_approved") return false;
      } else if (tabFilter === "discarded") {
        if (m.status !== "discarded") return false;
      } else {
        if (m.status === "discarded" && !search.trim()) {
          return false;
        }
      }

      // Search query
      if (search.trim()) {
        const q = search.toLowerCase();
        const matchesTitle = m.title.toLowerCase().includes(q);
        const matchesStatus = m.status.toLowerCase().includes(q);
        const matchesDesc = (m.description || "").toLowerCase().includes(q);
        return matchesTitle || matchesStatus || matchesDesc;
      }

      return true;
    });
  }, [meetings, tabFilter, search]);

  return (
    <AppShell
      pageTitle="Meetings"
      pageSubtitle="All scheduled, pending approval, and past recorded sessions."
      actionButton={
        canCreate && (
          <button
            type="button"
            onClick={() => navigate("/meetings/new")}
            className="btn-primary flex items-center gap-1.5"
          >
            <Plus size={14} />
            <span>Schedule Meeting</span>
          </button>
        )
      }
    >
      <div className="space-y-6">
        {/* ── Search & Filter Controls ─────────────────────────── */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          {/* Search box */}
          <div className="relative flex-1 max-w-md">
            <Search
              size={15}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-faint"
            />
            <input
              type="text"
              placeholder="Search by title, topic, or status…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full bg-surface border border-rule rounded-sm pl-9 pr-3 py-1.5 text-13 font-sans text-ink focus:border-ink outline-none transition-colors"
            />
            {search && (
              <button
                type="button"
                onClick={() => setSearch("")}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-11 text-ink-faint hover:text-ink"
              >
                Clear
              </button>
            )}
          </div>

          {/* Counts label */}
          <div className="font-mono text-11 text-ink-faint">
            Showing {filteredMeetings.length} of {meetings.length} sessions
          </div>
        </div>

        {/* ── Filter Tabs ───────────────────────────────────────── */}
        <div className="editorial-tabs">
          <button
            type="button"
            className={`editorial-tab ${tabFilter === "all" ? "active" : ""}`}
            onClick={() => setTabFilter("all")}
          >
            All Active
          </button>
          <button
            type="button"
            className={`editorial-tab ${tabFilter === "pending" ? "active" : ""}`}
            onClick={() => setTabFilter("pending")}
          >
            Pending Approval
          </button>
          <button
            type="button"
            className={`editorial-tab ${tabFilter === "scheduled" ? "active" : ""}`}
            onClick={() => setTabFilter("scheduled")}
          >
            Scheduled
          </button>
          <button
            type="button"
            className={`editorial-tab ${tabFilter === "completed" ? "active" : ""}`}
            onClick={() => setTabFilter("completed")}
          >
            Minutes Approved
          </button>
          <button
            type="button"
            className={`editorial-tab ${tabFilter === "discarded" ? "active" : ""}`}
            onClick={() => setTabFilter("discarded")}
          >
            Discarded
          </button>
        </div>

        {/* ── Error Banner ─────────────────────────────────────── */}
        {error && (
          <div className="error-banner flex items-center justify-between" role="alert">
            <span>{error}</span>
            <button
              type="button"
              onClick={fetchMeetings}
              className="text-11 font-sans underline ml-4 hover:opacity-80"
            >
              Retry
            </button>
          </div>
        )}

        {/* ── Meetings Table ───────────────────────────────────── */}
        <div className="editorial-card p-0 overflow-hidden">
          {loading ? (
            <div className="py-16 text-center font-serif italic text-ink-soft text-15">
              Loading university meetings…
            </div>
          ) : filteredMeetings.length === 0 ? (
            <div className="py-16 text-center space-y-2">
              <Calendar size={28} className="mx-auto text-ink-faint opacity-60 mb-2" />
              <p className="font-serif italic text-ink-soft text-15">
                No meetings matching your current filter.
              </p>
              {canCreate && (
                <button
                  type="button"
                  onClick={() => navigate("/meetings/new")}
                  className="btn-secondary text-12 inline-block mt-2"
                >
                  Schedule a new meeting
                </button>
              )}
            </div>
          ) : (
            <div className="w-full">
              <table className="w-full table-fixed text-left text-13 border-collapse">
                <thead>
                  <tr className="border-b border-rule-strong bg-surface font-sans text-11 uppercase tracking-wider text-ink-soft">
                    <th className="py-3 px-3 font-medium w-[24%]">Session Title</th>
                    <th className="py-3 px-2.5 font-medium w-[14%] whitespace-nowrap">Scheduled Time</th>
                    <th className="py-3 px-2 font-medium w-[7%] whitespace-nowrap">Duration</th>
                    <th className="py-3 px-2 font-medium hidden md:table-cell w-[19%]">Lifecycle Stage</th>
                    <th className="py-3 px-2 font-medium w-[15%] whitespace-nowrap">Status</th>
                    <th className="py-3 px-3 font-medium text-right w-[21%] whitespace-nowrap">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-rule font-sans">
                  {filteredMeetings.map((m) => (
                    <tr
                      key={m.id}
                      onClick={() => navigate(`/meetings/${m.id}`)}
                      className="table-row-hover group cursor-pointer transition-colors"
                    >
                      <td className="py-3 px-3 font-serif text-ink">
                        <div className="font-medium text-14 group-hover:text-accent transition-colors truncate">
                          {m.title}
                        </div>
                        {m.description && (
                          <div className="font-sans text-12 text-ink-faint truncate mt-0.5">
                            {m.description}
                          </div>
                        )}
                      </td>

                      <td className="py-3 px-2.5 font-mono text-12 text-ink-soft whitespace-nowrap">
                        {formatDateHuman(m.start_time)}
                      </td>

                      <td className="py-3 px-2 font-mono text-12 text-ink-soft whitespace-nowrap">
                        {m.duration_minutes}m
                      </td>

                      <td className="py-3 px-2 hidden md:table-cell">
                        <StageTracker status={m.status} meetingId={m.id} />
                      </td>

                      <td className="py-3 px-2 whitespace-nowrap">
                        {statusBadge(m.status)}
                      </td>

                      <td className="py-3 px-3 text-right whitespace-nowrap">
                        <div
                          className="inline-flex items-center justify-end gap-1 flex-nowrap"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <Link
                            to={`/meetings/${m.id}`}
                            className="text-11 font-sans text-ink-soft hover:text-ink px-2 py-0.5 rounded border border-rule hover:border-ink transition-colors shrink-0"
                          >
                            Details
                          </Link>
                          <Link
                            to={`/meetings/${m.id}/agenda`}
                            className="text-11 font-sans text-ink-soft hover:text-ink px-2 py-0.5 rounded border border-rule hover:border-ink transition-colors shrink-0"
                          >
                            Agenda
                          </Link>
                          <Link
                            to={`/meetings/${m.id}/minutes`}
                            className="text-11 font-sans text-ink-soft hover:text-ink px-2 py-0.5 rounded border border-rule hover:border-ink transition-colors shrink-0"
                          >
                            Minutes
                          </Link>
                          {canDiscard && m.status !== "discarded" && (
                            <button
                              type="button"
                              onClick={(e) => handleDiscard(e, m.id)}
                              className="text-11 font-sans text-accent hover:opacity-75 p-0.5 shrink-0 ml-0.5"
                              title="Discard meeting"
                              aria-label="Discard meeting"
                            >
                              <Trash2 size={13} />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
};
