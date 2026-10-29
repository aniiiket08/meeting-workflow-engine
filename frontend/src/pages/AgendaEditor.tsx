import React, { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { CheckCircle2, Plus, Trash2 } from "lucide-react";
import { api } from "../api/client";
import { AppShell } from "../components/AppShell";
import { MeetingWorkLinks } from "../components/MeetingWorkLinks";
import { StageTracker } from "../components/StageTracker";
import { useAuth } from "../lib/auth";

interface AgendaItem {
  item_number: number;
  title: string;
  owner: string;
  duration_minutes: number;
  unresolved_context?: string | null;
}

interface Agenda {
  id: number;
  meeting_id: number;
  meeting_title: string;
  meeting_status?: string;
  duration_minutes: number;
  items: AgendaItem[];
  status: "draft" | "approved" | "rejected";
  approved_at?: string | null;
}

function totalMinutes(items: AgendaItem[]): number {
  return items.reduce((s, i) => s + i.duration_minutes, 0);
}

function initials(name: string): string {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0].toUpperCase())
    .join("");
}

export const AgendaEditor: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();

  const canEdit = !!user && ["chairman", "principal", "hod", "teacher"].includes(user.role);
  const canApprove = !!user && ["chairman", "principal", "hod"].includes(user.role);

  const [agenda, setAgenda] = useState<Agenda | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [saving, setSaving] = useState<boolean>(false);
  const [approving, setApproving] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  useEffect(() => {
    fetchAgenda();
  }, [id]);

  const fetchAgenda = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.get<Agenda>(`/meetings/${id}/agenda`);
      setAgenda(data);
    } catch (err: any) {
      setError(err.message || "Could not load meeting agenda.");
    } finally {
      setLoading(false);
    }
  };

  const handleItemChange = (
    index: number,
    field: "title" | "owner" | "duration_minutes",
    value: string
  ) => {
    if (!agenda) return;
    const updated = [...agenda.items];
    updated[index] = {
      ...updated[index],
      [field]: field === "duration_minutes" ? Number(value) || 0 : value,
    };
    setAgenda({ ...agenda, items: updated });
  };

  const handleAddItem = () => {
    if (!agenda) return;
    setAgenda({
      ...agenda,
      items: [
        ...agenda.items,
        {
          item_number: agenda.items.length + 1,
          title: "New topic",
          owner: user?.name || "TBD",
          duration_minutes: 10,
        },
      ],
    });
  };

  const handleRemoveItem = (index: number) => {
    if (!agenda) return;
    setAgenda({
      ...agenda,
      items: agenda.items
        .filter((_, i) => i !== index)
        .map((item, i) => ({ ...item, item_number: i + 1 })),
    });
  };

  const handleSave = async () => {
    if (!agenda) return;
    setSaving(true);
    setError(null);
    setSuccessMsg(null);
    try {
      const updated = await api.put<Agenda>(`/meetings/${id}/agenda`, {
        items: agenda.items,
      });
      setAgenda(updated);
      setSuccessMsg("Agenda draft saved successfully.");
    } catch (err: any) {
      setError(err.message || "Could not save agenda.");
    } finally {
      setSaving(false);
    }
  };

  const handleApprove = async () => {
    if (!agenda) return;
    setApproving(true);
    setError(null);
    setSuccessMsg(null);
    try {
      const res = await api.post<Agenda>(`/agendas/${agenda.id}/approve`, {});
      setAgenda(res);
      setSuccessMsg("Agenda approved and version-locked.");
    } catch (err: any) {
      setError(err.message || "Could not approve agenda.");
    } finally {
      setApproving(false);
    }
  };

  const total = agenda ? totalMinutes(agenda.items) : 0;
  const planned = agenda?.duration_minutes ?? 0;
  const overPct = planned > 0 ? Math.min(total / planned, 1) : 0;

  return (
    <AppShell
      pageTitle={agenda ? agenda.meeting_title : "Meeting Agenda"}
      pageSubtitle={`Agenda Editor · Meeting #${id}`}
      actionButton={
        id && (
          <div className="flex items-center gap-2">
            <Link to={`/meetings/${id}`} className="btn-secondary text-11">
              Meeting Dossier
            </Link>
            <Link to={`/meetings/${id}/minutes`} className="btn-secondary text-11">
              Minutes Review
            </Link>
          </div>
        )
      }
    >
      <div className="space-y-6">
        {/* Status header & StageTracker */}
        {agenda && (
          <div className="editorial-card flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <span className="font-mono text-12 text-ink-faint">AGENDA STATUS</span>
              <span
                className={`editorial-tag ${
                  agenda.status === "approved" ? "editorial-tag-ok" : "editorial-tag-warn"
                }`}
              >
                {agenda.status.toUpperCase()}
              </span>
            </div>

            <div className="flex items-center gap-2">
              <span className="font-mono text-10 text-ink-faint uppercase mr-1">LIFECYCLE</span>
              <StageTracker
                status={agenda.meeting_status || "agenda_drafted"}
                meetingId={Number(id)}
              />
            </div>
          </div>
        )}

        {id && (
          <MeetingWorkLinks meetingId={id} />
        )}

        {/* Messages */}
        {error && (
          <div className="error-banner" role="alert">
            {error}
          </div>
        )}

        {successMsg && (
          <div className="p-3 bg-tint border-l-2 border-l-ink text-ink font-sans text-13">
            {successMsg}
          </div>
        )}

        {loading ? (
          <div className="py-16 text-center font-serif italic text-ink-soft text-15">
            Loading agenda details…
          </div>
        ) : !agenda ? (
          <div className="editorial-card py-16 text-center font-serif italic text-ink-soft text-15">
            No agenda draft generated for this meeting.
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
            {/* ── Main Agenda Item Editor (8 cols) ─────────────── */}
            <div className="lg:col-span-8 editorial-card-raised p-6 space-y-5">
              {/* Header with duration meter */}
              <div className="flex items-center justify-between pb-3 border-b border-rule">
                <div>
                  <h3 className="font-serif text-18 text-ink">Structured Topics</h3>
                  <span className="font-sans text-12 text-ink-faint">
                    Item title, responsible owner, and time box
                  </span>
                </div>

                <div className="flex items-center gap-3">
                  <div className="text-right">
                    <span className="font-mono text-12 text-ink block font-medium">
                      {total} / {planned} min
                    </span>
                    <span className="font-sans text-10 text-ink-faint">
                      {total > planned ? "Exceeds duration" : "Within scheduled time"}
                    </span>
                  </div>

                  <div
                    className="progress-rule-track w-24 h-1.5 bg-rule rounded-sm overflow-hidden"
                    title={`${total} of ${planned} minutes`}
                  >
                    <div
                      className="h-full transition-all duration-300"
                      style={{
                        width: `${overPct * 100}%`,
                        backgroundColor: total > planned ? "var(--accent)" : "var(--ink)",
                      }}
                    />
                  </div>
                </div>
              </div>

              {/* Items List */}
              <div className="space-y-2.5">
                {agenda.items.map((item, idx) => (
                  <div
                    key={idx}
                    className="p-3 bg-paper border border-rule rounded-sm flex flex-col sm:flex-row sm:items-center gap-3 group hover:border-ink transition-colors shadow-sm"
                  >
                    <span className="font-mono text-11 text-ink-faint shrink-0 w-6">
                      {String(idx + 1).padStart(2, "0")}
                    </span>

                    {/* Topic input */}
                    <div className="flex-1 min-w-0">
                      <input
                        type="text"
                        value={item.title}
                        disabled={!canEdit || agenda.status === "approved"}
                        onChange={(e) => handleItemChange(idx, "title", e.target.value)}
                        className="w-full bg-transparent font-serif text-14 text-ink outline-none border-b border-transparent focus:border-ink pb-0.5"
                        placeholder="Topic title…"
                      />
                    </div>

                    {/* Owner input */}
                    <div className="flex items-center gap-2 w-40 shrink-0">
                      <div className="monogram w-6 h-6 rounded-sm text-9 bg-tint text-ink border border-rule">
                        {initials(item.owner || "TBD")}
                      </div>
                      <input
                        type="text"
                        value={item.owner}
                        disabled={!canEdit || agenda.status === "approved"}
                        onChange={(e) => handleItemChange(idx, "owner", e.target.value)}
                        className="w-full bg-transparent font-sans text-12 text-ink-soft outline-none border-b border-transparent focus:border-ink"
                        placeholder="Owner name…"
                      />
                    </div>

                    {/* Duration input */}
                    <div className="flex items-center gap-1.5 shrink-0">
                      <input
                        type="number"
                        min={1}
                        max={180}
                        value={item.duration_minutes}
                        disabled={!canEdit || agenda.status === "approved"}
                        onChange={(e) => handleItemChange(idx, "duration_minutes", e.target.value)}
                        className="w-14 bg-tint border border-rule rounded-sm font-mono text-12 text-ink text-center py-1 outline-none focus:border-ink"
                      />
                      <span className="font-mono text-11 text-ink-faint">min</span>
                    </div>

                    {/* Remove button */}
                    {canEdit && agenda.status !== "approved" && (
                      <button
                        type="button"
                        onClick={() => handleRemoveItem(idx)}
                        className="text-ink-faint hover:text-accent p-1 transition-colors"
                        title="Remove topic"
                      >
                        <Trash2 size={13} />
                      </button>
                    )}
                  </div>
                ))}
              </div>

              {/* Add item button */}
              {canEdit && agenda.status !== "approved" && (
                <button
                  type="button"
                  onClick={handleAddItem}
                  className="btn-secondary text-11 py-1.5 px-3 flex items-center gap-1"
                >
                  <Plus size={13} />
                  <span>Add Agenda Topic</span>
                </button>
              )}
            </div>

            {/* ── Actions & Gate Check (4 cols) ───────────────── */}
            <div className="lg:col-span-4 space-y-5">
              <div className="editorial-card-raised p-6 space-y-4">
                <span className="label text-ink-faint block text-10">Human Approval Gate</span>

                {agenda.status === "approved" ? (
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-ok">
                      <CheckCircle2 size={16} />
                      <span className="font-serif font-medium text-14">Agenda Signed &amp; Locked</span>
                    </div>
                    <p className="font-sans text-12 text-ink-soft leading-relaxed">
                      This agenda has been formally approved. Items are distributed to attendees.
                    </p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    <p className="font-sans text-12 text-ink-soft leading-relaxed">
                      Review topics and time allocations. Once signed off by an approver, the agenda is released for meeting preparation.
                    </p>

                    <div className="space-y-2.5">
                      {canEdit && (
                        <button
                          type="button"
                          onClick={handleSave}
                          disabled={saving}
                          className="w-full py-2 px-3 border border-rule hover:border-ink rounded-sm font-sans text-12 text-ink hover:bg-tint transition-colors block text-center"
                        >
                          {saving ? "Saving Draft…" : "Save Agenda Draft"}
                        </button>
                      )}

                      {canApprove && (
                        <button
                          type="button"
                          onClick={handleApprove}
                          disabled={approving}
                          className="w-full btn-primary py-2 px-3 block text-center text-12"
                        >
                          {approving ? "Locking & Approving…" : "Approve & Sign Agenda"}
                        </button>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
};
