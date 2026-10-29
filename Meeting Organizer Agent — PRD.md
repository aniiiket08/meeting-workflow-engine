# Meeting Organizer Agent — Product Requirements Document

**Worklet 4 · Agentic AI Lab · KLE Tech** *From scheduling to signed-off minutes and tracked action items.*

---

## 1. Product Vision

A multi-agent system that owns the **entire meeting lifecycle**: finding the slot, preparing the agenda, booking the room, transcribing, writing minutes, getting them **human-approved**, tracking action items, and chasing follow-ups. Every step is traced, evaluated, and auditable.

**One-line pitch:** *"The meeting assistant that doesn't just take notes, it makes sure decisions actually happen."*

**Problem:** Meetings waste time on scheduling back-and-forth, unprepared agendas, lost minutes, and action items nobody follows up on.

**Goal:** Reduce coordinator effort from \~60 min per meeting to \~5 min (review and approve only).

## 2. Target Users

| User | Role | Needs |
| --- | --- | --- |
| **HOD / Teacher** (primary coordinator) | Faculty who organizes meetings | Fast scheduling, ready agenda, approved minutes |
| **Teacher / Student** | Faculty and student attendees | Clear agenda, their action items, reminders |
| **Chairman / Principal** (approver) | Chair or Head of Institution | Review and sign off agendas and minutes |
| **Chairman / Principal** (admin) | Senior authority / department office | Room and resource management, audit logs, Activity trace |

## 3. Scope

**In scope:** the 7 agents, 4 expected outputs, dashboard, MCP connector, memory/RAG, evaluation harness, safety layer. **Out of scope (v1):** video-call bots joining Zoom/Meet automatically, mobile app.

## 4. Agent Architecture (Multi-Agent Workflow, 15% weight)

Orchestrated as an **explicit node graph** (LangGraph) with a human-approval node. An **Orchestrator** routes between agents.

| # | Agent | Input | Output | Tools |
| --- | --- | --- | --- | --- |
| 1 | **Scheduling & Availability** | Attendees, duration, window | 3 ranked slots | Calendar API, availability scorer |
| 2 | **Agenda Preparation** | Topic, past meetings, pending actions | Structured agenda with time boxes | RAG over past minutes, LLM |
| 3 | **Transcription & Minutes** | Audio / transcript | Draft minutes (discussion, decisions, actions) | Whisper STT, LLM summarizer |
| 4 | **Action-Item Tracker** | Approved minutes | Items with owner, due date, status, priority | DB, entity resolver |
| 5 | **Follow-up Reminder** | Open items | Escalating reminders | Email/Calendar, scheduler |
| 6 | **Resource & Room Booking** | Headcount, equipment needs | Room booked, conflict-free | Room DB, calendar |
| 7 | **Distribution & Logging** | Approved artifacts | Emails, ICS invites, audit log | SMTP, logger |

**Workflow graph:** `Request → Scheduling → Room Booking → Agenda → [Human Approve Agenda] → Meeting → Transcription → Minutes → [Human Approve Minutes] → Action Tracker → Distribution → Follow-up loop`

**Rule:** no minutes or emails are released without explicit human approval (Lab 12: Safety & Governance).

## 5. Expected Outputs (mapped to brief)

1. **Proposed meeting slots**: ranked, with reasoning ("Tue 3 PM: all 6 free, no back-to-back").
2. **Structured agenda**: items, owner, time box, linked pending actions from last meeting.
3. **Approved minutes**: draft, edit, approve, version-locked, with approver and timestamp.
4. **Action-item tracker**: Kanban/table with owner, due date, status, overdue flag.

## 6. Core Features

### 6.1 Smart Scheduling

- Reads Google Calendar free/busy for all attendees.
- Scores slots by: everyone available, preference hours, no back-to-back, priority attendees.
- Shows **why** each slot was ranked, then user picks and invites are sent.

### 6.2 Auto Agenda

- Pulls unresolved action items and open decisions from prior meetings (RAG).
- Generates time-boxed agenda; total duration validated against meeting length.

### 6.3 Transcription & Minutes

- Upload audio or paste transcript; Whisper converts it to text with speaker labels.
- LLM produces structured minutes: **Attendees · Agenda covered · Discussion · Decisions · Action items**.
- Each action item shows its **source quote and timestamp** (grounded, anti-hallucination).

### 6.4 Approval Workflow

- Side-by-side editor: transcript on the left, minutes on the right.
- Approve, Request changes, or Reject. Approved minutes get locked and hashed.

### 6.5 Action-Item Tracker

- Auto-extracts owner, deadline ("by Friday" becomes a real date), priority.
- Status flow: Open → In Progress → Done / Blocked.
- Weekly digest and overdue alerts.

### 6.6 Room & Resource Booking

- Capacity + equipment (projector, mic) matching, double-booking prevention.

### 6.7 Distribution & Logging

- Sends minutes (PDF) and ICS invites by email; every action is written to an audit log.

## 7. Differentiators (what makes evaluators say "wow")

| # | Feature | Why it impresses | Rubric link |
| --- | --- | --- | --- |
| 1 | **Meeting Memory Chat**: ask *"What did we decide about the lab budget in September?"* and get cited answers across all meetings | Real RAG, not a demo | Lab 4, Capstone |
| 2 | **Decision Log**: every decision stored once, searchable, with contradiction detection ("this conflicts with the decision on 12 Sep") | Shows reasoning beyond summarization | Multi-agent |
| 3 | **Agent Trace Viewer**: timeline of every agent step, tool call, prompt, latency, token cost; one-click replay | Directly matches "prompt logs, tool calls, traces" grading | Weekly labs |
| 4 | **Evaluation Harness**: golden test set of 10 sample meetings; reports **WER, action-item precision/recall/F1, hallucination rate** | Evidence-based quality, rarely seen in student projects | Tests |
| 5 | **Own MCP Server**: exposes `find_slots`, `get_minutes`, `list_actions`, `book_room` so Claude Desktop or any MCP client can use your system | Lab 5 and tool integration shown live | MCP/tool 10% |
| 6 | **Meeting Health Score**: agenda coverage %, talk-time balance, decisions per hour, action clarity | Analytics that feel product-grade | Dashboard |
| 7 | **Follow-up Escalation Ladder**: gentle reminder, then nudge, then notify chair; adapts to owner's reliability | Autonomy with limits | Lab 12 |
| 8 | **Safety Layer**: PII redaction in transcripts, role-based permissions, rollback of agent actions, full audit log | Responsible autonomy | Governance |
| 9 | **Reusable Skills**: packaged `agenda-writer`, `minutes-writer`, `action-extractor` skills with documented prompts | Skill assignment 10% | Lab 3 |
| 10 | **Demo Mode**: one click loads seeded data and runs the full lifecycle in 3 minutes | Flawless presentation | Presentation 5% |
| 11 | **Multilingual minutes** (English, Hindi, Kannada summary) | Local relevance, memorable | Bonus |
| 12 | **Pre-meeting Brief**: one-page email to each attendee with their items and context | Proactive agent behavior | Agenda agent |

## 8. Dashboard & Interface (Pages)

1. **Home Dashboard**: upcoming meetings, pending approvals, overdue actions, health score trend, quick "New Meeting" button.
2. **New Meeting Wizard**: topic, attendees, duration, then ranked slots, room, agenda preview, confirm.
3. **Meeting Detail**: agenda, attendees, transcript, minutes, actions in tabs.
4. **Minutes Review**: split editor with approve/reject and version history.
5. **Action Tracker**: Kanban + table, filters by owner/status/due.
6. **Memory Chat**: conversational search across all meetings with citations.
7. **Trace Viewer**: agent-run timeline and replay.
8. **Evaluation Page**: metrics, charts, test results.
9. **Admin**: rooms, users, roles, audit log, settings.

## 9. Technical Requirements

| Layer | Choice |
| --- | --- |
| Language | Python 3.11 |
| Backend | FastAPI |
| Agent orchestration | LangGraph (node graph) |
| LLM | Claude API (or Gemini/OpenAI-compatible) |
| Speech-to-text | OpenAI Whisper / faster-whisper |
| Vector store (RAG) | ChromaDB or FAISS + sentence-transformers |
| Database | SQLite (dev) → PostgreSQL |
| Calendar | Google Calendar API (OAuth) |
| Email | SMTP / Gmail API |
| Tool protocol | MCP Python SDK |
| Frontend | React + Tailwind, or Streamlit for speed |
| Charts | Recharts / Plotly |
| Tests | pytest + custom eval scripts |
| Deploy | Docker Compose; demo on Render/Railway |

## 10. Database Schema (core tables)

- **users**(id, name, email, role)
- **meetings**(id, title, start, end, room_id, status, organizer_id)
- **attendees**(meeting_id, user_id, rsvp)
- **agendas**(id, meeting_id, items_json, status, approved_by)
- **transcripts**(id, meeting_id, text, speakers_json, audio_path)
- **minutes**(id, meeting_id, version, content, status, approved_by, approved_at, hash)
- **decisions**(id, meeting_id, text, source_quote, timestamp)
- **action_items**(id, meeting_id, description, owner_id, due_date, priority, status, source_quote, confidence)
- **rooms**(id, name, capacity, equipment)
- **reminders**(id, action_id, level, sent_at)
- **agent_runs**(id, meeting_id, agent, input, output, tools_json, latency_ms, tokens, created_at)
- **audit_log**(id, actor, action, entity, timestamp)
- **embeddings**: stored in the vector store (chunk, meeting_id, speaker, time)

## 11. Functional Requirements

| ID | Requirement | Priority |
| --- | --- | --- |
| FR1 | Suggest at least 3 ranked slots from calendar data | Must |
| FR2 | Generate time-boxed agenda from topic and history | Must |
| FR3 | Transcribe uploaded audio | Must |
| FR4 | Generate structured minutes with grounded citations | Must |
| FR5 | Require human approval before release | Must |
| FR6 | Extract action items with owner and due date | Must |
| FR7 | Track status and send reminders | Must |
| FR8 | Book rooms without conflicts | Must |
| FR9 | Email minutes and log every action | Must |
| FR10 | Memory chat with citations | Should |
| FR11 | Trace viewer and replay | Should |
| FR12 | Evaluation harness | Should |
| FR13 | MCP server | Should |
| FR14 | Health score, multilingual, contradiction detection | Could |

## 12. Non-Functional Requirements

- **Latency:** minutes for a 30-min meeting in under 2 minutes; slot suggestion under 5 seconds.
- **Accuracy targets:** action-item F1 ≥ 0.80, WER \< 15%, hallucinated items \< 5%.
- **Security:** OAuth, role-based access, secrets in env vars, PII redaction.
- **Reliability:** retries on tool failure; agent failure never loses data.
- **Auditability:** every agent action traceable.

## 13. Success Metrics

| Metric | Target |
| --- | --- |
| Coordinator time per meeting | \< 5 min |
| Action-item extraction F1 | ≥ 0.80 |
| Minutes approved without major edits | ≥ 70% |
| Action items completed on time | +30% vs baseline |
| End-to-end demo success | 100% in demo mode |

## 14. Mapping to Grading Rubric

| Component | Weight | How this project earns it |
| --- | --- | --- |
| Weekly labs | 25% | Each lab's concept is visible in the repo (tool agent, memory, node graph, etc.) |
| Skill assignment | 10% | 3 reusable, documented skills |
| MCP/tool integration | 10% | Own MCP server + Calendar, Email, STT tools |
| Multi-agent workflow | 15% | 7 agents on a LangGraph node graph with approval gates |
| Deep research report | 10% | Research topic: *"Agentic meeting assistants: state of the art, risks, evaluation"* |
| Capstone | 25% | Full working system + evaluation + safety |
| Presentation | 5% | 3-min Demo Mode, trace viewer on screen |

**Artifacts to submit (graded on evidence):** prompt logs, tool-call logs, traces, pytest results, eval report, demo recording.

## 15. Roadmap (4-person team)

| Week | Milestone | Owner idea |
| --- | --- | --- |
| 1 | Setup, DB schema, calendar + scheduling agent | Member 1 |
| 2 | Agenda agent, room booking, RAG pipeline | Member 2 |
| 3 | Transcription + minutes agent, approval UI | Member 3 |
| 4 | Action tracker, reminders, distribution | Member 4 |
| 5 | Node graph integration, MCP server, trace viewer | All |
| 6 | Eval harness, safety, dashboard polish, demo mode, report, slides | All |

## 16. Risks and Mitigations

| Risk | Mitigation |
| --- | --- |
| Calendar OAuth setup delays | Start day 1; fall back to mock calendar JSON |
| LLM hallucinated action items | Require source quote and confidence score; human approval |
| Poor audio quality | Support transcript paste; use Whisper medium model |
| Scope creep | Build all "Must" first, then add differentiators in order of rubric value (3, 4, 5, 1) |
| API cost | Cache responses; use smaller model for extraction |

## 17. Demo Script (3 minutes)

1. Type "Weekly project review, 6 people" and see 3 ranked slots with reasons.
2. Pick one, then the room auto-books and agenda appears from last meeting's pending items.
3. Upload sample recording, then minutes appear with cited quotes.
4. Approve minutes and action items populate the tracker.
5. Ask Memory Chat: "What did we decide about X?" and get a cited answer.
6. Open Trace Viewer, then the Eval page showing F1 and WER.
7. Show Claude Desktop calling your MCP server.

---

*Priority if time is short: Must items, then Trace Viewer, Eval Harness, MCP Server, Memory Chat.*