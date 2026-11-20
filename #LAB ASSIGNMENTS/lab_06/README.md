# Lab 6: OpenCLA/OpenClaw Runtime

SRN: **02FE23BCI038**

## Assignment requirements from the guide

Assignment 1 — Add Per-User Rate Limiting
Add a new control: each user may run at most 3 tasks per session. Implement this as a check inside `receive_task` (or a thin wrapper around it) without changing `run_task`'s core loop signature or its skill-dispatch logic. Submit the updated code and a transcript showing a 4th task being rejected.
Assignment 2 — Escalate After Two Failures
Add a rule: if the same skill fails twice in one session for the same user, the third attempt must escalate to a human instead of retrying the skill again. Implement this using the existing audit log (count prior error entries for that user/skill pair) rather than adding new hidden state. Submit the updated code and a transcript showing two failures followed by an escalation instead of a third attempt.

## Implementation notes

A thin interface wrapper enforces admission limits without editing run_task. User and skill failure counts come from audit entries. The third failing skill attempt escalates before admission; it does not invoke the skill again.

Each assignment script includes the original definitions plus its own enabled extension. `A1` and `A2` select the assignment features; both are enabled in `combined.py`. These are standalone scripts, so sibling imports are not required. The original guide demonstration is available unchanged as `reference.py`.

## Original source and captured output

Run from the repository root with `python labs/lab_06/reference.py`.

### Full source

```python
"""
Lab 6: OpenCLA/OpenClaw-Style Runtime -- Mini Personal Agent Runtime
Six components: interface, runtime loop, skill registry, tools,
scoped memory, audit log. A new skill can be registered without any
change to the core loop.
"""
from datetime import datetime


# ---- Tools ------------------------------------------------------------
def tool_word_count(text):
    return {"count": len(text.split())}


def tool_lookup_contact(name, contacts_db):
    return contacts_db.get(name, {"error": f"no contact found for {name}"})


TOOLS = {"word_count": tool_word_count, "lookup_contact": tool_lookup_contact}


# ---- Memory, scoped per user -------------------------------------------
class Memory:
    def __init__(self):
        self._store = {}

    def scope(self, user):
        return self._store.setdefault(user, {})


# ---- Audit -------------------------------------------------------------
class Audit:
    def __init__(self):
        self.entries = []

    def log(self, task, skill_name, tool_calls, result=None, error=None):
        self.entries.append({
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "task": task, "skill": skill_name, "tool_calls": tool_calls,
            "result": result, "error": error,
        })


# ---- Skills --------------------------------------------------------------
class SummarizeNotesSkill:
    def __init__(self, memory_scope):
        self.memory_scope = memory_scope
        self.tool_calls = []

    def execute(self, task):
        text = task.get("text", "")
        wc = TOOLS["word_count"](text)
        self.tool_calls.append({"tool": "word_count", "output": wc})
        self.memory_scope["last_note_length"] = wc["count"]
        return f"Summary stub: note has {wc['count']} words."


class DraftEmailSkill:
    CONTACTS = {"Dr. Meena": {"email": "meena@example.edu"}}

    def __init__(self, memory_scope):
        self.memory_scope = memory_scope
        self.tool_calls = []

    def execute(self, task):
        contact = TOOLS["lookup_contact"](task["to"], self.CONTACTS)
        self.tool_calls.append({"tool": "lookup_contact", "output": contact})
        if "error" in contact:
            raise RuntimeError(contact["error"])
        return f"Draft email to {contact['email']}: '{task['subject']}'"


# translate_text is added LATER, post-hoc, to prove the registry pattern.
class TranslateTextSkill:
    def __init__(self, memory_scope):
        self.memory_scope = memory_scope
        self.tool_calls = []

    def execute(self, task):
        # stub translation
        return f"[translated to {task['target_lang']}] {task['text']}"


SKILL_REGISTRY = {
    "summarize_notes": SummarizeNotesSkill,
    "draft_email": DraftEmailSkill,
}


# ---- Runtime core loop (must never change when a skill is added) --------
def select_skill(task):
    return task["skill"]


def run_task(task, user, memory, audit):
    skill_name = select_skill(task)
    skill_cls = SKILL_REGISTRY[skill_name]
    skill = skill_cls(memory.scope(user))
    try:
        result = skill.execute(task)
        audit.log(task, skill_name, skill.tool_calls, result=result)
        return result
    except Exception as e:
        audit.log(task, skill_name, skill.tool_calls, error=str(e))
        raise


# ---- Interface: the only entry point -----------------------------------
def receive_task(task, user, memory, audit):
    return run_task(task, user, memory, audit)


if __name__ == "__main__":
    memory, audit = Memory(), Audit()

    print("=== Successful run: summarize_notes ===")
    result = receive_task(
        {"skill": "summarize_notes", "text": "Agentic AI systems combine goals tools skills memory"},
        user="uday", memory=memory, audit=audit)
    print(result)

    print("\n=== Successful run: draft_email ===")
    result = receive_task(
        {"skill": "draft_email", "to": "Dr. Meena", "subject": "Lab guide review"},
        user="uday", memory=memory, audit=audit)
    print(result)

    print("\n=== Failing run: draft_email to unknown contact ===")
    try:
        receive_task(
            {"skill": "draft_email", "to": "Unknown Person", "subject": "Hello"},
            user="uday", memory=memory, audit=audit)
    except RuntimeError as e:
        print(f"Run failed as expected: {e}")

    print("\n=== Register a THIRD skill with ZERO changes to run_task/select_skill ===")
    SKILL_REGISTRY["translate_text"] = TranslateTextSkill
    result = receive_task(
        {"skill": "translate_text", "text": "Hello, team", "target_lang": "Kannada"},
        user="uday", memory=memory, audit=audit)
    print(result)

    print("\n=== Full audit log ===")
    for e in audit.entries:
        print(e)

    print("\n=== Scoped memory for user 'uday' ===")
    print(memory.scope("uday"))
```

### Captured output

```text
=== Successful run: summarize_notes ===
Summary stub: note has 8 words.

=== Successful run: draft_email ===
Draft email to meena@example.edu: 'Lab guide review'

=== Failing run: draft_email to unknown contact ===
Run failed as expected: no contact found for Unknown Person

=== Register a THIRD skill with ZERO changes to run_task/select_skill ===
[translated to Kannada] Hello, team

=== Full audit log ===
{'timestamp': '2026-11-15T08:04:41', 'task': {'skill': 'summarize_notes', 'text': 'Agentic AI systems combine goals tools skills memory'}, 'skill': 'summarize_notes', 'tool_calls': [{'tool': 'word_count', 'output': {'count': 8}}], 'result': 'Summary stub: note has 8 words.', 'error': None}
{'timestamp': '2026-11-15T08:04:41', 'task': {'skill': 'draft_email', 'to': 'Dr. Meena', 'subject': 'Lab guide review'}, 'skill': 'draft_email', 'tool_calls': [{'tool': 'lookup_contact', 'output': {'email': 'meena@example.edu'}}], 'result': "Draft email to meena@example.edu: 'Lab guide review'", 'error': None}
{'timestamp': '2026-11-15T08:04:41', 'task': {'skill': 'draft_email', 'to': 'Unknown Person', 'subject': 'Hello'}, 'skill': 'draft_email', 'tool_calls': [{'tool': 'lookup_contact', 'output': {'error': 'no contact found for Unknown Person'}}], 'result': None, 'error': 'no contact found for Unknown Person'}
{'timestamp': '2026-11-15T08:04:41', 'task': {'skill': 'translate_text', 'text': 'Hello, team', 'target_lang': 'Kannada'}, 'skill': 'translate_text', 'tool_calls': [], 'result': '[translated to Kannada] Hello, team', 'error': None}

=== Scoped memory for user 'uday' ===
{'last_note_length': 8}
```

## Assignment 1 source and captured output

Run from the repository root with `python labs/lab_06/assignment_1.py`.

### Full source

```python
# SRN 02FE23BCI038 | Lab 6: OpenCLA/OpenClaw Runtime | assignment_1
# Original definitions retained below; extensions follow.
"""
Lab 6: OpenCLA/OpenClaw-Style Runtime -- Mini Personal Agent Runtime
Six components: interface, runtime loop, skill registry, tools,
scoped memory, audit log. A new skill can be registered without any
change to the core loop.
"""
from datetime import datetime


# ---- Tools ------------------------------------------------------------
def tool_word_count(text):
    return {"count": len(text.split())}


def tool_lookup_contact(name, contacts_db):
    return contacts_db.get(name, {"error": f"no contact found for {name}"})


TOOLS = {"word_count": tool_word_count, "lookup_contact": tool_lookup_contact}


# ---- Memory, scoped per user -------------------------------------------
class Memory:
    def __init__(self):
        self._store = {}

    def scope(self, user):
        return self._store.setdefault(user, {})


# ---- Audit -------------------------------------------------------------
class Audit:
    def __init__(self):
        self.entries = []

    def log(self, task, skill_name, tool_calls, result=None, error=None):
        self.entries.append({
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "task": task, "skill": skill_name, "tool_calls": tool_calls,
            "result": result, "error": error,
        })


# ---- Skills --------------------------------------------------------------
class SummarizeNotesSkill:
    def __init__(self, memory_scope):
        self.memory_scope = memory_scope
        self.tool_calls = []

    def execute(self, task):
        text = task.get("text", "")
        wc = TOOLS["word_count"](text)
        self.tool_calls.append({"tool": "word_count", "output": wc})
        self.memory_scope["last_note_length"] = wc["count"]
        return f"Summary stub: note has {wc['count']} words."


class DraftEmailSkill:
    CONTACTS = {"Dr. Meena": {"email": "meena@example.edu"}}

    def __init__(self, memory_scope):
        self.memory_scope = memory_scope
        self.tool_calls = []

    def execute(self, task):
        contact = TOOLS["lookup_contact"](task["to"], self.CONTACTS)
        self.tool_calls.append({"tool": "lookup_contact", "output": contact})
        if "error" in contact:
            raise RuntimeError(contact["error"])
        return f"Draft email to {contact['email']}: '{task['subject']}'"


# translate_text is added LATER, post-hoc, to prove the registry pattern.
class TranslateTextSkill:
    def __init__(self, memory_scope):
        self.memory_scope = memory_scope
        self.tool_calls = []

    def execute(self, task):
        # stub translation
        return f"[translated to {task['target_lang']}] {task['text']}"


SKILL_REGISTRY = {
    "summarize_notes": SummarizeNotesSkill,
    "draft_email": DraftEmailSkill,
}


# ---- Runtime core loop (must never change when a skill is added) --------
def select_skill(task):
    return task["skill"]


def run_task(task, user, memory, audit):
    skill_name = select_skill(task)
    skill_cls = SKILL_REGISTRY[skill_name]
    skill = skill_cls(memory.scope(user))
    try:
        result = skill.execute(task)
        audit.log(task, skill_name, skill.tool_calls, result=result)
        return result
    except Exception as e:
        audit.log(task, skill_name, skill.tool_calls, error=str(e))
        raise


# ---- Interface: the only entry point -----------------------------------
def receive_task(task, user, memory, audit):
    return run_task(task, user, memory, audit)



A1=True
A2=False

# run_task and its skill dispatch above remain unchanged.
def controlled_receive_task(task,user,memory,audit):
    task={**task,'user':user}
    prior=[e for e in audit.entries if e['task'].get('user')==user]
    failures=[e for e in prior if e['skill']==task['skill'] and e['error']]
    if A2 and len(failures)>=2:
        return {'status':'escalated_to_human','user':user,'skill':task['skill'],'reason':'two prior errors; third skill attempt blocked'}
    attempts=sum(e.get('event')=='admitted' for e in prior)
    if A1 and attempts>=3:
        return {'status':'rate_limited','user':user,'reason':'maximum 3 tasks per session'}
    audit.entries.append({'task':task,'skill':task['skill'],'error':None,'event':'admitted'})
    try: return receive_task(task,user,memory,audit)
    except RuntimeError as e: return {'status':'error','reason':str(e)}
def demo():
    m,a=Memory(),Audit()
    if A1:
        for i in range(4):
            r=controlled_receive_task({'skill':'summarize_notes','text':'Agent loops use tools'},'limit_user',m,a);print('Task',i+1,r)
        assert r['status']=='rate_limited'
        print('Independent user:',controlled_receive_task({'skill':'summarize_notes','text':'Hello'},'other',m,a))
    if A2:
        for i in range(3):
            r=controlled_receive_task({'skill':'draft_email','to':'Unknown','subject':'Test'},'failure_user',m,a);print('Failure scenario attempt',i+1,r)
        assert r['status']=='escalated_to_human'
        assert sum(bool(e.get('error')) for e in a.entries)==2
    print('Audit:',a.entries)
    print('PASS: interface controls preserve core loop and count failures from audit')

if __name__ == "__main__":
    demo()
```

### Captured output

```text
Task 1 Summary stub: note has 4 words.
Task 2 Summary stub: note has 4 words.
Task 3 Summary stub: note has 4 words.
Task 4 {'status': 'rate_limited', 'user': 'limit_user', 'reason': 'maximum 3 tasks per session'}
Independent user: Summary stub: note has 1 words.
Audit: [{'task': {'skill': 'summarize_notes', 'text': 'Agent loops use tools', 'user': 'limit_user'}, 'skill': 'summarize_notes', 'error': None, 'event': 'admitted'}, {'timestamp': '2026-11-15T08:04:41', 'task': {'skill': 'summarize_notes', 'text': 'Agent loops use tools', 'user': 'limit_user'}, 'skill': 'summarize_notes', 'tool_calls': [{'tool': 'word_count', 'output': {'count': 4}}], 'result': 'Summary stub: note has 4 words.', 'error': None}, {'task': {'skill': 'summarize_notes', 'text': 'Agent loops use tools', 'user': 'limit_user'}, 'skill': 'summarize_notes', 'error': None, 'event': 'admitted'}, {'timestamp': '2026-11-15T08:04:41', 'task': {'skill': 'summarize_notes', 'text': 'Agent loops use tools', 'user': 'limit_user'}, 'skill': 'summarize_notes', 'tool_calls': [{'tool': 'word_count', 'output': {'count': 4}}], 'result': 'Summary stub: note has 4 words.', 'error': None}, {'task': {'skill': 'summarize_notes', 'text': 'Agent loops use tools', 'user': 'limit_user'}, 'skill': 'summarize_notes', 'error': None, 'event': 'admitted'}, {'timestamp': '2026-11-15T08:04:41', 'task': {'skill': 'summarize_notes', 'text': 'Agent loops use tools', 'user': 'limit_user'}, 'skill': 'summarize_notes', 'tool_calls': [{'tool': 'word_count', 'output': {'count': 4}}], 'result': 'Summary stub: note has 4 words.', 'error': None}, {'task': {'skill': 'summarize_notes', 'text': 'Hello', 'user': 'other'}, 'skill': 'summarize_notes', 'error': None, 'event': 'admitted'}, {'timestamp': '2026-11-15T08:04:41', 'task': {'skill': 'summarize_notes', 'text': 'Hello', 'user': 'other'}, 'skill': 'summarize_notes', 'tool_calls': [{'tool': 'word_count', 'output': {'count': 1}}], 'result': 'Summary stub: note has 1 words.', 'error': None}]
PASS: interface controls preserve core loop and count failures from audit
```

## Assignment 2 source and captured output

Run from the repository root with `python labs/lab_06/assignment_2.py`.

### Full source

```python
# SRN 02FE23BCI038 | Lab 6: OpenCLA/OpenClaw Runtime | assignment_2
# Original definitions retained below; extensions follow.
"""
Lab 6: OpenCLA/OpenClaw-Style Runtime -- Mini Personal Agent Runtime
Six components: interface, runtime loop, skill registry, tools,
scoped memory, audit log. A new skill can be registered without any
change to the core loop.
"""
from datetime import datetime


# ---- Tools ------------------------------------------------------------
def tool_word_count(text):
    return {"count": len(text.split())}


def tool_lookup_contact(name, contacts_db):
    return contacts_db.get(name, {"error": f"no contact found for {name}"})


TOOLS = {"word_count": tool_word_count, "lookup_contact": tool_lookup_contact}


# ---- Memory, scoped per user -------------------------------------------
class Memory:
    def __init__(self):
        self._store = {}

    def scope(self, user):
        return self._store.setdefault(user, {})


# ---- Audit -------------------------------------------------------------
class Audit:
    def __init__(self):
        self.entries = []

    def log(self, task, skill_name, tool_calls, result=None, error=None):
        self.entries.append({
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "task": task, "skill": skill_name, "tool_calls": tool_calls,
            "result": result, "error": error,
        })


# ---- Skills --------------------------------------------------------------
class SummarizeNotesSkill:
    def __init__(self, memory_scope):
        self.memory_scope = memory_scope
        self.tool_calls = []

    def execute(self, task):
        text = task.get("text", "")
        wc = TOOLS["word_count"](text)
        self.tool_calls.append({"tool": "word_count", "output": wc})
        self.memory_scope["last_note_length"] = wc["count"]
        return f"Summary stub: note has {wc['count']} words."


class DraftEmailSkill:
    CONTACTS = {"Dr. Meena": {"email": "meena@example.edu"}}

    def __init__(self, memory_scope):
        self.memory_scope = memory_scope
        self.tool_calls = []

    def execute(self, task):
        contact = TOOLS["lookup_contact"](task["to"], self.CONTACTS)
        self.tool_calls.append({"tool": "lookup_contact", "output": contact})
        if "error" in contact:
            raise RuntimeError(contact["error"])
        return f"Draft email to {contact['email']}: '{task['subject']}'"


# translate_text is added LATER, post-hoc, to prove the registry pattern.
class TranslateTextSkill:
    def __init__(self, memory_scope):
        self.memory_scope = memory_scope
        self.tool_calls = []

    def execute(self, task):
        # stub translation
        return f"[translated to {task['target_lang']}] {task['text']}"


SKILL_REGISTRY = {
    "summarize_notes": SummarizeNotesSkill,
    "draft_email": DraftEmailSkill,
}


# ---- Runtime core loop (must never change when a skill is added) --------
def select_skill(task):
    return task["skill"]


def run_task(task, user, memory, audit):
    skill_name = select_skill(task)
    skill_cls = SKILL_REGISTRY[skill_name]
    skill = skill_cls(memory.scope(user))
    try:
        result = skill.execute(task)
        audit.log(task, skill_name, skill.tool_calls, result=result)
        return result
    except Exception as e:
        audit.log(task, skill_name, skill.tool_calls, error=str(e))
        raise


# ---- Interface: the only entry point -----------------------------------
def receive_task(task, user, memory, audit):
    return run_task(task, user, memory, audit)



A1=False
A2=True

# run_task and its skill dispatch above remain unchanged.
def controlled_receive_task(task,user,memory,audit):
    task={**task,'user':user}
    prior=[e for e in audit.entries if e['task'].get('user')==user]
    failures=[e for e in prior if e['skill']==task['skill'] and e['error']]
    if A2 and len(failures)>=2:
        return {'status':'escalated_to_human','user':user,'skill':task['skill'],'reason':'two prior errors; third skill attempt blocked'}
    attempts=sum(e.get('event')=='admitted' for e in prior)
    if A1 and attempts>=3:
        return {'status':'rate_limited','user':user,'reason':'maximum 3 tasks per session'}
    audit.entries.append({'task':task,'skill':task['skill'],'error':None,'event':'admitted'})
    try: return receive_task(task,user,memory,audit)
    except RuntimeError as e: return {'status':'error','reason':str(e)}
def demo():
    m,a=Memory(),Audit()
    if A1:
        for i in range(4):
            r=controlled_receive_task({'skill':'summarize_notes','text':'Agent loops use tools'},'limit_user',m,a);print('Task',i+1,r)
        assert r['status']=='rate_limited'
        print('Independent user:',controlled_receive_task({'skill':'summarize_notes','text':'Hello'},'other',m,a))
    if A2:
        for i in range(3):
            r=controlled_receive_task({'skill':'draft_email','to':'Unknown','subject':'Test'},'failure_user',m,a);print('Failure scenario attempt',i+1,r)
        assert r['status']=='escalated_to_human'
        assert sum(bool(e.get('error')) for e in a.entries)==2
    print('Audit:',a.entries)
    print('PASS: interface controls preserve core loop and count failures from audit')

if __name__ == "__main__":
    demo()
```

### Captured output

```text
Failure scenario attempt 1 {'status': 'error', 'reason': 'no contact found for Unknown'}
Failure scenario attempt 2 {'status': 'error', 'reason': 'no contact found for Unknown'}
Failure scenario attempt 3 {'status': 'escalated_to_human', 'user': 'failure_user', 'skill': 'draft_email', 'reason': 'two prior errors; third skill attempt blocked'}
Audit: [{'task': {'skill': 'draft_email', 'to': 'Unknown', 'subject': 'Test', 'user': 'failure_user'}, 'skill': 'draft_email', 'error': None, 'event': 'admitted'}, {'timestamp': '2026-11-15T08:04:41', 'task': {'skill': 'draft_email', 'to': 'Unknown', 'subject': 'Test', 'user': 'failure_user'}, 'skill': 'draft_email', 'tool_calls': [{'tool': 'lookup_contact', 'output': {'error': 'no contact found for Unknown'}}], 'result': None, 'error': 'no contact found for Unknown'}, {'task': {'skill': 'draft_email', 'to': 'Unknown', 'subject': 'Test', 'user': 'failure_user'}, 'skill': 'draft_email', 'error': None, 'event': 'admitted'}, {'timestamp': '2026-11-15T08:04:41', 'task': {'skill': 'draft_email', 'to': 'Unknown', 'subject': 'Test', 'user': 'failure_user'}, 'skill': 'draft_email', 'tool_calls': [{'tool': 'lookup_contact', 'output': {'error': 'no contact found for Unknown'}}], 'result': None, 'error': 'no contact found for Unknown'}]
PASS: interface controls preserve core loop and count failures from audit
```

## Combined source and captured output

Run from the repository root with `python labs/lab_06/combined.py`.

### Full source

```python
# SRN 02FE23BCI038 | Lab 6: OpenCLA/OpenClaw Runtime | combined
# Original definitions retained below; extensions follow.
"""
Lab 6: OpenCLA/OpenClaw-Style Runtime -- Mini Personal Agent Runtime
Six components: interface, runtime loop, skill registry, tools,
scoped memory, audit log. A new skill can be registered without any
change to the core loop.
"""
from datetime import datetime


# ---- Tools ------------------------------------------------------------
def tool_word_count(text):
    return {"count": len(text.split())}


def tool_lookup_contact(name, contacts_db):
    return contacts_db.get(name, {"error": f"no contact found for {name}"})


TOOLS = {"word_count": tool_word_count, "lookup_contact": tool_lookup_contact}


# ---- Memory, scoped per user -------------------------------------------
class Memory:
    def __init__(self):
        self._store = {}

    def scope(self, user):
        return self._store.setdefault(user, {})


# ---- Audit -------------------------------------------------------------
class Audit:
    def __init__(self):
        self.entries = []

    def log(self, task, skill_name, tool_calls, result=None, error=None):
        self.entries.append({
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "task": task, "skill": skill_name, "tool_calls": tool_calls,
            "result": result, "error": error,
        })


# ---- Skills --------------------------------------------------------------
class SummarizeNotesSkill:
    def __init__(self, memory_scope):
        self.memory_scope = memory_scope
        self.tool_calls = []

    def execute(self, task):
        text = task.get("text", "")
        wc = TOOLS["word_count"](text)
        self.tool_calls.append({"tool": "word_count", "output": wc})
        self.memory_scope["last_note_length"] = wc["count"]
        return f"Summary stub: note has {wc['count']} words."


class DraftEmailSkill:
    CONTACTS = {"Dr. Meena": {"email": "meena@example.edu"}}

    def __init__(self, memory_scope):
        self.memory_scope = memory_scope
        self.tool_calls = []

    def execute(self, task):
        contact = TOOLS["lookup_contact"](task["to"], self.CONTACTS)
        self.tool_calls.append({"tool": "lookup_contact", "output": contact})
        if "error" in contact:
            raise RuntimeError(contact["error"])
        return f"Draft email to {contact['email']}: '{task['subject']}'"


# translate_text is added LATER, post-hoc, to prove the registry pattern.
class TranslateTextSkill:
    def __init__(self, memory_scope):
        self.memory_scope = memory_scope
        self.tool_calls = []

    def execute(self, task):
        # stub translation
        return f"[translated to {task['target_lang']}] {task['text']}"


SKILL_REGISTRY = {
    "summarize_notes": SummarizeNotesSkill,
    "draft_email": DraftEmailSkill,
}


# ---- Runtime core loop (must never change when a skill is added) --------
def select_skill(task):
    return task["skill"]


def run_task(task, user, memory, audit):
    skill_name = select_skill(task)
    skill_cls = SKILL_REGISTRY[skill_name]
    skill = skill_cls(memory.scope(user))
    try:
        result = skill.execute(task)
        audit.log(task, skill_name, skill.tool_calls, result=result)
        return result
    except Exception as e:
        audit.log(task, skill_name, skill.tool_calls, error=str(e))
        raise


# ---- Interface: the only entry point -----------------------------------
def receive_task(task, user, memory, audit):
    return run_task(task, user, memory, audit)



A1=True
A2=True

# run_task and its skill dispatch above remain unchanged.
def controlled_receive_task(task,user,memory,audit):
    task={**task,'user':user}
    prior=[e for e in audit.entries if e['task'].get('user')==user]
    failures=[e for e in prior if e['skill']==task['skill'] and e['error']]
    if A2 and len(failures)>=2:
        return {'status':'escalated_to_human','user':user,'skill':task['skill'],'reason':'two prior errors; third skill attempt blocked'}
    attempts=sum(e.get('event')=='admitted' for e in prior)
    if A1 and attempts>=3:
        return {'status':'rate_limited','user':user,'reason':'maximum 3 tasks per session'}
    audit.entries.append({'task':task,'skill':task['skill'],'error':None,'event':'admitted'})
    try: return receive_task(task,user,memory,audit)
    except RuntimeError as e: return {'status':'error','reason':str(e)}
def demo():
    m,a=Memory(),Audit()
    if A1:
        for i in range(4):
            r=controlled_receive_task({'skill':'summarize_notes','text':'Agent loops use tools'},'limit_user',m,a);print('Task',i+1,r)
        assert r['status']=='rate_limited'
        print('Independent user:',controlled_receive_task({'skill':'summarize_notes','text':'Hello'},'other',m,a))
    if A2:
        for i in range(3):
            r=controlled_receive_task({'skill':'draft_email','to':'Unknown','subject':'Test'},'failure_user',m,a);print('Failure scenario attempt',i+1,r)
        assert r['status']=='escalated_to_human'
        assert sum(bool(e.get('error')) for e in a.entries)==2
    print('Audit:',a.entries)
    print('PASS: interface controls preserve core loop and count failures from audit')

if __name__ == "__main__":
    demo()
```

### Captured output

```text
Task 1 Summary stub: note has 4 words.
Task 2 Summary stub: note has 4 words.
Task 3 Summary stub: note has 4 words.
Task 4 {'status': 'rate_limited', 'user': 'limit_user', 'reason': 'maximum 3 tasks per session'}
Independent user: Summary stub: note has 1 words.
Failure scenario attempt 1 {'status': 'error', 'reason': 'no contact found for Unknown'}
Failure scenario attempt 2 {'status': 'error', 'reason': 'no contact found for Unknown'}
Failure scenario attempt 3 {'status': 'escalated_to_human', 'user': 'failure_user', 'skill': 'draft_email', 'reason': 'two prior errors; third skill attempt blocked'}
Audit: [{'task': {'skill': 'summarize_notes', 'text': 'Agent loops use tools', 'user': 'limit_user'}, 'skill': 'summarize_notes', 'error': None, 'event': 'admitted'}, {'timestamp': '2026-11-15T08:04:41', 'task': {'skill': 'summarize_notes', 'text': 'Agent loops use tools', 'user': 'limit_user'}, 'skill': 'summarize_notes', 'tool_calls': [{'tool': 'word_count', 'output': {'count': 4}}], 'result': 'Summary stub: note has 4 words.', 'error': None}, {'task': {'skill': 'summarize_notes', 'text': 'Agent loops use tools', 'user': 'limit_user'}, 'skill': 'summarize_notes', 'error': None, 'event': 'admitted'}, {'timestamp': '2026-11-15T08:04:41', 'task': {'skill': 'summarize_notes', 'text': 'Agent loops use tools', 'user': 'limit_user'}, 'skill': 'summarize_notes', 'tool_calls': [{'tool': 'word_count', 'output': {'count': 4}}], 'result': 'Summary stub: note has 4 words.', 'error': None}, {'task': {'skill': 'summarize_notes', 'text': 'Agent loops use tools', 'user': 'limit_user'}, 'skill': 'summarize_notes', 'error': None, 'event': 'admitted'}, {'timestamp': '2026-11-15T08:04:41', 'task': {'skill': 'summarize_notes', 'text': 'Agent loops use tools', 'user': 'limit_user'}, 'skill': 'summarize_notes', 'tool_calls': [{'tool': 'word_count', 'output': {'count': 4}}], 'result': 'Summary stub: note has 4 words.', 'error': None}, {'task': {'skill': 'summarize_notes', 'text': 'Hello', 'user': 'other'}, 'skill': 'summarize_notes', 'error': None, 'event': 'admitted'}, {'timestamp': '2026-11-15T08:04:41', 'task': {'skill': 'summarize_notes', 'text': 'Hello', 'user': 'other'}, 'skill': 'summarize_notes', 'tool_calls': [{'tool': 'word_count', 'output': {'count': 1}}], 'result': 'Summary stub: note has 1 words.', 'error': None}, {'task': {'skill': 'draft_email', 'to': 'Unknown', 'subject': 'Test', 'user': 'failure_user'}, 'skill': 'draft_email', 'error': None, 'event': 'admitted'}, {'timestamp': '2026-11-15T08:04:41', 'task': {'skill': 'draft_email', 'to': 'Unknown', 'subject': 'Test', 'user': 'failure_user'}, 'skill': 'draft_email', 'tool_calls': [{'tool': 'lookup_contact', 'output': {'error': 'no contact found for Unknown'}}], 'result': None, 'error': 'no contact found for Unknown'}, {'task': {'skill': 'draft_email', 'to': 'Unknown', 'subject': 'Test', 'user': 'failure_user'}, 'skill': 'draft_email', 'error': None, 'event': 'admitted'}, {'timestamp': '2026-11-15T08:04:41', 'task': {'skill': 'draft_email', 'to': 'Unknown', 'subject': 'Test', 'user': 'failure_user'}, 'skill': 'draft_email', 'tool_calls': [{'tool': 'lookup_contact', 'output': {'error': 'no contact found for Unknown'}}], 'result': None, 'error': 'no contact found for Unknown'}]
PASS: interface controls preserve core loop and count failures from audit
```

