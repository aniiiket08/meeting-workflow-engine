import React, { useEffect, useMemo, useState } from "react";
import { ChevronDown, Plus, X } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { useAuth } from "../lib/auth";
import { AppShell } from "../components/AppShell";
import { MeetingWorkLinks } from "../components/MeetingWorkLinks";
import { Slot, SlotCard } from "../components/SlotCard";

// ── Types ─────────────────────────────────────────────────────────────────────

interface DirectoryUser {
  id: number;
  name: string;
  email: string;
  role: string;
}

interface RoomOption {
  id: number;
  name: string;
  capacity: number;
  equipment: string[];
}

interface RoomAvailability extends RoomOption {
  status: "available" | "booked" | "too_small";
  reason: string;
  is_best_fit: boolean;
  best_fit_reason?: string;
}

interface RoomAvailabilityResponse {
  rooms: RoomAvailability[];
  best_fit_id: number | null;
  headcount: number;
  required_equipment: string[];
}

// Equipment labels shown in the filter — canonical keys match backend
const EQUIPMENT_LABELS: Record<string, string> = {
  projector: "Projector",
  mic: "Microphone",
  whiteboard: "Whiteboard",
  video_conf: "Video conferencing",
  stage: "Stage",
  seating: "Extra seating",
};

const FILTER_EQUIPMENT = ["projector", "mic", "whiteboard", "video_conf"];

// ── Component ─────────────────────────────────────────────────────────────────

export const NewMeeting: React.FC = () => {
  // ── Form state ───────────────────────────────────────────────────────────
  const [title, setTitle]                     = useState("");
  const [description, setDescription]         = useState("");
  const [agendaItemsText, setAgendaItemsText] = useState("");
  const [durationMinutes, setDurationMinutes] = useState(60);
  const [targetDate, setTargetDate]           = useState("");
  const [selectedEmails, setSelectedEmails]   = useState<string[]>([]);
  const [directorySearch, setDirectorySearch] = useState("");
  const [externalEmail, setExternalEmail]     = useState("");
  const [attendeeError, setAttendeeError]     = useState<string | null>(null);

  // Equipment filter for the room section (user's stated requirements)
  const [equipmentNeeded, setEquipmentNeeded] = useState<string[]>([]);

  // ── Directory / rooms ─────────────────────────────────────────────────────
  const [directory, setDirectory]             = useState<DirectoryUser[]>([]);
  const [directoryLoading, setDirectoryLoading] = useState(true);

  // ── Slot state ────────────────────────────────────────────────────────────
  const [loading, setLoading]                 = useState(false);
  const [error, setError]                     = useState<string | null>(null);
  const [createdMeetingId, setCreatedMeetingId] = useState<number | null>(null);
  const [rankedSlots, setRankedSlots]         = useState<Slot[]>([]);

  // The slot the user clicked but hasn't confirmed yet
  const [stagedSlot, setStagedSlot]           = useState<Slot | null>(null);

  // ── Room picker state ─────────────────────────────────────────────────────
  const [roomsLoading, setRoomsLoading]       = useState(false);
  const [availableRooms, setAvailableRooms]   = useState<RoomAvailability[]>([]);
  const [selectedRoomId, setSelectedRoomId]   = useState<number | null>(null);
  const [isOnlineMeeting, setIsOnlineMeeting] = useState<boolean>(false);
  const [roomError, setRoomError]             = useState<string | null>(null);
  // Equipment filter local to the room picker (can differ from equipmentNeeded)
  const [roomEquipFilter, setRoomEquipFilter] = useState<string[]>([]);

  // ── Confirm state ─────────────────────────────────────────────────────────
  const [bookingLoading, setBookingLoading]   = useState(false);

  const { user } = useAuth();
  const navigate = useNavigate();

  // ── Load directory on mount ───────────────────────────────────────────────
  useEffect(() => {
    api.get<DirectoryUser[]>("/users")
      .then(setDirectory)
      .catch((err: Error) => setError(err.message || "Could not load member directory."))
      .finally(() => setDirectoryLoading(false));
  }, []);

  // ── Sync room equipment filter with the meeting's equipment requirements ──
  useEffect(() => {
    setRoomEquipFilter(equipmentNeeded);
  }, [equipmentNeeded]);

  // ── Attendee helpers ──────────────────────────────────────────────────────
  const visibleUsers = directory.filter((member) => {
    if (member.id === user?.id) return false;
    const searchText = `${member.name} ${member.email} ${member.role}`.toLowerCase();
    return searchText.includes(directorySearch.trim().toLowerCase());
  });

  const toggleAttendee = (email: string) => {
    setAttendeeError(null);
    setSelectedEmails((prev) =>
      prev.includes(email) ? prev.filter((e) => e !== email) : [...prev, email],
    );
  };

  const addExternalAttendee = () => {
    const email = externalEmail.trim().toLowerCase();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setAttendeeError("Enter a valid email address.");
      return;
    }
    if (email === user?.email.toLowerCase() || selectedEmails.includes(email)) {
      setAttendeeError("This person is already included.");
      return;
    }
    setSelectedEmails((prev) => [...prev, email]);
    setExternalEmail("");
    setAttendeeError(null);
  };

  // ── Step 1: create meeting + fetch slots ──────────────────────────────────
  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) {
      setError("Add a meeting title before finding times.");
      return;
    }
    setError(null);
    setLoading(true);
    setRankedSlots([]);
    setStagedSlot(null);
    setAvailableRooms([]);
    setSelectedRoomId(null);

    try {
      const res = await api.post<any>("/meetings", {
        title,
        description,
        agenda_items_text: agendaItemsText.trim() || null,
        duration_minutes: Number(durationMinutes),
        target_date: targetDate || null,
        attendee_emails: selectedEmails,
        equipment_needed: equipmentNeeded,
      });
      setCreatedMeetingId(res.meeting.id);
      setRankedSlots(res.slots || []);
    } catch (err: any) {
      setError(err.message || "Could not calculate ranked meeting slots.");
    } finally {
      setLoading(false);
    }
  };

  // ── Step 2: user picks a slot → load room availability ───────────────────
  const handleStageSlot = async (slot: Slot) => {
    if (!createdMeetingId) return;
    setStagedSlot(slot);
    setSelectedRoomId(null);
    setIsOnlineMeeting(false);
    setAvailableRooms([]);
    setRoomError(null);
    setRoomsLoading(true);

    // headcount = attendee emails + the organiser (user)
    const headcount = selectedEmails.length + 1;

    const params = new URLSearchParams({
      start_time: slot.start_time,
      end_time: slot.end_time,
      headcount: String(headcount),
      equipment: equipmentNeeded.join(","),
    });

    try {
      const res = await api.get<RoomAvailabilityResponse>(
        `/rooms/availability?${params.toString()}`,
      );
      setAvailableRooms(res.rooms);
      // Pre-select best fit if available
      if (res.best_fit_id !== null) {
        setSelectedRoomId(res.best_fit_id);
      } else {
        // Fallback to Zoom if no physical room fits
        setIsOnlineMeeting(true);
      }
    } catch (err: any) {
      setRoomError(err.message || "Could not load room availability.");
    } finally {
      setRoomsLoading(false);
    }
  };

  // ── Step 3: confirm slot + chosen room ────────────────────────────────────
  const handleConfirm = async () => {
    if (!createdMeetingId || !stagedSlot) return;
    setBookingLoading(true);
    setError(null);
    setRoomError(null);

    try {
      await api.post(`/meetings/${createdMeetingId}/confirm`, {
        selected_start_time: stagedSlot.start_time,
        selected_end_time: stagedSlot.end_time,
        room_id: isOnlineMeeting ? null : (selectedRoomId ?? null),
        is_online: isOnlineMeeting,
      });
      navigate("/meetings");
    } catch (err: any) {
      // Surface room-specific errors in the room section
      const msg = err.message || "Could not confirm the meeting.";
      if (msg.toLowerCase().includes("room")) {
        setRoomError(msg);
      } else {
        setError(msg);
      }
    } finally {
      setBookingLoading(false);
    }
  };

  // ── Filtered room list (client-side equipment filter) ─────────────────────
  const filteredRooms: RoomAvailability[] = useMemo(() => {
    if (!roomEquipFilter.length) return availableRooms;
    return availableRooms.map((r) => {
      if (r.status === "available") {
        const missing = roomEquipFilter.filter((eq) => !r.equipment.includes(eq));
        if (missing.length) {
          return {
            ...r,
            status: "too_small" as const,
            reason: `Missing: ${missing.map((e) => EQUIPMENT_LABELS[e] ?? e).join(", ")}`,
            is_best_fit: false,
          };
        }
      }
      return r;
    });
  }, [availableRooms, roomEquipFilter]);

  // If the selected room is now filtered out, deselect it
  useEffect(() => {
    if (selectedRoomId !== null) {
      const entry = filteredRooms.find((r) => r.id === selectedRoomId);
      if (entry && entry.status !== "available") {
        // Try to fall back to best fit that's still available
        const bestAvail = filteredRooms.find((r) => r.status === "available" && r.is_best_fit);
        const anyAvail = filteredRooms.find((r) => r.status === "available");
        setSelectedRoomId(bestAvail?.id ?? anyAvail?.id ?? null);
      }
    }
  }, [filteredRooms, selectedRoomId]);

  const selectedRoomEntry = filteredRooms.find((r) => r.id === selectedRoomId);
  const anyAvailableRoom  = filteredRooms.some((r) => r.status === "available");

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <AppShell
      pageTitle="New Meeting"
      pageSubtitle="Configure topic, select attendees, and review ranked slot proposals."
    >

        {/* ── Top-level error ───────────────────────────────── */}
        {error && (
          <div className="error-banner mb-8" role="alert">
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">

          {/* ── Left: form ───────────────────────────────────── */}
          <div className="lg:col-span-5 fade-section">
            <div className="editorial-card-raised p-6 space-y-5">
              <div className="border-b border-rule pb-3 mb-1">
                <span className="label text-soft text-10">01 — Request Details</span>
                <h3 className="font-serif text-18 text-ink mt-0.5">Configure Meeting</h3>
              </div>

              <form onSubmit={handleCreate} className="space-y-5" noValidate>
              <div className="field-float">
                <label htmlFor="nm-title" className="field-label">Meeting title</label>
                <input
                  id="nm-title"
                  type="text"
                  required
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="input-underline"
                />
              </div>

              <div className="field-float">
                <label htmlFor="nm-desc" className="field-label">Description / topic</label>
                <textarea
                  id="nm-desc"
                  rows={3}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="input-underline resize-none"
                  style={{ paddingTop: 8 }}
                />
              </div>

              <div className="field-float">
                <label htmlFor="nm-agenda-items" className="field-label">
                  Agenda items <span className="text-faint">(optional)</span>
                </label>
                <textarea
                  id="nm-agenda-items"
                  rows={5}
                  value={agendaItemsText}
                  onChange={(e) => setAgendaItemsText(e.target.value)}
                  className="input-underline resize-none font-mono"
                  style={{ paddingTop: 8, fontSize: 12 }}
                  placeholder={
                    "One item per line. Format: Title | Lead | Minutes\nExample:\nWelcome and objectives | HOD | 5\nLive demo | Aniket, Sujal | 15"
                  }
                  aria-describedby="nm-agenda-items-hint"
                />
                <p id="nm-agenda-items-hint" className="text-11 text-soft mt-2">
                  Items appear verbatim in the agenda, in this order. Lead and minutes are
                  optional — the agent fills in any blanks.
                </p>
              </div>

              <div className="field-float">
                <label htmlFor="nm-date" className="field-label">Preferred date</label>
                <input
                  id="nm-date"
                  type="date"
                  min={new Date(Date.now() - new Date().getTimezoneOffset() * 60000)
                    .toISOString()
                    .slice(0, 10)}
                  value={targetDate}
                  onChange={(e) => setTargetDate(e.target.value)}
                  className="input-underline"
                />
                <p className="text-11 text-soft mt-2">
                  Optional. Leave blank to find times on the next available day.
                </p>
              </div>

              <div className="field-float">
                <label htmlFor="nm-dur" className="field-label">Meeting length</label>
                <select
                  id="nm-dur"
                  value={durationMinutes}
                  onChange={(e) => setDurationMinutes(Number(e.target.value))}
                  className="input-underline bg-transparent"
                >
                  <option value={30}>30 minutes</option>
                  <option value={45}>45 minutes</option>
                  <option value={60}>60 minutes</option>
                  <option value={90}>90 minutes</option>
                  <option value={120}>2 hours</option>
                </select>
              </div>

              {/* Attendees */}
              <div>
                <label className="field-label" htmlFor="nm-directory-search">
                  Attendees
                </label>
                <details className="mt-2">
                  <summary className="input-underline flex cursor-pointer list-none items-center justify-between gap-3">
                    <span>
                      {selectedEmails.length
                        ? `${selectedEmails.length} additional ${selectedEmails.length === 1 ? "person" : "people"} selected`
                        : "Choose university members"}
                    </span>
                    <ChevronDown size={16} aria-hidden="true" />
                  </summary>
                  <div className="mt-1 w-full border border-rule bg-paper p-3">
                    <input
                      id="nm-directory-search"
                      type="search"
                      value={directorySearch}
                      onChange={(e) => setDirectorySearch(e.target.value)}
                      placeholder="Search name, email, or role"
                      className="input-underline w-full"
                    />
                    <div className="mt-2 max-h-56 overflow-y-auto">
                      {directoryLoading ? (
                        <p className="py-3 text-12 text-soft">Loading university members…</p>
                      ) : visibleUsers.length ? (
                        visibleUsers.map((member) => (
                          <label
                            key={member.id}
                            className="flex cursor-pointer items-start gap-3 border-b border-rule py-2 last:border-b-0"
                          >
                            <input
                              type="checkbox"
                              checked={selectedEmails.includes(member.email.toLowerCase())}
                              onChange={() => toggleAttendee(member.email.toLowerCase())}
                              className="mt-1 accent-[var(--accent)]"
                            />
                            <span className="min-w-0">
                              <span className="block text-13 text-ink">{member.name}</span>
                              <span className="block break-all text-11 text-soft">
                                {member.email} · {member.role.toUpperCase()}
                              </span>
                            </span>
                          </label>
                        ))
                      ) : (
                        <p className="py-3 text-12 text-soft">No matching members.</p>
                      )}
                    </div>
                  </div>
                </details>
                <p className="mt-2 text-11 text-soft">
                  You are included automatically. Add university members or an email address.
                </p>
                <div className="mt-3 flex gap-2">
                  <input
                    type="email"
                    value={externalEmail}
                    onChange={(e) => setExternalEmail(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        addExternalAttendee();
                      }
                    }}
                    placeholder="name@gmail.com"
                    aria-label="Add attendee by email address"
                    className="input-underline min-w-0 flex-1"
                  />
                  <button
                    type="button"
                    onClick={addExternalAttendee}
                    className="flex shrink-0 items-center gap-1 border border-rule px-3 text-12 text-ink hover:bg-accent-wash"
                  >
                    <Plus size={14} aria-hidden="true" /> Add attendee
                  </button>
                </div>
                {attendeeError && (
                  <p className="mt-2 text-12 text-accent" role="alert">{attendeeError}</p>
                )}
                <p className="mt-2 text-11 text-soft">
                  Attendees without connected calendar data are included, but their availability
                  cannot be checked.
                </p>
                {selectedEmails.length > 0 && (
                  <ul className="mt-3 flex flex-wrap gap-2" aria-label="Selected invitees">
                    {selectedEmails.map((email) => {
                      const member = directory.find(
                        (p) => p.email.toLowerCase() === email,
                      );
                      return (
                        <li
                          key={email}
                          className="inline-flex max-w-full items-center gap-2 border border-rule px-2 py-1 text-11"
                        >
                          <span className="min-w-0 truncate" title={email}>
                            {member ? member.name : email}
                          </span>
                          <button
                            type="button"
                            onClick={() => toggleAttendee(email)}
                            aria-label={`Remove ${email}`}
                            className="shrink-0 text-soft hover:text-accent"
                          >
                            <X size={14} aria-hidden="true" />
                          </button>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </div>

              {/* Equipment requirements */}
              <fieldset>
                <legend className="field-label">Room requirements</legend>
                <p className="mb-2 text-11 text-soft">
                  Check any equipment your meeting needs. Rooms that lack it will be
                  shown as unavailable.
                </p>
                <div className="grid grid-cols-2 gap-x-3 gap-y-2">
                  {FILTER_EQUIPMENT.map((eq) => (
                    <label key={eq} className="flex items-center gap-2 text-12 text-ink">
                      <input
                        type="checkbox"
                        checked={equipmentNeeded.includes(eq)}
                        onChange={() =>
                          setEquipmentNeeded((prev) =>
                            prev.includes(eq)
                              ? prev.filter((e) => e !== eq)
                              : [...prev, eq],
                          )
                        }
                        className="accent-[var(--accent)]"
                      />
                      <span>{EQUIPMENT_LABELS[eq] ?? eq}</span>
                    </label>
                  ))}
                </div>
              </fieldset>

              <button type="submit" disabled={loading} className="w-full btn-primary py-3 text-14">
                {loading ? "Finding slots…" : "Calculate best slots"}
              </button>
            </form>
            </div>
          </div>

          {/* ── Right: slots + room picker ────────────────────── */}
          <div className="lg:col-span-7 fade-section space-y-6">

            {/* ── Ranked slots ─────────────────────────────── */}
            <div className="editorial-card-raised p-6 space-y-4">
              <div className="border-b border-rule pb-3 flex justify-between items-center">
                <div>
                  <span className="label text-soft text-10">02 — Ranked Available Slots</span>
                  <h3 className="font-serif text-18 text-ink mt-0.5">Suggested Time Windows</h3>
                </div>
                {rankedSlots.length > 0 && (
                  <span className="font-mono text-12 text-ink-faint">
                    {rankedSlots.length} options
                  </span>
                )}
              </div>

              {rankedSlots.length === 0 ? (
                <div className="border-t border-rule">
                  <div className="empty-ghost py-8">
                    {[1, 2, 3].map((i) => (
                      <div
                        key={i}
                        style={{
                          height: 52,
                          borderBottom: "1px solid var(--rule)",
                          opacity: 1 - i * 0.25,
                        }}
                      />
                    ))}
                  </div>
                  <p className="font-serif italic text-soft text-14 mt-3">
                    Fill in the meeting details and calculate best slots to see ranked options.
                  </p>
                </div>
              ) : (
                <div className="border-t border-rule">
                  {rankedSlots.map((slot) => (
                    <SlotCard
                      key={slot.slot_index}
                      slot={slot}
                      onSelect={handleStageSlot}
                      isSelecting={roomsLoading && stagedSlot?.slot_index === slot.slot_index}
                      isSelected={stagedSlot?.slot_index === slot.slot_index}
                    />
                  ))}
                </div>
              )}
            </div>

            {/* ── Room picker (shown after a slot is staged) ─── */}
            {stagedSlot && (
              <div className="editorial-card-raised p-6 space-y-4">
                <div className="border-b border-rule pb-3 flex items-baseline justify-between">
                  <div>
                    <span className="label text-soft text-10">03 — Facility or Online Setup</span>
                    <h3 className="font-serif text-18 text-ink mt-0.5">Select Venue or Virtual Mode</h3>
                  </div>
                  <span className="font-mono text-12 text-ink-faint">
                    {stagedSlot.start_time.slice(11, 16)}–{stagedSlot.end_time.slice(11, 16)}
                  </span>
                </div>

                {/* Equipment filter for the room picker */}
                <div className="mb-4 flex flex-wrap gap-x-4 gap-y-2">
                  {FILTER_EQUIPMENT.map((eq) => (
                    <label key={eq} className="flex items-center gap-1.5 text-12 text-ink">
                      <input
                        type="checkbox"
                        checked={roomEquipFilter.includes(eq)}
                        onChange={() =>
                          setRoomEquipFilter((prev) =>
                            prev.includes(eq)
                              ? prev.filter((e) => e !== eq)
                              : [...prev, eq],
                          )
                        }
                        className="accent-[var(--accent)]"
                      />
                      <span>{EQUIPMENT_LABELS[eq] ?? eq}</span>
                    </label>
                  ))}
                </div>

                {roomsLoading ? (
                  <p className="font-serif italic text-soft text-15 py-6 border-t border-rule">
                    Checking room availability…
                  </p>
                ) : roomError ? (
                  <div className="error-banner" role="alert">{roomError}</div>
                ) : filteredRooms.length === 0 ? (
                  <p className="font-serif italic text-soft text-15 py-6 border-t border-rule">
                    No rooms found.
                  </p>
                ) : (
                  <>
                    {/* Room list — simple ruled list per design.md */}
                    <ul
                      className="border-t border-rule"
                      role="radiogroup"
                      aria-label="Choose a room"
                    >
                      {filteredRooms.map((room) => {
                        const selectable = room.status === "available";
                        const isSelected = selectedRoomId === room.id;

                        return (
                          <li
                            key={room.id}
                            className={`border-b border-rule py-4 px-1 flex items-start gap-4 ${
                              selectable ? "cursor-pointer" : "opacity-40"
                            }`}
                            onClick={() => selectable && setSelectedRoomId(room.id)}
                          >
                            {/* Radio indicator */}
                            <span
                              aria-hidden="true"
                              style={{
                                display: "inline-flex",
                                alignItems: "center",
                                justifyContent: "center",
                                width: 16,
                                height: 16,
                                borderRadius: "50%",
                                border: isSelected
                                  ? "2px solid var(--ink)"
                                  : "1px solid var(--rule-strong)",
                                flexShrink: 0,
                                marginTop: 3,
                              }}
                            >
                              {isSelected && (
                                <span
                                  style={{
                                    width: 7,
                                    height: 7,
                                    borderRadius: "50%",
                                    background: "var(--ink)",
                                    display: "block",
                                  }}
                                />
                              )}
                            </span>

                            <div className="flex-1 min-w-0">
                              {/* Name + capacity */}
                              <div className="flex items-baseline justify-between gap-2 flex-wrap">
                                <span className="font-serif text-15 text-ink">{room.name}</span>
                                <span className="font-mono text-11 text-soft shrink-0">
                                  {room.capacity} seats
                                </span>
                              </div>

                              {/* Equipment chips */}
                              <div className="flex flex-wrap gap-1.5 mt-1.5">
                                {room.equipment.map((eq) => (
                                  <span
                                    key={eq}
                                    style={{
                                      fontFamily: "var(--font-sans)",
                                      fontSize: 10,
                                      letterSpacing: "0.08em",
                                      textTransform: "uppercase",
                                      padding: "1px 6px",
                                      border: "1px solid var(--rule)",
                                      color: roomEquipFilter.includes(eq)
                                        ? "var(--ink)"
                                        : "var(--ink-faint)",
                                      fontWeight: roomEquipFilter.includes(eq) ? 600 : 400,
                                    }}
                                  >
                                    {EQUIPMENT_LABELS[eq] ?? eq}
                                  </span>
                                ))}
                              </div>

                              {/* Status line */}
                              {room.status !== "available" ? (
                                <p className="mt-1.5 text-11 font-sans text-soft italic">
                                  {room.reason}
                                </p>
                              ) : room.is_best_fit && room.best_fit_reason ? (
                                <p
                                  className="mt-1.5 text-11 font-sans"
                                  style={{ color: "var(--ok)" }}
                                >
                                  ✓ {room.best_fit_reason}
                                </p>
                              ) : null}
                            </div>

                            {/* Status badge */}
                            <span
                              className="label shrink-0 mt-0.5"
                              style={{
                                color:
                                  room.status === "available"
                                    ? "var(--ok)"
                                    : room.status === "booked"
                                    ? "var(--accent)"
                                    : "var(--ink-faint)",
                              }}
                            >
                              {room.status === "available"
                                ? "Available"
                                : room.status === "booked"
                                ? "Booked"
                                : "Too small"}
                            </span>
                          </li>
                        );
                      })}

                      {/* Zoom Online Meeting option */}
                      <li
                        className="border-b border-rule py-4 px-1 flex items-start gap-4 cursor-pointer"
                        style={{
                          background: isOnlineMeeting ? "rgba(43, 114, 186, 0.05)" : "transparent",
                        }}
                        onClick={() => {
                          setIsOnlineMeeting(true);
                          setSelectedRoomId(null);
                        }}
                      >
                        <span
                          aria-hidden="true"
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            justifyContent: "center",
                            width: 16,
                            height: 16,
                            borderRadius: "50%",
                            border: isOnlineMeeting
                              ? "2px solid #2B72BA"
                              : "1px solid var(--rule-strong)",
                            flexShrink: 0,
                            marginTop: 3,
                          }}
                        >
                          {isOnlineMeeting && (
                            <span
                              style={{
                                width: 7,
                                height: 7,
                                borderRadius: "50%",
                                background: "#2B72BA",
                                display: "block",
                              }}
                            />
                          )}
                        </span>

                        <div className="flex-1 min-w-0">
                          <div className="flex items-baseline justify-between gap-2 flex-wrap">
                            <span className="font-serif text-15 font-medium" style={{ color: "#2B72BA" }}>
                              Online Meeting (Zoom Video Conference)
                            </span>
                            <span className="font-mono text-11 text-soft shrink-0">
                              Unlimited remote seats
                            </span>
                          </div>
                          <p className="mt-1 text-12 font-sans text-soft">
                            MCP-powered Zoom meeting. Automatically creates a secure video room with join link.
                          </p>
                          {isOnlineMeeting && (
                            <p className="mt-1.5 text-11 font-sans" style={{ color: "#2B72BA" }}>
                              ✓ Zoom link will be created and shared with all participants
                            </p>
                          )}
                        </div>

                        <span
                          className="label shrink-0 mt-0.5"
                          style={{ color: "#2B72BA", border: "1px solid #2B72BA", padding: "1px 6px", borderRadius: 4 }}
                        >
                          Zoom MCP
                        </span>
                      </li>
                    </ul>

                    {/* Offline room unavailable banner if applicable */}
                    {!anyAvailableRoom && (
                      <div
                        className="mt-4 p-3 border rounded text-13"
                        style={{ borderColor: "#2B72BA", background: "rgba(43, 114, 186, 0.08)", color: "var(--ink)" }}
                        role="alert"
                      >
                        <strong>No physical room matches your headcount/equipment.</strong>
                        <p className="mt-1 text-12">
                          You can proceed seamlessly by choosing <strong>Online Meeting (Zoom Video Conference)</strong> above.
                        </p>
                      </div>
                    )}

                    {/* Confirm button */}
                    <div className="mt-6">
                      {isOnlineMeeting ? (
                        <p className="text-13 text-soft mb-3">
                          <span className="font-serif text-ink" style={{ color: "#2B72BA" }}>Zoom Video Conference</span>
                          {" "}&middot; Online Meeting
                        </p>
                      ) : selectedRoomEntry ? (
                        <p className="text-13 text-soft mb-3">
                          <span className="font-serif text-ink">{selectedRoomEntry.name}</span>
                          {" "}&middot; {selectedRoomEntry.capacity} seats
                        </p>
                      ) : null}
                      <button
                        onClick={handleConfirm}
                        disabled={bookingLoading || (!selectedRoomId && !isOnlineMeeting)}
                        className="btn-primary disabled:opacity-50"
                        style={{ minWidth: 240 }}
                      >
                        {bookingLoading
                          ? "Scheduling…"
                          : isOnlineMeeting
                          ? "Confirm & Create Zoom Meeting"
                          : selectedRoomId
                          ? `Confirm and book ${selectedRoomEntry?.name ?? "room"}`
                          : "Select a room or Zoom to continue"}
                      </button>
                    </div>
                  </>
                )}
              </div>
            )}
          </div>
        </div>

        {/* ── 04 — Always available links ──────────────────────── */}
        <div className="mt-12 border-t border-rule-strong pt-4 fade-section">
          <div className="mb-3">
            <span className="label text-soft">04 — Always available</span>
          </div>
          {createdMeetingId ? (
            <>
              <p className="font-serif italic text-soft text-15 mb-4">
                This meeting is created. Open any step without waiting for the rest to finish.
              </p>
              <MeetingWorkLinks meetingId={createdMeetingId} />
            </>
          ) : (
            <p className="font-serif italic text-soft text-15">
              After you calculate slots, Agenda, Minutes, and Tasks stay visible for this meeting.
            </p>
          )}
        </div>
    </AppShell>
  );
};
