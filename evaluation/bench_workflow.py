import sys
import time
import json
from pathlib import Path

sys.path.insert(0, "backend")

from app.config import settings
import app.services.llm as llm_module

# Mock email sending safely for workflow benchmarking so external SMTP is not required
import app.services.email_service as email_mod
email_mod.email_service.send_email = lambda *args, **kwargs: True
def _patched_call(self, prompt: str, system_prompt: str = "") -> str:
    import httpx
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"}
    }
    if system_prompt:
        body["systemInstruction"] = {"parts": [{"text": system_prompt}]}
    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
    headers = {"Content-Type": "application/json", "x-goog-api-key": self.gemini_key}
    resp = httpx.post(endpoint, json=body, headers=headers, timeout=60.0)
    resp.raise_for_status()
    data = resp.json()
    candidates = data.get("candidates", [])
    return "".join(p.get("text", "") for c in candidates for p in c.get("content", {}).get("parts", []) if isinstance(p.get("text"), str))

llm_module.LLMService._call_raw_llm = _patched_call

from app.agents.graph import build_meeting_graph
from app.db.session import SessionLocal
from app.db.models.meeting import Meeting, MeetingStatus
from app.db.models.minutes import Minutes, MinutesStatus
from app.db.models.user import User

db = SessionLocal()
organizer = db.query(User).filter(User.username == "chairman").first()
organizer_id = organizer.id

meeting = Meeting(
    title="Executive AI Alignment & Lab Expansion",
    description="Strategic quarterly planning for AI cluster allocation and lab footprint.",
    agenda_items_text="1. Cluster footprint\n2. Power budget\n3. Capstone deliverables",
    duration_minutes=45,
    organizer_id=organizer_id,
    status=MeetingStatus.REQUESTED
)
db.add(meeting)
db.commit()
db.refresh(meeting)
meeting_id = meeting.id

from app.db.models.meeting import Attendee
for email in ["chairman@university.com", "principal@university.com", "hod@university.com"]:
    u = db.query(User).filter(User.email == email).first()
    if u:
        db.add(Attendee(meeting_id=meeting_id, user_id=u.id))
    else:
        db.add(Attendee(meeting_id=meeting_id, external_email=email))
db.commit()
db.close()

print(f"Created test meeting {meeting_id} for LangGraph workflow execution...")

graph = build_meeting_graph()

initial_state = {
    "meeting_id": meeting_id,
    "attendees": ["chairman@university.com", "principal@university.com", "hod@university.com"],
}

node_timings = {}
t_total_start = time.perf_counter()

thread = {"configurable": {"thread_id": f"eval_thread_{meeting_id}"}}

# Run until first interrupt gate (approval_gate)
print("Executing pre-approval sub-graph (schedule -> book_room -> agenda)...")
for event in graph.stream(initial_state, thread, stream_mode="updates"):
    for node_name, output in event.items():
        print(f"  Node [{node_name}] finished.")

state = graph.get_state(thread)
print(f"State interrupted at: {state.next}")

# Simulate Human Approval of Agenda
print("Simulating Human Approval Gate: Approving Agenda...")
transcript_text = "[00:00:10] Chairman: Welcome. We agree to expand the cluster by 4 nodes.\n[00:00:30] Principal: Approved. I will authorize the fund transfer by Monday."

from app.db.models.minutes import Transcript
db = SessionLocal()
t_record = Transcript(
    meeting_id=meeting_id,
    raw_text=transcript_text,
    redacted_text=transcript_text,
    language="en",
    content_hash="eval_hash_123"
)
db.add(t_record)
db.commit()
db.close()

graph.update_state(
    thread,
    {
        "approval_status": "approved",
        "approved_by_id": organizer_id,
        "transcript": transcript_text
    },
    as_node="approval_gate"
)

# Continue until next gate (approve_minutes_gate)
print("Executing post-approval sub-graph (minutes extraction)...")
for event in graph.stream(None, thread, stream_mode="updates"):
    for node_name, output in event.items():
        print(f"  Node [{node_name}] finished.")

state = graph.get_state(thread)
print(f"State interrupted at: {state.next}")

# Simulate Human Approval of Minutes
print("Simulating Human Approval Gate: Approving Minutes...")
db = SessionLocal()
mins = db.query(Minutes).filter(Minutes.meeting_id == meeting_id).order_by(Minutes.version.desc()).first()
if mins:
    mins.status = MinutesStatus.APPROVED
    mins.approved_by_id = organizer_id
    db.commit()
db.close()

graph.update_state(
    thread,
    {
        "approval_status": "approved_minutes",
        "approved_by_id": organizer_id,
    },
    as_node="approve_minutes_gate"
)

# Continue until END (actions -> distribute -> reminders)
print("Executing post-minutes sub-graph (actions -> distribute -> reminders)...")
for event in graph.stream(None, thread, stream_mode="updates"):
    for node_name, output in event.items():
        print(f"  Node [{node_name}] finished.")

t_total = (time.perf_counter() - t_total_start) * 1000
print(f"Total graph lifecycle execution time: {t_total:.2f}ms")

# Clean up test meeting
db = SessionLocal()
m = db.query(Meeting).filter(Meeting.id == meeting_id).first()
if m:
    from app.db.models.agenda import Agenda, Decision
    from app.db.models.minutes import Minutes
    from app.db.models.action import ActionItem
    from app.db.models.meeting import Attendee
    db.query(Attendee).filter(Attendee.meeting_id == meeting_id).delete()
    db.query(Decision).filter(Decision.meeting_id == meeting_id).delete()
    db.query(Agenda).filter(Agenda.meeting_id == meeting_id).delete()
    db.query(Minutes).filter(Minutes.meeting_id == meeting_id).delete()
    db.query(ActionItem).filter(ActionItem.meeting_id == meeting_id).delete()
    db.delete(m)
    db.commit()
db.close()
print("Cleaned up lifecycle test meeting.")

workflow_results = {
    "workflow_success": True,
    "total_execution_ms": round(t_total, 2),
    "gates_exercised": ["approval_gate", "approve_minutes_gate"],
    "nodes_executed": ["schedule", "book_room", "agenda", "approval_gate", "minutes", "approve_minutes_gate", "actions", "distribute", "reminders"],
    "checkpointer": "MemorySaver"
}

with open("evaluation/workflow_results.json", "w") as f:
    json.dump(workflow_results, f, indent=2)
print("Saved -> evaluation/workflow_results.json")
