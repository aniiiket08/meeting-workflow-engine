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
