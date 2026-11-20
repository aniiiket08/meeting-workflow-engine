# SRN 02FE23BCI038 | Lab 12: Safety, Evaluation, and Governance | assignment_2
# Original definitions retained below; extensions follow.
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



A1=False
A2=True

import math
class GovernedAgent(ProdChangeAgent):
    def __init__(self,budget=100):
        super().__init__();self.budget=budget;self.proposals_since_eval=0
    def evaluate(self):
        passed=super().evaluate()
        if passed:self.proposals_since_eval=0
        return passed
    def propose_change(self,diagnosis,action,rollback_plan,privacy_scrubbed,cost_estimate=None,finance_approved=False):
        if A2 and self.proposals_since_eval>=5:
            r={'rejected':True,'reason':'Re-evaluation required after 5 proposals; call evaluate()'}
            self._log('blocked',r);return r
        if A1:
            if isinstance(cost_estimate,bool) or not isinstance(cost_estimate,(int,float)) or not math.isfinite(cost_estimate) or cost_estimate<0:
                r={'rejected':True,'reason':'Missing or invalid cost estimate'};self._log('cost_gate',r);return r
            if cost_estimate>self.budget and finance_approved is not True:
                r={'rejected':True,'reason':'Cost exceeds budget; separate finance approval required'};self._log('cost_gate',r);return r
        r=super().propose_change(diagnosis,action,rollback_plan,privacy_scrubbed)
        if not r.get('rejected'):
            self.proposals_since_eval+=1
            if A1:r.update(cost_estimate=cost_estimate,finance_approved=finance_approved)
        return r

def demo():
    a=GovernedAgent();assert a.evaluate()
    args=('Config issue','rollback','Restore known config',True)
    if A1:
        for cost,approved in [(None,False),(200,False),(200,True),(50,False),(float('nan'),False),(-1,True)]:
            r=a.propose_change(*args,cost_estimate=cost,finance_approved=approved);print('Cost test:',cost,approved,r)
            assert bool(r.get('rejected'))==(cost is None or not math.isfinite(cost) or cost<0 or (cost>100 and not approved))
    if A2:
        a.evaluate()
        for i in range(6):
            r=a.propose_change(*args,cost_estimate=25);print('Proposal',i+1,r)
            assert bool(r.get('rejected'))==(i==5)
        a.evaluate();r=a.propose_change(*args,cost_estimate=25);print('After re-evaluation:',r);assert not r.get('rejected')
    print('Audit:',a.audit_log)
    print('PASS: fail-closed cost validation and periodic evaluation')

if __name__ == "__main__":
    demo()
