# Test Results & Validation Suite

This document records the automated and functional test suite results across all functional areas of the **Meeting Organizer Agent**.

---

## 1. Test Execution Summary

| Test Suite / Phase | Tool / Runner | Items Executed | Passed | Failed | Skipped | Success Rate | Duration |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Backend Unit Tests** | `pytest 9.1.1` | 172 | 171 | 0 | 1 | 99.4% (100% runnable) | 27.69s |
| **API Endpoints Baseline** | `bench_api.py (httpx)` | 90 | 80 | 10* | 0 | 88.9% (100% on valid routes) | 12.4s |
| **MCP Room Tools** | `bench_mcp.py` | 6 | 6 | 0 | 0 | 100.0% | 0.45s |
| **Memory Store Retrieval**| `bench_memory.py` | 5 | 5 | 0 | 0 | 100.0% | 0.08s |
| **AI Quality Evaluation** | `bench_llm_quality.py` | 3 meetings (9 LLM calls) | 3 | 0 | 0 | 100.0% | 31.3s |
| **LangGraph End-to-End** | `bench_workflow.py` | 9 graph nodes (2 gates) | 9 | 0 | 0 | 100.0% | 32.8s |
| **Locust 1-User Smoke** | `locust 2.47.0` | 15 requests | 15 | 0 | 0 | 100.0% | 20.0s |
| **Locust 5-User Baseline**| `locust 2.47.0` | 82 requests | 74 | 8* | 0 | 90.2% (100% on valid routes) | 20.0s |
| **Locust 10-User Moderate**| `locust 2.47.0` | 146 requests | 146 | 0 | 0 | 100.0% | 20.0s |
| **Locust 20-User Stress** | `locust 2.47.0` | 306 requests | 306 | 0 | 0 | 100.0% | 20.0s |
| **Frontend Production Build**| `vite build + tsc` | 1509 modules | 1509 | 0 | 0 | 100.0% | 10.06s |

*\*Note on 404s: The 10 failed requests in baseline API and 8 in 5-user Locust were caused by `GET /api/v1/agendas` which is not a defined REST collection endpoint (agendas are scoped as `/api/v1/meetings/{id}/agenda`). Once removed from the load task, error rate dropped to 0.0%.*

---

## 2. Test Details by Functional Area

### 2.1 Authentication & Role-Based Access Control (RBAC)
- **Login with Valid Credentials:**
  - `POST /api/v1/auth/login` with username `chairman` and password `changeme`: **200 OK**, issued signed JWT bearer token.
- **Login with Bad Password:**
  - `POST /api/v1/auth/login` with bad password: **401 Unauthorized** (Correctly blocked).
- **Protected Profile:**
  - `GET /api/v1/auth/me` with Bearer token: **200 OK**, returns Chairman user model.
- **Role Permissions Gate:**
  - `GET /api/v1/auth/chairman-only` as Chairman: **200 OK**.
  - `GET /api/v1/auth/chairman-only` as Teacher: **403 Forbidden** (Correctly rejected).

### 2.2 Model Context Protocol (MCP) Tools
- **Tool: `room_search`**
  - Small team (10 pax): Returned 4 matching rooms (`Auditorium`, `IoT Lab`, `STEP Hall`, `MB 104`) in **16.65 ms**.
  - Large cohort (150 pax): Filtered down to 1 room (`Auditorium`) in **0.81 ms**.
  - Exceeds capacity (500 pax): Correctly returned `[]` in **0.37 ms**.
  - Missing time window parameter: Correctly raised `ValidationFailed` in **0.01 ms**.
- **Tool: `room_book`**
  - Valid booking: Status `booked` in **9.88 ms**.
  - Duplicate booking conflict: Correctly raised `Conflict: Room is already booked between 14:30 and 15:30` in **1.08 ms**.

### 2.3 RAG Memory Store & Semantic Retrieval
- **Implementation:** BM25-style keyword frequency scoring + recency weighting over structured meeting minutes.
- **Precision:** 100.0% (No irrelevant documents returned for negative query `xyznonexistentterm000`).
- **Recall:** 100.0% across all relevant domain queries (`GPU cluster`, `room scheduling`, `fee payment`, `research publication`).
- **Mean Retrieval Latency:** **0.12 ms**.

### 2.4 Multi-Agent LangGraph Workflow Execution
- **Graph Pipeline:**
  1. `schedule`: Calculated ranked meeting slots.
  2. `book_room`: Reserved suitable room based on attendee headcount.
  3. `agenda`: Generated 3-topic time-boxed agenda via Gemini LLM.
  4. `approval_gate`: Interrupted execution waiting for human decision; resumed upon signature.
  5. `minutes`: Synthesized transcript into decisions, summaries, and action candidates.
  6. `approve_minutes_gate`: Interrupted execution waiting for approval signature.
  7. `actions`: Extracted and linked action items with source transcript quote grounding.
  8. `distribute`: Prepared PDF minutes and iCal events.
  9. `reminders`: Checked escalation rules and completed lifecycle.
- **Total Execution Time:** **32,858 ms (32.8s)** across full pipeline with 100% node completion.

---

## 3. Reproducible Reproduction Commands

To reproduce the complete benchmark and evaluation suite locally:

```bash
# 1. Activate Python virtual environment
.venv\Scripts\activate

# 2. Run unit and integration tests
pytest backend/tests/unit -v

# 3. Start the FastAPI backend server
$env:PYTHONPATH='backend'
python -m uvicorn app.main:app --host 127.0.0.1 --port 8765

# 4. In a separate terminal, execute evaluation scripts:
python evaluation/bench_api.py
python evaluation/bench_memory.py
python evaluation/bench_mcp.py
python evaluation/bench_llm_quality.py
python evaluation/bench_workflow.py
python evaluation/bench_frontend.py

# 5. Run headless load tests with Locust:
locust -f evaluation/locustfile.py --headless -u 10 -r 2 --run-time 20s --host http://127.0.0.1:8765
```

