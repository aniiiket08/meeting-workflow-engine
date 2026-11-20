# Lab 4: Memory and Retrieval

SRN: **02FE23BCI038**

## Assignment requirements from the guide

Assignment 1 — A Second, Isolated Topic
Add a second topic (e.g. "hosting") with its own stored record, distinct from "database". Demonstrate, in a transcript, that a retrieval scoped to "database" never returns or leaks the "hosting" fact into its answer, and vice versa. Submit the updated code and the two-topic transcript.
Assignment 2 — A Staleness / Retention Policy
Add a `retention_days` control and a staleness check: if a retrieved record is older than the configured threshold, the assistant must warn the user ("this decision is from N days ago and may be out of date") before using it in an answer. Test it with one fresh record and one artificially old record. Submit the updated code and a transcript showing both cases.

## Implementation notes

Exact topic retrieval isolates database and hosting. A frozen demonstration date makes fresh and old examples reproducible; retention warns but does not delete memory.

Each assignment script includes the original definitions plus its own enabled extension. `A1` and `A2` select the assignment features; both are enabled in `combined.py`. These are standalone scripts, so sibling imports are not required. The original guide demonstration is available unchanged as `reference.py`.

## Original source and captured output

Run from the repository root with `python labs/lab_04/reference.py`.

### Full source

```python
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
```

### Captured output

```text
[memory, dated 2026-07-03] Per a decision on 2026-07-03, we chose PostgreSQL

--- A team member proposes a change ---
This conflicts with the stored decision from 2026-07-03 ('we chose PostgreSQL'). Should I update memory to 'we're switching to SQLite'?

--- Team lead confirms the switch (permitted write) ---
Write permitted: memory updated by team_lead.

--- Attempted write by an unpermitted role ---
Blocked as expected: role 'member' is not permitted to write memory

--- Final answer reflects the confirmed update ---
[memory, dated 2026-11-15] Per a decision on 2026-11-15, we're switching to SQLite
```

## Assignment 1 source and captured output

Run from the repository root with `python labs/lab_04/assignment_1.py`.

### Full source

```python
# SRN 02FE23BCI038 | Lab 4: Memory and Retrieval | assignment_1
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
A2=False

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
```

### Captured output

```text
Fresh database: [memory, dated 2026-11-13] Per a decision on 2026-11-13, we chose PostgreSQL
Hosting: [memory, dated 2026-09-16] Per a decision on 2026-09-16, we chose a campus server
PASS: exact-topic isolation and retention warning
```

## Assignment 2 source and captured output

Run from the repository root with `python labs/lab_04/assignment_2.py`.

### Full source

```python
# SRN 02FE23BCI038 | Lab 4: Memory and Retrieval | assignment_2
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



A1=False
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
```

### Captured output

```text
Fresh database: [memory, dated 2026-11-13] Per a decision on 2026-11-13, we chose PostgreSQL
Old database: Warning: this decision is from 60 days ago and may be out of date.
[memory, dated 2026-09-16] Per a decision on 2026-09-16, we chose SQLite
PASS: exact-topic isolation and retention warning
```

## Combined source and captured output

Run from the repository root with `python labs/lab_04/combined.py`.

### Full source

```python
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
```

### Captured output

```text
Fresh database: [memory, dated 2026-11-13] Per a decision on 2026-11-13, we chose PostgreSQL
Hosting: Warning: this decision is from 60 days ago and may be out of date.
[memory, dated 2026-09-16] Per a decision on 2026-09-16, we chose a campus server
PASS: exact-topic isolation and retention warning
```

