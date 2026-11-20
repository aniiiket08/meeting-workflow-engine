"""
Lab 4: Memory and Retrieval -- Multi-Session Project Assistant
Separates short-term session state, long-term tagged memory, and a
control layer (write permissions), with source-tagged answers and
explicit conflict detection.
"""
from dataclasses import dataclass, field
from datetime import date


@dataclass
class MemoryRecord:
    topic: str
    fact: str
    date: str
    source: str = "memory"


class ProjectMemory:
    def __init__(self):
        self.records = []          # long-term store
        self.allowed_writers = {"team_lead"}

    def retrieve(self, topic):
        # Scoped retrieval -- only records matching the topic, not the whole store.
        return [r for r in self.records if r.topic == topic]

    def write(self, record, user_role):
        if user_role not in self.allowed_writers:
            raise PermissionError(f"role '{user_role}' is not permitted to write memory")
        self.records.append(record)


class ProjectAssistant:
    def __init__(self, memory):
        self.memory = memory
        self.session_facts = {}   # short-term working state

    def answer(self, topic, question):
        hits = self.memory.retrieve(topic)
        if not hits:
            return f"[session] No stored decision on '{topic}' yet. {question}"
        latest = hits[-1]
        return (f"[memory, dated {latest.date}] Per a decision on {latest.date}, "
                f"{latest.fact}")

    def receive_statement(self, topic, new_fact, user_role):
        """A team member states something new. Check for conflict with memory
        before deciding whether to write it."""
        hits = self.memory.retrieve(topic)
        if hits and hits[-1].fact.lower() != new_fact.lower():
            return {
                "conflict": True,
                "stored": hits[-1].fact,
                "stored_date": hits[-1].date,
                "new": new_fact,
                "message": (f"This conflicts with the stored decision from "
                            f"{hits[-1].date} ('{hits[-1].fact}'). "
                            f"Should I update memory to '{new_fact}'?"),
            }
        # No conflict -- safe to write (still permission-gated).
        record = MemoryRecord(topic=topic, fact=new_fact, date=str(date.today()))
        self.memory.write(record, user_role)
        return {"conflict": False, "message": f"Recorded: {new_fact}", "written": True}


if __name__ == "__main__":
    memory = ProjectMemory()
    memory.write(
        MemoryRecord(topic="database", fact="we chose PostgreSQL", date="2026-07-03"),
        user_role="team_lead",
    )

    assistant = ProjectAssistant(memory)

    print(assistant.answer("database", "What did we decide about the database?"))

    print("\n--- A team member proposes a change ---")
    result = assistant.receive_statement(
        "database", "we're switching to SQLite", user_role="member")
    print(result["message"])

    print("\n--- Team lead confirms the switch (permitted write) ---")
    confirm = assistant.receive_statement(
        "database", "we're switching to SQLite", user_role="team_lead")
    # First call already flagged the conflict; simulate confirmed re-statement
    # arriving from the team lead this time -- write should now succeed.
    if result["conflict"]:
        memory.write(
            MemoryRecord(topic="database", fact="we're switching to SQLite",
                         date=str(date.today())),
            user_role="team_lead",
        )
        print("Write permitted: memory updated by team_lead.")

    print("\n--- Attempted write by an unpermitted role ---")
    try:
        memory.write(
            MemoryRecord(topic="database", fact="switch to MongoDB", date=str(date.today())),
            user_role="member",
        )
    except PermissionError as e:
        print(f"Blocked as expected: {e}")

    print("\n--- Final answer reflects the confirmed update ---")
    print(assistant.answer("database", "What did we decide about the database?"))
