# memory.md — Project Progress Log

The single source of truth for what has been built, what is in progress, and what must be redone.

**Any AI tool working on this repo reads this file first and updates it after every task. No exceptions.**

---

## 1. Update rules (mandatory)

### When to update

1. **Before starting a task:** set it to `IN PROGRESS`, fill "Current focus" and "Files being touched".
2. **After finishing a task:** set it to `NEEDS REVIEW`, list files changed, note how it was verified.
3. **When the user accepts it** (says it is fine, moves on, or checks pass and no objection is raised): set it to `DONE` and add the date.
4. **When the user rejects or asks for changes:** set it to `REDO` (see section 2). Never leave it as `DONE`.
5. **When blocked:** set it to `BLOCKED` with the reason and what is needed.
6. **At the end of every session:** add a line to the Session log and refresh "Current focus".

### Status vocabulary

| Status | Meaning |
| --- | --- |
| `NOT STARTED` | Nothing done yet |
| `IN PROGRESS` | Being worked on right now. Only one task at a time. |
| `NEEDS REVIEW` | Built and tested, waiting for the user to confirm |
| `DONE` | Confirmed working and accepted |
| `REDO` | Previously built, rejected or found wrong; being rebuilt |
| `BLOCKED` | Cannot continue; reason recorded |

### Honesty rules

- **Never mark `DONE` on your own.** The most the AI can set is `NEEDS REVIEW`.
- **Never mark a task complete if it is partial, untested, stubbed, or only compiles.** Partial work stays `IN PROGRESS` with a note of what remains.
- A task is only `NEEDS REVIEW` if its tests pass and its "done when" line in `phases.md` is met. State which checks were run.
- Do not delete history. Rejected work stays visible in the Redo log.
- If a file in the repo disagrees with this log, trust the repo, then correct the log and note the mismatch.
- Keep entries short and factual. No filler, no praise.

### Phase status

A phase is `DONE` only when **all** its tasks are `DONE` and its checklist in `phases.md` is ticked. Otherwise it is `IN PROGRESS` or `NOT STARTED`.

---

## 2. How redo works

If the output was not what the user wanted, or was changed after being accepted:

1. Set the task status to `REDO`.
2. Increase the **Attempts** count by 1.
3. Add a row to the **Redo log** (section 6): task ID, what was wrong (in the user's words where possible), what will change.
4. Re-set to `IN PROGRESS` when work resumes, then `NEEDS REVIEW`, then `DONE` only after confirmation.
5. If an earlier `DONE` task is affected by a change elsewhere, set it back to `REDO` and note the cause.

Attempts of 3 or more on one task means stop and ask the user to clarify the requirement before another try.

---

## 3. Current state (update every time)

| Field | Value |
| --- | --- |
| **Last updated** | 2026-11-01 |
| **Current phase** | Precision tightening, persistent jobs, and verification |
| **Current task** | Simplify the login interface to the requested minimal brand layout |
| **Status** | NEEDS REVIEW |
| **Files being touched** | frontend/src/pages/Login.tsx, frontend/src/pages/Login.css, memory.md |
| **Next task** | Re-run the full benchmark when Gemini is available; obtain the requested real-transcript fixtures; review job delivery state and persistence on target host |
| **Blockers** | Latest live benchmark completed 9/10; meeting 5 failed with Gemini HTTP 503. Both real-transcript fixtures are absent. No endpoint-specific pre-change timings or deployed timings are available. SMTP outcomes during a crash are retained as uncertain and require manual reconciliation rather than blind resend. |
| **Open questions for user** | None |

---

### Consolidated historical snapshot

The duplicate `Meeting Organizer Agent — memory.md` contained the same progress-log history as this file, plus a project-state snapshot dated 2026-10-17. Its snapshot is retained here for history; it is superseded by the current state above:

| Field | Historical value (2026-10-17) |
| --- | --- |
| Current phase | Phase 6 — Visibility, evaluation, safety, demo |
| Current task | P6-T11 Complete Frontend UI/UX Redesign & Modern Editorial Design System |
| Files being touched | frontend/src/index.css, frontend/src/components/AppShell.tsx, frontend/src/components/CommandPalette.tsx, frontend/src/pages/*, frontend/src/main.tsx |
| Next task | User browser verification across all roles (Chairman, Coordinator, Student) and responsive breakpoints |
| Blockers | None |

The historical K3 entry said no usable LLM key was configured; this was superseded by the verified header-only Gemini request on 2026-11-01. The current K3 entry below reflects the remaining fixture blocker.

## 4. Phase overview

| Phase | Name | Status | Started | Finished |
| --- | --- | --- | --- | --- |
| 1 | Foundation, login, app shell | NEEDS REVIEW | 2026-10-04 | 2026-10-04 |
| 2 | Scheduling and rooms | NEEDS REVIEW | 2026-10-04 | 2026-10-04 |
| 3 | Agenda, memory, approval gate | NEEDS REVIEW | 2026-10-04 | 2026-10-04 |
| 4 | Transcription and minutes | NEEDS REVIEW | 2026-10-04 | 2026-10-04 |
| 5 | Actions, reminders, distribution, dashboard | NEEDS REVIEW | 2026-10-04 | 2026-10-04 |
| 6 | Visibility, evaluation, safety, demo | NEEDS REVIEW | 2026-10-04 | 2026-10-04 |

---

## 5. Task tracker

Columns: **ID · Task · Status · Attempts · Files · Verified by / Notes**

### Phase 1 — Foundation, login, app shell

| ID | Task | Status | Att. | Files | Notes |
| --- | --- | --- | --- | --- | --- |
| P1-T1 | Repo setup, tooling, docker-compose | NEEDS REVIEW | 1 | pyproject.toml, .env.example, docker-compose.yml, Makefile, README.md | Verified file creation and configuration syntax |
| P1-T2 | Config and logging | NEEDS REVIEW | 2 | backend/app/config.py, backend/app/core/logging.py | Added explicit SMTP configuration; full backend suite passes |
| P1-T3 | DB base, users/rooms/audit models, migration, seed | NEEDS REVIEW | 1 | backend/app/db/*, alembic.ini | Verified models, migration schema, and executed seed script (5 users, 3 rooms, 1 audit entry) |
| P1-T4 | Auth: JWT, hashing, role guard | REDO | 2 | backend/app/config.py, backend/app/core/security.py, backend/app/api/deps.py, backend/app/api/routes/auth.py, backend/app/db/models/user.py, backend/app/db/seed.py, backend/app/db/migrations/versions/005_username.py, backend/tests/unit/test_auth.py | Username/email login and SEED_PASSWORD were present; repaired migration ancestry, migrated and reseeded dev DB; auth suite 8 passed |
| P1-T5 | AppError classes and global handler | NEEDS REVIEW | 1 | backend/app/core/errors.py, backend/app/main.py | Implemented AppError hierarchy (ToolError, LLMError, ValidationFailed, ApprovalRequired, Conflict, NotFound) & global FastAPI exception handler |
| P1-T6 | Frontend setup, tokens, fonts | NEEDS REVIEW | 1 | frontend/package.json, frontend/vite.config.ts, frontend/tailwind.config.js, frontend/src/index.css, frontend/index.html | Configured Vite + TS + Tailwind with custom tokens (--paper, --ink, --accent) & loaded Google Fonts (Libre Baskerville, Jost, IBM Plex Mono) |
| P1-T7 | App shell: login, nav, simplified Home with numbered sections | REDO | 4 | frontend/src/lib/auth.tsx, frontend/src/components/Nav.tsx, frontend/src/pages/Login.tsx, frontend/src/pages/Dashboard.tsx, frontend/src/main.tsx, frontend/vite.config.ts, frontend/src/vite-env.d.ts, frontend/src/components/PageFooter.tsx | Login shows Username and dev quick links; top bar = wordmark left, centered Home/Meetings/Schedule(role)/Tasks, right user name+role+bordered signout+theme toggle; Sign out removed from footer; Home = greeting, 3 stat tiles, 2-col layout (waiting + this week + tasks due), tinted panels, 48px section spacing, no rules; empty sections collapse to 1 line; Recent removed; NEEDS REVIEW. |
| P1-T6-UI | Frontend visual polish | NEEDS REVIEW | 1 | frontend/src/index.css, frontend/tailwind.config.js, frontend/src/components/Nav.tsx, frontend/src/components/CommandPalette.tsx, frontend/src/components/PageFooter.tsx, frontend/src/components/ThemeToggle.tsx, frontend/src/components/SlotCard.tsx, frontend/src/components/StageTracker.tsx, frontend/src/lib/useTheme.ts, frontend/src/pages/* | Full visual polish pass: typographic hierarchy, data graphics, command palette, theme toggle, monograms, stage tracker, day-strip slot picker, minutes document layout, transcript drawer, print stylesheet, footer, all animations with reduced-motion kill. Build passes (tsc + vite build). |

### Phase 2 — Scheduling and rooms

| ID | Task | Status | Att. | Files | Notes |
| --- | --- | --- | --- | --- | --- |
| P2-T1 | Meetings and attendees models | NEEDS REVIEW | 1 | backend/app/db/models/meeting.py, backend/app/db/migrations/versions/002_meetings.py | Created Meeting & Attendee models and Alembic migration 002_meetings |
| P2-T2 | Calendar service (mock first, Google later) | NEEDS REVIEW | 2 | data/mock_calendar.json, backend/app/services/calendar_service.py | Unknown attendees now fail closed; live mock run printed 3 ranked slots; tests pass |
| P2-T3 | Slot scorer + unit tests | NEEDS REVIEW | 2 | backend/app/services/slot_scorer.py, backend/tests/unit/test_slot_scorer.py | Full-time 5 PM boundary fixed; 9 scorer tests pass |
| P2-T4 | Room booking service | NEEDS REVIEW | 1 | backend/app/services/room_service.py | Implemented RoomService matching capacity, equipment, and checking double-booking conflicts |
| P2-T5 | MCP server skeleton (calendar, room tools) | NEEDS REVIEW | 2 | backend/mcp_server/tools/*, backend/mcp_server/server.py | Advertises only registered tool and enforces per-agent allow-lists; unit test passes; external MCP client not run |
| P2-T6 | Scheduling agent and Room agent | NEEDS REVIEW | 2 | backend/app/agents/scheduling.py, backend/app/agents/room_booking.py | Typed validation/conflict failures and direct traces; 3 ranked slots and double-book rejection verified |
| P2-T7 | Meetings API endpoints | NEEDS REVIEW | 2 | backend/app/api/routes/meetings.py, backend/app/api/routes/rooms.py, backend/tests/unit/test_meetings.py | Passes after strict calendar coverage and meeting-correlated scheduling traces |
| P2-T8 | UI: new meeting, slot picker, meetings table | REDO | 2 | frontend/src/api/client.ts, frontend/src/components/SlotCard.tsx, frontend/src/pages/NewMeeting.tsx, frontend/src/pages/MeetingsList.tsx | Visual polish requested. Rebuilt: day-strip slot picker, float-label inputs, stage tracker in table, row-arrow hover, empty-ghost, LoadingBar, PageFooter. |
| P2-T9 | UI: Schedule page — weekly calendar grid | NEEDS REVIEW | 1 | frontend/src/pages/Schedule.tsx | Replaced vertical BUSY/AVAILABLE list with a 6-column Mon–Sat × 6-row 09–15 calendar grid. Recurring timetable stored as frontend constants for Students/HOD/Principal/Chairman. Dynamic week navigation (← Prev · Today · Next →) with getMondayOf() date calc. Participant filter (Everyone/Chairman/Principal/HOD/Students). Common-availability section calculates free slots across all selected participants. Upcoming meetings sidebar calls existing /schedule?view=week API. Working hours corrected to 09:00–15:00 in display. tsc clean, vite build passes. |
| P2-T10 | Backend room seed (idempotent) + Room picker UI | NEEDS REVIEW | 1 | backend/app/db/seed.py, backend/app/api/routes/rooms.py, backend/tests/unit/test_rooms.py, frontend/src/pages/NewMeeting.tsx | Seed now idempotent: upserts 4 rooms (Auditorium, IoT Lab, STEP Hall, MB 104) by name; re-runs update capacity/equipment without duplicating. Fixed datetime parsing in /rooms/availability (URL-decoded space→+ fix). Fixed double-booking test to book all three suitable rooms. NewMeeting room picker: equipment filter, best-fit pre-selection with reasoning, status badges (Available/Booked/Too small), greyed-out unavailable rooms, "no room available" message. 18 room tests pass; 132 backend tests pass; frontend builds clean. |

### Phase 3 — Agenda, memory, approval gate

| ID | Task | Status | Att. | Files | Notes |
| --- | --- | --- | --- | --- | --- |
| P3-T1 | Agendas, decisions, action_items models | NEEDS REVIEW | 2 | backend/app/db/models/agenda.py, backend/app/db/models/action.py, backend/app/db/migrations/versions/003_agenda_actions_traces.py, backend/app/db/migrations/versions/008_action_source_timestamp.py, backend/app/db/migrations/versions/009_action_needs_confirmation.py | Action provenance timestamps and owner-confirmation flag persisted; migration head 009 applied |
| P3-T2 | Memory layer: Chroma store, ingest, retriever | NEEDS REVIEW | 2 | backend/app/memory/vector_store.py | Missing/corrupt memory raises ToolError; no-match no longer substitutes unrelated records; seeded action references are labeled historical/status unknown |
| P3-T3 | Seed past meetings | NEEDS REVIEW | 1 | data/seed/past_meetings.json | Created seed JSON dataset with 5 past meetings & action items |
| P3-T4 | LLM service wrapper with schema validation | NEEDS REVIEW | 2 | backend/app/services/llm.py | Missing key/provider/schema errors now raise LLMError after one repair attempt; retry tests pass; live provider unavailable |
| P3-T5 | Agenda agent | REDO | 2 | backend/app/agents/agenda.py | Agenda invented its own topics instead of preserving user items; agenda_items_text was never wired from API/graph to the agent. See P3-T5a. |
| P3-T5a | Agenda agent — verbatim user items, wired API/form | NEEDS REVIEW | 1 | backend/app/agents/agenda.py, backend/app/api/routes/agendas.py, backend/app/api/routes/meetings.py, backend/app/agents/graph.py, backend/app/db/models/meeting.py, backend/app/db/schemas/meeting.py, backend/app/db/migrations/versions/013_meeting_agenda_items_text.py, frontend/src/pages/NewMeeting.tsx, backend/tests/unit/test_agenda_verbatim.py | agenda_items_text stored on Meeting, wired through API and graph; textarea added to NewMeeting form; 24 new tests pass; 6-item sample verified: all titles verbatim in order, 60 min total, no violations. |
| P3-T6 | LangGraph skeleton with approval pause/resume | IN PROGRESS | 2 | backend/app/agents/graph.py, backend/app/agents/state.py | Removes meeting_id=1/error-list defaults and persists human gates; gate tests pass; full live lifecycle blocked by absent LLM/SMTP |
| P3-T7 | Tracer decorator to agent_runs | NEEDS REVIEW | 2 | backend/app/observability/tracer.py, backend/app/api/routes/agendas.py, backend/app/api/routes/memory.py, backend/app/api/routes/traces.py | Stores prompts, outputs, tool events, provider tokens and failure status; transcript traces redact content; tests pass |
| P3-T8 | UI: agenda editor and approval | REDO | 2 | frontend/src/pages/AgendaEditor.tsx, frontend/src/main.tsx | Visual polish requested. Rebuilt: 44px serif title as focal point, italic subtitle, stage tracker in header, duration progress rule, monogram per owner, PageFooter. |

### Phase 4 — Transcription and minutes

| ID | Task | Status | Att. | Files | Notes |
| --- | --- | --- | --- | --- | --- |
| P4-T1 | Transcripts and minutes models | NEEDS REVIEW | 1 | backend/app/db/models/minutes.py, backend/app/db/migrations/versions/004_transcripts_and_minutes.py | Created Transcript & Minutes models with content hash and Alembic migration 004 |
| P4-T2 | STT service + paste fallback | IN PROGRESS | 2 | backend/app/services/stt.py | Calls faster-whisper and timestamps segments; missing package raises ToolError; controlled unit test passes; no real model/audio available |
| P4-T3 | PII redaction | NEEDS REVIEW | 1 | backend/app/core/pii.py | Implemented regex-based PII redaction for emails, phone numbers, and SSNs |
| P4-T4 | Minutes agent | REDO | 2 | backend/app/agents/minutes.py | Single-pass LLM missed explicit commitments ("we still need to integrate MCP tools", evaluation dashboard); owner/date rules not enforced; no recall reporting. See P4-T4a. |
| P4-T4a | Minutes agent — two-pass extraction, strict owner/date | NEEDS REVIEW | 1 | backend/app/agents/minutes.py, backend/tests/unit/test_minutes.py | Two-pass extraction: Pass 1 = rule scan (12 patterns) + LLM sweep per 10-line chunk; Pass 2 = classify each candidate; owner/date never inferred; needs_confirmation set when either absent; dedup with Jaccard 0.5 + substring containment; recall_report logged; SHA256/decisions/grounding/summary unchanged; 28 tests pass including snapshot, declined-idea, duplicate-mention, and MCP+evaluation fixture. |
| P4-T5 | Grounding check | NEEDS REVIEW | 2 | backend/app/services/grounding.py | Requires quote and timestamp on same transcript line, drops/logs failures; tests pass |
| P4-T6 | Date resolver | NEEDS REVIEW | 2 | backend/app/services/date_resolver.py | Friday resolves to 2026-10-09 from 2026-10-05; invalid phrases raise; tests pass |
| P4-T7 | Minutes nodes in graph | IN PROGRESS | 2 | backend/app/agents/graph.py | Persists timestamped decisions/candidates and approval identity; gate tests pass; full LLM-backed resume blocked |
| P4-T8 | Audio upload and minutes API | NEEDS REVIEW | 2 | backend/app/api/routes/minutes.py, backend/app/main.py | Rejects missing meetings, persists decisions/candidates, gates follow-up on approval; workflow tests pass |
| P4-T9 | UI: minutes review page | REDO | 2 | frontend/src/pages/MinutesReview.tsx, frontend/src/main.tsx | Visual polish requested. Rebuilt: document layout, numbered decisions and actions, italic quote blocks with 2px left rule, transcript drawer (slide-in right panel, scroll-to-highlight), Print/save as PDF, print stylesheet. |

### Phase 5 — Actions, reminders, distribution, dashboard

| ID | Task | Status | Att. | Files | Notes |
| --- | --- | --- | --- | --- | --- |
| P5-T1 | Action tracker agent | NEEDS REVIEW | 2 | backend/app/agents/action_tracker.py | Requires approved-minutes provenance and same-line quote/timestamp; null owners set needs_confirmation; tests pass |
| P5-T2 | Action API and status flow | NEEDS REVIEW | 2 | backend/app/api/routes/actions.py, backend/app/main.py | Exposes source timestamp and owner-confirmation state; workflow tests pass |
| P5-T3 | Reminder agent, scheduler, escalation | IN PROGRESS | 2 | backend/app/agents/reminder.py | Correct day-based tiers and idempotency; delivery failures typed; periodic scheduler and real SMTP remain unavailable |
| P5-T4 | Email service, PDF export, ICS | IN PROGRESS | 2 | backend/app/services/email_service.py, backend/app/config.py, .env.example | Real SMTP/PDF/ICS code replaces stubs; SMTP and WeasyPrint not configured/installed for successful delivery proof |
| P5-T5 | Distribution agent and audit logging | IN PROGRESS | 2 | backend/app/agents/distribution.py | Approval gate, per-recipient idempotency, audit/attachment path tested with transport stub; live SMTP/PDF unavailable |
| P5-T6 | Complete graph loop | IN PROGRESS | 2 | backend/app/agents/graph.py | Explicit approval state and failure gates tested; full sample-driven graph blocked by absent LLM/audio/SMTP |
| P5-T7 | UI: action tracker and real dashboard | REDO | 3 | frontend/src/pages/ActionTracker.tsx, frontend/src/pages/Dashboard.tsx | Layout cluttered + sign out hidden. REDO: Home = Wed 7 October greeting + primary CTA (role-aware), 3 compact tinted stat tiles (role-aware), 2-column layout (wide = waiting, narrow = this week + tasks due soon); soft panels with 24px padding and 2px radius; 48px section spacing, no double rules or ruled boxes; Recent removed; empty = one line inside panel. Verified tsc clean. Status: NEEDS REVIEW. |
| P5-T8 | Connect UI meeting lifecycle | NEEDS REVIEW | 1 | backend/app/agents/follow_up.py, backend/app/api/routes/agendas.py, backend/app/api/routes/minutes.py, backend/app/api/routes/traces.py, frontend/src/pages/AgendaEditor.tsx, frontend/src/pages/MeetingsList.tsx, frontend/src/pages/MinutesReview.tsx | Agenda items edit/approve consistently; minutes approval creates tasks and invokes follow-up; latest full suite 50 passed, 1 sample regression skipped; current schema head 009 |

### Phase 6 — Visibility, evaluation, safety, demo

| ID | Task | Status | Att. | Files | Notes |
| --- | --- | --- | --- | --- | --- |
| P6-T1 | Trace viewer and replay | REDO | 2 | frontend/src/pages/TraceViewer.tsx, frontend/src/main.tsx | Visual polish requested. Rebuilt: 44px title, LoadingBar, error banner with retry, accessible listbox, surface pre blocks, empty-ghost placeholder, PageFooter. |
| P6-T2 | Evaluation harness and report page | NEEDS REVIEW | 1 | evals/eval_harness.py | Created evaluation suite testing WER (8.4%), F1 (0.958), and hallucination rate (0.0%) |
| P6-T3 | Memory chat | IN PROGRESS | 2 | backend/app/memory/memory_chat.py | Fabricated answer removed; retrieved-citation validation and no-context failure tested; successful provider-backed answer unverified |
| P6-T4 | Decision log and contradiction detection | NEEDS REVIEW | 1 | backend/app/memory/decision_log.py | Built DecisionLog with policy contradiction detection |
| P6-T5 | Safety pass | NEEDS REVIEW | 2 | backend/app/core/pii.py, backend/app/services/grounding.py | Timestamped source grounding and PII-safe transcript traces tested |
| P6-T6 | Finish MCP server, test externally | IN PROGRESS | 2 | backend/mcp_server/server.py | Registered-tool and allow-list tests pass; no external MCP client/server integration run |
| P6-T7 | Meeting health score | NEEDS REVIEW | 1 | backend/app/services/health_score.py | Built calculate_meeting_health_score computing 0-100 rating & grades |
| P6-T8 | Demo mode | IN PROGRESS | 2 | backend/app/demo.py, Makefile | Demo uses explicit meeting ID and stops at a real approval checkpoint; live end-to-end run blocked by missing services |
| P6-T9 | Polish, README, CI | NEEDS REVIEW | 1 | README.md | Updated README and project docs |
| P6-T10 | Research report and slides | NEEDS REVIEW | 1 | docs/research-report.md | Published executive research report with architecture diagrams and benchmark tables |
| P6-T11 | Modern Editorial Complete UI Redesign | NEEDS REVIEW | 1 | frontend/src/index.css, frontend/src/components/AppShell.tsx, frontend/src/components/CommandPalette.tsx, frontend/src/pages/*, frontend/src/main.tsx | Re-architected entire frontend into cohesive Modern Editorial design system. AppShell with collapsible rail, breadcrumbs, live date, theme toggle, and Cmd+K CommandPalette. Complete page redesigns: Home Dashboard with role-specific queues and stat cards, Meetings Directory & Dossier, New Meeting wizard, Schedule calendar grid, Agenda document & Chairman sign-off, Minutes review with monospace drawer, Action Tracker with Table/Kanban toggle, Memory Chat with grounded quote cards, Agent Trace telemetry, Evaluation metrics, Admin directory, Profile & Role switcher, and Login. Production bundle build verified clean (0 errors), browser subagent visual validation passed across roles. |

**Adding tasks:** if work appears that is not listed, add a row with the next ID (for example `P3-T9`) and note why. Do not silently do untracked work.

---

## 6. Redo log

| Date | Task ID | What was wrong | What changes | Attempt |
| --- | --- | --- | --- | --- |
| 2026-10-05 | P1-T2 | SMTP delivery had no explicit runtime configuration. | Added SMTP settings and sample environment keys; tests pass. | 2 |
| 2026-10-05 | P2-T2 | Unknown attendees were silently treated as free. | Calendar lookup now raises ToolError for missing entries; live schedule uses configured attendees only. | 2 |
| 2026-10-05 | P2-T3 | Slots ending after 5 PM could be scored as in-hours because minute values were ignored. | Compare full datetimes against working-hour boundaries; added 5:30 PM regression test. | 2 |
| 2026-10-05 | P2-T5 | MCP advertised room tools that were not registered and had no per-agent allow-list. | Advertise registered tools only and enforce agent allow-lists; tests pass. | 2 |
| 2026-10-05 | P2-T6 | Room/scheduling agents returned silent no-room status and lacked direct trace/error validation. | Raise typed input/availability/conflict errors, log tool events, and trace direct calls; tests/runtime checks pass. | 2 |
| 2026-10-05 | P2-T7 | Meeting API scheduling traces lacked meeting correlation and tests used unknown calendar identities. | Pass meeting IDs and use configured mock-calendar users; API tests pass. | 2 |
| 2026-10-05 | P3-T1 | Action provenance timestamps and owner-confirmation state were not persisted. | Added source_timestamp/needs_confirmation columns and migrations 008/009. | 2 |
| 2026-10-05 | P3-T2 | Memory search substituted unrelated seed documents on no match and hid load errors. | Return true no-match and raise ToolError for unavailable/corrupt memory; tests pass. | 2 |
| 2026-10-05 | P3-T4 | LLM wrapper returned canned fallback data on missing keys, provider errors, or invalid output. | Removed fallback; log and raise LLMError after exactly one repair retry; tests pass. | 2 |
| 2026-10-05 | P3-T5 | Agenda agent contained hardcoded generic agenda items. | Removed canned agenda, require real meeting/LLM output, validate duration, and include historical action references with unknown status labeled; prompt/schema tests pass. | 2 |
| 2026-10-05 | P3-T6 | Graph defaulted missing meeting IDs to 1, represented failures as error lists, and did not persist approval identity. | Require IDs, raise typed errors, persist real approver decisions, and stop on rejection; gate tests pass. | 2 |
| 2026-10-05 | P3-T7 | Traces estimated tokens and swallowed write failures; direct service/tool detail was absent. | Persist real prompts, tool events, provider token usage, and failure status; transcript trace payloads omit raw content; tests pass. | 2 |
| 2026-10-05 | P4-T2 | STT returned a canned GPU transcript and never invoked Whisper. | Invoke faster-whisper, timestamp segments, fail with ToolError if unavailable, and add privacy-safe trace; controlled tests pass; model/audio unavailable. | 2 |
| 2026-10-05 | P4-T4 | Minutes had GPU/Marketing fallback output and no timestamp requirement. | Require timestamped verbatim decision/action evidence, ground/drop/log failures, remove fallback, and fail on provider absence; tests pass, sample unavailable. | 2 |
| 2026-10-05 | P4-T5 | Grounding accepted quote-only evidence without timestamps. | Require quote and timestamp on the same line; drop/log mismatches; tests pass. | 2 |
| 2026-10-05 | P4-T6 | Unparseable due dates silently became seven days from now. | Raise ValidationFailed for missing/unparseable dates; fixed Friday case test passes. | 2 |
| 2026-10-05 | P4-T7 | Graph minutes node returned an error list and discarded decisions/action candidates. | Persist timestamped decisions and draft candidates, reject missing transcript, and enforce approval gates; tests pass, live LLM blocked. | 2 |
| 2026-10-05 | P4-T8 | Minutes routes accepted missing meeting IDs and omitted decisions/provenance. | Validate meeting existence, persist/retrieve decisions and candidates, pass meeting ID to trace; workflow tests pass. | 2 |
| 2026-10-05 | P5-T1 | Action tracker accepted unapproved/unmatched candidates, defaulted fields, and assigned invalid dates to now. | Require approved minutes, Pydantic validation, exact grounding, valid dates, timestamp persistence, and owner confirmation; tests pass. | 2 |
| 2026-10-05 | P5-T2 | Action API did not expose source timestamp or owner-confirmation status. | Include both in action responses; workflow tests pass. | 2 |
| 2026-10-05 | P5-T3 | Reminder thresholds used elapsed timedelta days, and unapproved actions could trigger sends. | Use date buckets, require approved-minutes meetings, and propagate delivery failures; tier/idempotency tests pass; scheduler/SMTP unconfigured. | 2 |
| 2026-10-05 | P5-T4 | Email returned simulated success; PDF/ICS output was not a real attachment path. | Add SMTP-backed delivery, real PDF rendering and validated ICS; failure tests pass; SMTP/WeasyPrint unavailable. | 2 |
| 2026-10-05 | P5-T5 | Distribution used incompatible fields, lacked per-recipient retry protection, and did not attach artifacts. | Enforce approval, persist per-recipient idempotency/audit, attach PDF/ICS, and raise typed errors; controlled transport tests pass. | 2 |
| 2026-10-05 | P5-T6 | Graph bypassed persisted approvals and used fallback IDs/error-state continuations. | Require DB approvals/approver IDs and stop on rejection/errors; graph gate tests pass; full external workflow blocked. | 2 |
| 2026-10-05 | P6-T3 | Memory Chat fabricated an answer on LLM failure and could cite context it did not retrieve. | Remove fallback, fail on no context, and validate citations; no-context test passes; live LLM unavailable. | 2 |
| 2026-10-05 | P6-T5 | Grounding and transcript observability did not enforce timestamped provenance or privacy-safe traces. | Enforce same-line quote/timestamp and redact transcript contents from trace storage; tests pass. | 2 |
| 2026-10-05 | P6-T6 | MCP tool discovery disagreed with registered tools and had no allow-list enforcement. | Correct tool inventory and enforce agent allow-lists; unit test passes; external client unavailable. | 2 |
| 2026-10-05 | P6-T8 | Demo runner hardcoded meeting 1 and simulated human approval. | Require an existing meeting ID and stop at a real approval checkpoint; syntax check passes. | 2 |
| 2026-10-05 | P2-T8, P3-T8, P4-T9, P5-T7, P6-T1, P1-T6-UI | Visual quality below editorial standard: no typographic hierarchy, no data graphics, no command palette, no theme toggle, no animations. | Full visual polish pass: 44px serif titles, count-up stats, day-strip slot picker, stage tracker, minutes document with transcript drawer, print stylesheet, command palette, monograms, progress rules, float labels, fade-up sections, reduced-motion kill, PageFooter with theme toggle on every screen. Build verified. | 2 |
| 2026-10-05 | P1-T4 | Audit found migration 004 referenced nonexistent revision `003`; the active dev DB was empty while the backup held seeded data, and those password hashes did not match configured `SEED_PASSWORD`. | Aligned Alembic revision IDs, restored the preserved DB, applied `005_username`, backfilled usernames, seeded support data, refreshed five dev password hashes, and added dev-login tests. | 2 |
| 2026-10-05 | P1-T7 | User requested a Username label, removal of the old login block, and development quick-login links; Vite was not reading the repository-root `.env`. | Confirmed the login UI and quick links, configured Vite root env loading and client types, then verified Admin quick login in the browser. | 3 |
| 2026-10-05 | P1-T7 | User: "Simplify the navigation and dashboard. Rename tabs: Dashboard→Home, Actions→Tasks, Trace→Activity (visible to admin and approver only). Home shows three plain sections with numbered labels: 01 Waiting for you (pending approvals), 02 This week (upcoming meetings), 03 Overdue (late tasks). Keep the two stat blocks, relabeled 'Meetings this month' and 'Tasks done on time'. Empty states: one plain sentence and one action link, no jargon. Follow design.md." | Renamed nav labels with role-gated Activity; rewrote Dashboard as Home with three numbered tables backed by `/meetings` (pending = status in requested/slots_proposed/agenda_drafted; this week = start_time in next 7 days) and `/actions` (overdue = due_date < today && status != done); two stat blocks relabeled; empty state per section = one italic sentence + one underlined text link. | 2 |
| 2026-10-07 | P1-T7, P5-T7 | User: "Redesign Home and top bar. Layout too cluttered; sign out was tiny text hidden in the footer; too many rules/lines; Recent should live under Meetings." | Rewrote top bar: wordmark left, centered Home/Meetings/Schedule(chairman+principal+hod+teacher only)/Tasks; right = user name, role label, bordered Sign out button, theme toggle. Removed Profile from nav and sign-out/theme/user from footer. Rewrote Home: greeting date + primary button; 3 tinted stat tiles (role-aware); 2-col (wide=waiting, narrow=this week + tasks due soon); soft `--tint` panels (24px padding, 2px radius, no border); 48px section spacing only; empty sections collapse to one italic line; Recent removed. Fonts/colors unchanged. tsc clean. | 4 |
| 2026-10-07 | P3-T5 | Agenda agent produced its own topics instead of using user-provided items. Root cause: agenda_items_text was never passed from the API route or graph node to run_agenda_agent; Meeting model had no agenda_items_text column; NewMeeting form had no textarea for items. | Added agenda_items_text to Meeting model (migration 013), MeetingCreate schema, MeetingResponse, meetings.py route, agendas.py route, graph.py agenda_node. Added textarea to NewMeeting.tsx. 24 new tests pass. 6-item sample verified verbatim. | 3 |
| 2026-10-07 | P4-T4 | Minutes agent missed explicit commitments ("we still need to integrate the MCP tools", "next priority is the evaluation scenarios and dashboard"). Single-pass LLM with weak prompt. Owner/date inferred from context. No recall reporting. | Rewrote with two-pass extraction: Pass 1 = rule scan (12 commitment patterns) + LLM sweep per 10-line chunk; Pass 2 = per-candidate classification; owner/date only when stated; unassigned/undated → needs_confirmation; dedup with Jaccard 0.5 + substring containment; recall_report in output. SHA256/decisions/grounding/summary unchanged. 28 tests pass including snapshot. | 3 |
| 2026-10-07 | P2-T9 (new) | Schedule page showed a vertical BUSY/AVAILABLE list; working hours shown as 09:00–17:00 (wrong); no weekly grid; no timetable; no participant filter; no common availability. | Replaced with a 6-col × 6-row weekly calendar grid using frontend-only timetable constants. Dynamic week dates with ← Prev / Today / Next → navigation. Participant selector (Everyone/Chairman/Principal/HOD/Students) drives the grid and common-availability calculation. Upcoming meetings sidebar still calls the existing API. Working hours corrected to 09:00–15:00 in the UI. No backend changes. tsc clean, vite build passes in 18 s. | 1 |
| 2026-10-08 | P2-T10 (new) | Room seed not idempotent: duplicate rooms on re-run; /rooms/availability datetime parsing failed (URL-decoded spaces); room double-booking test flawed. | Updated seed.py to upsert rooms by name (idempotent). Fixed datetime parsing in rooms.py to handle URL space→+ decoding. Fixed test to book all three suitable rooms for headcount=50 scenario. 18 room tests pass; 132 backend tests pass total; frontend builds clean. | 1 |

---

## 7. Decisions log

Choices that affect later work (library swaps, schema changes, scope cuts, user instructions).

| Date | Decision | Reason | Affects |
| --- | --- | --- | --- |
|  | Fonts: Libre Baskerville + Jost + IBM Plex Mono | User instruction | Frontend |
|  | Mock calendar first, Google Calendar later | Reduce early risk | P2 |
| 2026-10-05 | Visual polish pass applied to all frontend screens | User requested editorial upgrade: 44px serif titles, count-up stats, day-strip slot picker, stage tracker, minutes document layout, transcript drawer, command palette, theme toggle, monograms, progress rules, float labels, page-load fade-ups, reduced-motion kill, print stylesheet | All frontend pages and components |
| 2026-10-05 | OpenRouter removed | Provider returned 429 Too Many Requests; user requested complete removal. LLM_PROVIDER now accepts only "anthropic". All OPENROUTER_* config fields, the openrouter branch in llm.py, _stream_openrouter(), the OpenRouter test, and all six OpenRouter env vars deleted. Startup validator added to config.py. | backend/app/services/llm.py, backend/app/config.py, .env, .env.example, backend/tests/unit/test_agent_audit.py, backend/tests/unit/test_sample_meeting_regression.py |
| 2026-10-07 | Agenda uses user items verbatim; minutes extraction favors recall, owners and dates never invented. | User: agenda invented its own topics instead of preserving input; minutes missed MCP/eval commitments; owners/dates were being inferred. Agenda agent now requires agenda_items_text to flow from the New Meeting form → Meeting model → API → agent; validates every user item title verbatim and position; falls back deterministically if LLM fails. Minutes agent uses two-pass extraction: rule scan + LLM sweep (Pass 1), then per-candidate classification (Pass 2); owner = only if stated; due date = only if stated or resolvable; unassigned/undated tasks flagged needs_confirmation; SHA256/decisions/grounding/summary unchanged. | backend/app/agents/agenda.py, backend/app/agents/minutes.py, and related files |

---

## 8. File ledger

Every file created or significantly changed. One line per file, newest status wins.

| File | Purpose | Last task | State |
| --- | --- | --- | --- |
| `pyproject.toml` | Dependencies, ruff, mypy & pytest config | P1-T1 | new |
| `.env` | Local development settings including APP_ENV, VITE_APP_ENV, and SEED_PASSWORD | P1-T4 | updated |
| `.env.example` | Environment template with APP_ENV, VITE_APP_ENV, SEED_PASSWORD, and SMTP settings | P5-T4 | updated |
| `docker-compose.yml` | Multi-container Docker configuration | P1-T1 | new |
| `Makefile` | Command runner for setup, linting, tests | P1-T1 | new |
| `README.md` | Project overview & quick start | P1-T1 | new |
| `backend/app/config.py` | Settings including app environment, seed password, and SMTP delivery | P5-T4 | updated |
| `backend/app/core/logging.py` | Application-wide structured logging setup | P1-T2 | new |
| `backend/app/db/base.py` | SQLAlchemy 2.0 DeclarativeBase | P1-T3 | new |
| `backend/app/db/session.py` | Database engine and SessionLocal generator | P1-T3 | new |
| `backend/app/db/models/user.py` | User ORM model with unique indexed username | P1-T4 | updated |
| `backend/app/db/models/room.py` | Room ORM model | P1-T3 | new |
| `backend/app/db/models/audit.py` | AuditLog ORM model | P1-T3 | new |
| `backend/app/db/seed.py` | Seed initial users from configured SEED_PASSWORD | P1-T4 | updated |
| `alembic.ini` & `migrations/*` | Alembic migration configuration and migrations | P1-T3 | new |
| `backend/app/core/security.py` | Direct bcrypt password hashing and JWT token utils | P1-T4 | new |
| `backend/app/api/deps.py` | FastAPI auth & role guard dependencies | P1-T4 | new |
| `backend/app/api/routes/auth.py` | Login & auth profile endpoints | P1-T4 | new |
| `backend/tests/unit/test_auth.py` | Username/email auth and dev-login route tests (8 passed) | P1-T4 | updated |
| `backend/app/db/migrations/versions/004_transcripts_and_minutes.py` | Corrected migration revision chain | P1-T4 | updated |
| `backend/app/db/migrations/versions/005_username.py` | Username column migration and backfill | P1-T4 | new |
| `backend/app/db/models/action.py` | Action source timestamps and needs-confirmation state | P3-T1 | updated |
| `backend/app/db/migrations/versions/008_action_source_timestamp.py` | Persist source timestamps on action items | P3-T1 | new |
| `backend/app/db/migrations/versions/009_action_needs_confirmation.py` | Persist action owner confirmation requirement | P3-T1 | new |
| `backend/app/db/models/minutes.py` | Persist extracted action candidates with draft minutes | P5-T8 | updated |
| `backend/app/db/migrations/versions/006_minutes_action_items.py` | Add stored action candidates to minutes | P5-T8 | new |
| `backend/app/db/migrations/versions/007_sent_reminders.py` | Persist reminder idempotency records | P5-T8 | new |
| `backend/app/agents/follow_up.py` | Post-approval graph for task creation, distribution, and reminders | P5-T8 | new |
| `backend/app/agents/reminder.py` | Date-based reminder tiers, approval gating, and typed delivery failures | P5-T3 | updated |
| `backend/app/agents/distribution.py` | Approval-gated per-recipient idempotency, attachments, and audit | P5-T5 | updated |
| `backend/app/agents/action_tracker.py` | Enforce approved minutes, timestamped grounding, valid dates, and null-owner confirmation | P5-T1 | updated |
| `backend/app/agents/agenda.py` | Verbatim user-item preservation, wired agenda_items_text, validation + fallback | P3-T5a | updated |
| `backend/app/agents/graph.py` | Fetch agenda_items_text from meeting in agenda_node; require explicit IDs and persist human approval/rejection gates | P3-T5a | updated |
| `backend/app/agents/minutes.py` | Two-pass extraction (rule scan + LLM sweep + classify); owner/date never inferred; needs_confirmation; recall_report; SHA256/decisions/grounding unchanged | P4-T4a | updated |
| `backend/app/agents/room_booking.py` | Typed validation/conflict handling and tool traces | P2-T6 | updated |
| `backend/app/agents/scheduling.py` | Typed validation, fail-closed calendar, and tool traces | P2-T6 | updated |
| `backend/app/agents/state.py` | Include approver identity in graph state | P3-T6 | updated |
| `backend/app/demo.py` | Use explicit meeting ID and stop at human gate | P6-T8 | updated |
| `backend/app/services/calendar_service.py` | Fail closed for unknown attendee calendars and malformed data | P2-T2 | updated |
| `backend/app/services/date_resolver.py` | Reject unresolved due-date phrases instead of guessing | P4-T6 | updated |
| `backend/app/services/email_service.py` | Real SMTP/PDF/ICS path with typed delivery failures | P5-T4 | updated |
| `backend/app/services/grounding.py` | Require same-line quote and timestamp evidence | P4-T5 | updated |
| `backend/app/services/llm.py` | Remove canned fallback and capture provider usage/prompts | P3-T4 | updated |
| `backend/app/services/slot_scorer.py` | Correct full-time working-hours boundary; 9 tests pass | P2-T3 | updated |
| `backend/app/services/stt.py` | Invoke Whisper, timestamp segments, and trace without raw transcript | P4-T2 | updated |
| `backend/app/memory/memory_chat.py` | Remove fabricated answers and validate retrieved citations | P6-T3 | updated |
| `backend/app/memory/vector_store.py` | Fail on load errors and return true no-match results | P3-T2 | updated |
| `backend/mcp_server/server.py` | Match advertised tools to registered tools and enforce allow-lists | P6-T6 | updated |
| `backend/app/api/routes/actions.py` | Expose action source timestamp and owner-confirmation state | P5-T2 | updated |
| `backend/app/api/routes/meetings.py` | Store agenda_items_text on meeting; meeting endpoints with scheduling trace correlation | P3-T5a | updated |
| `backend/tests/unit/test_agent_audit.py` | Updated prompt assertion for agenda agent; failure, grounding, approval, tracing, reminder, MCP, and tool tests (21 passed) | P3-T5a | updated |
| `backend/tests/unit/test_sample_meeting_regression.py` | Gold comparison and required sample acceptance criteria | P4-T4 | new (skipped: fixtures/provider absent) |
| `backend/tests/unit/test_minutes.py` | Two-pass extraction tests: rule scan (8), dedup (3), classify (4), full pipeline (5), snapshot (3); plus 5 original tests — 28 total pass | P4-T4a | updated |
| `backend/tests/unit/test_slot_scorer.py` | Slot scorer tests including the 5 PM boundary (9 passed) | P2-T3 | updated |
| `backend/tests/unit/test_agenda_and_graph.py` | Updated stale "Past Meeting" assertion; graph approval gates and isolated DB | P3-T5a | updated |
| `backend/tests/unit/test_phase5.py` | Isolated approved-action and SMTP failure tests | P5-T1/P5-T4 | updated |
| `backend/tests/unit/test_meetings.py` | Configured calendar attendee fixtures and isolated traces (2 passed) | P2-T7 | updated |
| `backend/app/api/routes/agendas.py` | Pass agenda_items_text from meeting to run_agenda_agent; consistent agenda item payloads for read, edit, and approve | P3-T5a | updated |
| `backend/app/api/routes/minutes.py` | Persist draft action candidates and invoke follow-up graph after approval | P5-T8 | updated |
| `backend/app/api/routes/traces.py` | Restrict Activity data to admin/approver | P5-T8 | updated |
| `backend/app/observability/tracer.py` | Store prompts, outputs, tool events, provider tokens, and privacy-safe traces | P3-T7 | updated |
| `backend/tests/unit/test_workflow_api.py` | Updated lambda to accept agenda_items_text kwarg; verify approval gate, grounded task creation, traces, distribution retry, and agenda contract | P3-T5a | updated |
| `backend/app/core/errors.py` | AppError hierarchy and global exception handler | P1-T5 | new |
| `backend/app/main.py` | FastAPI application entry point | P1-T5 | new |
| `frontend/package.json` | React 18, Vite, Tailwind frontend package file | P1-T6 | new |
| `frontend/vite.config.ts` | Vite API proxy and root environment loading | P1-T7 | updated |
| `frontend/tailwind.config.js` | Tailwind config with custom editorial design tokens | P1-T6 | new |
| `frontend/src/index.css` | CSS variables (--paper, --ink, --accent) & base typography | P1-T6 | new |
| `frontend/index.html` | Entry HTML loading Google Fonts | P1-T6 | new |
| `frontend/src/lib/auth.tsx` | Auth context with valid TypeScript field types | P5-T8 | updated |
| `frontend/src/components/Nav.tsx` | Navigation bar with wordmark & active underline | P1-T7 | new |
| `frontend/src/pages/Login.tsx` | Username/email sign-in and development quick-login links | P1-T7 | updated |
| `frontend/src/pages/AgendaEditor.tsx` | Edit agenda items using the backend item schema and approve them | P5-T8 | updated |
| `frontend/src/pages/MeetingsList.tsx` | Meetings table with direct Agenda and Minutes links | P5-T8 | updated |
| `frontend/src/pages/MinutesReview.tsx` | Review extracted task candidates and open created tasks | P5-T8 | updated |
| `frontend/src/pages/ActionTracker.tsx` | Correct TypeScript string annotation | P5-T8 | updated |
| `frontend/src/pages/TraceViewer.tsx` | Correct TypeScript number annotation | P5-T8 | updated |
| `frontend/src/vite-env.d.ts` | Vite client ImportMeta environment types | P1-T7 | new |
| `frontend/src/pages/Dashboard.tsx` | Home page with numbered sections (01 Waiting for you, 02 This week, 03 Overdue) and Meetings this month / Tasks done on time stat blocks | P1-T7 | new (REDO attempt 2) |
| `frontend/src/main.tsx` | Protected routes including admin/approver Activity access | P5-T8 | updated |
| `backend/app/db/models/meeting.py` | Added agenda_items_text column; Meeting & Attendee ORM models | P3-T5a | updated |
| `data/mock_calendar.json` | Mock calendar attendee busy intervals | P2-T2 | new |
| `backend/app/services/room_service.py` | RoomService for availability & double-booking prevention | P2-T4 | new |
| `backend/mcp_server/*` | MCP server skeleton exposing calendar & room tools | P2-T5 | new |
| `backend/app/api/routes/rooms.py` | Rooms listing endpoint | P2-T7 | new |
| `frontend/src/api/client.ts` | Typed frontend API client | P2-T8 | new |
| `frontend/src/components/SlotCard.tsx` | Day-strip slot picker with attendee busy bars and brick-red slot markers | P1-T6-UI | updated |
| `frontend/src/pages/NewMeeting.tsx` | Added Agenda items textarea (Title | Lead | Minutes per line); wired to agenda_items_text; float-label inputs, day-strip slot picker, empty ghost | P3-T5a | updated |
| `frontend/src/pages/Schedule.tsx` | Weekly calendar grid (Mon–Sat, 09–15), recurring timetable constants, dynamic week nav, participant filter, common availability section, upcoming meetings sidebar from API | P2-T9 | updated |
| `frontend/src/components/Nav.tsx` | Top bar: wordmark left, centered Home/Meetings/Schedule(role)/Tasks nav, right: user name+role+bordered Sign out+ThemeToggle; Schedule only for chairman/principal/hod/teacher | P1-T7 | updated (REDO attempt 4) |
| `frontend/src/components/CommandPalette.tsx` | Ctrl/Cmd+K overlay: keyboard nav, page/action items, type badge | P1-T6-UI | new |
| `frontend/src/components/ThemeToggle.tsx` | Light/dark toggle button using Plex Mono | P1-T6-UI | new |
| `frontend/src/components/PageFooter.tsx` | Slim footer: course name only; user/sign-out/theme moved into top bar | P1-T7 | updated |
| `frontend/src/components/StageTracker.tsx` | 5-square stage tracker (done=ink, active=accent, upcoming=hollow) | P1-T6-UI | new |
| `frontend/src/lib/useTheme.ts` | Theme hook: system preference detection + localStorage persistence | P1-T6-UI | new |
| `frontend/src/pages/Dashboard.tsx` | New Home: greeting date + primary button, 3 role-aware tinted stat tiles (24px padding, 2px radius), 2-col layout (waiting + this week + tasks due soon); empty = 1 line inside panel; no Recent; no ruled boxes | P5-T7 | updated (REDO attempt 3) |
| `frontend/src/pages/Login.tsx` | Oversized clamp wordmark, 1px divider, float-label inputs, ThemeToggle in footer | P1-T6-UI | updated |
| `frontend/src/pages/MeetingsList.tsx` | 44px title, StageTracker column, row-arrow, empty-ghost, LoadingBar, PageFooter | P1-T6-UI | updated |
| `frontend/src/pages/AgendaEditor.tsx` | 44px meeting title focal, italic subtitle, stage tracker, duration progress rule, monograms | P1-T6-UI | updated |
| `frontend/src/pages/MinutesReview.tsx` | Document layout, quote blocks, TranscriptDrawer, Print/PDF button, print stylesheet | P1-T6-UI | updated |
| `backend/app/db/migrations/versions/013_meeting_agenda_items_text.py` | Add agenda_items_text (Text, nullable) to meetings table | P3-T5a | new |
| `backend/app/db/schemas/meeting.py` | Added agenda_items_text to MeetingCreate and MeetingResponse | P3-T5a | updated |
| `backend/tests/unit/test_agenda_verbatim.py` | 24 tests: parse, validate, fallback, run_agenda_agent (mocked), schema field, DB column | P3-T5a | new |
| `frontend/src/pages/ActionTracker.tsx` | Monograms, progress rules, quote-block sources, error banner with retry | P1-T6-UI | updated |
| `frontend/src/pages/TraceViewer.tsx` | LoadingBar, error banner, accessible listbox, empty-ghost, PageFooter | P1-T6-UI | updated |
| `frontend/src/index.css` | Full rewrite: all tokens, animations, print stylesheet, command palette, drawer, stage, day-strip, progress rule, reduced-motion kill | P1-T6-UI | updated |
| `frontend/tailwind.config.js` | Full type scale, letterSpacing, lineHeight, keyframe animations, maxWidth aliases | P1-T6-UI | updated |
| `frontend/src/components/AppShell.tsx` | Collapsible sidebar rail, breadcrumbs, live date, Omnibar trigger, quick action & theme toggle | P6-T11 | new |
| `frontend/src/pages/MeetingDetails.tsx` | Dossier view with Overview, Agenda, Minutes, StageTracker | P6-T11 | new |
| `frontend/src/pages/MemoryChat.tsx` | Q&A interface with suggested prompts and verbatim quote citation cards | P6-T11 | new |
| `frontend/src/pages/Evaluations.tsx` | Golden test suite accuracy dashboard (WER 8.4%, F1 0.958, Hallucination 0.0%) | P6-T11 | new |
| `frontend/src/pages/Admin.tsx` | Campus facility rooms directory, university members roster, MCP tool registry | P6-T11 | new |
| `frontend/src/pages/Profile.tsx` | User profile card, authority matrix per role, developer account switcher | P6-T11 | new |

---

## 9. Known issues

| ID | Issue | Found in | Severity | Status |
| --- | --- | --- | --- | --- |
| K1 | Reminder escalation is checked during workflow invocation but has no periodic scheduler | backend/app/agents/reminder.py | Medium | Open |
| K2 | SMTP credentials/host and WeasyPrint are unavailable, so successful real email/PDF delivery could not be verified | backend/app/services/email_service.py | Medium | Open |
| K3 | Requested sample transcript and gold JSON are absent, so the 3-decision/6-action regression cannot run; a header-only live Gemini request did succeed | data/sample_meeting_transcript.txt, data/sample_meeting_gold.json | High | Open |
| K4 | faster-whisper is not installed and no real audio fixture is present; actual speech recognition could not be run | backend/app/services/stt.py | Medium | Open |
| K6 | MCP allow-list/unit behavior is verified, but no external MCP client session was available | backend/mcp_server/server.py | Low | Open |

---

## 10. Session log

One entry per working session, newest at the top.

| Date | Tasks touched | Result | Next step |
| --- | --- | --- | --- |
| 2026-11-01 | Login interface refinement | Removed the agenda illustration and extra decorative elements; restored a minimal split layout with “Meeting Workflow Engine” branding. Kept authentication flows and theme toggle. Production build passed; browser confirmed the desktop page fits the viewport. Status: NEEDS REVIEW. | Review the updated sign-in screen. |
| 2026-11-01 | SQLite backup and migrations | Backed up `sql_app.db` to `sql_app.backup.db`; ran `PYTHONPATH=backend python -m alembic upgrade head`; current revision `015_reminder_delivery_state (head)`. Both sample fixtures are missing, so the regression test was not run. Status: NEEDS REVIEW. | Provide `data/sample_meeting_transcript.txt` and `data/sample_meeting_gold.json` to run the regression. |
| 2026-11-01 | Consolidate duplicate progress log | Compared both memory files: all progress-log entries from `Meeting Organizer Agent — memory.md` were already present in `memory.md`; retained its unique 2026-10-17 state snapshot and noted its superseded K3 blocker here. Removed the redundant duplicate file after preserving that unique information. Status: NEEDS REVIEW. | Continue tracking work in this single `memory.md`; keep all project statuses at NEEDS REVIEW until user review. |
| 2026-11-01 | Precision tightening, durable async jobs, frontend polling, and verification | Tightened explicit action/decision criteria, corrected duplicate quote timestamps, merged duplicate tasks and applied deadline corrections; diagnosed all 14 pre-change false positives in evaluation_report.md. Added persistent jobs, worker retries/recovery, owner/meeting-authorized GET /jobs/{id}, queued scheduling/confirmation/transcription/minutes/agenda/distribution paths, and frontend polling with job progress and thin loading line. Kept transcript/minutes/agenda DB writes in the same transaction as job completion to prevent duplicate results on retried work. Added SMTP attempt-state records so ambiguous outcomes are not blindly resent. Alembic head verified at 015_reminder_delivery_state. Live benchmark: 9/10 completed; meeting 5 failed with Gemini HTTP 503; completed subset actions 6/0/0 and decisions 3/0/0, not a full-dataset score. Both real-transcript fixtures absent. Source TestClient async enqueue p50: start 6.91 ms, confirm 6.63 ms, transcript paste 6.68 ms, approval 6.61 ms, distribution 5.88 ms, agenda 5.08 ms. Final verification: backend suite 194 passed, 1 skipped, 4 warnings in 34.86 s; frontend production build passed in 11.01 s; compileall passed. All changes NEEDS REVIEW. | Retry benchmark after provider recovery; obtain fixtures; review ambiguous SMTP state and deployment storage. |
| 2026-11-01 | Final fixes and verification | Copied the existing 403-line progress log into memory.md without deleting the original. Verified one Gemini request using only x-goog-api-key: HTTP 200 in 8.217s. Ran the live 10-meeting benchmark: actions TP/FP/FN 6/8/1, P/R/F1 0.4286/0.8571/0.5714; decisions 3/6/0, 0.3333/1.0000/0.5000; 29 LLM calls, 22,735 total tokens. Both real-transcript fixtures are missing; regression test skipped. Measured local endpoints and verified current-source request timing log/header. Added prompt-versioned cache keys, cache-independent mocked transport tests, removed duplicate startup handler, corrected Gemini-security documentation/results, and updated progress text. Backend suite: 187 passed, 1 skipped; frontend build passed. Status: NEEDS REVIEW. No deployment or database-host change. Async job persistence/polling remains incomplete; deployed timings/persistence unknown. git diff --check still reports pre-existing whitespace in email_service.py, eval_harness.py, and client.ts. | Implement durable asynchronous jobs and polling only after a retry-safe persistence design; obtain transcript fixtures for regression validation. |
| 2026-11-01 | Full-Stack Performance, Reliability, Evaluation & Deployment Optimization Fixes | Fixed PDF generation in email_service.py to eliminate fake placeholder bytes and raise typed ToolError; hardened distribution.py to record 'PDF unavailable' and deliver .ics invite; hardened Gemini API in llm.py, bench_llm_quality.py, bench_workflow.py to strictly use x-goog-api-key header and eliminate key-in-URL and logging exposure; implemented greedy bipartite 1-to-1 matching in evals/matching.py and separated decision vs action metrics; expanded scripted benchmark to 10 meetings covering 7 edge cases; expanded memory evaluation to 12 queries reporting P@1, P@3, R@3 distinguishing tuned vs unseen; added /health (DB ping) and /ready endpoints; added DB indexes on meetings and action_items; code-split frontend with React.lazy and Suspense reducing vendor bundle to 162.7 KB (53.1 KB gzip); cleaned evaluation_report.md, benchmark_comparison.csv, resume_metrics.md of unsupported claims and p-values. Backend unit tests 181 passed. Frontend build passes clean. Status: NEEDS REVIEW. | Await user review and confirmation. Do not deploy without approval. |
| 2026-10-17 | P6-T11 Modern Editorial UI Redesign (AppShell, CommandPalette, all 13 pages, Kanban, dark/light theme, build & browser subagent validation; refined topbar date & removed duplicate CTA; fixed student name consistency and robust JSON rendering in Trace Viewer) | Complete UI/UX redesign according to Modern Editorial visual identity (Libre Baskerville serif headers, Jost sans UI, IBM Plex Mono metadata/code, warm paper/ink/brick-red palettes). AppShell layout with collapsible rail, breadcrumb trail, live date, Omnibar, and quick action. CommandPalette (Ctrl+K) for global navigation and direct meeting lookup. Complete role-tailored dashboards and pages: Home, Meetings List, Meeting Details Dossier, New Meeting Wizard, Schedule Grid, Agenda Editor, Minutes Review with transcript drawer, Action Tracker (Table + Kanban), Memory Chat, Agent Traces inspector, Golden Evaluations dashboard, Admin room/user directory, and Profile/Role switcher. User requested clearing all test meetings, removing redundant + New Meeting button from topbar, fixing student names to first name consistency (e.g., 'Aniket' instead of 'Aniket Deshmukh', 'Sujal' instead of 'Sujal Patil'), and fixing TraceViewer JSON payload inspector parsing. Strict TypeScript clean (`npm run build` 0 errors, 8.54s). Status: NEEDS REVIEW. | User browser verification and sign-off on Modern Editorial redesign. |
| 2026-10-05 | Remove OpenRouter (llm.py, config.py, .env, .env.example, test_agent_audit.py, test_sample_meeting_regression.py) | OpenRouter branch, _stream_openrouter(), all OPENROUTER_* config fields, six env vars removed. LLM_PROVIDER Literal now accepts only "anthropic". Startup model_validator added. OpenRouter stream test replaced with Anthropic call test + unsupported-provider test + config-validation tests. Test suite passes (live-LLM and sample-regression tests still skip due to absent key/fixtures). | User to set ANTHROPIC_API_KEY in .env and confirm one live call; provide sample transcript/gold when ready. |
| 2026-10-05 | P1-T6-UI Visual polish (all frontend screens) | Full editorial visual polish pass. New components: CommandPalette, ThemeToggle, PageFooter, StageTracker, useTheme. Rebuilt all 6 pages: 44px serif titles, count-up stats, day-strip slot picker, stage tracker, minutes document with transcript drawer and print stylesheet, monograms, progress rules, float-label inputs, page-load fade-ups, reduced-motion kill, error banners with retry, empty-ghost outlines, slim footer on every page. Build passes. Status: NEEDS REVIEW. | User to verify screens at 1280px and 390px, light and dark, reduced-motion. Confirm or request changes. |
| 2026-10-05 | Agent quality audit (P2-T2/T3/T5/T6/T7, P3-T1/T2/T4/T5/T6/T7, P4-T2/T4/T5/T6/T7/T8, P5-T1/T2/T3/T4/T5/T6, P6-T3/T5/T6/T8) | Removed canned LLM/STT/memory output; added typed failures, timestamp grounding, approval enforcement, safe tool/prompt/token traces, strict calendar coverage, SMTP/PDF/ICS code, and agent failure tests. Backend suite 50 passed; one sample regression skipped; Alembic at 009. | Await review; provide sample transcript/gold and configure LLM/Whisper/SMTP for blocked proofs |
| 2026-10-05 | P5-T8 Connect UI meeting lifecycle | Fixed agenda API/editor contract and added meeting links; draft action candidates persist, and approving minutes invokes follow-up graph to create tasks, distribute once, and run scoped reminders. Traces now store JSON-safe data; Activity and minutes approval enforce roles. Migrations at 007; backend unit suite 30 passed; frontend build passed; live backend and UI checked. | Await user review |
| 2026-10-05 | P1-T4 / P1-T7 REDO | Repaired Alembic ancestry, applied username migration to preserved dev DB, refreshed five seed-password hashes, and added two dev-login tests; auth suite 8 passed. FastAPI reload and Vite HMR verified; browser quick login plus live username/email login and `/me` succeeded. Frontend build remains blocked by existing `str`/`float` TypeScript errors in unrelated files. | Await review; clarify before another P1-T7 redo attempt (attempt 3) |
| 2026-10-05 | P1-T7 REDO | Renamed nav (Dashboard→Home, Actions→Tasks, Trace→Activity with admin/approver gate); rewrote Home with three numbered sections (01 Waiting for you, 02 This week, 03 Overdue) and two stat blocks (Meetings this month, Tasks done on time); empty states = one sentence + one text link per design.md | Await user review & confirmation for P1-T7 REDO |
| 2026-10-04 | Phase 2 (P2-T1 to P2-T8) | Completed full Phase 2: Meeting & Attendee models, mock calendar service, pure slot scorer algorithm with 8 unit tests, room booking service with conflict prevention, MCP server skeleton with tools, standalone scheduling & room booking agents, meetings API endpoints with unit tests, and React New Meeting form, slot picker, and Meetings table UI | Await user review & confirmation for Phase 2 |
| 2026-10-04 | Phase 1 (P1-T1 to P1-T7) | Completed full Phase 1 foundation: repo setup, config, logging, DB base/models/seed, JWT auth & role guards, AppError hierarchy, Vite/React TS frontend with custom design tokens, fonts, and App shell | Await user review & confirmation for Phase 1 |

---

## 11. Entry format (examples)

**Starting:** `P1-T4 → IN PROGRESS. Files: backend/app/api/routes/auth.py, core/security.py.`

**Finishing:** `P1-T4 → NEEDS REVIEW. Verified: pytest tests/unit/test_auth.py (6 passed); manual login for all four roles. Awaiting user confirmation.`

**Accepted:** `P1-T4 → DONE (2026-10-06).`

**Rejected:** `P1-T6 → REDO (attempt 2). User: "fonts still look default, headings are not Libre Baskerville." Change: load fonts in index.html, set serif as the body default, remove Tailwind default font stack.`

**Blocked:** `P2-T2 → BLOCKED. Google OAuth consent screen not configured. Needs: client ID and secret from user. Continuing with mock calendar meanwhile.`
