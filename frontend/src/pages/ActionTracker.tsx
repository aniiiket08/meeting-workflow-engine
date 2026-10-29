import React, { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  CheckCircle2,
  Kanban,
  List,
  Quote,
  Search,
  X,
} from "lucide-react";
import { api } from "../api/client";
import { AppShell } from "../components/AppShell";
import { useAuth } from "../lib/auth";

interface ActionItem {
  id: number;
  meeting_id: number;
  description: string;
  owner_id: number | null;
  owner_name: string;
  owner_email: string | null;
  due_date: string | null;
  priority: "low" | "medium" | "high";
  status: "pending" | "in_progress" | "completed";
  confidence: number;
  source_quote: string | null;
  source_timestamp?: string | null;
}

interface DirectoryUser {
  id: number;
  name: string;
  email: string;
  role: string;
}

function formatDate(iso: string | null): string {
  if (!iso) return "No date set";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "No date set";
  return d.toLocaleDateString("en-GB", {
    weekday: "short",
    day: "numeric",
    month: "short",
  });
}

function priorityBadge(p: string) {
  switch (p) {
    case "high":
      return <span className="editorial-tag editorial-tag-accent text-9">HIGH</span>;
    case "medium":
      return <span className="editorial-tag editorial-tag-warn text-9">MED</span>;
    default:
      return <span className="editorial-tag editorial-tag-default text-9">LOW</span>;
  }
}

export const ActionTracker: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const meetingFilter = searchParams.get("meeting");
  const { user } = useAuth();

  const [items, setItems] = useState<ActionItem[]>([]);
  const [members, setMembers] = useState<DirectoryUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // View mode: Table vs. Kanban
  const [viewMode, setViewMode] = useState<"table" | "kanban">("table");

  // Filters
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [onlyMine, setOnlyMine] = useState(false);

  // Grounded quote modal state
  const [inspectedQuote, setInspectedQuote] = useState<ActionItem | null>(null);

  const canAssign = user && ["chairman", "principal", "hod"].includes(user.role);

  useEffect(() => {
    fetchActions();
    if (canAssign) {
      api.get<DirectoryUser[]>("/users").then(setMembers).catch(() => {});
    }
  }, [canAssign]);

  const fetchActions = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.get<ActionItem[]>("/actions");
      setItems(data);
    } catch (err: any) {
      setError(err.message || "Could not load action items.");
    } finally {
      setLoading(false);
    }
  };

  const handleStatusChange = async (id: number, nextStatus: "pending" | "in_progress" | "completed") => {
    try {
      await api.put(`/actions/${id}/status`, { status: nextStatus });
      setItems((prev) =>
        prev.map((item) => (item.id === id ? { ...item, status: nextStatus } : item))
      );
    } catch (err: any) {
      alert(err.message || "Failed to update action status.");
    }
  };

  const handleAssigneeChange = async (actionId: number, ownerId: number) => {
    try {
      await api.put(`/actions/${actionId}/assign`, { owner_id: ownerId });
      const member = members.find((m) => m.id === ownerId);
      setItems((prev) =>
        prev.map((item) =>
          item.id === actionId
            ? {
                ...item,
                owner_id: ownerId,
                owner_name: member?.name || item.owner_name,
                owner_email: member?.email || item.owner_email,
              }
            : item
        )
      );
    } catch (err: any) {
      alert(err.message || "Failed to reassign action.");
    }
  };

  const filteredItems = useMemo(() => {
    return items.filter((item) => {
      // Meeting filter
      if (meetingFilter && String(item.meeting_id) !== meetingFilter) return false;

      // Status filter
      if (statusFilter !== "all" && item.status !== statusFilter) return false;

      // Only mine
      if (onlyMine && user) {
        if (item.owner_email?.toLowerCase() !== user.email.toLowerCase()) return false;
      }

      // Search query
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchesDesc = item.description.toLowerCase().includes(q);
        const matchesOwner = (item.owner_name || "").toLowerCase().includes(q);
        return matchesDesc || matchesOwner;
      }

      return true;
    });
  }, [items, meetingFilter, statusFilter, onlyMine, searchQuery, user]);

  return (
    <AppShell
      pageTitle="Action Tracker"
      pageSubtitle="Audited commitments, ownership deadlines, and grounded transcript evidence."
    >
      <div className="space-y-6">
        {/* Error */}
        {error && (
          <div className="error-banner mb-4" role="alert">
            {error}
          </div>
        )}

        {/* ── Filter & Search Toolbar ──────────────────────────── */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex flex-wrap items-center gap-3 flex-1">
            {/* Search */}
            <div className="relative min-w-[240px]">
              <Search
                size={14}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-faint"
              />
              <input
                type="text"
                placeholder="Search description or owner…"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-surface border border-rule rounded-sm pl-8 pr-3 py-1.5 text-13 font-sans text-ink focus:border-ink outline-none"
              />
            </div>

            {/* My tasks toggle */}
            <button
              type="button"
              onClick={() => setOnlyMine((prev) => !prev)}
              className={`px-3 py-1.5 text-12 font-sans border rounded-sm transition-colors ${
                onlyMine
                  ? "bg-ink text-paper border-ink"
                  : "bg-surface border-rule text-ink-soft hover:text-ink hover:border-ink"
              }`}
            >
              My Tasks Only
            </button>

            {/* Meeting Filter Chip (if active) */}
            {meetingFilter && (
              <div className="editorial-tag editorial-tag-accent flex items-center gap-1.5">
                <span>Meeting #{meetingFilter}</span>
                <button
                  type="button"
                  onClick={() => setSearchParams({})}
                  className="hover:opacity-75"
                >
                  <X size={12} />
                </button>
              </div>
            )}
          </div>

          {/* View Mode Toggle: Table vs Kanban */}
          <div className="flex items-center gap-1 bg-surface border border-rule p-0.5 rounded-sm shrink-0">
            <button
              type="button"
              onClick={() => setViewMode("table")}
              className={`p-1.5 text-12 font-sans flex items-center gap-1 rounded-sm transition-colors ${
                viewMode === "table" ? "bg-paper text-ink shadow-sm" : "text-ink-soft hover:text-ink"
              }`}
              title="Table View"
            >
              <List size={14} />
              <span className="hidden sm:inline">Table</span>
            </button>
            <button
              type="button"
              onClick={() => setViewMode("kanban")}
              className={`p-1.5 text-12 font-sans flex items-center gap-1 rounded-sm transition-colors ${
                viewMode === "kanban" ? "bg-paper text-ink shadow-sm" : "text-ink-soft hover:text-ink"
              }`}
              title="Kanban Board View"
            >
              <Kanban size={14} />
              <span className="hidden sm:inline">Kanban</span>
            </button>
          </div>
        </div>

        {/* ── Status Tabs (Table Mode) ─────────────────────────── */}
        {viewMode === "table" && (
          <div className="editorial-tabs">
            {["all", "pending", "in_progress", "completed"].map((st) => (
              <button
                key={st}
                type="button"
                className={`editorial-tab ${statusFilter === st ? "active" : ""}`}
                onClick={() => setStatusFilter(st)}
              >
                {st === "all" ? "All Items" : st.replace("_", " ")} (
                {items.filter((i) => (st === "all" ? true : i.status === st)).length}
                )
              </button>
            ))}
          </div>
        )}

        {/* ── Loading / Empty ──────────────────────────────────── */}
        {loading ? (
          <div className="py-16 text-center font-serif italic text-ink-soft text-15">
            Loading action items…
          </div>
        ) : filteredItems.length === 0 ? (
          <div className="editorial-card py-16 text-center space-y-2">
            <CheckCircle2 size={28} className="mx-auto text-ink-faint opacity-60 mb-2" />
            <p className="font-serif italic text-ink-soft text-15">
              No tasks found matching your filter criteria.
            </p>
          </div>
        ) : viewMode === "table" ? (
          /* ── Table View ───────────────────────────────────────── */
          <div className="editorial-card p-0 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-13 border-collapse">
                <thead>
                  <tr className="border-b border-rule-strong bg-surface font-sans text-11 uppercase tracking-wider text-ink-soft">
                    <th className="py-4 px-6 font-medium">Task Description</th>
                    <th className="py-4 px-6 font-medium">Owner</th>
                    <th className="py-4 px-6 font-medium">Due Date</th>
                    <th className="py-4 px-6 font-medium">Priority</th>
                    <th className="py-4 px-6 font-medium">Status</th>
                    <th className="py-4 px-6 font-medium text-right">Grounding</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-rule font-sans">
                  {filteredItems.map((item) => (
                    <tr key={item.id} className="hover:bg-tint/40 transition-colors">
                      <td className="py-5 px-6 font-serif text-ink">
                        <div className="font-medium text-15 leading-relaxed">{item.description}</div>
                        <div className="font-mono text-11 text-ink-faint mt-1">
                          From <Link to={`/meetings/${item.meeting_id}`} className="hover:underline">Meeting #{item.meeting_id}</Link>
                        </div>
                      </td>

                      <td className="py-5 px-6 text-13">
                        {canAssign ? (
                          <select
                            value={item.owner_id || ""}
                            onChange={(e) => handleAssigneeChange(item.id, Number(e.target.value))}
                            className="bg-transparent border-b border-rule text-13 font-sans py-1.5 outline-none text-ink cursor-pointer focus:border-ink"
                          >
                            <option value="">{item.owner_name || "Unassigned"}</option>
                            {members.map((m) => (
                              <option key={m.id} value={m.id}>
                                {m.name} ({m.role})
                              </option>
                            ))}
                          </select>
                        ) : (
                          <span className="font-serif text-ink">
                            {item.owner_name || item.owner_email || "Unassigned"}
                          </span>
                        )}
                      </td>

                      <td className="py-5 px-6 font-mono text-13 text-ink-soft">
                        {formatDate(item.due_date)}
                      </td>

                      <td className="py-3 px-4">
                        {priorityBadge(item.priority)}
                      </td>

                      <td className="py-3 px-4">
                        <select
                          value={item.status}
                          onChange={(e) => handleStatusChange(item.id, e.target.value as any)}
                          className="bg-paper border border-rule rounded-sm px-2 py-1 text-11 font-sans text-ink outline-none cursor-pointer hover:border-ink transition-colors"
                        >
                          <option value="pending">Pending</option>
                          <option value="in_progress">In Progress</option>
                          <option value="completed">Completed</option>
                        </select>
                      </td>

                      <td className="py-3 px-4 text-right">
                        {item.source_quote ? (
                          <button
                            type="button"
                            onClick={() => setInspectedQuote(item)}
                            className="editorial-tag editorial-tag-default hover:border-ink cursor-pointer text-10"
                            title="Inspect verbatim source quote and timestamp"
                          >
                            <Quote size={10} className="mr-1" />
                            <span>Cited</span>
                          </button>
                        ) : (
                          <span className="text-11 text-ink-faint italic">No quote</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          /* ── Kanban View ───────────────────────────────────────── */
          <div className="kanban-grid">
            {(["pending", "in_progress", "completed"] as const).map((columnStatus) => {
              const colItems = filteredItems.filter((i) => i.status === columnStatus);
              const colTitle =
                columnStatus === "pending"
                  ? "Pending"
                  : columnStatus === "in_progress"
                  ? "In Progress"
                  : "Completed";

              return (
                <div key={columnStatus} className="kanban-column">
                  <div className="kanban-column-header">
                    <span className="font-serif text-15 font-medium text-ink">
                      {colTitle}
                    </span>
                    <span className="editorial-tag editorial-tag-default text-10">
                      {colItems.length}
                    </span>
                  </div>

                  <div className="space-y-4 flex-1 overflow-y-auto">
                    {colItems.map((item) => (
                      <div
                        key={item.id}
                        className="kanban-card p-5"
                        onClick={() => item.source_quote && setInspectedQuote(item)}
                      >
                        <div className="flex items-start justify-between gap-3">
                          <span className="font-serif text-15 font-medium text-ink leading-relaxed">
                            {item.description}
                          </span>
                          <div className="shrink-0">{priorityBadge(item.priority)}</div>
                        </div>

                        <div className="flex items-center justify-between text-12 font-mono text-ink-faint pt-3 border-t border-rule/50">
                          <span className="flex items-center gap-1">
                            Due: {formatDate(item.due_date)}
                          </span>
                          <span className="truncate max-w-[140px] text-ink-soft font-sans font-medium">
                            {item.owner_name || "Unassigned"}
                          </span>
                        </div>

                        {/* Status switcher */}
                        <div
                          className="pt-2.5 flex items-center justify-between text-11 font-sans border-t border-rule/30"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <span className="text-ink-faint">Move stage:</span>
                          <div className="flex gap-1.5">
                            {columnStatus !== "pending" && (
                              <button
                                type="button"
                                onClick={() => handleStatusChange(item.id, "pending")}
                                className="px-2 py-0.5 border border-rule hover:border-ink rounded text-ink-soft hover:text-ink transition-colors"
                              >
                                Pending
                              </button>
                            )}
                            {columnStatus !== "in_progress" && (
                              <button
                                type="button"
                                onClick={() => handleStatusChange(item.id, "in_progress")}
                                className="px-2 py-0.5 border border-rule hover:border-ink rounded text-ink-soft hover:text-ink transition-colors"
                              >
                                Active
                              </button>
                            )}
                            {columnStatus !== "completed" && (
                              <button
                                type="button"
                                onClick={() => handleStatusChange(item.id, "completed")}
                                className="px-1.5 py-0.5 border border-ok hover:bg-ok/10 rounded-sm text-ok"
                              >
                                Done
                              </button>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* ── Grounded Quote Inspection Modal ─────────────────── */}
        {inspectedQuote && (
          <div
            className="fixed inset-0 bg-ink/40 z-50 flex items-center justify-center p-4"
            onClick={() => setInspectedQuote(null)}
          >
            <div
              className="editorial-card max-w-lg w-full bg-paper p-6 space-y-4 shadow-xl"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-start justify-between border-b border-rule pb-3">
                <div>
                  <span className="label text-accent block">Transcript Grounding Evidence</span>
                  <h4 className="font-serif text-16 text-ink mt-0.5">
                    {inspectedQuote.description}
                  </h4>
                </div>
                <button
                  type="button"
                  onClick={() => setInspectedQuote(null)}
                  className="p-1 text-ink-faint hover:text-ink"
                >
                  <X size={16} />
                </button>
              </div>

              <blockquote className="quote-block text-14 text-ink-soft py-1">
                "{inspectedQuote.source_quote}"
              </blockquote>

              <div className="flex items-center justify-between text-11 font-mono text-ink-faint pt-2 border-t border-rule">
                <span>
                  Timestamp: {inspectedQuote.source_timestamp || "Verified in segment"}
                </span>
                <Link
                  to={`/meetings/${inspectedQuote.meeting_id}/minutes`}
                  className="text-accent underline"
                >
                  View in Full Transcript
                </Link>
              </div>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
};
