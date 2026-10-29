/**
 * Schedule — Weekly Calendar Grid
 *
 * What lives here (frontend only, no backend changes):
 *  - Fixed recurring timetable per role / participant group
 *  - Dynamic week calculation with ← Prev / TODAY / Next → navigation
 *  - Participant filter: Everyone · Chairman · Principal · HOD · Students
 *  - 6-column Mon–Sat weekly grid, 6 rows 09–15, compact cells
 *  - Common-availability section (slots where ALL selected people are FREE)
 *  - Upcoming Meetings sidebar (unchanged, from /schedule API)
 *  - Working hours corrected to 09:00–15:00 in the display
 */

import React, { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { AppShell } from "../components/AppShell";
import { useAuth } from "../lib/auth";

// ─────────────────────────────────────────────────────────────────────────────
// TIMETABLE DATA  (frontend constant — never touches the backend)
// ─────────────────────────────────────────────────────────────────────────────

/** Slot index: 0 = 09–10, 1 = 10–11, 2 = 11–12, 3 = 12–13, 4 = 13–14 (Lunch), 5 = 14–15 */
const HOUR_SLOTS = [
  { label: "09:00–10:00", start: 9, end: 10 },
  { label: "10:00–11:00", start: 10, end: 11 },
  { label: "11:00–12:00", start: 11, end: 12 },
  { label: "12:00–13:00", start: 12, end: 13 },
  { label: "13:00–14:00", start: 13, end: 14 }, // Lunch
  { label: "14:00–15:00", start: 14, end: 15 },
] as const;

type SlotKind = "free" | "class" | "lunch" | "meeting_item" | "admin";
// "meeting_item" = scheduled meeting from the timetable (dept meeting, faculty meeting, etc.)

interface SlotEntry {
  kind: SlotKind;
  label: string; // display text inside the cell
}

/** Day = 0 Mon … 5 Sat */
type WeeklySchedule = SlotEntry[][]; // [dayIndex 0–5][slotIndex 0–5]

const FREE: SlotEntry = { kind: "free", label: "Free" };
const LUNCH: SlotEntry = { kind: "lunch", label: "Lunch" };

function day(
  s0: SlotEntry,
  s1: SlotEntry,
  s2: SlotEntry,
  s3: SlotEntry,
  s5: SlotEntry,
): SlotEntry[] {
  // slot 4 is always Lunch
  return [s0, s1, s2, s3, LUNCH, s5];
}

function cls(subject: string): SlotEntry {
  return { kind: "class", label: subject };
}
function adm(title: string): SlotEntry {
  return { kind: "admin", label: title };
}
function mtg(title: string): SlotEntry {
  return { kind: "meeting_item", label: title };
}

// ── Students (Aniket, Sujal, Viraj, Sarvesh — all identical) ─────────────────
const STUDENTS_SCHEDULE: WeeklySchedule = [
  // Mon
  day(cls("Cryptography"), FREE, cls("Agentic AI"), FREE, FREE),
  // Tue
  day(cls("Constitution"), cls("Agentic AI"), FREE, cls("Software Testing"), FREE),
  // Wed
  day(cls("Software Testing"), FREE, cls("Cryptography"), FREE, cls("Agentic AI")),
  // Thu
  day(cls("Responsible AI"), cls("Cryptography"), FREE, cls("Agentic AI"), FREE),
  // Fri
  day(cls("Agentic AI"), FREE, cls("Constitution"), FREE, cls("Software Testing")),
  // Sat
  day(cls("Software Testing"), FREE, cls("Responsible AI"), FREE, FREE),
];

// ── HOD ───────────────────────────────────────────────────────────────────────
const HOD_SCHEDULE: WeeklySchedule = [
  // Mon
  day(adm("Dept Class"), FREE, mtg("Dept Meeting"), FREE, FREE),
  // Tue
  day(mtg("Faculty Meeting"), cls("Agentic AI Class"), FREE, adm("Student Mentoring"), FREE),
  // Wed
  day(adm("Faculty Coordination"), FREE, cls("Cryptography Class"), FREE, FREE),
  // Thu
  day(adm("Dept Administration"), cls("Cryptography Class"), FREE, mtg("Faculty Meeting"), FREE),
  // Fri
  day(mtg("Dept Meeting"), FREE, adm("Faculty Coordination"), FREE, FREE),
  // Sat
  day(adm("Student Project Review"), FREE, adm("Dept Review"), FREE, FREE),
];

// ── Principal ─────────────────────────────────────────────────────────────────
const PRINCIPAL_SCHEDULE: WeeklySchedule = [
  // Mon
  day(adm("Campus Admin"), FREE, adm("Faculty Review"), FREE, adm("Admin Work")),
  // Tue
  day(adm("Ext Correspondence"), FREE, FREE, mtg("Faculty Meeting"), FREE),
  // Wed
  day(adm("Campus Admin"), FREE, adm("Academic Review"), FREE, adm("Admin Work")),
  // Thu
  day(mtg("External Meeting"), FREE, FREE, adm("Academic Review"), FREE),
  // Fri
  day(adm("Campus Admin"), FREE, adm("Admin Work"), FREE, adm("Faculty Review")),
  // Sat
  day(adm("Campus Admin"), FREE, mtg("Faculty Meeting"), FREE, FREE),
];

// ── Chairman ──────────────────────────────────────────────────────────────────
const CHAIRMAN_SCHEDULE: WeeklySchedule = [
  // Mon
  day(mtg("External Meeting"), FREE, FREE, FREE, FREE),
  // Tue
  day(adm("Campus Review"), FREE, FREE, mtg("External Meeting"), FREE),
  // Wed
  day(FREE, FREE, mtg("External Meeting"), FREE, FREE),
  // Thu
  day(adm("Campus Review"), FREE, FREE, mtg("External Meeting"), FREE),
  // Fri
  day(mtg("External Meeting"), FREE, adm("Campus Visit"), FREE, FREE),
  // Sat
  day(FREE, FREE, mtg("External Meeting"), FREE, FREE),
];

// ─────────────────────────────────────────────────────────────────────────────
// PARTICIPANT GROUPS
// ─────────────────────────────────────────────────────────────────────────────

type ParticipantKey = "everyone" | "chairman" | "principal" | "hod" | "students";

interface ParticipantOption {
  key: ParticipantKey;
  label: string;
  count: number; // number of individual people represented
  schedules: WeeklySchedule[];
}

const PARTICIPANT_OPTIONS: ParticipantOption[] = [
  {
    key: "everyone",
    label: "Everyone",
    count: 8, // 4 students + HOD + Principal + Chairman + (teacher omitted from timetable, assumed free)
    schedules: [CHAIRMAN_SCHEDULE, PRINCIPAL_SCHEDULE, HOD_SCHEDULE, STUDENTS_SCHEDULE],
  },
  { key: "chairman", label: "Chairman", count: 1, schedules: [CHAIRMAN_SCHEDULE] },
  { key: "principal", label: "Principal", count: 1, schedules: [PRINCIPAL_SCHEDULE] },
  { key: "hod", label: "HOD", count: 1, schedules: [HOD_SCHEDULE] },
  {
    key: "students",
    label: "Students",
    count: 4,
    schedules: [STUDENTS_SCHEDULE], // all 4 share the same schedule
  },
];

// ─────────────────────────────────────────────────────────────────────────────
// AVAILABILITY HELPERS
// ─────────────────────────────────────────────────────────────────────────────

/** For a given set of schedules, return a boolean[6][6] — true = ALL free */
function computeCommonAvailability(schedules: WeeklySchedule[]): boolean[][] {
  // [day][slot]
  const grid: boolean[][] = Array.from({ length: 6 }, () =>
    Array(6).fill(true),
  );
  for (const sched of schedules) {
    for (let d = 0; d < 6; d++) {
      for (let s = 0; s < 6; s++) {
        const entry = sched[d]?.[s];
        // Lunch slot is never a free meeting slot
        if (!entry || entry.kind !== "free") {
          grid[d][s] = false;
        }
      }
    }
  }
  return grid;
}

/** Build a merged grid cell for display: if any schedule has non-free, show that;
 *  otherwise show FREE. Used for "Everyone" combined view. */
function mergeGridCell(schedules: WeeklySchedule[], day: number, slot: number): SlotEntry {
  // Lunch always wins
  if (slot === 4) return LUNCH;
  const entries = schedules.map((s) => s[day]?.[slot] ?? FREE);
  // If ALL free → free
  if (entries.every((e) => e.kind === "free")) return FREE;
  // Otherwise surface the first non-free entry (prefer class > meeting > admin)
  const priority: SlotKind[] = ["class", "meeting_item", "admin", "lunch", "free"];
  entries.sort(
    (a, b) => priority.indexOf(a.kind) - priority.indexOf(b.kind),
  );
  return entries[0];
}

// ─────────────────────────────────────────────────────────────────────────────
// DATE UTILITIES
// ─────────────────────────────────────────────────────────────────────────────

const MONTH_SHORT = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];
const DAY_FULL = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
const DAY_SHORT = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

/** Get the Monday of the week containing `date` (Mon=start). */
function getMondayOf(date: Date): Date {
  const d = new Date(date);
  const dow = d.getDay(); // 0=Sun … 6=Sat
  const diff = dow === 0 ? -6 : 1 - dow; // shift to Monday
  d.setDate(d.getDate() + diff);
  d.setHours(0, 0, 0, 0);
  return d;
}

/** Add `days` to a date (returns new Date). */
function addDays(date: Date, days: number): Date {
  const d = new Date(date);
  d.setDate(d.getDate() + days);
  return d;
}

function formatMonthDay(d: Date): string {
  return `${d.getDate()} ${MONTH_SHORT[d.getMonth()]}`;
}

function isSameLocalDay(a: Date, b: Date): boolean {
  return a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate();
}

// ─────────────────────────────────────────────────────────────────────────────
// API TYPES  (unchanged from original)
// ─────────────────────────────────────────────────────────────────────────────

interface UpcomingMeeting {
  id: number;
  title: string;
  date_label: string;
  time_label: string;
  start_time: string;
  end_time: string | null;
  attendees_count?: number;
}

interface ScheduleResponse {
  upcoming_meetings: UpcomingMeeting[];
}

// ─────────────────────────────────────────────────────────────────────────────
// CELL STYLING
// ─────────────────────────────────────────────────────────────────────────────

function cellStyle(kind: SlotKind): React.CSSProperties {
  switch (kind) {
    case "free":
      return {
        background: "color-mix(in srgb, var(--ok) 10%, transparent)",
        color: "var(--ok)",
      };
    case "class":
      return {
        background: "color-mix(in srgb, var(--ink) 7%, transparent)",
        color: "var(--ink)",
      };
    case "lunch":
      return {
        background: "color-mix(in srgb, var(--ink-faint) 12%, transparent)",
        color: "var(--ink-faint)",
      };
    case "meeting_item":
      return {
        background: "color-mix(in srgb, var(--accent) 10%, transparent)",
        color: "var(--accent)",
      };
    case "admin":
      return {
        background: "color-mix(in srgb, var(--warn) 10%, transparent)",
        color: "var(--warn)",
      };
  }
}

function availCellStyle(): React.CSSProperties {
  return {
    background: "color-mix(in srgb, var(--ok) 15%, transparent)",
    color: "var(--ok)",
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// COMPONENT
// ─────────────────────────────────────────────────────────────────────────────

export const Schedule: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const canSchedule =
    !!user && ["chairman", "principal", "hod", "teacher"].includes(user.role);

  // ── Week state ────────────────────────────────────────────────────────────
  const today = useMemo(() => {
    const d = new Date();
    d.setHours(0, 0, 0, 0);
    return d;
  }, []);

  const [weekMonday, setWeekMonday] = useState<Date>(() => getMondayOf(today));

  const weekDates = useMemo(
    () => Array.from({ length: 6 }, (_, i) => addDays(weekMonday, i)),
    [weekMonday],
  );

  const isCurrentWeek = isSameLocalDay(weekMonday, getMondayOf(today));

  // ── Participant filter ────────────────────────────────────────────────────
  const [participantKey, setParticipantKey] =
    useState<ParticipantKey>("everyone");

  const selectedOption = PARTICIPANT_OPTIONS.find(
    (o) => o.key === participantKey,
  )!;

  // ── Grid data ─────────────────────────────────────────────────────────────
  /** Display grid: [dayIndex 0–5][slotIndex 0–5] */
  const displayGrid: SlotEntry[][] = useMemo(() => {
    if (participantKey === "everyone") {
      return Array.from({ length: 6 }, (_, d) =>
        Array.from({ length: 6 }, (_, s) =>
          mergeGridCell(selectedOption.schedules, d, s),
        ),
      );
    }
    // Single schedule — just use the first (and only) entry
    return selectedOption.schedules[0];
  }, [participantKey, selectedOption]);

  /** Common availability: [day][slot] → boolean */
  const commonAvail = useMemo(
    () => computeCommonAvailability(selectedOption.schedules),
    [selectedOption],
  );

  /** Collect free slots per day for the sidebar summary */
  const freeByDay = useMemo(() => {
    const result: { dayIndex: number; slots: number[] }[] = [];
    for (let d = 0; d < 6; d++) {
      const slots: number[] = [];
      for (let s = 0; s < 6; s++) {
        if (commonAvail[d][s]) slots.push(s);
      }
      if (slots.length) result.push({ dayIndex: d, slots });
    }
    return result;
  }, [commonAvail]);

  const totalFreeSlots = freeByDay.reduce((n, d) => n + d.slots.length, 0);

  // ── API: upcoming meetings only ───────────────────────────────────────────
  const [upcoming, setUpcoming] = useState<UpcomingMeeting[]>([]);
  const [apiLoading, setApiLoading] = useState(true);
  const [apiError, setApiError] = useState<string | null>(null);

  useEffect(() => {
    setApiLoading(true);
    setApiError(null);
    api
      .get<ScheduleResponse>("/schedule?view=week")
      .then((d) => setUpcoming(d.upcoming_meetings ?? []))
      .catch((err: Error) =>
        setApiError(err.message || "Could not load upcoming meetings."),
      )
      .finally(() => setApiLoading(false));
  }, []);

  // ─────────────────────────────────────────────────────────────────────────
  // RENDER
  // ─────────────────────────────────────────────────────────────────────────

  return (
    <AppShell
      pageTitle="Weekly Schedule"
      pageSubtitle="Campus timetable, multi-stakeholder common availability, and upcoming sessions."
      actionButton={
        canSchedule ? (
          <button
            onClick={() => navigate("/meetings/new")}
            className="btn-primary no-print shrink-0"
          >
            + Schedule Meeting
          </button>
        ) : undefined
      }
    >

        {/* ── Controls row ──────────────────────────────────────────────── */}
        <div className="flex flex-wrap items-center justify-between gap-4 mb-6 fade-section">
          {/* Week navigation */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => setWeekMonday((m) => addDays(m, -7))}
              className="btn-secondary"
              aria-label="Previous week"
            >
              ← Prev
            </button>
            <button
              onClick={() => setWeekMonday(getMondayOf(today))}
              disabled={isCurrentWeek}
              className="btn-secondary"
              style={
                isCurrentWeek
                  ? { opacity: 0.4, cursor: "default" }
                  : undefined
              }
              aria-label="Go to current week"
            >
              Today
            </button>
            <button
              onClick={() => setWeekMonday((m) => addDays(m, 7))}
              className="btn-secondary"
              aria-label="Next week"
            >
              Next →
            </button>
            <span
              className="font-mono text-soft ml-3"
              style={{ fontSize: 12 }}
            >
              {formatMonthDay(weekMonday)} – {formatMonthDay(addDays(weekMonday, 5))}
            </span>
          </div>

          {/* Participant selector */}
          <div className="flex items-center gap-2">
            <span className="label text-soft" style={{ fontSize: 11 }}>
              View:
            </span>
            <select
              value={participantKey}
              onChange={(e) =>
                setParticipantKey(e.target.value as ParticipantKey)
              }
              className="input-underline"
              style={{
                width: "auto",
                paddingRight: 28,
                fontSize: 13,
                fontFamily: "var(--font-sans)",
                cursor: "pointer",
              }}
              aria-label="Filter by participant"
            >
              {PARTICIPANT_OPTIONS.map((o) => (
                <option key={o.key} value={o.key}>
                  {o.label}
                  {o.count > 1 ? ` (${o.count})` : ""}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* ── Main two-column layout ────────────────────────────────────── */}
        <div className="grid gap-8" style={{ gridTemplateColumns: "1fr 280px" }}>
          {/* ── LEFT: Calendar grid + common availability ──────────────── */}
          <div className="fade-section min-w-0">
            {/* Section label */}
            <div
              className="border-t pt-3 mb-4 flex items-center justify-between"
              style={{ borderColor: "var(--rule-strong)" }}
            >
              <span className="label text-soft">01 — Weekly Timetable</span>
              <span className="font-mono text-faint" style={{ fontSize: 11 }}>
                09:00 – 15:00 · Mon–Sat
              </span>
            </div>

            {/* Legend */}
            <div className="flex flex-wrap gap-4 mb-4" style={{ fontSize: 11 }}>
              {(
                [
                  ["free", "Free"],
                  ["class", "Class"],
                  ["meeting_item", "Meeting"],
                  ["admin", "Admin/Work"],
                  ["lunch", "Lunch"],
                ] as [SlotKind, string][]
              ).map(([kind, lbl]) => (
                <span key={kind} className="flex items-center gap-1.5">
                  <span
                    style={{
                      display: "inline-block",
                      width: 10,
                      height: 10,
                      borderRadius: 2,
                      ...cellStyle(kind),
                      border: "1px solid var(--rule)",
                    }}
                  />
                  <span
                    style={{
                      fontFamily: "var(--font-sans)",
                      color: "var(--ink-soft)",
                      letterSpacing: "0.06em",
                    }}
                  >
                    {lbl}
                  </span>
                </span>
              ))}
            </div>

            {/* ── The grid ───────────────────────────────────────────── */}
            <div style={{ overflowX: "auto" }}>
              <table
                style={{
                  width: "100%",
                  minWidth: 640,
                  borderCollapse: "collapse",
                  tableLayout: "fixed",
                }}
                aria-label="Weekly timetable"
              >
                <colgroup>
                  {/* time column */}
                  <col style={{ width: 120 }} />
                  {/* 6 day columns */}
                  {weekDates.map((_, i) => (
                    <col key={i} />
                  ))}
                </colgroup>

                {/* Header: day names + dates */}
                <thead>
                  <tr>
                    <th
                      scope="col"
                      style={{
                        padding: "14px 16px",
                        borderBottom: "1px solid var(--rule-strong)",
                        textAlign: "left",
                        fontFamily: "var(--font-sans)",
                        fontSize: 11,
                        letterSpacing: "0.12em",
                        textTransform: "uppercase",
                        color: "var(--ink-faint)",
                        fontWeight: 600,
                      }}
                    >
                      Time
                    </th>
                    {weekDates.map((d, i) => {
                      const isToday = isSameLocalDay(d, today);
                      return (
                        <th
                          key={i}
                          scope="col"
                          style={{
                            padding: "14px 16px",
                            borderBottom: isToday
                              ? "3px solid var(--accent)"
                              : "1px solid var(--rule-strong)",
                            textAlign: "left",
                            fontFamily: "var(--font-sans)",
                            fontSize: 12,
                            letterSpacing: "0.08em",
                            textTransform: "uppercase",
                            color: isToday ? "var(--accent)" : "var(--ink-soft)",
                            fontWeight: isToday ? 600 : 500,
                            background: isToday
                              ? "color-mix(in srgb, var(--accent) 6%, transparent)"
                              : "transparent",
                          }}
                        >
                          <span style={{ display: "block" }}>{DAY_SHORT[i]}</span>
                          <span
                            style={{
                              fontFamily: "var(--font-mono)",
                              fontSize: 12,
                              fontWeight: 400,
                              letterSpacing: 0,
                              color: isToday ? "var(--accent)" : "var(--ink-faint)",
                            }}
                          >
                            {formatMonthDay(d)}
                          </span>
                        </th>
                      );
                    })}
                  </tr>
                </thead>

                {/* Body: 6 time rows */}
                <tbody>
                  {HOUR_SLOTS.map((slot, si) => (
                    <tr key={si}>
                      {/* Time label */}
                      <td
                        style={{
                          padding: "16px 16px",
                          borderBottom: "1px solid var(--rule)",
                          fontFamily: "var(--font-mono)",
                          fontSize: 11.5,
                          color: "var(--ink-faint)",
                          whiteSpace: "nowrap",
                          verticalAlign: "middle",
                        }}
                      >
                        {slot.label}
                      </td>

                      {/* One cell per day */}
                      {weekDates.map((d, di) => {
                        const isToday = isSameLocalDay(d, today);
                        const entry = displayGrid[di]?.[si] ?? FREE;
                        const isAvail = commonAvail[di]?.[si] ?? false;

                        // When "Everyone" is shown, use merged cell
                        // Highlight the cell if it's a common-availability slot
                        const showAvailHighlight =
                          participantKey === "everyone" && isAvail && si !== 4;

                        const style: React.CSSProperties = {
                          padding: "14px 16px",
                          borderBottom: "1px solid var(--rule)",
                          borderLeft: isToday
                            ? "2px solid color-mix(in srgb, var(--accent) 40%, transparent)"
                            : "1px solid var(--rule)",
                          verticalAlign: "top",
                          minHeight: 64,
                          ...(showAvailHighlight ? availCellStyle() : cellStyle(entry.kind)),
                        };

                        return (
                          <td key={di} style={style}>
                            <span
                              style={{
                                fontFamily: "var(--font-sans)",
                                fontSize: 12.5,
                                fontWeight: 500,
                                lineHeight: 1.4,
                                display: "block",
                              }}
                            >
                              {showAvailHighlight ? "Free" : entry.label}
                            </span>
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* ── Common Availability Section ──────────────────────────── */}
            <div
              className="mt-8 border-t pt-4"
              style={{ borderColor: "var(--rule-strong)" }}
            >
              <div className="flex items-baseline justify-between mb-3">
                <span className="label text-soft">
                  02 — Common Availability
                </span>
                <span className="font-mono text-faint" style={{ fontSize: 11 }}>
                  {selectedOption.count}/{selectedOption.count} participants ·{" "}
                  {totalFreeSlots} free{" "}
                  {totalFreeSlots === 1 ? "slot" : "slots"} this week
                </span>
              </div>

              {totalFreeSlots === 0 ? (
                <p
                  className="font-serif italic"
                  style={{ color: "var(--ink-soft)", fontSize: 14 }}
                >
                  No common free slots for the selected participants this week.
                </p>
              ) : (
                <div
                  className="grid gap-3"
                  style={{
                    gridTemplateColumns:
                      "repeat(auto-fill, minmax(180px, 1fr))",
                  }}
                >
                  {freeByDay.map(({ dayIndex, slots }) => (
                    <div
                      key={dayIndex}
                      style={{
                        borderLeft: "2px solid var(--ok)",
                        paddingLeft: 10,
                      }}
                    >
                      <div
                        style={{
                          fontFamily: "var(--font-sans)",
                          fontSize: 11,
                          letterSpacing: "0.1em",
                          textTransform: "uppercase",
                          color: "var(--ok)",
                          fontWeight: 600,
                          marginBottom: 4,
                        }}
                      >
                        {DAY_FULL[dayIndex]}
                      </div>
                      <div
                        style={{
                          borderLeft: "none",
                          display: "flex",
                          flexDirection: "column",
                          gap: 3,
                        }}
                      >
                        {slots.map((si) => (
                          <span
                            key={si}
                            style={{
                              fontFamily: "var(--font-mono)",
                              fontSize: 11,
                              color: "var(--ink)",
                            }}
                          >
                            {HOUR_SLOTS[si].label}
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Quick demo note */}
              <p
                className="mt-4"
                style={{
                  fontFamily: "var(--font-sans)",
                  fontSize: 11,
                  color: "var(--ink-faint)",
                  fontStyle: "italic",
                }}
              >
                Slots where every selected participant is simultaneously free.
                Use the participant filter above to refine.
              </p>
            </div>
          </div>

          {/* ── RIGHT: Upcoming meetings sidebar ─────────────────────────── */}
          <aside
            className="fade-section"
            style={{ borderLeft: "1px solid var(--rule)", paddingLeft: 20 }}
          >
            <div
              className="border-t pt-3 mb-4"
              style={{ borderColor: "var(--rule-strong)" }}
            >
              <span className="label text-soft">03 — Upcoming Meetings</span>
            </div>

            {apiLoading ? (
              <p
                className="font-serif italic"
                style={{ color: "var(--ink-soft)", fontSize: 14 }}
              >
                Loading…
              </p>
            ) : apiError ? (
              <p
                style={{
                  fontFamily: "var(--font-sans)",
                  fontSize: 12,
                  color: "var(--accent)",
                }}
              >
                {apiError}
              </p>
            ) : upcoming.length === 0 ? (
              <div>
                <p
                  className="font-serif italic"
                  style={{ color: "var(--ink-soft)", fontSize: 14 }}
                >
                  No upcoming meetings.
                </p>
                {canSchedule && (
                  <button
                    onClick={() => navigate("/meetings/new")}
                    className="mt-3 label text-ink"
                    style={{
                      textDecoration: "underline",
                      textUnderlineOffset: 3,
                      background: "none",
                      border: "none",
                      cursor: "pointer",
                      fontSize: 11,
                    }}
                  >
                    Schedule one →
                  </button>
                )}
              </div>
            ) : (
              <ul
                style={{
                  listStyle: "none",
                  margin: 0,
                  padding: 0,
                  borderTop: "1px solid var(--rule)",
                }}
              >
                {upcoming.map((m) => (
                  <li
                    key={m.id}
                    onClick={() => navigate(`/meetings/${m.id}/agenda`)}
                    style={{
                      padding: "12px 4px",
                      borderBottom: "1px solid var(--rule)",
                      cursor: "pointer",
                      transition: "background 120ms ease",
                    }}
                    onMouseEnter={(e) => {
                      (e.currentTarget as HTMLElement).style.background =
                        "var(--tint)";
                    }}
                    onMouseLeave={(e) => {
                      (e.currentTarget as HTMLElement).style.background =
                        "transparent";
                    }}
                  >
                    {/* Meeting title */}
                    <div
                      style={{
                        fontFamily: "var(--font-serif)",
                        fontSize: 14,
                        color: "var(--ink)",
                        lineHeight: 1.3,
                        marginBottom: 4,
                      }}
                    >
                      {m.title}
                    </div>
                    {/* Date · time */}
                    <div
                      style={{
                        fontFamily: "var(--font-mono)",
                        fontSize: 11,
                        color: "var(--ink-soft)",
                      }}
                    >
                      {m.date_label} · {m.time_label}
                    </div>
                  </li>
                ))}
              </ul>
            )}

            {/* ── Working hours note ─────────────────────────────────── */}
            <div
              style={{
                marginTop: 32,
                borderTop: "1px solid var(--rule)",
                paddingTop: 12,
              }}
            >
              <span className="label text-soft" style={{ display: "block", marginBottom: 8 }}>
                Working Hours
              </span>
              <div
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: 11,
                  color: "var(--ink-soft)",
                  lineHeight: 1.8,
                }}
              >
                <div>Mon – Sat</div>
                <div>09:00 – 15:00</div>
                <div style={{ color: "var(--ink-faint)" }}>
                  Lunch 13:00 – 14:00
                </div>
                <div style={{ color: "var(--ink-faint)", marginTop: 4 }}>
                  Sunday — Holiday
                </div>
              </div>
            </div>
          </aside>
        </div>
    </AppShell>
  );
};
