# phases.md — Build Plan

Six phases. Each ends with something that runs and can be demonstrated. Do not start a phase until the previous one passes its checklist.

Read `rule.md` and `architecture.md` before every phase.

---

## How to work each phase

1. Open a fresh AI session per phase. Paste: `rule.md`, the relevant part of `architecture.md`, and only that phase's section below.
2. Give the AI **one task at a time** (the numbered tasks), never the whole phase at once.
3. After each task: run it, test it, commit it.
4. Do not let the AI touch files outside the phase's file list.
5. Finish the phase checklist, tag the commit (`phase-1-done`), then move on.

---

## Overview

| Phase | Name | Outcome | Time |
| --- | --- | --- | --- |
| 1 | Foundation, login, app shell | Sign in, roles, empty styled app | Week 1 |
| 2 | Scheduling and rooms | Request a meeting, get ranked slots, book a room | Week 2 |
| 3 | Agenda, memory, approval gate | Agenda drafted from past meetings, approve it | Week 3 |
| 4 | Transcription and minutes | Audio to approved minutes with citations | Week 4 |
| 5 | Actions, reminders, distribution, dashboard | Full lifecycle closes the loop | Week 5 |
| 6 | Visibility, evaluation, safety, demo | Trace viewer, eval scores, demo mode, polish | Week 6 |

---

## Phase 1 — Foundation, login, app shell

**Goal:** a running skeleton with auth and the final look, so every later screen inherits it.

**Tasks**

1. Repo setup: folders per `architecture.md`, `pyproject.toml`, `.env.example`, `docker-compose.yml`, ruff, mypy.
2. Config and logging (`config.py`, `core/logging.py`).
3. Database: SQLAlchemy base, models for `users`, `rooms`, `audit_log`; Alembic first migration; seed script.
4. Auth: JWT login, password hashing, role guard (`chairman`, `principal`, `hod`, `teacher`, `student`).
5. Error handling base: `AppError` classes and global handler.
6. Frontend setup: Vite + TS, Tailwind with custom tokens, load Libre Baskerville, Josefin Sans, IBM Plex Mono.
7. App shell: login page, sidebar/top nav, empty Dashboard, route guards.

**Files:** `backend/app/{main,config}.py`, `core/*`, `db/*`, `api/routes/auth.py`, `frontend/src/{main,pages/Login,pages/Dashboard,lib/theme}`.

**Done when**

- [ ] `make up` starts everything
- [ ] Log in as each role; wrong role gets blocked
- [ ] Tokens, fonts, and spacing match `rule.md`; no default Tailwind colors
- [ ] Tests for auth pass

---

## Phase 2 — Scheduling and rooms

**Goal:** the first real agent. Request a meeting and receive ranked slots with reasons.

**Tasks**

1. Models: `meetings`, `attendees`; migration.
2. Calendar service with a **mock calendar (JSON)** first; Google OAuth added after it works.
3. `slot_scorer.py`: availability, preferred hours, back-to-back penalty, priority attendees. Pure function, fully unit tested.
4. Room booking service: capacity and equipment match, conflict check.
5. MCP server skeleton with `calendar_tools` and `room_tools`.
6. Scheduling agent and Room agent as standalone functions (graph comes in Phase 3).
7. API: `POST /meetings`, `GET /meetings/{id}/slots`, `POST /meetings/{id}/confirm`.
8. UI: New Meeting form, slot picker (ruled list with reasoning), meetings table.

**Files:** `agents/{scheduling,room_booking}.py`, `services/slot_scorer.py`, `mcp_server/*`, `api/routes/{meetings,rooms}.py`, `pages/{NewMeeting,MeetingDetail}`.

**Done when**

- [ ] 3 ranked slots with one-line reasons
- [ ] Double-booking a room is rejected with a clear message
- [ ] Scorer has 8+ unit tests including edge cases
- [ ] Works with mock calendar; Google calendar optional switch

---

## Phase 3 — Agenda, memory, approval gate

**Goal:** agents that remember. Agenda is built from past meetings, and nothing leaves without approval.

**Tasks**

1. Models: `agendas`, `decisions`, `action_items` (schema only).
2. Memory layer: ChromaDB store, chunk and embed past minutes, retriever.
3. Seed 5 past meetings' minutes for testing.
4. LLM service wrapper with schema validation and one repair retry.
5. Agenda agent: topic + retrieved context + open actions, outputting time-boxed agenda (Pydantic model).
6. **LangGraph skeleton:** `MeetingState`, nodes `schedule → book_room → agenda → approval`, checkpointing, pause and resume at approval.
7. Tracer decorator writing to `agent_runs`.
8. UI: agenda editor, approve / request changes buttons, status labels.

**Files:** `memory/*`, `services/llm.py`, `agents/{agenda,graph,state}.py`, `observability/tracer.py`, `pages/AgendaEditor`.

**Done when**

- [ ] Agenda includes unresolved items from earlier meetings
- [ ] Graph pauses at approval and resumes after click
- [ ] Killing the server mid-run and restarting resumes from the last node
- [ ] Agenda total time never exceeds meeting length

---

## Phase 4 — Transcription and minutes

**Goal:** the core value. Audio in, grounded and approved minutes out.

**Tasks**

1. Models: `transcripts`, `minutes` with versions and hash.
2. STT service with `faster-whisper`; transcript paste as fallback.
3. PII redaction (`core/pii.py`) before any LLM call.
4. Minutes agent: attendees, discussion, decisions, action items, each with source quote and timestamp.
5. `grounding.py`: verify every quote exists in the transcript; drop and log failures.
6. `date_resolver.py`: "by Friday" becomes an actual date.
7. Add `minutes` and `approve_minutes` nodes to the graph.
8. API: audio upload, minutes get, approve, reject.
9. UI: minutes review page (transcript left, minutes right, margin comments, version history).

**Files:** `services/{stt,grounding,date_resolver}.py`, `core/pii.py`, `agents/minutes.py`, `api/routes/minutes.py`, `pages/MinutesReviewPage`.

**Done when**

- [ ] A 5-minute sample meeting produces minutes in under 2 minutes
- [ ] Every action item shows its source quote
- [ ] Invented items are dropped by the grounding check (test with a poisoned example)
- [ ] Approved minutes are locked and hashed

---

## Phase 5 — Actions, reminders, distribution, dashboard

**Goal:** close the loop. Approved minutes become tracked work with follow-ups.

**Tasks**

1. Action tracker agent: create items from approved minutes with owner, due date, priority, confidence.
2. Action API and status flow (Open, In Progress, Done, Blocked).
3. Reminder agent and APScheduler job; escalation ladder (gentle, nudge, notify chair).
4. Email service (SMTP) with idempotency keys; minutes PDF export; ICS file.
5. Distribution agent with audit logging.
6. Finish graph: `actions → distribute → reminders` loop.
7. UI: action tracker (table first, Kanban second), real Dashboard with "Awaiting approval", "This week", "Overdue".
8. Admin pages: rooms, users, audit log.

**Files:** `agents/{action_tracker,reminder,distribution}.py`, `jobs/reminders.py`, `services/pdf.py`, `pages/{ActionTracker,Dashboard,Admin}`.

**Done when**

- [ ] Full lifecycle runs: request to closed actions
- [ ] Retrying an email never sends twice
- [ ] Overdue item triggers the next reminder level
- [ ] Dashboard shows live data from the database

---

## Phase 6 — Visibility, evaluation, safety, demo

**Goal:** the parts that earn marks. Show that it works, is safe, and can be explained.

**Tasks**

1. Trace viewer: list runs, show steps, prompts, tool calls, latency, tokens; replay.
2. Evaluation harness: 10 gold meetings, WER, action-item precision/recall/F1, hallucination rate; report page.
3. Memory chat with cited answers.
4. Decision log with contradiction detection.
5. Safety pass: tool allow-lists per agent, step limits, prompt-injection delimiters, rollback of agent actions.
6. Finish MCP server; test it from Claude Desktop.
7. Meeting health score.
8. Demo mode: `make demo` loads seed data and runs the lifecycle.
9. Final polish against the `rule.md` checklist; README with screenshots; CI on GitHub Actions.
10. Deep research report and presentation slides.

**Files:** `pages/{TraceViewer,Evaluation,MemoryChat}`, `evals/*`, `memory/decision_log.py`, `services/health_score.py`, `data/seed/*`, `docs/research-report.md`.

**Done when**

- [ ] Eval report shows WER \< 15%, F1 ≥ 0.80, hallucination \< 5%
- [ ] Demo mode completes the full run in under 3 minutes
- [ ] MCP tools callable from an external client
- [ ] Every item on the `rule.md` definition-of-done list is checked
- [ ] Cold-open test: nothing looks default

---

## If time runs short

Cut in this order (last first): health score, multilingual minutes, decision-log contradictions, Kanban view, Google Calendar (keep mock). Never cut: approval gates, grounding check, trace viewer, evaluation harness, MCP server.

## Rubric alignment

| Rubric item | Where it is earned |
| --- | --- |
| Weekly labs (25%) | Phases 1–5 each map to lab concepts |
| Skill assignment (10%) | Phase 3 and 4 prompts packaged as skills |
| MCP / tool integration (10%) | Phases 2 and 6 |
| Multi-agent workflow (15%) | Phases 3–5 graph |
| Deep research report (10%) | Phase 6 |
| Capstone (25%) | Whole system, Phase 6 evidence |
| Presentation (5%) | Phase 6 demo mode |