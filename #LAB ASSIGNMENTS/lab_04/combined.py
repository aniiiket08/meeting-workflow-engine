# SRN 02FE23BCI038 | Lab 4: Memory and Retrieval | combined
# Original definitions retained below; extensions follow.
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



A1=True
A2=True

from datetime import timedelta
class RetainedAssistant(ProjectAssistant):
    def __init__(self, memory, retention_days=30, today=None):
        super().__init__(memory); self.retention_days=retention_days; self.today=today or date.today()
    def answer(self, topic, question):
        hits=self.memory.retrieve(topic)
        if not hits: return super().answer(topic, question)
        age=(self.today-date.fromisoformat(hits[-1].date)).days
        warning=f'Warning: this decision is from {age} days ago and may be out of date.\n' if A2 and age>self.retention_days else ''
        return warning+super().answer(topic,question)
def demo():
    today=date(2026,11,15); m=ProjectMemory()
    m.write(MemoryRecord('database','we chose PostgreSQL',str(today-timedelta(days=2))), 'team_lead')
    if A1: m.write(MemoryRecord('hosting','we chose a campus server',str(today-timedelta(days=60))), 'team_lead')
    a=RetainedAssistant(m,30,today)
    db=a.answer('database','Which database?');print('Fresh database:',db)
    assert 'campus server' not in db and 'Warning' not in db
    if A1:
        host=a.answer('hosting','Which host?');print('Hosting:',host)
        assert 'PostgreSQL' not in host
        if A2: assert '60 days ago' in host
    if A2 and not A1:
        m.write(MemoryRecord('database','we chose SQLite',str(today-timedelta(days=60))), 'team_lead')
        old=a.answer('database','Which database?');print('Old database:',old);assert '60 days ago' in old
    print('PASS: exact-topic isolation and retention warning')

if __name__ == "__main__":
    demo()
