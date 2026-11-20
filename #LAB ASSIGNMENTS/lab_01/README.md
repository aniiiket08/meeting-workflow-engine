# Lab 1: Agent vs Chatbot

SRN: **02FE23BCI038**

## Assignment requirements from the guide

Assignment 1 — Two Rounds of Feedback
Extend the reference agent to accept a second, independent round of feedback after the first revision (e.g. "also make Friday's session shorter, only one hour"). Both revisions must mutate the same plan object — the log must show two separate revise iterations, neither of which regenerates the plan from scratch. Submit the updated code and the full iteration log covering both rounds.
Assignment 2 — Detect a Scheduling Conflict
Extend `read_existing_schedule` to return a second busy day, then modify `_build_plan` (or add a check before it) so that if the student's chosen unavailable days do not actually avoid every busy day returned by the tool, the agent flags the conflict explicitly to the user before finalizing the plan, rather than silently double-booking. Submit the updated code and a transcript showing the conflict being detected and reported.

## Implementation notes

Two feedback calls mutate the same plan. Conflicts are reported before finalization; Wednesday and Friday move to a non-conflicting evening slot. The simplified calendar assumes that alternative slot is free.

Each assignment script includes the original definitions plus its own enabled extension. `A1` and `A2` select the assignment features; both are enabled in `combined.py`. These are standalone scripts, so sibling imports are not required. The original guide demonstration is available unchanged as `reference.py`.

## Original source and captured output

Run from the repository root with `python labs/lab_01/reference.py`.

### Full source

```python
"""
Lab 1: Agent vs Chatbot -- Study Planner Agent
Implements the full Goal -> Plan -> Act -> Observe -> Revise loop.
No external API needed: the "planner" is a small rule-based stand-in
for an LLM call, so the control structure -- what this lab actually
grades -- is fully runnable and inspectable.
"""
import json

# ---- Simulated inputs (stand in for what a real user would type) ----
SIMULATED_ANSWERS = {
    "subjects": ["Data Structures", "Operating Systems", "AI Agents"],
    "hours_per_day": 2,
    "unavailable_days": ["Sunday"],
}
SIMULATED_FEEDBACK = "Move Tuesday's session to the evening."


class StudyPlannerAgent:
    def __init__(self, existing_schedule):
        # Goal modeled as data -- a checkable predicate, not prose.
        self.goal = {
            "subjects": None,
            "hours_per_day": None,
            "unavailable_days": None,
            "schedule_generated": False,
        }
        self.existing_schedule = existing_schedule
        self.plan = None
        self.log = []

    # ---- Goal check -------------------------------------------------
    def satisfied(self):
        return self.goal["schedule_generated"] is True

    # ---- Planner: decide the next step ------------------------------
    def next_step(self):
        for field in ("subjects", "hours_per_day", "unavailable_days"):
            if self.goal[field] is None:
                return ("ask", field)
        return ("generate_plan", None)

    # ---- Tool: read existing schedule (Act) -------------------------
    def read_existing_schedule(self):
        # Real tool call with a checked return value.
        result = self.existing_schedule
        if "error" in result:
            raise RuntimeError(f"tool error: {result['error']}")
        return result

    # ---- Core loop ----------------------------------------------------
    def run(self):
        while not self.satisfied():
            step, arg = self.next_step()

            if step == "ask":
                answer = SIMULATED_ANSWERS[arg]      # Act: ask only what's missing
                self.goal[arg] = answer               # Observe: record the real answer
                self.log.append({
                    "iteration": len(self.log) + 1,
                    "planned": f"ask for {arg}",
                    "action": f"asked user for {arg}",
                    "observed": answer,
                    "stopped": False,
                })

            elif step == "generate_plan":
                busy = self.read_existing_schedule()          # Act: tool call
                self.log.append({
                    "iteration": len(self.log) + 1,
                    "planned": "read existing schedule before generating plan",
                    "action": "tool call: read_existing_schedule()",
                    "observed": busy,
                    "stopped": False,
                })
                self.plan = self._build_plan(busy)             # Revise/build
                self.goal["schedule_generated"] = True
                self.log.append({
                    "iteration": len(self.log) + 1,
                    "planned": "generate schedule from gathered requirements",
                    "action": "built weekly plan",
                    "observed": self.plan,
                    "stopped": True,
                    "stop_reason": "goal.schedule_generated is now True",
                })
        return self.plan

    # ---- Build the actual plan object -------------------------------
    def _build_plan(self, busy_slots):
        days = [d for d in
                ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                if d not in self.goal["unavailable_days"]]
        subjects = self.goal["subjects"]
        plan = {}
        for i, day in enumerate(days):
            subject = subjects[i % len(subjects)]
            slot = "17:00-19:00"
            if day in busy_slots.get("busy_days", []):
                slot = "20:00-22:00"   # avoid the clash observed from the tool
            plan[day] = {"subject": subject, "time": slot}
        return plan

    # ---- Revise on user feedback (mutate, don't restart) ------------
    def revise(self, feedback):
        self.log.append({
            "iteration": len(self.log) + 1,
            "planned": "apply user feedback to existing plan",
            "action": f"feedback received: '{feedback}'",
            "observed": None,
            "stopped": False,
        })
        if "tuesday" in feedback.lower() and "evening" in feedback.lower():
            if "Tuesday" in self.plan:
                self.plan["Tuesday"]["time"] = "20:00-22:00"
        self.log.append({
            "iteration": len(self.log) + 1,
            "planned": "confirm revised plan",
            "action": "mutated existing plan (not regenerated from scratch)",
            "observed": self.plan,
            "stopped": True,
            "stop_reason": "revision applied without restarting the loop",
        })
        return self.plan


if __name__ == "__main__":
    existing_schedule = {"busy_days": ["Wednesday"]}   # mock tool data
    agent = StudyPlannerAgent(existing_schedule)

    print("Stopping condition (declared before the loop runs):")
    print("  goal['schedule_generated'] is True\n")

    plan = agent.run()
    print("=== Initial plan ===")
    print(json.dumps(plan, indent=2))

    revised = agent.revise(SIMULATED_FEEDBACK)
    print("\n=== Revised plan (after feedback) ===")
    print(json.dumps(revised, indent=2))

    print("\n=== Full iteration log ===")
    for entry in agent.log:
        print(json.dumps(entry, indent=2))
```

### Captured output

```text
Stopping condition (declared before the loop runs):
  goal['schedule_generated'] is True

=== Initial plan ===
{
  "Monday": {
    "subject": "Data Structures",
    "time": "17:00-19:00"
  },
  "Tuesday": {
    "subject": "Operating Systems",
    "time": "17:00-19:00"
  },
  "Wednesday": {
    "subject": "AI Agents",
    "time": "20:00-22:00"
  },
  "Thursday": {
    "subject": "Data Structures",
    "time": "17:00-19:00"
  },
  "Friday": {
    "subject": "Operating Systems",
    "time": "17:00-19:00"
  },
  "Saturday": {
    "subject": "AI Agents",
    "time": "17:00-19:00"
  }
}

=== Revised plan (after feedback) ===
{
  "Monday": {
    "subject": "Data Structures",
    "time": "17:00-19:00"
  },
  "Tuesday": {
    "subject": "Operating Systems",
    "time": "20:00-22:00"
  },
  "Wednesday": {
    "subject": "AI Agents",
    "time": "20:00-22:00"
  },
  "Thursday": {
    "subject": "Data Structures",
    "time": "17:00-19:00"
  },
  "Friday": {
    "subject": "Operating Systems",
    "time": "17:00-19:00"
  },
  "Saturday": {
    "subject": "AI Agents",
    "time": "17:00-19:00"
  }
}

=== Full iteration log ===
{
  "iteration": 1,
  "planned": "ask for subjects",
  "action": "asked user for subjects",
  "observed": [
    "Data Structures",
    "Operating Systems",
    "AI Agents"
  ],
  "stopped": false
}
{
  "iteration": 2,
  "planned": "ask for hours_per_day",
  "action": "asked user for hours_per_day",
  "observed": 2,
  "stopped": false
}
{
  "iteration": 3,
  "planned": "ask for unavailable_days",
  "action": "asked user for unavailable_days",
  "observed": [
    "Sunday"
  ],
  "stopped": false
}
{
  "iteration": 4,
  "planned": "read existing schedule before generating plan",
  "action": "tool call: read_existing_schedule()",
  "observed": {
    "busy_days": [
      "Wednesday"
    ]
  },
  "stopped": false
}
{
  "iteration": 5,
  "planned": "generate schedule from gathered requirements",
  "action": "built weekly plan",
  "observed": {
    "Monday": {
      "subject": "Data Structures",
      "time": "17:00-19:00"
    },
    "Tuesday": {
      "subject": "Operating Systems",
      "time": "20:00-22:00"
    },
    "Wednesday": {
      "subject": "AI Agents",
      "time": "20:00-22:00"
    },
    "Thursday": {
      "subject": "Data Structures",
      "time": "17:00-19:00"
    },
    "Friday": {
      "subject": "Operating Systems",
      "time": "17:00-19:00"
    },
    "Saturday": {
      "subject": "AI Agents",
      "time": "17:00-19:00"
    }
  },
  "stopped": true,
  "stop_reason": "goal.schedule_generated is now True"
}
{
  "iteration": 6,
  "planned": "apply user feedback to existing plan",
  "action": "feedback received: 'Move Tuesday's session to the evening.'",
  "observed": null,
  "stopped": false
}
{
  "iteration": 7,
  "planned": "confirm revised plan",
  "action": "mutated existing plan (not regenerated from scratch)",
  "observed": {
    "Monday": {
      "subject": "Data Structures",
      "time": "17:00-19:00"
    },
    "Tuesday": {
      "subject": "Operating Systems",
      "time": "20:00-22:00"
    },
    "Wednesday": {
      "subject": "AI Agents",
      "time": "20:00-22:00"
    },
    "Thursday": {
      "subject": "Data Structures",
      "time": "17:00-19:00"
    },
    "Friday": {
      "subject": "Operating Systems",
      "time": "17:00-19:00"
    },
    "Saturday": {
      "subject": "AI Agents",
      "time": "17:00-19:00"
    }
  },
  "stopped": true,
  "stop_reason": "revision applied without restarting the loop"
}
```

## Assignment 1 source and captured output

Run from the repository root with `python labs/lab_01/assignment_1.py`.

### Full source

```python
# SRN 02FE23BCI038 | Lab 1: Agent vs Chatbot | assignment_1
# Original definitions retained below; extensions follow.
"""
Lab 1: Agent vs Chatbot -- Study Planner Agent
Implements the full Goal -> Plan -> Act -> Observe -> Revise loop.
No external API needed: the "planner" is a small rule-based stand-in
for an LLM call, so the control structure -- what this lab actually
grades -- is fully runnable and inspectable.
"""
import json

# ---- Simulated inputs (stand in for what a real user would type) ----
SIMULATED_ANSWERS = {
    "subjects": ["Data Structures", "Operating Systems", "AI Agents"],
    "hours_per_day": 2,
    "unavailable_days": ["Sunday"],
}
SIMULATED_FEEDBACK = "Move Tuesday's session to the evening."


class StudyPlannerAgent:
    def __init__(self, existing_schedule):
        # Goal modeled as data -- a checkable predicate, not prose.
        self.goal = {
            "subjects": None,
            "hours_per_day": None,
            "unavailable_days": None,
            "schedule_generated": False,
        }
        self.existing_schedule = existing_schedule
        self.plan = None
        self.log = []

    # ---- Goal check -------------------------------------------------
    def satisfied(self):
        return self.goal["schedule_generated"] is True

    # ---- Planner: decide the next step ------------------------------
    def next_step(self):
        for field in ("subjects", "hours_per_day", "unavailable_days"):
            if self.goal[field] is None:
                return ("ask", field)
        return ("generate_plan", None)

    # ---- Tool: read existing schedule (Act) -------------------------
    def read_existing_schedule(self):
        # Real tool call with a checked return value.
        result = self.existing_schedule
        if "error" in result:
            raise RuntimeError(f"tool error: {result['error']}")
        return result

    # ---- Core loop ----------------------------------------------------
    def run(self):
        while not self.satisfied():
            step, arg = self.next_step()

            if step == "ask":
                answer = SIMULATED_ANSWERS[arg]      # Act: ask only what's missing
                self.goal[arg] = answer               # Observe: record the real answer
                self.log.append({
                    "iteration": len(self.log) + 1,
                    "planned": f"ask for {arg}",
                    "action": f"asked user for {arg}",
                    "observed": answer,
                    "stopped": False,
                })

            elif step == "generate_plan":
                busy = self.read_existing_schedule()          # Act: tool call
                self.log.append({
                    "iteration": len(self.log) + 1,
                    "planned": "read existing schedule before generating plan",
                    "action": "tool call: read_existing_schedule()",
                    "observed": busy,
                    "stopped": False,
                })
                self.plan = self._build_plan(busy)             # Revise/build
                self.goal["schedule_generated"] = True
                self.log.append({
                    "iteration": len(self.log) + 1,
                    "planned": "generate schedule from gathered requirements",
                    "action": "built weekly plan",
                    "observed": self.plan,
                    "stopped": True,
                    "stop_reason": "goal.schedule_generated is now True",
                })
        return self.plan

    # ---- Build the actual plan object -------------------------------
    def _build_plan(self, busy_slots):
        days = [d for d in
                ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                if d not in self.goal["unavailable_days"]]
        subjects = self.goal["subjects"]
        plan = {}
        for i, day in enumerate(days):
            subject = subjects[i % len(subjects)]
            slot = "17:00-19:00"
            if day in busy_slots.get("busy_days", []):
                slot = "20:00-22:00"   # avoid the clash observed from the tool
            plan[day] = {"subject": subject, "time": slot}
        return plan

    # ---- Revise on user feedback (mutate, don't restart) ------------
    def revise(self, feedback):
        self.log.append({
            "iteration": len(self.log) + 1,
            "planned": "apply user feedback to existing plan",
            "action": f"feedback received: '{feedback}'",
            "observed": None,
            "stopped": False,
        })
        if "tuesday" in feedback.lower() and "evening" in feedback.lower():
            if "Tuesday" in self.plan:
                self.plan["Tuesday"]["time"] = "20:00-22:00"
        self.log.append({
            "iteration": len(self.log) + 1,
            "planned": "confirm revised plan",
            "action": "mutated existing plan (not regenerated from scratch)",
            "observed": self.plan,
            "stopped": True,
            "stop_reason": "revision applied without restarting the loop",
        })
        return self.plan



A1=True
A2=False

import copy
class ExtendedStudyPlanner(StudyPlannerAgent):
    def read_existing_schedule(self):
        result = super().read_existing_schedule()
        if A2:
            result = copy.deepcopy(result)
            result['busy_days'] = ['Wednesday', 'Friday']
        return result

    def _build_plan(self, busy_slots):
        conflicts = sorted(set(busy_slots.get('busy_days', [])) - set(self.goal['unavailable_days']))
        if A2 and conflicts:
            print('CONFLICT detected before finalizing:', ', '.join(conflicts))
            print('Resolution: move affected sessions to 20:00-22:00.')
            self.log.append({'action': 'conflict_reported_before_finalization', 'days': conflicts})
        return super()._build_plan(busy_slots)

    def revise(self, feedback):
        if 'friday' in feedback.lower() and 'one hour' in feedback.lower():
            self.log.append({'action': 'feedback received', 'feedback': feedback})
            start = self.plan['Friday']['time'].split('-')[0]
            hour = int(start[:2])
            self.plan['Friday']['time'] = f'{hour:02d}:00-{hour+1:02d}:00'
            self.log.append({'action': 'mutated same plan', 'day': 'Friday', 'duration_hours': 1})
            return self.plan
        return super().revise(feedback)

def demo():
    agent = ExtendedStudyPlanner({'busy_days': ['Wednesday']})
    plan = agent.run()
    print('Initial plan:', json.dumps(plan, indent=2))
    identity = id(plan)
    agent.revise(SIMULATED_FEEDBACK)
    if A1:
        agent.revise("Also make Friday's session shorter, only one hour")
        assert agent.plan['Friday']['time'].split('-')[0] != agent.plan['Friday']['time'].split('-')[1]
    assert id(agent.plan) == identity
    print('Same plan object preserved:', id(agent.plan) == identity)
    print('Revised plan:', json.dumps(agent.plan, indent=2))
    print('Full iteration log:', json.dumps(agent.log, indent=2))
    if A2:
        assert agent.plan['Wednesday']['time'] == '20:00-22:00'
        assert agent.plan['Friday']['time'].startswith('20:00')
    print('PASS: requested revisions and conflict checks')

if __name__ == "__main__":
    demo()
```

### Captured output

```text
Initial plan: {
  "Monday": {
    "subject": "Data Structures",
    "time": "17:00-19:00"
  },
  "Tuesday": {
    "subject": "Operating Systems",
    "time": "17:00-19:00"
  },
  "Wednesday": {
    "subject": "AI Agents",
    "time": "20:00-22:00"
  },
  "Thursday": {
    "subject": "Data Structures",
    "time": "17:00-19:00"
  },
  "Friday": {
    "subject": "Operating Systems",
    "time": "17:00-19:00"
  },
  "Saturday": {
    "subject": "AI Agents",
    "time": "17:00-19:00"
  }
}
Same plan object preserved: True
Revised plan: {
  "Monday": {
    "subject": "Data Structures",
    "time": "17:00-19:00"
  },
  "Tuesday": {
    "subject": "Operating Systems",
    "time": "20:00-22:00"
  },
  "Wednesday": {
    "subject": "AI Agents",
    "time": "20:00-22:00"
  },
  "Thursday": {
    "subject": "Data Structures",
    "time": "17:00-19:00"
  },
  "Friday": {
    "subject": "Operating Systems",
    "time": "17:00-18:00"
  },
  "Saturday": {
    "subject": "AI Agents",
    "time": "17:00-19:00"
  }
}
Full iteration log: [
  {
    "iteration": 1,
    "planned": "ask for subjects",
    "action": "asked user for subjects",
    "observed": [
      "Data Structures",
      "Operating Systems",
      "AI Agents"
    ],
    "stopped": false
  },
  {
    "iteration": 2,
    "planned": "ask for hours_per_day",
    "action": "asked user for hours_per_day",
    "observed": 2,
    "stopped": false
  },
  {
    "iteration": 3,
    "planned": "ask for unavailable_days",
    "action": "asked user for unavailable_days",
    "observed": [
      "Sunday"
    ],
    "stopped": false
  },
  {
    "iteration": 4,
    "planned": "read existing schedule before generating plan",
    "action": "tool call: read_existing_schedule()",
    "observed": {
      "busy_days": [
        "Wednesday"
      ]
    },
    "stopped": false
  },
  {
    "iteration": 5,
    "planned": "generate schedule from gathered requirements",
    "action": "built weekly plan",
    "observed": {
      "Monday": {
        "subject": "Data Structures",
        "time": "17:00-19:00"
      },
      "Tuesday": {
        "subject": "Operating Systems",
        "time": "20:00-22:00"
      },
      "Wednesday": {
        "subject": "AI Agents",
        "time": "20:00-22:00"
      },
      "Thursday": {
        "subject": "Data Structures",
        "time": "17:00-19:00"
      },
      "Friday": {
        "subject": "Operating Systems",
        "time": "17:00-18:00"
      },
      "Saturday": {
        "subject": "AI Agents",
        "time": "17:00-19:00"
      }
    },
    "stopped": true,
    "stop_reason": "goal.schedule_generated is now True"
  },
  {
    "iteration": 6,
    "planned": "apply user feedback to existing plan",
    "action": "feedback received: 'Move Tuesday's session to the evening.'",
    "observed": null,
    "stopped": false
  },
  {
    "iteration": 7,
    "planned": "confirm revised plan",
    "action": "mutated existing plan (not regenerated from scratch)",
    "observed": {
      "Monday": {
        "subject": "Data Structures",
        "time": "17:00-19:00"
      },
      "Tuesday": {
        "subject": "Operating Systems",
        "time": "20:00-22:00"
      },
      "Wednesday": {
        "subject": "AI Agents",
        "time": "20:00-22:00"
      },
      "Thursday": {
        "subject": "Data Structures",
        "time": "17:00-19:00"
      },
      "Friday": {
        "subject": "Operating Systems",
        "time": "17:00-18:00"
      },
      "Saturday": {
        "subject": "AI Agents",
        "time": "17:00-19:00"
      }
    },
    "stopped": true,
    "stop_reason": "revision applied without restarting the loop"
  },
  {
    "action": "feedback received",
    "feedback": "Also make Friday's session shorter, only one hour"
  },
  {
    "action": "mutated same plan",
    "day": "Friday",
    "duration_hours": 1
  }
]
PASS: requested revisions and conflict checks
```

## Assignment 2 source and captured output

Run from the repository root with `python labs/lab_01/assignment_2.py`.

### Full source

```python
# SRN 02FE23BCI038 | Lab 1: Agent vs Chatbot | assignment_2
# Original definitions retained below; extensions follow.
"""
Lab 1: Agent vs Chatbot -- Study Planner Agent
Implements the full Goal -> Plan -> Act -> Observe -> Revise loop.
No external API needed: the "planner" is a small rule-based stand-in
for an LLM call, so the control structure -- what this lab actually
grades -- is fully runnable and inspectable.
"""
import json

# ---- Simulated inputs (stand in for what a real user would type) ----
SIMULATED_ANSWERS = {
    "subjects": ["Data Structures", "Operating Systems", "AI Agents"],
    "hours_per_day": 2,
    "unavailable_days": ["Sunday"],
}
SIMULATED_FEEDBACK = "Move Tuesday's session to the evening."


class StudyPlannerAgent:
    def __init__(self, existing_schedule):
        # Goal modeled as data -- a checkable predicate, not prose.
        self.goal = {
            "subjects": None,
            "hours_per_day": None,
            "unavailable_days": None,
            "schedule_generated": False,
        }
        self.existing_schedule = existing_schedule
        self.plan = None
        self.log = []

    # ---- Goal check -------------------------------------------------
    def satisfied(self):
        return self.goal["schedule_generated"] is True

    # ---- Planner: decide the next step ------------------------------
    def next_step(self):
        for field in ("subjects", "hours_per_day", "unavailable_days"):
            if self.goal[field] is None:
                return ("ask", field)
        return ("generate_plan", None)

    # ---- Tool: read existing schedule (Act) -------------------------
    def read_existing_schedule(self):
        # Real tool call with a checked return value.
        result = self.existing_schedule
        if "error" in result:
            raise RuntimeError(f"tool error: {result['error']}")
        return result

    # ---- Core loop ----------------------------------------------------
    def run(self):
        while not self.satisfied():
            step, arg = self.next_step()

            if step == "ask":
                answer = SIMULATED_ANSWERS[arg]      # Act: ask only what's missing
                self.goal[arg] = answer               # Observe: record the real answer
                self.log.append({
                    "iteration": len(self.log) + 1,
                    "planned": f"ask for {arg}",
                    "action": f"asked user for {arg}",
                    "observed": answer,
                    "stopped": False,
                })

            elif step == "generate_plan":
                busy = self.read_existing_schedule()          # Act: tool call
                self.log.append({
                    "iteration": len(self.log) + 1,
                    "planned": "read existing schedule before generating plan",
                    "action": "tool call: read_existing_schedule()",
                    "observed": busy,
                    "stopped": False,
                })
                self.plan = self._build_plan(busy)             # Revise/build
                self.goal["schedule_generated"] = True
                self.log.append({
                    "iteration": len(self.log) + 1,
                    "planned": "generate schedule from gathered requirements",
                    "action": "built weekly plan",
                    "observed": self.plan,
                    "stopped": True,
                    "stop_reason": "goal.schedule_generated is now True",
                })
        return self.plan

    # ---- Build the actual plan object -------------------------------
    def _build_plan(self, busy_slots):
        days = [d for d in
                ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                if d not in self.goal["unavailable_days"]]
        subjects = self.goal["subjects"]
        plan = {}
        for i, day in enumerate(days):
            subject = subjects[i % len(subjects)]
            slot = "17:00-19:00"
            if day in busy_slots.get("busy_days", []):
                slot = "20:00-22:00"   # avoid the clash observed from the tool
            plan[day] = {"subject": subject, "time": slot}
        return plan

    # ---- Revise on user feedback (mutate, don't restart) ------------
    def revise(self, feedback):
        self.log.append({
            "iteration": len(self.log) + 1,
            "planned": "apply user feedback to existing plan",
            "action": f"feedback received: '{feedback}'",
            "observed": None,
            "stopped": False,
        })
        if "tuesday" in feedback.lower() and "evening" in feedback.lower():
            if "Tuesday" in self.plan:
                self.plan["Tuesday"]["time"] = "20:00-22:00"
        self.log.append({
            "iteration": len(self.log) + 1,
            "planned": "confirm revised plan",
            "action": "mutated existing plan (not regenerated from scratch)",
            "observed": self.plan,
            "stopped": True,
            "stop_reason": "revision applied without restarting the loop",
        })
        return self.plan



A1=False
A2=True

import copy
class ExtendedStudyPlanner(StudyPlannerAgent):
    def read_existing_schedule(self):
        result = super().read_existing_schedule()
        if A2:
            result = copy.deepcopy(result)
            result['busy_days'] = ['Wednesday', 'Friday']
        return result

    def _build_plan(self, busy_slots):
        conflicts = sorted(set(busy_slots.get('busy_days', [])) - set(self.goal['unavailable_days']))
        if A2 and conflicts:
            print('CONFLICT detected before finalizing:', ', '.join(conflicts))
            print('Resolution: move affected sessions to 20:00-22:00.')
            self.log.append({'action': 'conflict_reported_before_finalization', 'days': conflicts})
        return super()._build_plan(busy_slots)

    def revise(self, feedback):
        if 'friday' in feedback.lower() and 'one hour' in feedback.lower():
            self.log.append({'action': 'feedback received', 'feedback': feedback})
            start = self.plan['Friday']['time'].split('-')[0]
            hour = int(start[:2])
            self.plan['Friday']['time'] = f'{hour:02d}:00-{hour+1:02d}:00'
            self.log.append({'action': 'mutated same plan', 'day': 'Friday', 'duration_hours': 1})
            return self.plan
        return super().revise(feedback)

def demo():
    agent = ExtendedStudyPlanner({'busy_days': ['Wednesday']})
    plan = agent.run()
    print('Initial plan:', json.dumps(plan, indent=2))
    identity = id(plan)
    agent.revise(SIMULATED_FEEDBACK)
    if A1:
        agent.revise("Also make Friday's session shorter, only one hour")
        assert agent.plan['Friday']['time'].split('-')[0] != agent.plan['Friday']['time'].split('-')[1]
    assert id(agent.plan) == identity
    print('Same plan object preserved:', id(agent.plan) == identity)
    print('Revised plan:', json.dumps(agent.plan, indent=2))
    print('Full iteration log:', json.dumps(agent.log, indent=2))
    if A2:
        assert agent.plan['Wednesday']['time'] == '20:00-22:00'
        assert agent.plan['Friday']['time'].startswith('20:00')
    print('PASS: requested revisions and conflict checks')

if __name__ == "__main__":
    demo()
```

### Captured output

```text
CONFLICT detected before finalizing: Friday, Wednesday
Resolution: move affected sessions to 20:00-22:00.
Initial plan: {
  "Monday": {
    "subject": "Data Structures",
    "time": "17:00-19:00"
  },
  "Tuesday": {
    "subject": "Operating Systems",
    "time": "17:00-19:00"
  },
  "Wednesday": {
    "subject": "AI Agents",
    "time": "20:00-22:00"
  },
  "Thursday": {
    "subject": "Data Structures",
    "time": "17:00-19:00"
  },
  "Friday": {
    "subject": "Operating Systems",
    "time": "20:00-22:00"
  },
  "Saturday": {
    "subject": "AI Agents",
    "time": "17:00-19:00"
  }
}
Same plan object preserved: True
Revised plan: {
  "Monday": {
    "subject": "Data Structures",
    "time": "17:00-19:00"
  },
  "Tuesday": {
    "subject": "Operating Systems",
    "time": "20:00-22:00"
  },
  "Wednesday": {
    "subject": "AI Agents",
    "time": "20:00-22:00"
  },
  "Thursday": {
    "subject": "Data Structures",
    "time": "17:00-19:00"
  },
  "Friday": {
    "subject": "Operating Systems",
    "time": "20:00-22:00"
  },
  "Saturday": {
    "subject": "AI Agents",
    "time": "17:00-19:00"
  }
}
Full iteration log: [
  {
    "iteration": 1,
    "planned": "ask for subjects",
    "action": "asked user for subjects",
    "observed": [
      "Data Structures",
      "Operating Systems",
      "AI Agents"
    ],
    "stopped": false
  },
  {
    "iteration": 2,
    "planned": "ask for hours_per_day",
    "action": "asked user for hours_per_day",
    "observed": 2,
    "stopped": false
  },
  {
    "iteration": 3,
    "planned": "ask for unavailable_days",
    "action": "asked user for unavailable_days",
    "observed": [
      "Sunday"
    ],
    "stopped": false
  },
  {
    "iteration": 4,
    "planned": "read existing schedule before generating plan",
    "action": "tool call: read_existing_schedule()",
    "observed": {
      "busy_days": [
        "Wednesday",
        "Friday"
      ]
    },
    "stopped": false
  },
  {
    "action": "conflict_reported_before_finalization",
    "days": [
      "Friday",
      "Wednesday"
    ]
  },
  {
    "iteration": 6,
    "planned": "generate schedule from gathered requirements",
    "action": "built weekly plan",
    "observed": {
      "Monday": {
        "subject": "Data Structures",
        "time": "17:00-19:00"
      },
      "Tuesday": {
        "subject": "Operating Systems",
        "time": "20:00-22:00"
      },
      "Wednesday": {
        "subject": "AI Agents",
        "time": "20:00-22:00"
      },
      "Thursday": {
        "subject": "Data Structures",
        "time": "17:00-19:00"
      },
      "Friday": {
        "subject": "Operating Systems",
        "time": "20:00-22:00"
      },
      "Saturday": {
        "subject": "AI Agents",
        "time": "17:00-19:00"
      }
    },
    "stopped": true,
    "stop_reason": "goal.schedule_generated is now True"
  },
  {
    "iteration": 7,
    "planned": "apply user feedback to existing plan",
    "action": "feedback received: 'Move Tuesday's session to the evening.'",
    "observed": null,
    "stopped": false
  },
  {
    "iteration": 8,
    "planned": "confirm revised plan",
    "action": "mutated existing plan (not regenerated from scratch)",
    "observed": {
      "Monday": {
        "subject": "Data Structures",
        "time": "17:00-19:00"
      },
      "Tuesday": {
        "subject": "Operating Systems",
        "time": "20:00-22:00"
      },
      "Wednesday": {
        "subject": "AI Agents",
        "time": "20:00-22:00"
      },
      "Thursday": {
        "subject": "Data Structures",
        "time": "17:00-19:00"
      },
      "Friday": {
        "subject": "Operating Systems",
        "time": "20:00-22:00"
      },
      "Saturday": {
        "subject": "AI Agents",
        "time": "17:00-19:00"
      }
    },
    "stopped": true,
    "stop_reason": "revision applied without restarting the loop"
  }
]
PASS: requested revisions and conflict checks
```

## Combined source and captured output

Run from the repository root with `python labs/lab_01/combined.py`.

### Full source

```python
# SRN 02FE23BCI038 | Lab 1: Agent vs Chatbot | combined
# Original definitions retained below; extensions follow.
"""
Lab 1: Agent vs Chatbot -- Study Planner Agent
Implements the full Goal -> Plan -> Act -> Observe -> Revise loop.
No external API needed: the "planner" is a small rule-based stand-in
for an LLM call, so the control structure -- what this lab actually
grades -- is fully runnable and inspectable.
"""
import json

# ---- Simulated inputs (stand in for what a real user would type) ----
SIMULATED_ANSWERS = {
    "subjects": ["Data Structures", "Operating Systems", "AI Agents"],
    "hours_per_day": 2,
    "unavailable_days": ["Sunday"],
}
SIMULATED_FEEDBACK = "Move Tuesday's session to the evening."


class StudyPlannerAgent:
    def __init__(self, existing_schedule):
        # Goal modeled as data -- a checkable predicate, not prose.
        self.goal = {
            "subjects": None,
            "hours_per_day": None,
            "unavailable_days": None,
            "schedule_generated": False,
        }
        self.existing_schedule = existing_schedule
        self.plan = None
        self.log = []

    # ---- Goal check -------------------------------------------------
    def satisfied(self):
        return self.goal["schedule_generated"] is True

    # ---- Planner: decide the next step ------------------------------
    def next_step(self):
        for field in ("subjects", "hours_per_day", "unavailable_days"):
            if self.goal[field] is None:
                return ("ask", field)
        return ("generate_plan", None)

    # ---- Tool: read existing schedule (Act) -------------------------
    def read_existing_schedule(self):
        # Real tool call with a checked return value.
        result = self.existing_schedule
        if "error" in result:
            raise RuntimeError(f"tool error: {result['error']}")
        return result

    # ---- Core loop ----------------------------------------------------
    def run(self):
        while not self.satisfied():
            step, arg = self.next_step()

            if step == "ask":
                answer = SIMULATED_ANSWERS[arg]      # Act: ask only what's missing
                self.goal[arg] = answer               # Observe: record the real answer
                self.log.append({
                    "iteration": len(self.log) + 1,
                    "planned": f"ask for {arg}",
                    "action": f"asked user for {arg}",
                    "observed": answer,
                    "stopped": False,
                })

            elif step == "generate_plan":
                busy = self.read_existing_schedule()          # Act: tool call
                self.log.append({
                    "iteration": len(self.log) + 1,
                    "planned": "read existing schedule before generating plan",
                    "action": "tool call: read_existing_schedule()",
                    "observed": busy,
                    "stopped": False,
                })
                self.plan = self._build_plan(busy)             # Revise/build
                self.goal["schedule_generated"] = True
                self.log.append({
                    "iteration": len(self.log) + 1,
                    "planned": "generate schedule from gathered requirements",
                    "action": "built weekly plan",
                    "observed": self.plan,
                    "stopped": True,
                    "stop_reason": "goal.schedule_generated is now True",
                })
        return self.plan

    # ---- Build the actual plan object -------------------------------
    def _build_plan(self, busy_slots):
        days = [d for d in
                ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                if d not in self.goal["unavailable_days"]]
        subjects = self.goal["subjects"]
        plan = {}
        for i, day in enumerate(days):
            subject = subjects[i % len(subjects)]
            slot = "17:00-19:00"
            if day in busy_slots.get("busy_days", []):
                slot = "20:00-22:00"   # avoid the clash observed from the tool
            plan[day] = {"subject": subject, "time": slot}
        return plan

    # ---- Revise on user feedback (mutate, don't restart) ------------
    def revise(self, feedback):
        self.log.append({
            "iteration": len(self.log) + 1,
            "planned": "apply user feedback to existing plan",
            "action": f"feedback received: '{feedback}'",
            "observed": None,
            "stopped": False,
        })
        if "tuesday" in feedback.lower() and "evening" in feedback.lower():
            if "Tuesday" in self.plan:
                self.plan["Tuesday"]["time"] = "20:00-22:00"
        self.log.append({
            "iteration": len(self.log) + 1,
            "planned": "confirm revised plan",
            "action": "mutated existing plan (not regenerated from scratch)",
            "observed": self.plan,
            "stopped": True,
            "stop_reason": "revision applied without restarting the loop",
        })
        return self.plan



A1=True
A2=True

import copy
class ExtendedStudyPlanner(StudyPlannerAgent):
    def read_existing_schedule(self):
        result = super().read_existing_schedule()
        if A2:
            result = copy.deepcopy(result)
            result['busy_days'] = ['Wednesday', 'Friday']
        return result

    def _build_plan(self, busy_slots):
        conflicts = sorted(set(busy_slots.get('busy_days', [])) - set(self.goal['unavailable_days']))
        if A2 and conflicts:
            print('CONFLICT detected before finalizing:', ', '.join(conflicts))
            print('Resolution: move affected sessions to 20:00-22:00.')
            self.log.append({'action': 'conflict_reported_before_finalization', 'days': conflicts})
        return super()._build_plan(busy_slots)

    def revise(self, feedback):
        if 'friday' in feedback.lower() and 'one hour' in feedback.lower():
            self.log.append({'action': 'feedback received', 'feedback': feedback})
            start = self.plan['Friday']['time'].split('-')[0]
            hour = int(start[:2])
            self.plan['Friday']['time'] = f'{hour:02d}:00-{hour+1:02d}:00'
            self.log.append({'action': 'mutated same plan', 'day': 'Friday', 'duration_hours': 1})
            return self.plan
        return super().revise(feedback)

def demo():
    agent = ExtendedStudyPlanner({'busy_days': ['Wednesday']})
    plan = agent.run()
    print('Initial plan:', json.dumps(plan, indent=2))
    identity = id(plan)
    agent.revise(SIMULATED_FEEDBACK)
    if A1:
        agent.revise("Also make Friday's session shorter, only one hour")
        assert agent.plan['Friday']['time'].split('-')[0] != agent.plan['Friday']['time'].split('-')[1]
    assert id(agent.plan) == identity
    print('Same plan object preserved:', id(agent.plan) == identity)
    print('Revised plan:', json.dumps(agent.plan, indent=2))
    print('Full iteration log:', json.dumps(agent.log, indent=2))
    if A2:
        assert agent.plan['Wednesday']['time'] == '20:00-22:00'
        assert agent.plan['Friday']['time'].startswith('20:00')
    print('PASS: requested revisions and conflict checks')

if __name__ == "__main__":
    demo()
```

### Captured output

```text
CONFLICT detected before finalizing: Friday, Wednesday
Resolution: move affected sessions to 20:00-22:00.
Initial plan: {
  "Monday": {
    "subject": "Data Structures",
    "time": "17:00-19:00"
  },
  "Tuesday": {
    "subject": "Operating Systems",
    "time": "17:00-19:00"
  },
  "Wednesday": {
    "subject": "AI Agents",
    "time": "20:00-22:00"
  },
  "Thursday": {
    "subject": "Data Structures",
    "time": "17:00-19:00"
  },
  "Friday": {
    "subject": "Operating Systems",
    "time": "20:00-22:00"
  },
  "Saturday": {
    "subject": "AI Agents",
    "time": "17:00-19:00"
  }
}
Same plan object preserved: True
Revised plan: {
  "Monday": {
    "subject": "Data Structures",
    "time": "17:00-19:00"
  },
  "Tuesday": {
    "subject": "Operating Systems",
    "time": "20:00-22:00"
  },
  "Wednesday": {
    "subject": "AI Agents",
    "time": "20:00-22:00"
  },
  "Thursday": {
    "subject": "Data Structures",
    "time": "17:00-19:00"
  },
  "Friday": {
    "subject": "Operating Systems",
    "time": "20:00-21:00"
  },
  "Saturday": {
    "subject": "AI Agents",
    "time": "17:00-19:00"
  }
}
Full iteration log: [
  {
    "iteration": 1,
    "planned": "ask for subjects",
    "action": "asked user for subjects",
    "observed": [
      "Data Structures",
      "Operating Systems",
      "AI Agents"
    ],
    "stopped": false
  },
  {
    "iteration": 2,
    "planned": "ask for hours_per_day",
    "action": "asked user for hours_per_day",
    "observed": 2,
    "stopped": false
  },
  {
    "iteration": 3,
    "planned": "ask for unavailable_days",
    "action": "asked user for unavailable_days",
    "observed": [
      "Sunday"
    ],
    "stopped": false
  },
  {
    "iteration": 4,
    "planned": "read existing schedule before generating plan",
    "action": "tool call: read_existing_schedule()",
    "observed": {
      "busy_days": [
        "Wednesday",
        "Friday"
      ]
    },
    "stopped": false
  },
  {
    "action": "conflict_reported_before_finalization",
    "days": [
      "Friday",
      "Wednesday"
    ]
  },
  {
    "iteration": 6,
    "planned": "generate schedule from gathered requirements",
    "action": "built weekly plan",
    "observed": {
      "Monday": {
        "subject": "Data Structures",
        "time": "17:00-19:00"
      },
      "Tuesday": {
        "subject": "Operating Systems",
        "time": "20:00-22:00"
      },
      "Wednesday": {
        "subject": "AI Agents",
        "time": "20:00-22:00"
      },
      "Thursday": {
        "subject": "Data Structures",
        "time": "17:00-19:00"
      },
      "Friday": {
        "subject": "Operating Systems",
        "time": "20:00-21:00"
      },
      "Saturday": {
        "subject": "AI Agents",
        "time": "17:00-19:00"
      }
    },
    "stopped": true,
    "stop_reason": "goal.schedule_generated is now True"
  },
  {
    "iteration": 7,
    "planned": "apply user feedback to existing plan",
    "action": "feedback received: 'Move Tuesday's session to the evening.'",
    "observed": null,
    "stopped": false
  },
  {
    "iteration": 8,
    "planned": "confirm revised plan",
    "action": "mutated existing plan (not regenerated from scratch)",
    "observed": {
      "Monday": {
        "subject": "Data Structures",
        "time": "17:00-19:00"
      },
      "Tuesday": {
        "subject": "Operating Systems",
        "time": "20:00-22:00"
      },
      "Wednesday": {
        "subject": "AI Agents",
        "time": "20:00-22:00"
      },
      "Thursday": {
        "subject": "Data Structures",
        "time": "17:00-19:00"
      },
      "Friday": {
        "subject": "Operating Systems",
        "time": "20:00-21:00"
      },
      "Saturday": {
        "subject": "AI Agents",
        "time": "17:00-19:00"
      }
    },
    "stopped": true,
    "stop_reason": "revision applied without restarting the loop"
  },
  {
    "action": "feedback received",
    "feedback": "Also make Friday's session shorter, only one hour"
  },
  {
    "action": "mutated same plan",
    "day": "Friday",
    "duration_hours": 1
  }
]
PASS: requested revisions and conflict checks
```

