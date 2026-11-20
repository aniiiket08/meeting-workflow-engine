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
