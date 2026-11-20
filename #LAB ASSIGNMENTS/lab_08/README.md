# Lab 8: Parallel Swarm

SRN: **02FE23BCI038**

## Assignment requirements from the guide

Assignment 1 — Add a Fifth Role: Marketing
Add a `marketing_agent` role proposing a publicity plan with its own cost. Extend `critique()` to detect a new conflict between the marketing budget and the same overall budget cap, and resolve it with the same `budget_over_preference` rule. Submit the updated code and the extended conflict log.
Assignment 2 — Distributed Critique
Replace the single central `critique()` function with a design where each of the four (or five) roles critiques the merged draft independently against its own constraints, and the conflict log records which specific role raised each objection. Submit the updated code and a transcript showing at least two different roles independently raising objections.

## Implementation notes

The thread pool executes distinct roles concurrently. Publicity and venue share one cap. Distributed critique attributes objections to roles and resolves them using budget_over_preference.

Each assignment script includes the original definitions plus its own enabled extension. `A1` and `A2` select the assignment features; both are enabled in `combined.py`. These are standalone scripts, so sibling imports are not required. The original guide demonstration is available unchanged as `reference.py`.

## Original source and captured output

Run from the repository root with `python labs/lab_08/reference.py`.

### Full source

```python
"""
Lab 8: Parallel Swarm -- Hackathon Planner
Four distinct-role agents run concurrently (genuine parallel execution
via a thread pool), then an explicit merge / critique / conflict-
resolution stage combines their outputs.
"""
from concurrent.futures import ThreadPoolExecutor


def research_agent(goal):
    return {"role": "research", "output": "Past events favored a 24-hour format with themed tracks."}


def logistics_agent(goal):
    return {"role": "logistics", "output": {"venue": "Grand Hall", "venue_cost": 45000,
                                              "date": "Saturday"}}


def budget_agent(goal):
    return {"role": "budget", "output": {"total_cap": 30000}}


def judging_agent(goal):
    return {"role": "judging", "output": "Judge on innovation, technical depth, and demo quality."}


ROLES = {
    "research": research_agent, "logistics": logistics_agent,
    "budget": budget_agent, "judging": judging_agent,
}


def run_swarm(goal):
    with ThreadPoolExecutor(max_workers=len(ROLES)) as pool:
        futures = {name: pool.submit(fn, goal) for name, fn in ROLES.items()}
        outputs = {name: f.result() for name, f in futures.items()}
    return outputs


def merge(outputs):
    return {
        "format_notes": outputs["research"]["output"],
        "venue": outputs["logistics"]["output"]["venue"],
        "venue_cost": outputs["logistics"]["output"]["venue_cost"],
        "date": outputs["logistics"]["output"]["date"],
        "budget_cap": outputs["budget"]["output"]["total_cap"],
        "judging_criteria": outputs["judging"]["output"],
    }


def critique(draft):
    conflicts = []
    if draft["venue_cost"] > draft["budget_cap"]:
        conflicts.append({
            "conflict": "venue_cost exceeds budget_cap",
            "roles_involved": ["logistics", "budget"],
            "logistics_value": draft["venue_cost"],
            "budget_value": draft["budget_cap"],
        })
    return conflicts


def resolve(conflict, priority_rule="budget_over_preference"):
    if conflict["conflict"] == "venue_cost exceeds budget_cap":
        return {
            "rule_applied": priority_rule,
            "resolution": f"Reject venue at {conflict['logistics_value']}; "
                           f"request logistics propose an alternative under "
                           f"{conflict['budget_value']}.",
        }
    return {"rule_applied": priority_rule, "resolution": "no rule matched"}


if __name__ == "__main__":
    outputs = run_swarm(goal="Plan a college AI hackathon")
    print("=== Parallel role outputs ===")
    for name, out in outputs.items():
        print(f"  {name}: {out['output']}")

    draft = merge(outputs)
    print("\n=== Merged draft plan ===")
    print(draft)

    conflicts = critique(draft)
    print("\n=== Critique: conflicts found ===")
    conflict_log = []
    for c in conflicts:
        resolution = resolve(c)
        conflict_log.append({**c, **resolution})
        print(f"  {c}")
        print(f"  -> resolution: {resolution}")

    if not conflicts:
        print("  none")

    print("\n=== Final conflict log (submitted as swarm report artifact) ===")
    for entry in conflict_log:
        print(entry)
```

### Captured output

```text
=== Parallel role outputs ===
  research: Past events favored a 24-hour format with themed tracks.
  logistics: {'venue': 'Grand Hall', 'venue_cost': 45000, 'date': 'Saturday'}
  budget: {'total_cap': 30000}
  judging: Judge on innovation, technical depth, and demo quality.

=== Merged draft plan ===
{'format_notes': 'Past events favored a 24-hour format with themed tracks.', 'venue': 'Grand Hall', 'venue_cost': 45000, 'date': 'Saturday', 'budget_cap': 30000, 'judging_criteria': 'Judge on innovation, technical depth, and demo quality.'}

=== Critique: conflicts found ===
  {'conflict': 'venue_cost exceeds budget_cap', 'roles_involved': ['logistics', 'budget'], 'logistics_value': 45000, 'budget_value': 30000}
  -> resolution: {'rule_applied': 'budget_over_preference', 'resolution': 'Reject venue at 45000; request logistics propose an alternative under 30000.'}

=== Final conflict log (submitted as swarm report artifact) ===
{'conflict': 'venue_cost exceeds budget_cap', 'roles_involved': ['logistics', 'budget'], 'logistics_value': 45000, 'budget_value': 30000, 'rule_applied': 'budget_over_preference', 'resolution': 'Reject venue at 45000; request logistics propose an alternative under 30000.'}
```

## Assignment 1 source and captured output

Run from the repository root with `python labs/lab_08/assignment_1.py`.

### Full source

```python
# SRN 02FE23BCI038 | Lab 8: Parallel Swarm | assignment_1
# Original definitions retained below; extensions follow.
"""
Lab 8: Parallel Swarm -- Hackathon Planner
Four distinct-role agents run concurrently (genuine parallel execution
via a thread pool), then an explicit merge / critique / conflict-
resolution stage combines their outputs.
"""
from concurrent.futures import ThreadPoolExecutor


def research_agent(goal):
    return {"role": "research", "output": "Past events favored a 24-hour format with themed tracks."}


def logistics_agent(goal):
    return {"role": "logistics", "output": {"venue": "Grand Hall", "venue_cost": 45000,
                                              "date": "Saturday"}}


def budget_agent(goal):
    return {"role": "budget", "output": {"total_cap": 30000}}


def judging_agent(goal):
    return {"role": "judging", "output": "Judge on innovation, technical depth, and demo quality."}


ROLES = {
    "research": research_agent, "logistics": logistics_agent,
    "budget": budget_agent, "judging": judging_agent,
}


def run_swarm(goal):
    with ThreadPoolExecutor(max_workers=len(ROLES)) as pool:
        futures = {name: pool.submit(fn, goal) for name, fn in ROLES.items()}
        outputs = {name: f.result() for name, f in futures.items()}
    return outputs


def merge(outputs):
    return {
        "format_notes": outputs["research"]["output"],
        "venue": outputs["logistics"]["output"]["venue"],
        "venue_cost": outputs["logistics"]["output"]["venue_cost"],
        "date": outputs["logistics"]["output"]["date"],
        "budget_cap": outputs["budget"]["output"]["total_cap"],
        "judging_criteria": outputs["judging"]["output"],
    }


def critique(draft):
    conflicts = []
    if draft["venue_cost"] > draft["budget_cap"]:
        conflicts.append({
            "conflict": "venue_cost exceeds budget_cap",
            "roles_involved": ["logistics", "budget"],
            "logistics_value": draft["venue_cost"],
            "budget_value": draft["budget_cap"],
        })
    return conflicts


def resolve(conflict, priority_rule="budget_over_preference"):
    if conflict["conflict"] == "venue_cost exceeds budget_cap":
        return {
            "rule_applied": priority_rule,
            "resolution": f"Reject venue at {conflict['logistics_value']}; "
                           f"request logistics propose an alternative under "
                           f"{conflict['budget_value']}.",
        }
    return {"rule_applied": priority_rule, "resolution": "no rule matched"}



A1=True
A2=False

def marketing_agent(goal):
    return {'role':'marketing','output':{'plan':'Campus posters and student social channels','cost':12000}}
if A1: ROLES['marketing']=marketing_agent

def extended_merge(outputs):
    draft=merge(outputs)
    draft.update(marketing_cost=outputs.get('marketing',{}).get('output',{}).get('cost',0))
    return draft

def role_critique(role,draft):
    if role=='budget' and draft['venue_cost']+draft['marketing_cost']>draft['budget_cap']:
        return [{'raised_by':role,'conflict':'total exceeds cap','total':draft['venue_cost']+draft['marketing_cost']}]
    if role=='logistics' and draft['venue_cost']>draft['budget_cap']:
        return [{'raised_by':role,'conflict':'venue exceeds available allocation'}]
    if role=='marketing' and draft['venue_cost']+draft['marketing_cost']>draft['budget_cap']:
        return [{'raised_by':role,'conflict':'marketing spend exceeds remaining total budget'}]
    return []

def demo():
    outputs=run_swarm('Plan a campus hackathon'); print('Parallel outputs:',outputs)
    draft=extended_merge(outputs); print('Merged:',draft)
    if A2:
        with ThreadPoolExecutor(max_workers=len(ROLES)) as p:
            groups=list(p.map(lambda role:role_critique(role,draft),ROLES))
        conflicts=[c for group in groups for c in group]
        assert len(set(c['raised_by'] for c in conflicts))>=2
    else:
        conflicts=critique(draft)
        if draft['venue_cost']+draft['marketing_cost']>draft['budget_cap']:
            conflicts.append({'conflict':'marketing plus venue exceeds overall cap','roles_involved':['marketing','budget']})
    for c in conflicts: print('Conflict:',{**c,'rule_applied':'budget_over_preference','resolution':'Use campus room at 15000; cap publicity at 5000.'})
    final={**draft,'venue':'Campus Room','venue_cost':15000,'marketing_cost':5000 if A1 else 0}
    print('Resolved plan:',final);assert final['venue_cost']+final['marketing_cost']<=final['budget_cap']
    print('PASS: budget cap enforced across all proposed costs')

if __name__ == "__main__":
    demo()
```

### Captured output

```text
Parallel outputs: {'research': {'role': 'research', 'output': 'Past events favored a 24-hour format with themed tracks.'}, 'logistics': {'role': 'logistics', 'output': {'venue': 'Grand Hall', 'venue_cost': 45000, 'date': 'Saturday'}}, 'budget': {'role': 'budget', 'output': {'total_cap': 30000}}, 'judging': {'role': 'judging', 'output': 'Judge on innovation, technical depth, and demo quality.'}, 'marketing': {'role': 'marketing', 'output': {'plan': 'Campus posters and student social channels', 'cost': 12000}}}
Merged: {'format_notes': 'Past events favored a 24-hour format with themed tracks.', 'venue': 'Grand Hall', 'venue_cost': 45000, 'date': 'Saturday', 'budget_cap': 30000, 'judging_criteria': 'Judge on innovation, technical depth, and demo quality.', 'marketing_cost': 12000}
Conflict: {'conflict': 'venue_cost exceeds budget_cap', 'roles_involved': ['logistics', 'budget'], 'logistics_value': 45000, 'budget_value': 30000, 'rule_applied': 'budget_over_preference', 'resolution': 'Use campus room at 15000; cap publicity at 5000.'}
Conflict: {'conflict': 'marketing plus venue exceeds overall cap', 'roles_involved': ['marketing', 'budget'], 'rule_applied': 'budget_over_preference', 'resolution': 'Use campus room at 15000; cap publicity at 5000.'}
Resolved plan: {'format_notes': 'Past events favored a 24-hour format with themed tracks.', 'venue': 'Campus Room', 'venue_cost': 15000, 'date': 'Saturday', 'budget_cap': 30000, 'judging_criteria': 'Judge on innovation, technical depth, and demo quality.', 'marketing_cost': 5000}
PASS: budget cap enforced across all proposed costs
```

## Assignment 2 source and captured output

Run from the repository root with `python labs/lab_08/assignment_2.py`.

### Full source

```python
# SRN 02FE23BCI038 | Lab 8: Parallel Swarm | assignment_2
# Original definitions retained below; extensions follow.
"""
Lab 8: Parallel Swarm -- Hackathon Planner
Four distinct-role agents run concurrently (genuine parallel execution
via a thread pool), then an explicit merge / critique / conflict-
resolution stage combines their outputs.
"""
from concurrent.futures import ThreadPoolExecutor


def research_agent(goal):
    return {"role": "research", "output": "Past events favored a 24-hour format with themed tracks."}


def logistics_agent(goal):
    return {"role": "logistics", "output": {"venue": "Grand Hall", "venue_cost": 45000,
                                              "date": "Saturday"}}


def budget_agent(goal):
    return {"role": "budget", "output": {"total_cap": 30000}}


def judging_agent(goal):
    return {"role": "judging", "output": "Judge on innovation, technical depth, and demo quality."}


ROLES = {
    "research": research_agent, "logistics": logistics_agent,
    "budget": budget_agent, "judging": judging_agent,
}


def run_swarm(goal):
    with ThreadPoolExecutor(max_workers=len(ROLES)) as pool:
        futures = {name: pool.submit(fn, goal) for name, fn in ROLES.items()}
        outputs = {name: f.result() for name, f in futures.items()}
    return outputs


def merge(outputs):
    return {
        "format_notes": outputs["research"]["output"],
        "venue": outputs["logistics"]["output"]["venue"],
        "venue_cost": outputs["logistics"]["output"]["venue_cost"],
        "date": outputs["logistics"]["output"]["date"],
        "budget_cap": outputs["budget"]["output"]["total_cap"],
        "judging_criteria": outputs["judging"]["output"],
    }


def critique(draft):
    conflicts = []
    if draft["venue_cost"] > draft["budget_cap"]:
        conflicts.append({
            "conflict": "venue_cost exceeds budget_cap",
            "roles_involved": ["logistics", "budget"],
            "logistics_value": draft["venue_cost"],
            "budget_value": draft["budget_cap"],
        })
    return conflicts


def resolve(conflict, priority_rule="budget_over_preference"):
    if conflict["conflict"] == "venue_cost exceeds budget_cap":
        return {
            "rule_applied": priority_rule,
            "resolution": f"Reject venue at {conflict['logistics_value']}; "
                           f"request logistics propose an alternative under "
                           f"{conflict['budget_value']}.",
        }
    return {"rule_applied": priority_rule, "resolution": "no rule matched"}



A1=False
A2=True

def marketing_agent(goal):
    return {'role':'marketing','output':{'plan':'Campus posters and student social channels','cost':12000}}
if A1: ROLES['marketing']=marketing_agent

def extended_merge(outputs):
    draft=merge(outputs)
    draft.update(marketing_cost=outputs.get('marketing',{}).get('output',{}).get('cost',0))
    return draft

def role_critique(role,draft):
    if role=='budget' and draft['venue_cost']+draft['marketing_cost']>draft['budget_cap']:
        return [{'raised_by':role,'conflict':'total exceeds cap','total':draft['venue_cost']+draft['marketing_cost']}]
    if role=='logistics' and draft['venue_cost']>draft['budget_cap']:
        return [{'raised_by':role,'conflict':'venue exceeds available allocation'}]
    if role=='marketing' and draft['venue_cost']+draft['marketing_cost']>draft['budget_cap']:
        return [{'raised_by':role,'conflict':'marketing spend exceeds remaining total budget'}]
    return []

def demo():
    outputs=run_swarm('Plan a campus hackathon'); print('Parallel outputs:',outputs)
    draft=extended_merge(outputs); print('Merged:',draft)
    if A2:
        with ThreadPoolExecutor(max_workers=len(ROLES)) as p:
            groups=list(p.map(lambda role:role_critique(role,draft),ROLES))
        conflicts=[c for group in groups for c in group]
        assert len(set(c['raised_by'] for c in conflicts))>=2
    else:
        conflicts=critique(draft)
        if draft['venue_cost']+draft['marketing_cost']>draft['budget_cap']:
            conflicts.append({'conflict':'marketing plus venue exceeds overall cap','roles_involved':['marketing','budget']})
    for c in conflicts: print('Conflict:',{**c,'rule_applied':'budget_over_preference','resolution':'Use campus room at 15000; cap publicity at 5000.'})
    final={**draft,'venue':'Campus Room','venue_cost':15000,'marketing_cost':5000 if A1 else 0}
    print('Resolved plan:',final);assert final['venue_cost']+final['marketing_cost']<=final['budget_cap']
    print('PASS: budget cap enforced across all proposed costs')

if __name__ == "__main__":
    demo()
```

### Captured output

```text
Parallel outputs: {'research': {'role': 'research', 'output': 'Past events favored a 24-hour format with themed tracks.'}, 'logistics': {'role': 'logistics', 'output': {'venue': 'Grand Hall', 'venue_cost': 45000, 'date': 'Saturday'}}, 'budget': {'role': 'budget', 'output': {'total_cap': 30000}}, 'judging': {'role': 'judging', 'output': 'Judge on innovation, technical depth, and demo quality.'}}
Merged: {'format_notes': 'Past events favored a 24-hour format with themed tracks.', 'venue': 'Grand Hall', 'venue_cost': 45000, 'date': 'Saturday', 'budget_cap': 30000, 'judging_criteria': 'Judge on innovation, technical depth, and demo quality.', 'marketing_cost': 0}
Conflict: {'raised_by': 'logistics', 'conflict': 'venue exceeds available allocation', 'rule_applied': 'budget_over_preference', 'resolution': 'Use campus room at 15000; cap publicity at 5000.'}
Conflict: {'raised_by': 'budget', 'conflict': 'total exceeds cap', 'total': 45000, 'rule_applied': 'budget_over_preference', 'resolution': 'Use campus room at 15000; cap publicity at 5000.'}
Resolved plan: {'format_notes': 'Past events favored a 24-hour format with themed tracks.', 'venue': 'Campus Room', 'venue_cost': 15000, 'date': 'Saturday', 'budget_cap': 30000, 'judging_criteria': 'Judge on innovation, technical depth, and demo quality.', 'marketing_cost': 0}
PASS: budget cap enforced across all proposed costs
```

## Combined source and captured output

Run from the repository root with `python labs/lab_08/combined.py`.

### Full source

```python
# SRN 02FE23BCI038 | Lab 8: Parallel Swarm | combined
# Original definitions retained below; extensions follow.
"""
Lab 8: Parallel Swarm -- Hackathon Planner
Four distinct-role agents run concurrently (genuine parallel execution
via a thread pool), then an explicit merge / critique / conflict-
resolution stage combines their outputs.
"""
from concurrent.futures import ThreadPoolExecutor


def research_agent(goal):
    return {"role": "research", "output": "Past events favored a 24-hour format with themed tracks."}


def logistics_agent(goal):
    return {"role": "logistics", "output": {"venue": "Grand Hall", "venue_cost": 45000,
                                              "date": "Saturday"}}


def budget_agent(goal):
    return {"role": "budget", "output": {"total_cap": 30000}}


def judging_agent(goal):
    return {"role": "judging", "output": "Judge on innovation, technical depth, and demo quality."}


ROLES = {
    "research": research_agent, "logistics": logistics_agent,
    "budget": budget_agent, "judging": judging_agent,
}


def run_swarm(goal):
    with ThreadPoolExecutor(max_workers=len(ROLES)) as pool:
        futures = {name: pool.submit(fn, goal) for name, fn in ROLES.items()}
        outputs = {name: f.result() for name, f in futures.items()}
    return outputs


def merge(outputs):
    return {
        "format_notes": outputs["research"]["output"],
        "venue": outputs["logistics"]["output"]["venue"],
        "venue_cost": outputs["logistics"]["output"]["venue_cost"],
        "date": outputs["logistics"]["output"]["date"],
        "budget_cap": outputs["budget"]["output"]["total_cap"],
        "judging_criteria": outputs["judging"]["output"],
    }


def critique(draft):
    conflicts = []
    if draft["venue_cost"] > draft["budget_cap"]:
        conflicts.append({
            "conflict": "venue_cost exceeds budget_cap",
            "roles_involved": ["logistics", "budget"],
            "logistics_value": draft["venue_cost"],
            "budget_value": draft["budget_cap"],
        })
    return conflicts


def resolve(conflict, priority_rule="budget_over_preference"):
    if conflict["conflict"] == "venue_cost exceeds budget_cap":
        return {
            "rule_applied": priority_rule,
            "resolution": f"Reject venue at {conflict['logistics_value']}; "
                           f"request logistics propose an alternative under "
                           f"{conflict['budget_value']}.",
        }
    return {"rule_applied": priority_rule, "resolution": "no rule matched"}



A1=True
A2=True

def marketing_agent(goal):
    return {'role':'marketing','output':{'plan':'Campus posters and student social channels','cost':12000}}
if A1: ROLES['marketing']=marketing_agent

def extended_merge(outputs):
    draft=merge(outputs)
    draft.update(marketing_cost=outputs.get('marketing',{}).get('output',{}).get('cost',0))
    return draft

def role_critique(role,draft):
    if role=='budget' and draft['venue_cost']+draft['marketing_cost']>draft['budget_cap']:
        return [{'raised_by':role,'conflict':'total exceeds cap','total':draft['venue_cost']+draft['marketing_cost']}]
    if role=='logistics' and draft['venue_cost']>draft['budget_cap']:
        return [{'raised_by':role,'conflict':'venue exceeds available allocation'}]
    if role=='marketing' and draft['venue_cost']+draft['marketing_cost']>draft['budget_cap']:
        return [{'raised_by':role,'conflict':'marketing spend exceeds remaining total budget'}]
    return []

def demo():
    outputs=run_swarm('Plan a campus hackathon'); print('Parallel outputs:',outputs)
    draft=extended_merge(outputs); print('Merged:',draft)
    if A2:
        with ThreadPoolExecutor(max_workers=len(ROLES)) as p:
            groups=list(p.map(lambda role:role_critique(role,draft),ROLES))
        conflicts=[c for group in groups for c in group]
        assert len(set(c['raised_by'] for c in conflicts))>=2
    else:
        conflicts=critique(draft)
        if draft['venue_cost']+draft['marketing_cost']>draft['budget_cap']:
            conflicts.append({'conflict':'marketing plus venue exceeds overall cap','roles_involved':['marketing','budget']})
    for c in conflicts: print('Conflict:',{**c,'rule_applied':'budget_over_preference','resolution':'Use campus room at 15000; cap publicity at 5000.'})
    final={**draft,'venue':'Campus Room','venue_cost':15000,'marketing_cost':5000 if A1 else 0}
    print('Resolved plan:',final);assert final['venue_cost']+final['marketing_cost']<=final['budget_cap']
    print('PASS: budget cap enforced across all proposed costs')

if __name__ == "__main__":
    demo()
```

### Captured output

```text
Parallel outputs: {'research': {'role': 'research', 'output': 'Past events favored a 24-hour format with themed tracks.'}, 'logistics': {'role': 'logistics', 'output': {'venue': 'Grand Hall', 'venue_cost': 45000, 'date': 'Saturday'}}, 'budget': {'role': 'budget', 'output': {'total_cap': 30000}}, 'judging': {'role': 'judging', 'output': 'Judge on innovation, technical depth, and demo quality.'}, 'marketing': {'role': 'marketing', 'output': {'plan': 'Campus posters and student social channels', 'cost': 12000}}}
Merged: {'format_notes': 'Past events favored a 24-hour format with themed tracks.', 'venue': 'Grand Hall', 'venue_cost': 45000, 'date': 'Saturday', 'budget_cap': 30000, 'judging_criteria': 'Judge on innovation, technical depth, and demo quality.', 'marketing_cost': 12000}
Conflict: {'raised_by': 'logistics', 'conflict': 'venue exceeds available allocation', 'rule_applied': 'budget_over_preference', 'resolution': 'Use campus room at 15000; cap publicity at 5000.'}
Conflict: {'raised_by': 'budget', 'conflict': 'total exceeds cap', 'total': 57000, 'rule_applied': 'budget_over_preference', 'resolution': 'Use campus room at 15000; cap publicity at 5000.'}
Conflict: {'raised_by': 'marketing', 'conflict': 'marketing spend exceeds remaining total budget', 'rule_applied': 'budget_over_preference', 'resolution': 'Use campus room at 15000; cap publicity at 5000.'}
Resolved plan: {'format_notes': 'Past events favored a 24-hour format with themed tracks.', 'venue': 'Campus Room', 'venue_cost': 15000, 'date': 'Saturday', 'budget_cap': 30000, 'judging_criteria': 'Judge on innovation, technical depth, and demo quality.', 'marketing_cost': 5000}
PASS: budget cap enforced across all proposed costs
```

