import React, { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ExternalLink, Trash2 } from "lucide-react";
import { api } from "../api/client";
import { AppShell } from "../components/AppShell";
import { MeetingWorkLinks } from "../components/MeetingWorkLinks";
import { StageTracker } from "../components/StageTracker";
import { useAuth } from "../lib/auth";

interface Meeting {
  id: number;
  title: string;
  description: string | null;
  agenda_items_text?: string | null;
  duration_minutes: number;
  start_time: string | null;
  end_time: string | null;
  room_id: number | null;
  zoom_meeting_id?: string | null;
  zoom_join_url?: string | null;
  status: string;
  created_at: string;
}

interface AgendaItem {
  item_number: number;
  title: string;
  owner: string;
  duration_minutes: number;
}

interface Agenda {
  id: number;
  meeting_id: number;
  status: string;
  items: AgendaItem[];
}

interface MinutesData {
  id: number;
  summary: string;
  key_discussion_points: string[];
  action_items: any[];
  status: string;
}

function formatDate(iso: string | null): string {
  if (!iso) return "Not scheduled";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "Not scheduled";
  return d
    .toLocaleString("en-GB", {
      weekday: "long",
      day: "numeric",
      month: "short",
      year: "numeric",
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
      return <span className="editorial-tag editorial-tag-ok">{status.replace("_", " ")}</span>;
    case "requested":
    case "slots_proposed":
      return <span className="editorial-tag editorial-tag-warn">{status.replace("_", " ")}</span>;
    case "discarded":
      return <span className="editorial-tag editorial-tag-accent">discarded</span>;
    default:
      return <span className="editorial-tag editorial-tag-default">{status.replace(/_/g, " ")}</span>;
  }
}

export const MeetingDetails: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();

  const [meeting, setMeeting] = useState<Meeting | null>(null);
  const [agenda, setAgenda] = useState<Agenda | null>(null);
  const [minutes, setMinutes] = useState<MinutesData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"overview" | "agenda" | "minutes">("overview");

  const canDiscard = user && ["chairman", "principal", "hod"].includes(user.role);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    api.get<Meeting[]>("/meetings")
      .then((meetings) => {
        const found = meetings.find((m) => String(m.id) === id);
        if (found) {
          setMeeting(found);
          // Pre-fetch agenda and minutes if available
          api.get<Agenda>(`/meetings/${id}/agenda`).then(setAgenda).catch(() => {});
          api.get<MinutesData>(`/meetings/${id}/minutes`).then(setMinutes).catch(() => {});
        } else {
          setError(`Meeting #${id} was not found.`);
        }
      })
      .catch((err) => setError(err.message || "Could not load meeting details."))
      .finally(() => setLoading(false));
  }, [id]);

  const handleDiscard = async () => {
    if (!meeting) return;
    if (!window.confirm("Are you sure you want to discard this meeting?")) return;
    try {
      await api.post(`/meetings/${meeting.id}/discard`, {});
      setMeeting({ ...meeting, status: "discarded" });
    } catch (err: any) {
      alert(err.message || "Failed to discard meeting.");
    }
  };

  return (
    <AppShell
      pageTitle={meeting ? meeting.title : "Meeting Details"}
      pageSubtitle={
        meeting
          ? `Meeting #${meeting.id} · ${formatDate(meeting.start_time)}`
          : undefined
      }
      actionButton={
        meeting && (
          <div className="flex items-center gap-2">
            <Link to={`/meetings/${meeting.id}/agenda`} className="btn-secondary text-11">
              Agenda Editor
            </Link>
            <Link to={`/meetings/${meeting.id}/minutes`} className="btn-secondary text-11">
              Minutes Review
            </Link>
            {canDiscard && meeting.status !== "discarded" && (
              <button
                type="button"
                onClick={handleDiscard}
                className="text-11 font-sans text-accent hover:underline flex items-center gap-1 ml-2"
              >
                <Trash2 size={13} />
                <span>Discard</span>
              </button>
            )}
          </div>
        )
      }
    >
      {loading ? (
        <div className="py-12 font-serif italic text-ink-soft text-center text-15">
          Loading meeting dossier…
        </div>
      ) : error || !meeting ? (
        <div className="error-banner" role="alert">
          {error || "Meeting not found."}
        </div>
      ) : (
        <div className="space-y-6">
          {/* ── Status & Stage Tracker ─────────────────────────── */}
          <div className="editorial-card-raised p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex flex-wrap items-center gap-3 shrink-0">
              <span className="font-mono text-11 text-ink-faint">STATUS</span>
              {statusBadge(meeting.status)}
              <span className="font-mono text-12 text-ink-faint ml-1">
                DURATION: {meeting.duration_minutes}m
              </span>
            </div>

            <div className="flex items-center gap-3 w-full md:w-auto justify-end">
              <span className="font-mono text-10 text-ink-faint uppercase shrink-0">LIFECYCLE</span>
              <div className="w-full sm:w-[280px]">
                <StageTracker status={meeting.status} meetingId={meeting.id} />
              </div>
            </div>
          </div>

          {/* ── Work Links ───────────────────────────────────────── */}
          <MeetingWorkLinks meetingId={meeting.id} />

          {/* ── Tabs ────────────────────────────────────────────── */}
          <div className="editorial-tabs">
            <button
              type="button"
              className={`editorial-tab ${activeTab === "overview" ? "active" : ""}`}
              onClick={() => setActiveTab("overview")}
            >
              Overview &amp; Schedule
            </button>
            <button
              type="button"
              className={`editorial-tab ${activeTab === "agenda" ? "active" : ""}`}
              onClick={() => setActiveTab("agenda")}
            >
              Agenda {agenda ? `(${agenda.items.length})` : ""}
            </button>
            <button
              type="button"
              className={`editorial-tab ${activeTab === "minutes" ? "active" : ""}`}
              onClick={() => setActiveTab("minutes")}
            >
              Minutes &amp; Decisions {minutes ? "(Available)" : ""}
            </button>
          </div>

          {/* ── Tab Content ─────────────────────────────────────── */}
          {activeTab === "overview" && (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
              {/* Left Column: Meeting Details (7 cols) */}
              <div className="lg:col-span-7 editorial-card-raised p-6 space-y-5">
                <div className="border-b border-rule pb-3">
                  <span className="label text-ink-faint block text-10">Meeting Particulars</span>
                  <h3 className="font-serif text-18 text-ink mt-1 font-normal">Session Dossier</h3>
                </div>

                <div className="space-y-3.5 text-13 font-sans">
                  <div className="flex flex-col sm:flex-row sm:items-baseline gap-1 sm:gap-3">
                    <span className="text-ink-soft font-medium sm:w-36 shrink-0">Scheduled Slot:</span>
                    <span className="font-serif text-ink text-14">{formatDate(meeting.start_time)}</span>
                  </div>

                  <div className="flex flex-col sm:flex-row sm:items-baseline gap-1 sm:gap-3">
                    <span className="text-ink-soft font-medium sm:w-36 shrink-0">Expected Duration:</span>
                    <span className="font-mono text-ink text-13">{meeting.duration_minutes} minutes</span>
                  </div>

                  <div className="flex flex-col sm:flex-row sm:items-baseline gap-1 sm:gap-3">
                    <span className="text-ink-soft font-medium sm:w-36 shrink-0">Location / Venue:</span>
                    {meeting.zoom_join_url ? (
                      <span className="font-sans flex flex-wrap items-center gap-2">
                        <span className="text-10 uppercase tracking-wider px-2 py-0.5 rounded font-semibold bg-[#2B72BA] text-white">
                          Zoom Meeting
                        </span>
                        <a
                          href={meeting.zoom_join_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="font-mono text-12 underline text-blue-400 hover:text-blue-300 inline-flex items-center gap-1"
                        >
                          Join Zoom Meeting <ExternalLink size={12} />
                        </a>
                      </span>
                    ) : (
                      <span className="font-serif text-ink text-14">
                        {meeting.room_id ? `Campus Room #${meeting.room_id}` : "To be decided"}
                      </span>
                    )}
                  </div>

                  <div className="flex flex-col sm:flex-row sm:items-start gap-1 sm:gap-3 pt-1">
                    <span className="text-ink-soft font-medium sm:w-36 shrink-0 pt-0.5">Description:</span>
                    <p className="font-serif italic text-ink text-14 leading-relaxed max-w-prose break-words">
                      {meeting.description || "No description provided."}
                    </p>
                  </div>
                </div>

                {meeting.agenda_items_text && (
                  <div className="pt-4 border-t border-rule space-y-2">
                    <span className="label text-ink-faint block text-10">Original Topics Stated</span>
                    <p className="font-serif text-13 text-ink-soft whitespace-pre-line leading-relaxed max-w-prose">
                      {meeting.agenda_items_text}
                    </p>
                  </div>
                )}
              </div>

              {/* Right Column: Workflows & Artifacts (5 cols) */}
              <div className="lg:col-span-5 editorial-card-raised p-6 space-y-4">
                <div className="border-b border-rule pb-3">
                  <span className="label text-ink-faint block text-10">Artifacts &amp; Follow-up</span>
                  <h3 className="font-serif text-18 text-ink mt-1 font-normal">Active Workflows</h3>
                </div>

                <div className="space-y-3">
                  <Link
                    to={`/meetings/${meeting.id}/agenda`}
                    className="p-3.5 bg-paper border border-rule rounded-sm flex items-center justify-between text-13 hover:border-ink hover:bg-tint/30 transition-all block group"
                  >
                    <div>
                      <div className="font-serif font-medium text-ink group-hover:text-accent transition-colors">Structured Agenda</div>
                      <div className="font-sans text-11 text-ink-soft mt-0.5">
                        {agenda ? `${agenda.items.length} items planned` : "View or edit agenda items"}
                      </div>
                    </div>
                    <ExternalLink size={14} className="text-ink-faint group-hover:text-ink transition-colors" />
                  </Link>

                  <Link
                    to={`/meetings/${meeting.id}/minutes`}
                    className="p-3.5 bg-paper border border-rule rounded-sm flex items-center justify-between text-13 hover:border-ink hover:bg-tint/30 transition-all block group"
                  >
                    <div>
                      <div className="font-serif font-medium text-ink group-hover:text-accent transition-colors">Minutes &amp; Decisions</div>
                      <div className="font-sans text-11 text-ink-soft mt-0.5">
                        Transcript-linked evidence and action items
                      </div>
                    </div>
                    <ExternalLink size={14} className="text-ink-faint group-hover:text-ink transition-colors" />
                  </Link>

                  <Link
                    to={`/actions?meeting=${meeting.id}`}
                    className="p-3.5 bg-paper border border-rule rounded-sm flex items-center justify-between text-13 hover:border-ink hover:bg-tint/30 transition-all block group"
                  >
                    <div>
                      <div className="font-serif font-medium text-ink group-hover:text-accent transition-colors">Assigned Tasks</div>
                      <div className="font-sans text-11 text-ink-soft mt-0.5">
                        Track follow-through and owner deadlines
                      </div>
                    </div>
                    <ExternalLink size={14} className="text-ink-faint group-hover:text-ink transition-colors" />
                  </Link>
                </div>
              </div>
            </div>
          )}

          {activeTab === "agenda" && (
            <div className="editorial-card-raised p-6 space-y-4">
              <div className="flex items-center justify-between border-b border-rule pb-3">
                <h3 className="font-serif text-18 text-ink font-normal">Planned Agenda Topics</h3>
                <Link to={`/meetings/${meeting.id}/agenda`} className="btn-primary text-11 py-1.5 px-3">
                  Open Agenda Editor
                </Link>
              </div>

              {!agenda || agenda.items.length === 0 ? (
                <p className="font-serif italic text-ink-soft text-14 py-4">
                  No agenda draft generated yet. Open the Agenda Editor to prepare topics.
                </p>
              ) : (
                <div className="divide-y divide-rule font-sans text-13">
                  {agenda.items.map((item) => (
                    <div key={item.item_number} className="py-3.5 flex items-center justify-between gap-4">
                      <div className="flex items-center gap-3">
                        <span className="font-mono text-11 text-ink-faint">
                          {String(item.item_number).padStart(2, "0")}
                        </span>
                        <span className="font-serif text-15 text-ink font-medium">
                          {item.title}
                        </span>
                      </div>
                      <div className="flex items-center gap-4 text-12 text-ink-soft shrink-0">
                        <span>Owner: <strong className="text-ink">{item.owner}</strong></span>
                        <span className="font-mono bg-tint px-2 py-0.5 rounded-sm">
                          {item.duration_minutes}m
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {activeTab === "minutes" && (
            <div className="editorial-card-raised p-6 space-y-4">
              <div className="flex items-center justify-between border-b border-rule pb-3">
                <h3 className="font-serif text-18 text-ink font-normal">Executive Minutes</h3>
                <Link to={`/meetings/${meeting.id}/minutes`} className="btn-primary text-11 py-1.5 px-3">
                  Full Document &amp; Transcript
                </Link>
              </div>

              {!minutes ? (
                <p className="font-serif italic text-ink-soft text-14 py-4">
                  Minutes have not been processed for this meeting yet.
                </p>
              ) : (
                <div className="space-y-4">
                  <div>
                    <span className="label text-ink-faint block mb-1.5 text-10">Executive Summary</span>
                    <p className="font-serif text-15 text-ink leading-relaxed max-w-prose">
                      {minutes.summary}
                    </p>
                  </div>

                  {minutes.key_discussion_points && minutes.key_discussion_points.length > 0 && (
                    <div className="pt-3 border-t border-rule">
                      <span className="label text-ink-faint block mb-2 text-10">Key Discussion Points</span>
                      <ul className="space-y-1.5 font-sans text-13 text-ink-soft list-disc list-inside leading-relaxed">
                        {minutes.key_discussion_points.map((pt, i) => (
                          <li key={i}>{pt}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </AppShell>
  );
};
