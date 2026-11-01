# Bottleneck Analysis & Root Cause Investigation

This document details the root cause analysis, severity rankings, architectural bottlenecks, and empirical fixes identified during the comprehensive evaluation of the **Meeting Organizer Agent**.

> Historical findings below were not all reproduced in the 2026-11-01 verification. See `evaluation_report.md` for current measurements. Do not treat historical measurements or root-cause hypotheses as current results.

---

## 1. Executive Bottleneck Hierarchy

| Rank | Bottleneck / Defect | Severity | Impact Area | Confidence | Root Cause | Implemented Resolution |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | **Gemini API connectivity** | **Needs review** | All LLM agents (Minutes, Agenda, Actions) | Current run measured | An earlier report attributed timeouts to header authentication; that cause was not re-established. | Current implementation and benchmark use only the `x-goog-api-key` header. The 2026-11-01 direct request returned HTTP 200 in 8.217 s. |
| **2** | **Stale SQLite DB Schema & Missing Columns** | **CRITICAL (P0)** | Authentication, Meeting lists, Schedule views | 100% | `backend/sql_app.db` was out of sync with migrations (missing `users.username`, `meetings.zoom_meeting_id`, `meetings.max_attendees`). | Applied missing column migrations and synchronized tables with the model definitions. |
| **3** | **WeasyPrint Dynamic Library Missing on Host** | **Needs review** | Document Distribution Node, PDF Export | Historical finding | WeasyPrint depends on native libraries that may be unavailable on Windows hosts. | PDF generation now raises a typed `ToolError` on renderer failure; the distribution path records the PDF as unavailable rather than emitting placeholder PDF bytes. |
| **4** | **Unauthenticated /agendas Collection Endpoint** | **MEDIUM (P2)** | API Navigation / Frontend Agenda Loader | 100% | Frontend expects a root `GET /agendas` collection route, but router only defines meeting-scoped subroutes (`/meetings/{id}/agenda`). | Documented API discrepancy; updated frontend calling contracts to use scoped endpoints. |
| **5** | **Memory Store Keyword Vocabulary Gaps** | **LOW (P3)** | RAG Agenda & History Ingestion | 95% | BM25 retrieval missed queries lacking exact token overlap (e.g. "timetable" vs "room scheduling"). | Updated seed and retrieval keyword mappings to support standard academic scheduling synonyms. |

---

## 2. In-Depth Root Cause Analysis

### 2.1 Gemini API Authentication and Connectivity

- **Current implementation:** Gemini authentication is sent only in the `x-goog-api-key` header. The request URL contains no credential query parameter.
- **2026-11-01 verification:** One direct API request returned HTTP 200 in 8.217 seconds. The 10-meeting benchmark made 29 requests with zero retries.
- **Historical timeout diagnosis:** The prior claim that custom-header authentication caused network timeouts was not reproduced or otherwise verified during this run. No key-in-URL workaround is present or permitted.

### 2.2 Schema Divergence on Local SQLite Databases (P0)
- **Symptom:** `POST /api/v1/auth/login` and `GET /api/v1/meetings` threw HTTP 500 Internal Server Error.
- **Diagnostic Trace:**
  ```text
  sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) no such column: users.username
  sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) no such column: meetings.zoom_meeting_id
  ```
- **Root Cause:** Alembic migrations `005_username.py` and `010_meeting_invitees_options.py` had been executed on the root directory database `sql_app.db`, but the backend process started inside `backend/` was referencing an unmigrated `backend/sql_app.db` snapshot.
- **Verification:**
  - Before: 33.3% of tested API endpoints returned 500 Internal Server Error.
  - After: 0% error rate across all valid endpoints; login succeeds in ~220ms with token issuance.

### 2.3 Native Dependency Crash on PDF Minutes Distribution (P1)
- **Symptom:** Multi-agent LangGraph workflow crashed at `distribute_node` with `app.core.errors.ToolError: Could not generate the minutes PDF`.
- **Diagnostic Trace:**
  ```text
  OSError: cannot load library 'libgobject-2.0-0': error 0x7e.
  Additionally, ctypes.util.find_library() did not manage to locate a library called 'libgobject-2.0-0'
    File "backend/app/services/email_service.py", line 85, in generate_pdf_minutes
      from weasyprint import HTML
  ```
- **Root Cause:** `weasyprint` relies on GTK/Pango C shared libraries (`libgobject-2.0-0`, `libpango-1.0-0`) that are absent in non-containerized Windows operating systems. When this call raised an exception, the entire LangGraph workflow halted at the final step, leaving the meeting in an incomplete state.
- **Current handling:** PDF generation raises a typed `ToolError` when the renderer is unavailable. Distribution records the PDF as unavailable and does not attach fake PDF bytes. Current test results are reported separately after the full backend suite.

---

## 3. Database & Concurrency Profiling

- **Query Latencies:**
  - `SELECT 1` ping: 0.058 ms (p50)
  - `User by id` lookup: 0.256 ms (p50)
  - `User by email` lookup: 0.259 ms (p50)
  - `All rooms` retrieval: 0.182 ms (p50)
  - `Meeting insert + rollback`: 0.911 ms (p50)
- **Concurrency Scalability:**
  - SQLite under `QueuePool` handled up to 20 concurrent virtual users without connection exhaustion or locking timeouts (`database is locked` error count = 0 across 306 requests).
  - Average response time under 20-user load was **22.0 ms** across all API operations, with p50 at **4.0 ms**.
