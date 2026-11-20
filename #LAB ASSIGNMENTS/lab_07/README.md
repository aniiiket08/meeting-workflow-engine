# Lab 7: Agentic Node Graph

SRN: **02FE23BCI038**

## Assignment requirements from the guide

Assignment 1 — Add a Security-Scan Node
Insert a new `security_scan` node between `builder` and `tester`, with its own input, output, owner, success criteria, and failure behavior. Update both the success-path and failure-path simulations to include it, and produce a case where the security scan itself is the node that fails.
Assignment 2 — Add a Retry Limit to the Builder Node
Modify the graph so the `builder` node is allowed exactly one retry before escalating to a human. Implement and demonstrate two scenarios: (a) the builder fails once, retries, and succeeds; (b) the builder fails twice and correctly escalates instead of retrying a third time.

## Implementation notes

The security node has an explicit contract and stops downstream testing on failure. Builder attempts are bounded to two total calls when Assignment 2 is enabled.

Each assignment script includes the original definitions plus its own enabled extension. `A1` and `A2` select the assignment features; both are enabled in `combined.py`. These are standalone scripts, so sibling imports are not required. The original guide demonstration is available unchanged as `reference.py`.

## Original source and captured output

Run from the repository root with `python labs/lab_07/reference.py`.

### Full source

```python
"""
Lab 7: Agentic Node Graph -- Campus Event App
Each node declares input, output, owner, success criteria, and failure
behavior. The graph is simulated once on a success path and once with
a deliberate failure to exercise the failure behavior.
"""

class Node:
    def __init__(self, name, owner, success_fn, on_success, on_fail):
        self.name = name
        self.owner = owner
        self.success_fn = success_fn      # state -> bool
        self.on_success = on_success       # state -> state (next stage's input)
        self.on_fail = on_fail             # description of failure behavior


def requirement_node(state):
    state["requirements"] = ["user login", "event listing", "RSVP button"]
    return state


def planner_node(state):
    state["tasks"] = {req: f"task_for({req})" for req in state["requirements"]}
    return state


def builder_node(state):
    if state.get("force_build_fail"):
        state["build_ok"] = False
        return state
    state["build_ok"] = True
    state["code"] = "app.py generated"
    return state


def tester_node(state):
    state["tests_passed"] = state.get("build_ok", False)
    return state


def reviewer_node(state):
    state["review_clean"] = state.get("tests_passed", False)
    return state


def human_gate_node(state):
    state["human_signoff"] = state.get("review_clean", False)
    return state


GRAPH = [
    Node("requirement", "requirement_agent",
         lambda s: len(s.get("requirements", [])) >= 3,
         requirement_node,
         "escalate_to_human('goal too vague to extract 3+ requirements')"),
    Node("planner", "planner_agent",
         lambda s: all(r in s.get("tasks", {}) for r in s.get("requirements", [])),
         planner_node,
         "return_to('requirement')"),
    Node("builder", "builder_agent",
         lambda s: s.get("build_ok", False),
         builder_node,
         "retry_build_or_escalate"),
    Node("tester", "tester_agent",
         lambda s: s.get("tests_passed", False),
         tester_node,
         "route_back_to('builder')"),
    Node("reviewer", "reviewer_agent",
         lambda s: s.get("review_clean", False),
         reviewer_node,
         "route_back_to('builder')"),
    Node("human_gate", "human",
         lambda s: s.get("human_signoff", False),
         human_gate_node,
         "return_to('planner', reason=human.notes)"),
]


def simulate(force_build_fail=False):
    state = {"force_build_fail": force_build_fail}
    trace = []
    for node in GRAPH:
        state = node.on_success(state)
        ok = node.success_fn(state)
        trace.append({"node": node.name, "owner": node.owner, "success": ok,
                      "state_after": {k: v for k, v in state.items() if k != "force_build_fail"}})
        if not ok:
            trace.append({"node": node.name, "failure_behavior_triggered": node.on_fail})
            break
    return trace


if __name__ == "__main__":
    print("=== SUCCESS PATH ===")
    for step in simulate(force_build_fail=False):
        print(step)

    print("\n=== FAILURE PATH (builder fails) ===")
    for step in simulate(force_build_fail=True):
        print(step)
```

### Captured output

```text
=== SUCCESS PATH ===
{'node': 'requirement', 'owner': 'requirement_agent', 'success': True, 'state_after': {'requirements': ['user login', 'event listing', 'RSVP button']}}
{'node': 'planner', 'owner': 'planner_agent', 'success': True, 'state_after': {'requirements': ['user login', 'event listing', 'RSVP button'], 'tasks': {'user login': 'task_for(user login)', 'event listing': 'task_for(event listing)', 'RSVP button': 'task_for(RSVP button)'}}}
{'node': 'builder', 'owner': 'builder_agent', 'success': True, 'state_after': {'requirements': ['user login', 'event listing', 'RSVP button'], 'tasks': {'user login': 'task_for(user login)', 'event listing': 'task_for(event listing)', 'RSVP button': 'task_for(RSVP button)'}, 'build_ok': True, 'code': 'app.py generated'}}
{'node': 'tester', 'owner': 'tester_agent', 'success': True, 'state_after': {'requirements': ['user login', 'event listing', 'RSVP button'], 'tasks': {'user login': 'task_for(user login)', 'event listing': 'task_for(event listing)', 'RSVP button': 'task_for(RSVP button)'}, 'build_ok': True, 'code': 'app.py generated', 'tests_passed': True}}
{'node': 'reviewer', 'owner': 'reviewer_agent', 'success': True, 'state_after': {'requirements': ['user login', 'event listing', 'RSVP button'], 'tasks': {'user login': 'task_for(user login)', 'event listing': 'task_for(event listing)', 'RSVP button': 'task_for(RSVP button)'}, 'build_ok': True, 'code': 'app.py generated', 'tests_passed': True, 'review_clean': True}}
{'node': 'human_gate', 'owner': 'human', 'success': True, 'state_after': {'requirements': ['user login', 'event listing', 'RSVP button'], 'tasks': {'user login': 'task_for(user login)', 'event listing': 'task_for(event listing)', 'RSVP button': 'task_for(RSVP button)'}, 'build_ok': True, 'code': 'app.py generated', 'tests_passed': True, 'review_clean': True, 'human_signoff': True}}

=== FAILURE PATH (builder fails) ===
{'node': 'requirement', 'owner': 'requirement_agent', 'success': True, 'state_after': {'requirements': ['user login', 'event listing', 'RSVP button']}}
{'node': 'planner', 'owner': 'planner_agent', 'success': True, 'state_after': {'requirements': ['user login', 'event listing', 'RSVP button'], 'tasks': {'user login': 'task_for(user login)', 'event listing': 'task_for(event listing)', 'RSVP button': 'task_for(RSVP button)'}}}
{'node': 'builder', 'owner': 'builder_agent', 'success': False, 'state_after': {'requirements': ['user login', 'event listing', 'RSVP button'], 'tasks': {'user login': 'task_for(user login)', 'event listing': 'task_for(event listing)', 'RSVP button': 'task_for(RSVP button)'}, 'build_ok': False}}
{'node': 'builder', 'failure_behavior_triggered': 'retry_build_or_escalate'}
```

## Assignment 1 source and captured output

Run from the repository root with `python labs/lab_07/assignment_1.py`.

### Full source

```python
# SRN 02FE23BCI038 | Lab 7: Agentic Node Graph | assignment_1
# Original definitions retained below; extensions follow.
"""
Lab 7: Agentic Node Graph -- Campus Event App
Each node declares input, output, owner, success criteria, and failure
behavior. The graph is simulated once on a success path and once with
a deliberate failure to exercise the failure behavior.
"""

class Node:
    def __init__(self, name, owner, success_fn, on_success, on_fail):
        self.name = name
        self.owner = owner
        self.success_fn = success_fn      # state -> bool
        self.on_success = on_success       # state -> state (next stage's input)
        self.on_fail = on_fail             # description of failure behavior


def requirement_node(state):
    state["requirements"] = ["user login", "event listing", "RSVP button"]
    return state


def planner_node(state):
    state["tasks"] = {req: f"task_for({req})" for req in state["requirements"]}
    return state


def builder_node(state):
    if state.get("force_build_fail"):
        state["build_ok"] = False
        return state
    state["build_ok"] = True
    state["code"] = "app.py generated"
    return state


def tester_node(state):
    state["tests_passed"] = state.get("build_ok", False)
    return state


def reviewer_node(state):
    state["review_clean"] = state.get("tests_passed", False)
    return state


def human_gate_node(state):
    state["human_signoff"] = state.get("review_clean", False)
    return state


GRAPH = [
    Node("requirement", "requirement_agent",
         lambda s: len(s.get("requirements", [])) >= 3,
         requirement_node,
         "escalate_to_human('goal too vague to extract 3+ requirements')"),
    Node("planner", "planner_agent",
         lambda s: all(r in s.get("tasks", {}) for r in s.get("requirements", [])),
         planner_node,
         "return_to('requirement')"),
    Node("builder", "builder_agent",
         lambda s: s.get("build_ok", False),
         builder_node,
         "retry_build_or_escalate"),
    Node("tester", "tester_agent",
         lambda s: s.get("tests_passed", False),
         tester_node,
         "route_back_to('builder')"),
    Node("reviewer", "reviewer_agent",
         lambda s: s.get("review_clean", False),
         reviewer_node,
         "route_back_to('builder')"),
    Node("human_gate", "human",
         lambda s: s.get("human_signoff", False),
         human_gate_node,
         "return_to('planner', reason=human.notes)"),
]


def simulate(force_build_fail=False):
    state = {"force_build_fail": force_build_fail}
    trace = []
    for node in GRAPH:
        state = node.on_success(state)
        ok = node.success_fn(state)
        trace.append({"node": node.name, "owner": node.owner, "success": ok,
                      "state_after": {k: v for k, v in state.items() if k != "force_build_fail"}})
        if not ok:
            trace.append({"node": node.name, "failure_behavior_triggered": node.on_fail})
            break
    return trace



A1=True
A2=False

def security_scan_node(state):
    state['security_ok']=not state.get('force_security_fail',False)
    state['security_findings']=[] if state['security_ok'] else ['unsafe generated dependency']
    return state
SECURITY_CONTRACT={'input':'generated code and dependencies','output':'security_ok and findings','owner':'security_agent','success':'no blocking findings','failure':'stop and return to builder'}
if A1:
    GRAPH.insert(3,Node('security_scan','security_agent',lambda s:s.get('security_ok',False),security_scan_node,'stop_and_return_to_builder'))
def extended_simulate(build_failures=0,scan_fail=False):
    state={'force_security_fail':scan_fail};trace=[]
    for node in GRAPH:
        maximum=2 if A2 and node.name=='builder' else 1
        for attempt in range(1,maximum+1):
            if node.name=='builder': state['force_build_fail']=attempt<=build_failures
            state=node.on_success(state);ok=node.success_fn(state)
            trace.append({'node':node.name,'owner':node.owner,'attempt':attempt,'success':ok})
            if ok: break
        if not ok:
            trace.append({'failure':node.on_fail,'escalated_to_human':node.name=='builder','attempts':attempt})
            return trace
    return trace

def demo():
    if A1: print('Security contract:',SECURITY_CONTRACT)
    print('SUCCESS PATH:',extended_simulate())
    print('BUILDER FAILURE:',extended_simulate(build_failures=2))
    if A1:
        trace=extended_simulate(scan_fail=True);print('SCAN FAILURE:',trace)
        assert any(t.get('node')=='security_scan' and t.get('success') is False for t in trace)
        assert not any(t.get('node')=='tester' for t in trace)
    if A2:
        recovery=extended_simulate(build_failures=1);failure=extended_simulate(build_failures=2)
        print('ONE RETRY RECOVERS:',recovery);print('TWO FAILURES ESCALATE:',failure)
        assert recovery[-1]['success'] and failure[-1]['escalated_to_human']
        assert len([t for t in failure if t.get('node')=='builder'])==2
    print('PASS: security node and bounded builder retry')

if __name__ == "__main__":
    demo()
```

### Captured output

```text
Security contract: {'input': 'generated code and dependencies', 'output': 'security_ok and findings', 'owner': 'security_agent', 'success': 'no blocking findings', 'failure': 'stop and return to builder'}
SUCCESS PATH: [{'node': 'requirement', 'owner': 'requirement_agent', 'attempt': 1, 'success': True}, {'node': 'planner', 'owner': 'planner_agent', 'attempt': 1, 'success': True}, {'node': 'builder', 'owner': 'builder_agent', 'attempt': 1, 'success': True}, {'node': 'security_scan', 'owner': 'security_agent', 'attempt': 1, 'success': True}, {'node': 'tester', 'owner': 'tester_agent', 'attempt': 1, 'success': True}, {'node': 'reviewer', 'owner': 'reviewer_agent', 'attempt': 1, 'success': True}, {'node': 'human_gate', 'owner': 'human', 'attempt': 1, 'success': True}]
BUILDER FAILURE: [{'node': 'requirement', 'owner': 'requirement_agent', 'attempt': 1, 'success': True}, {'node': 'planner', 'owner': 'planner_agent', 'attempt': 1, 'success': True}, {'node': 'builder', 'owner': 'builder_agent', 'attempt': 1, 'success': False}, {'failure': 'retry_build_or_escalate', 'escalated_to_human': True, 'attempts': 1}]
SCAN FAILURE: [{'node': 'requirement', 'owner': 'requirement_agent', 'attempt': 1, 'success': True}, {'node': 'planner', 'owner': 'planner_agent', 'attempt': 1, 'success': True}, {'node': 'builder', 'owner': 'builder_agent', 'attempt': 1, 'success': True}, {'node': 'security_scan', 'owner': 'security_agent', 'attempt': 1, 'success': False}, {'failure': 'stop_and_return_to_builder', 'escalated_to_human': False, 'attempts': 1}]
PASS: security node and bounded builder retry
```

## Assignment 2 source and captured output

Run from the repository root with `python labs/lab_07/assignment_2.py`.

### Full source

```python
# SRN 02FE23BCI038 | Lab 7: Agentic Node Graph | assignment_2
# Original definitions retained below; extensions follow.
"""
Lab 7: Agentic Node Graph -- Campus Event App
Each node declares input, output, owner, success criteria, and failure
behavior. The graph is simulated once on a success path and once with
a deliberate failure to exercise the failure behavior.
"""

class Node:
    def __init__(self, name, owner, success_fn, on_success, on_fail):
        self.name = name
        self.owner = owner
        self.success_fn = success_fn      # state -> bool
        self.on_success = on_success       # state -> state (next stage's input)
        self.on_fail = on_fail             # description of failure behavior


def requirement_node(state):
    state["requirements"] = ["user login", "event listing", "RSVP button"]
    return state


def planner_node(state):
    state["tasks"] = {req: f"task_for({req})" for req in state["requirements"]}
    return state


def builder_node(state):
    if state.get("force_build_fail"):
        state["build_ok"] = False
        return state
    state["build_ok"] = True
    state["code"] = "app.py generated"
    return state


def tester_node(state):
    state["tests_passed"] = state.get("build_ok", False)
    return state


def reviewer_node(state):
    state["review_clean"] = state.get("tests_passed", False)
    return state


def human_gate_node(state):
    state["human_signoff"] = state.get("review_clean", False)
    return state


GRAPH = [
    Node("requirement", "requirement_agent",
         lambda s: len(s.get("requirements", [])) >= 3,
         requirement_node,
         "escalate_to_human('goal too vague to extract 3+ requirements')"),
    Node("planner", "planner_agent",
         lambda s: all(r in s.get("tasks", {}) for r in s.get("requirements", [])),
         planner_node,
         "return_to('requirement')"),
    Node("builder", "builder_agent",
         lambda s: s.get("build_ok", False),
         builder_node,
         "retry_build_or_escalate"),
    Node("tester", "tester_agent",
         lambda s: s.get("tests_passed", False),
         tester_node,
         "route_back_to('builder')"),
    Node("reviewer", "reviewer_agent",
         lambda s: s.get("review_clean", False),
         reviewer_node,
         "route_back_to('builder')"),
    Node("human_gate", "human",
         lambda s: s.get("human_signoff", False),
         human_gate_node,
         "return_to('planner', reason=human.notes)"),
]


def simulate(force_build_fail=False):
    state = {"force_build_fail": force_build_fail}
    trace = []
    for node in GRAPH:
        state = node.on_success(state)
        ok = node.success_fn(state)
        trace.append({"node": node.name, "owner": node.owner, "success": ok,
                      "state_after": {k: v for k, v in state.items() if k != "force_build_fail"}})
        if not ok:
            trace.append({"node": node.name, "failure_behavior_triggered": node.on_fail})
            break
    return trace



A1=False
A2=True

def security_scan_node(state):
    state['security_ok']=not state.get('force_security_fail',False)
    state['security_findings']=[] if state['security_ok'] else ['unsafe generated dependency']
    return state
SECURITY_CONTRACT={'input':'generated code and dependencies','output':'security_ok and findings','owner':'security_agent','success':'no blocking findings','failure':'stop and return to builder'}
if A1:
    GRAPH.insert(3,Node('security_scan','security_agent',lambda s:s.get('security_ok',False),security_scan_node,'stop_and_return_to_builder'))
def extended_simulate(build_failures=0,scan_fail=False):
    state={'force_security_fail':scan_fail};trace=[]
    for node in GRAPH:
        maximum=2 if A2 and node.name=='builder' else 1
        for attempt in range(1,maximum+1):
            if node.name=='builder': state['force_build_fail']=attempt<=build_failures
            state=node.on_success(state);ok=node.success_fn(state)
            trace.append({'node':node.name,'owner':node.owner,'attempt':attempt,'success':ok})
            if ok: break
        if not ok:
            trace.append({'failure':node.on_fail,'escalated_to_human':node.name=='builder','attempts':attempt})
            return trace
    return trace

def demo():
    if A1: print('Security contract:',SECURITY_CONTRACT)
    print('SUCCESS PATH:',extended_simulate())
    print('BUILDER FAILURE:',extended_simulate(build_failures=2))
    if A1:
        trace=extended_simulate(scan_fail=True);print('SCAN FAILURE:',trace)
        assert any(t.get('node')=='security_scan' and t.get('success') is False for t in trace)
        assert not any(t.get('node')=='tester' for t in trace)
    if A2:
        recovery=extended_simulate(build_failures=1);failure=extended_simulate(build_failures=2)
        print('ONE RETRY RECOVERS:',recovery);print('TWO FAILURES ESCALATE:',failure)
        assert recovery[-1]['success'] and failure[-1]['escalated_to_human']
        assert len([t for t in failure if t.get('node')=='builder'])==2
    print('PASS: security node and bounded builder retry')

if __name__ == "__main__":
    demo()
```

### Captured output

```text
SUCCESS PATH: [{'node': 'requirement', 'owner': 'requirement_agent', 'attempt': 1, 'success': True}, {'node': 'planner', 'owner': 'planner_agent', 'attempt': 1, 'success': True}, {'node': 'builder', 'owner': 'builder_agent', 'attempt': 1, 'success': True}, {'node': 'tester', 'owner': 'tester_agent', 'attempt': 1, 'success': True}, {'node': 'reviewer', 'owner': 'reviewer_agent', 'attempt': 1, 'success': True}, {'node': 'human_gate', 'owner': 'human', 'attempt': 1, 'success': True}]
BUILDER FAILURE: [{'node': 'requirement', 'owner': 'requirement_agent', 'attempt': 1, 'success': True}, {'node': 'planner', 'owner': 'planner_agent', 'attempt': 1, 'success': True}, {'node': 'builder', 'owner': 'builder_agent', 'attempt': 1, 'success': False}, {'node': 'builder', 'owner': 'builder_agent', 'attempt': 2, 'success': False}, {'failure': 'retry_build_or_escalate', 'escalated_to_human': True, 'attempts': 2}]
ONE RETRY RECOVERS: [{'node': 'requirement', 'owner': 'requirement_agent', 'attempt': 1, 'success': True}, {'node': 'planner', 'owner': 'planner_agent', 'attempt': 1, 'success': True}, {'node': 'builder', 'owner': 'builder_agent', 'attempt': 1, 'success': False}, {'node': 'builder', 'owner': 'builder_agent', 'attempt': 2, 'success': True}, {'node': 'tester', 'owner': 'tester_agent', 'attempt': 1, 'success': True}, {'node': 'reviewer', 'owner': 'reviewer_agent', 'attempt': 1, 'success': True}, {'node': 'human_gate', 'owner': 'human', 'attempt': 1, 'success': True}]
TWO FAILURES ESCALATE: [{'node': 'requirement', 'owner': 'requirement_agent', 'attempt': 1, 'success': True}, {'node': 'planner', 'owner': 'planner_agent', 'attempt': 1, 'success': True}, {'node': 'builder', 'owner': 'builder_agent', 'attempt': 1, 'success': False}, {'node': 'builder', 'owner': 'builder_agent', 'attempt': 2, 'success': False}, {'failure': 'retry_build_or_escalate', 'escalated_to_human': True, 'attempts': 2}]
PASS: security node and bounded builder retry
```

## Combined source and captured output

Run from the repository root with `python labs/lab_07/combined.py`.

### Full source

```python
# SRN 02FE23BCI038 | Lab 7: Agentic Node Graph | combined
# Original definitions retained below; extensions follow.
"""
Lab 7: Agentic Node Graph -- Campus Event App
Each node declares input, output, owner, success criteria, and failure
behavior. The graph is simulated once on a success path and once with
a deliberate failure to exercise the failure behavior.
"""

class Node:
    def __init__(self, name, owner, success_fn, on_success, on_fail):
        self.name = name
        self.owner = owner
        self.success_fn = success_fn      # state -> bool
        self.on_success = on_success       # state -> state (next stage's input)
        self.on_fail = on_fail             # description of failure behavior


def requirement_node(state):
    state["requirements"] = ["user login", "event listing", "RSVP button"]
    return state


def planner_node(state):
    state["tasks"] = {req: f"task_for({req})" for req in state["requirements"]}
    return state


def builder_node(state):
    if state.get("force_build_fail"):
        state["build_ok"] = False
        return state
    state["build_ok"] = True
    state["code"] = "app.py generated"
    return state


def tester_node(state):
    state["tests_passed"] = state.get("build_ok", False)
    return state


def reviewer_node(state):
    state["review_clean"] = state.get("tests_passed", False)
    return state


def human_gate_node(state):
    state["human_signoff"] = state.get("review_clean", False)
    return state


GRAPH = [
    Node("requirement", "requirement_agent",
         lambda s: len(s.get("requirements", [])) >= 3,
         requirement_node,
         "escalate_to_human('goal too vague to extract 3+ requirements')"),
    Node("planner", "planner_agent",
         lambda s: all(r in s.get("tasks", {}) for r in s.get("requirements", [])),
         planner_node,
         "return_to('requirement')"),
    Node("builder", "builder_agent",
         lambda s: s.get("build_ok", False),
         builder_node,
         "retry_build_or_escalate"),
    Node("tester", "tester_agent",
         lambda s: s.get("tests_passed", False),
         tester_node,
         "route_back_to('builder')"),
    Node("reviewer", "reviewer_agent",
         lambda s: s.get("review_clean", False),
         reviewer_node,
         "route_back_to('builder')"),
    Node("human_gate", "human",
         lambda s: s.get("human_signoff", False),
         human_gate_node,
         "return_to('planner', reason=human.notes)"),
]


def simulate(force_build_fail=False):
    state = {"force_build_fail": force_build_fail}
    trace = []
    for node in GRAPH:
        state = node.on_success(state)
        ok = node.success_fn(state)
        trace.append({"node": node.name, "owner": node.owner, "success": ok,
                      "state_after": {k: v for k, v in state.items() if k != "force_build_fail"}})
        if not ok:
            trace.append({"node": node.name, "failure_behavior_triggered": node.on_fail})
            break
    return trace



A1=True
A2=True

def security_scan_node(state):
    state['security_ok']=not state.get('force_security_fail',False)
    state['security_findings']=[] if state['security_ok'] else ['unsafe generated dependency']
    return state
SECURITY_CONTRACT={'input':'generated code and dependencies','output':'security_ok and findings','owner':'security_agent','success':'no blocking findings','failure':'stop and return to builder'}
if A1:
    GRAPH.insert(3,Node('security_scan','security_agent',lambda s:s.get('security_ok',False),security_scan_node,'stop_and_return_to_builder'))
def extended_simulate(build_failures=0,scan_fail=False):
    state={'force_security_fail':scan_fail};trace=[]
    for node in GRAPH:
        maximum=2 if A2 and node.name=='builder' else 1
        for attempt in range(1,maximum+1):
            if node.name=='builder': state['force_build_fail']=attempt<=build_failures
            state=node.on_success(state);ok=node.success_fn(state)
            trace.append({'node':node.name,'owner':node.owner,'attempt':attempt,'success':ok})
            if ok: break
        if not ok:
            trace.append({'failure':node.on_fail,'escalated_to_human':node.name=='builder','attempts':attempt})
            return trace
    return trace

def demo():
    if A1: print('Security contract:',SECURITY_CONTRACT)
    print('SUCCESS PATH:',extended_simulate())
    print('BUILDER FAILURE:',extended_simulate(build_failures=2))
    if A1:
        trace=extended_simulate(scan_fail=True);print('SCAN FAILURE:',trace)
        assert any(t.get('node')=='security_scan' and t.get('success') is False for t in trace)
        assert not any(t.get('node')=='tester' for t in trace)
    if A2:
        recovery=extended_simulate(build_failures=1);failure=extended_simulate(build_failures=2)
        print('ONE RETRY RECOVERS:',recovery);print('TWO FAILURES ESCALATE:',failure)
        assert recovery[-1]['success'] and failure[-1]['escalated_to_human']
        assert len([t for t in failure if t.get('node')=='builder'])==2
    print('PASS: security node and bounded builder retry')

if __name__ == "__main__":
    demo()
```

### Captured output

```text
Security contract: {'input': 'generated code and dependencies', 'output': 'security_ok and findings', 'owner': 'security_agent', 'success': 'no blocking findings', 'failure': 'stop and return to builder'}
SUCCESS PATH: [{'node': 'requirement', 'owner': 'requirement_agent', 'attempt': 1, 'success': True}, {'node': 'planner', 'owner': 'planner_agent', 'attempt': 1, 'success': True}, {'node': 'builder', 'owner': 'builder_agent', 'attempt': 1, 'success': True}, {'node': 'security_scan', 'owner': 'security_agent', 'attempt': 1, 'success': True}, {'node': 'tester', 'owner': 'tester_agent', 'attempt': 1, 'success': True}, {'node': 'reviewer', 'owner': 'reviewer_agent', 'attempt': 1, 'success': True}, {'node': 'human_gate', 'owner': 'human', 'attempt': 1, 'success': True}]
BUILDER FAILURE: [{'node': 'requirement', 'owner': 'requirement_agent', 'attempt': 1, 'success': True}, {'node': 'planner', 'owner': 'planner_agent', 'attempt': 1, 'success': True}, {'node': 'builder', 'owner': 'builder_agent', 'attempt': 1, 'success': False}, {'node': 'builder', 'owner': 'builder_agent', 'attempt': 2, 'success': False}, {'failure': 'retry_build_or_escalate', 'escalated_to_human': True, 'attempts': 2}]
SCAN FAILURE: [{'node': 'requirement', 'owner': 'requirement_agent', 'attempt': 1, 'success': True}, {'node': 'planner', 'owner': 'planner_agent', 'attempt': 1, 'success': True}, {'node': 'builder', 'owner': 'builder_agent', 'attempt': 1, 'success': True}, {'node': 'security_scan', 'owner': 'security_agent', 'attempt': 1, 'success': False}, {'failure': 'stop_and_return_to_builder', 'escalated_to_human': False, 'attempts': 1}]
ONE RETRY RECOVERS: [{'node': 'requirement', 'owner': 'requirement_agent', 'attempt': 1, 'success': True}, {'node': 'planner', 'owner': 'planner_agent', 'attempt': 1, 'success': True}, {'node': 'builder', 'owner': 'builder_agent', 'attempt': 1, 'success': False}, {'node': 'builder', 'owner': 'builder_agent', 'attempt': 2, 'success': True}, {'node': 'security_scan', 'owner': 'security_agent', 'attempt': 1, 'success': True}, {'node': 'tester', 'owner': 'tester_agent', 'attempt': 1, 'success': True}, {'node': 'reviewer', 'owner': 'reviewer_agent', 'attempt': 1, 'success': True}, {'node': 'human_gate', 'owner': 'human', 'attempt': 1, 'success': True}]
TWO FAILURES ESCALATE: [{'node': 'requirement', 'owner': 'requirement_agent', 'attempt': 1, 'success': True}, {'node': 'planner', 'owner': 'planner_agent', 'attempt': 1, 'success': True}, {'node': 'builder', 'owner': 'builder_agent', 'attempt': 1, 'success': False}, {'node': 'builder', 'owner': 'builder_agent', 'attempt': 2, 'success': False}, {'failure': 'retry_build_or_escalate', 'escalated_to_human': True, 'attempts': 2}]
PASS: security node and bounded builder retry
```

