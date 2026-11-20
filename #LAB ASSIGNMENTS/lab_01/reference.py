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
