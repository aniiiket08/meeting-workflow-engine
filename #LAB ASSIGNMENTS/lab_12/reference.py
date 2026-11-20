"""
Lab 12: Safety, Evaluation, and Governance -- Guardrails for a
Production-Change Agent. Implements all six controls from Concept 12
and rejects the action if required evidence is missing.
"""

REGRESSION_SUITE_RESULT = {"passed": 9, "total": 10}   # this agent's diagnostic accuracy


class ProdChangeAgent:
    permissions = {"can_write": "staging_only"}   # 1. Permissions (least privilege)

    def __init__(self):
        self.audit_log = []
        self.evaluated = False

    def evaluate(self):
        # 2. Evaluation -- must pass before being trusted with diagnosis
        pass_rate = REGRESSION_SUITE_RESULT["passed"] / REGRESSION_SUITE_RESULT["total"]
        self.evaluated = pass_rate >= 0.8
        self._log("evaluation", {"pass_rate": pass_rate, "passed_gate": self.evaluated})
        return self.evaluated

    def _log(self, step, data):
        # 4. Audit logs -- every decision point, not just the final action
        self.audit_log.append({"step": step, "data": data})

    def propose_change(self, diagnosis, action, rollback_plan, privacy_scrubbed):
        if not self.evaluated:
            self._log("propose_change", {"rejected": True, "reason": "agent not evaluated"})
            return {"rejected": True, "reason": "Evaluation gate not passed; cannot propose changes."}

        if self.permissions["can_write"] != "staging_only":
            raise PermissionError("Agent must not hold direct production write access.")

        if not privacy_scrubbed:
            # 6. Privacy -- reject if customer data wasn't scrubbed from the diagnostic input
            self._log("propose_change", {"rejected": True, "reason": "unscrubbed customer data in input"})
            return {"rejected": True, "reason": "Diagnostic input was not privacy-scrubbed; rejecting."}

        if not rollback_plan:
            # 5. Rollback -- required before any approval request is even drafted
            self._log("propose_change", {"rejected": True, "reason": "no rollback plan supplied"})
            return {"rejected": True, "reason": "No rollback plan defined; rejecting proposal."}

        # 3. Human approval -- production change category always requires a gate
        request = {
            "diagnosis": diagnosis,
            "proposed_action": action,
            "rollback_plan": rollback_plan,
            "category": "production",
            "requires_approval": True,
        }
        self._log("approval_requested", request)
        return request

    def apply_after_approval(self, request, human_decision):
        # A separate, privileged process would apply the change --
        # this agent still never executes it directly.
        self._log("human_decision", {"decision": human_decision})
        if human_decision != "approved":
            return {"applied": False, "reason": "not approved by human"}
        return {"applied": False,  # still False for THIS agent -- a privileged actor applies it
                "handed_off_to": "privileged_deploy_process",
                "note": "This agent never holds production write access; a separate "
                        "privileged process performs the actual apply step."}


if __name__ == "__main__":
    agent = ProdChangeAgent()

    print("=== Control 2: Evaluation gate ===")
    print(f"Evaluated and passed: {agent.evaluate()}")

    print("\n=== Attempt 1: missing rollback plan (should be rejected) ===")
    result = agent.propose_change(
        diagnosis="Config X causes memory leak under load.",
        action="revert config X to previous value",
        rollback_plan=None,
        privacy_scrubbed=True,
    )
    print(result)

    print("\n=== Attempt 2: unscrubbed customer data (should be rejected) ===")
    result = agent.propose_change(
        diagnosis="Config X causes memory leak under load.",
        action="revert config X to previous value",
        rollback_plan="Revert config X to v3 if v4 also leaks.",
        privacy_scrubbed=False,
    )
    print(result)

    print("\n=== Attempt 3: complete, valid proposal ===")
    request = agent.propose_change(
        diagnosis="Config X causes memory leak under load.",
        action="revert config X to previous value",
        rollback_plan="Revert config X to v3 if v4 also leaks.",
        privacy_scrubbed=True,
    )
    print(request)

    print("\n=== Human approves; a SEPARATE privileged process applies it ===")
    outcome = agent.apply_after_approval(request, human_decision="approved")
    print(outcome)

    print("\n=== Adversarial test: agent attempts direct production write ===")
    try:
        agent.permissions["can_write"] = "production"  # simulate a misconfigured/attacked agent
        agent.propose_change("test", "test", "test", True)
    except PermissionError as e:
        print(f"Blocked as expected: {e}")

    print("\n=== Full audit log ===")
    for entry in agent.audit_log:
        print(entry)
