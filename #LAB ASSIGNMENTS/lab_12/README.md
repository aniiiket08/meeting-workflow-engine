# Lab 12: Safety, Evaluation, and Governance

SRN: **02FE23BCI038**

## Assignment requirements from the guide

Assignment 1 — A Cost-Category Control
Add a cost estimate to each proposed action and a budget threshold. Reject any proposal whose estimated cost exceeds the threshold unless a separate `finance_approved` flag is set. Write an adversarial test that attempts to bypass this by omitting the cost estimate entirely, and confirm it is rejected rather than defaulting to approved.
Assignment 2 — Mandatory Re-Evaluation After N Proposals
Add a rule that the agent must be re-evaluated (call `evaluate()` again) after every 5 proposals it has made. Track the proposal count, and demonstrate a 6th proposal being blocked with a clear message until `evaluate()` is called again.

## Implementation notes

Cost validation rejects missing, negative, nonnumeric, boolean, NaN, and infinite values. Finance approval permits an over-budget request but does not grant production write permission. The sixth accepted-proposal attempt is blocked until re-evaluation; rejected requests do not consume the proposal counter.

Each assignment script includes the original definitions plus its own enabled extension. `A1` and `A2` select the assignment features; both are enabled in `combined.py`. These are standalone scripts, so sibling imports are not required. The original guide demonstration is available unchanged as `reference.py`.

## Original source and captured output

Run from the repository root with `python labs/lab_12/reference.py`.

### Full source

```python
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
```

### Captured output

```text
=== Control 2: Evaluation gate ===
Evaluated and passed: True

=== Attempt 1: missing rollback plan (should be rejected) ===
{'rejected': True, 'reason': 'No rollback plan defined; rejecting proposal.'}

=== Attempt 2: unscrubbed customer data (should be rejected) ===
{'rejected': True, 'reason': 'Diagnostic input was not privacy-scrubbed; rejecting.'}

=== Attempt 3: complete, valid proposal ===
{'diagnosis': 'Config X causes memory leak under load.', 'proposed_action': 'revert config X to previous value', 'rollback_plan': 'Revert config X to v3 if v4 also leaks.', 'category': 'production', 'requires_approval': True}

=== Human approves; a SEPARATE privileged process applies it ===
{'applied': False, 'handed_off_to': 'privileged_deploy_process', 'note': 'This agent never holds production write access; a separate privileged process performs the actual apply step.'}

=== Adversarial test: agent attempts direct production write ===
Blocked as expected: Agent must not hold direct production write access.

=== Full audit log ===
{'step': 'evaluation', 'data': {'pass_rate': 0.9, 'passed_gate': True}}
{'step': 'propose_change', 'data': {'rejected': True, 'reason': 'no rollback plan supplied'}}
{'step': 'propose_change', 'data': {'rejected': True, 'reason': 'unscrubbed customer data in input'}}
{'step': 'approval_requested', 'data': {'diagnosis': 'Config X causes memory leak under load.', 'proposed_action': 'revert config X to previous value', 'rollback_plan': 'Revert config X to v3 if v4 also leaks.', 'category': 'production', 'requires_approval': True}}
{'step': 'human_decision', 'data': {'decision': 'approved'}}
```

## Assignment 1 source and captured output

Run from the repository root with `python labs/lab_12/assignment_1.py`.

### Full source

```python
# SRN 02FE23BCI038 | Lab 12: Safety, Evaluation, and Governance | assignment_1
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



A1=True
A2=False

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
```

### Captured output

```text
Cost test: None False {'rejected': True, 'reason': 'Missing or invalid cost estimate'}
Cost test: 200 False {'rejected': True, 'reason': 'Cost exceeds budget; separate finance approval required'}
Cost test: 200 True {'diagnosis': 'Config issue', 'proposed_action': 'rollback', 'rollback_plan': 'Restore known config', 'category': 'production', 'requires_approval': True, 'cost_estimate': 200, 'finance_approved': True}
Cost test: 50 False {'diagnosis': 'Config issue', 'proposed_action': 'rollback', 'rollback_plan': 'Restore known config', 'category': 'production', 'requires_approval': True, 'cost_estimate': 50, 'finance_approved': False}
Cost test: nan False {'rejected': True, 'reason': 'Missing or invalid cost estimate'}
Cost test: -1 True {'rejected': True, 'reason': 'Missing or invalid cost estimate'}
Audit: [{'step': 'evaluation', 'data': {'pass_rate': 0.9, 'passed_gate': True}}, {'step': 'cost_gate', 'data': {'rejected': True, 'reason': 'Missing or invalid cost estimate'}}, {'step': 'cost_gate', 'data': {'rejected': True, 'reason': 'Cost exceeds budget; separate finance approval required'}}, {'step': 'approval_requested', 'data': {'diagnosis': 'Config issue', 'proposed_action': 'rollback', 'rollback_plan': 'Restore known config', 'category': 'production', 'requires_approval': True, 'cost_estimate': 200, 'finance_approved': True}}, {'step': 'approval_requested', 'data': {'diagnosis': 'Config issue', 'proposed_action': 'rollback', 'rollback_plan': 'Restore known config', 'category': 'production', 'requires_approval': True, 'cost_estimate': 50, 'finance_approved': False}}, {'step': 'cost_gate', 'data': {'rejected': True, 'reason': 'Missing or invalid cost estimate'}}, {'step': 'cost_gate', 'data': {'rejected': True, 'reason': 'Missing or invalid cost estimate'}}]
PASS: fail-closed cost validation and periodic evaluation
```

## Assignment 2 source and captured output

Run from the repository root with `python labs/lab_12/assignment_2.py`.

### Full source

```python
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
```

### Captured output

```text
Proposal 1 {'diagnosis': 'Config issue', 'proposed_action': 'rollback', 'rollback_plan': 'Restore known config', 'category': 'production', 'requires_approval': True}
Proposal 2 {'diagnosis': 'Config issue', 'proposed_action': 'rollback', 'rollback_plan': 'Restore known config', 'category': 'production', 'requires_approval': True}
Proposal 3 {'diagnosis': 'Config issue', 'proposed_action': 'rollback', 'rollback_plan': 'Restore known config', 'category': 'production', 'requires_approval': True}
Proposal 4 {'diagnosis': 'Config issue', 'proposed_action': 'rollback', 'rollback_plan': 'Restore known config', 'category': 'production', 'requires_approval': True}
Proposal 5 {'diagnosis': 'Config issue', 'proposed_action': 'rollback', 'rollback_plan': 'Restore known config', 'category': 'production', 'requires_approval': True}
Proposal 6 {'rejected': True, 'reason': 'Re-evaluation required after 5 proposals; call evaluate()'}
After re-evaluation: {'diagnosis': 'Config issue', 'proposed_action': 'rollback', 'rollback_plan': 'Restore known config', 'category': 'production', 'requires_approval': True}
Audit: [{'step': 'evaluation', 'data': {'pass_rate': 0.9, 'passed_gate': True}}, {'step': 'evaluation', 'data': {'pass_rate': 0.9, 'passed_gate': True}}, {'step': 'approval_requested', 'data': {'diagnosis': 'Config issue', 'proposed_action': 'rollback', 'rollback_plan': 'Restore known config', 'category': 'production', 'requires_approval': True}}, {'step': 'approval_requested', 'data': {'diagnosis': 'Config issue', 'proposed_action': 'rollback', 'rollback_plan': 'Restore known config', 'category': 'production', 'requires_approval': True}}, {'step': 'approval_requested', 'data': {'diagnosis': 'Config issue', 'proposed_action': 'rollback', 'rollback_plan': 'Restore known config', 'category': 'production', 'requires_approval': True}}, {'step': 'approval_requested', 'data': {'diagnosis': 'Config issue', 'proposed_action': 'rollback', 'rollback_plan': 'Restore known config', 'category': 'production', 'requires_approval': True}}, {'step': 'approval_requested', 'data': {'diagnosis': 'Config issue', 'proposed_action': 'rollback', 'rollback_plan': 'Restore known config', 'category': 'production', 'requires_approval': True}}, {'step': 'blocked', 'data': {'rejected': True, 'reason': 'Re-evaluation required after 5 proposals; call evaluate()'}}, {'step': 'evaluation', 'data': {'pass_rate': 0.9, 'passed_gate': True}}, {'step': 'approval_requested', 'data': {'diagnosis': 'Config issue', 'proposed_action': 'rollback', 'rollback_plan': 'Restore known config', 'category': 'production', 'requires_approval': True}}]
PASS: fail-closed cost validation and periodic evaluation
```

## Combined source and captured output

Run from the repository root with `python labs/lab_12/combined.py`.

### Full source

```python
# SRN 02FE23BCI038 | Lab 12: Safety, Evaluation, and Governance | combined
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



A1=True
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
```

### Captured output

```text
Cost test: None False {'rejected': True, 'reason': 'Missing or invalid cost estimate'}
Cost test: 200 False {'rejected': True, 'reason': 'Cost exceeds budget; separate finance approval required'}
Cost test: 200 True {'diagnosis': 'Config issue', 'proposed_action': 'rollback', 'rollback_plan': 'Restore known config', 'category': 'production', 'requires_approval': True, 'cost_estimate': 200, 'finance_approved': True}
Cost test: 50 False {'diagnosis': 'Config issue', 'proposed_action': 'rollback', 'rollback_plan': 'Restore known config', 'category': 'production', 'requires_approval': True, 'cost_estimate': 50, 'finance_approved': False}
Cost test: nan False {'rejected': True, 'reason': 'Missing or invalid cost estimate'}
Cost test: -1 True {'rejected': True, 'reason': 'Missing or invalid cost estimate'}
Proposal 1 {'diagnosis': 'Config issue', 'proposed_action': 'rollback', 'rollback_plan': 'Restore known config', 'category': 'production', 'requires_approval': True, 'cost_estimate': 25, 'finance_approved': False}
Proposal 2 {'diagnosis': 'Config issue', 'proposed_action': 'rollback', 'rollback_plan': 'Restore known config', 'category': 'production', 'requires_approval': True, 'cost_estimate': 25, 'finance_approved': False}
Proposal 3 {'diagnosis': 'Config issue', 'proposed_action': 'rollback', 'rollback_plan': 'Restore known config', 'category': 'production', 'requires_approval': True, 'cost_estimate': 25, 'finance_approved': False}
Proposal 4 {'diagnosis': 'Config issue', 'proposed_action': 'rollback', 'rollback_plan': 'Restore known config', 'category': 'production', 'requires_approval': True, 'cost_estimate': 25, 'finance_approved': False}
Proposal 5 {'diagnosis': 'Config issue', 'proposed_action': 'rollback', 'rollback_plan': 'Restore known config', 'category': 'production', 'requires_approval': True, 'cost_estimate': 25, 'finance_approved': False}
Proposal 6 {'rejected': True, 'reason': 'Re-evaluation required after 5 proposals; call evaluate()'}
After re-evaluation: {'diagnosis': 'Config issue', 'proposed_action': 'rollback', 'rollback_plan': 'Restore known config', 'category': 'production', 'requires_approval': True, 'cost_estimate': 25, 'finance_approved': False}
Audit: [{'step': 'evaluation', 'data': {'pass_rate': 0.9, 'passed_gate': True}}, {'step': 'cost_gate', 'data': {'rejected': True, 'reason': 'Missing or invalid cost estimate'}}, {'step': 'cost_gate', 'data': {'rejected': True, 'reason': 'Cost exceeds budget; separate finance approval required'}}, {'step': 'approval_requested', 'data': {'diagnosis': 'Config issue', 'proposed_action': 'rollback', 'rollback_plan': 'Restore known config', 'category': 'production', 'requires_approval': True, 'cost_estimate': 200, 'finance_approved': True}}, {'step': 'approval_requested', 'data': {'diagnosis': 'Config issue', 'proposed_action': 'rollback', 'rollback_plan': 'Restore known config', 'category': 'production', 'requires_approval': True, 'cost_estimate': 50, 'finance_approved': False}}, {'step': 'cost_gate', 'data': {'rejected': True, 'reason': 'Missing or invalid cost estimate'}}, {'step': 'cost_gate', 'data': {'rejected': True, 'reason': 'Missing or invalid cost estimate'}}, {'step': 'evaluation', 'data': {'pass_rate': 0.9, 'passed_gate': True}}, {'step': 'approval_requested', 'data': {'diagnosis': 'Config issue', 'proposed_action': 'rollback', 'rollback_plan': 'Restore known config', 'category': 'production', 'requires_approval': True, 'cost_estimate': 25, 'finance_approved': False}}, {'step': 'approval_requested', 'data': {'diagnosis': 'Config issue', 'proposed_action': 'rollback', 'rollback_plan': 'Restore known config', 'category': 'production', 'requires_approval': True, 'cost_estimate': 25, 'finance_approved': False}}, {'step': 'approval_requested', 'data': {'diagnosis': 'Config issue', 'proposed_action': 'rollback', 'rollback_plan': 'Restore known config', 'category': 'production', 'requires_approval': True, 'cost_estimate': 25, 'finance_approved': False}}, {'step': 'approval_requested', 'data': {'diagnosis': 'Config issue', 'proposed_action': 'rollback', 'rollback_plan': 'Restore known config', 'category': 'production', 'requires_approval': True, 'cost_estimate': 25, 'finance_approved': False}}, {'step': 'approval_requested', 'data': {'diagnosis': 'Config issue', 'proposed_action': 'rollback', 'rollback_plan': 'Restore known config', 'category': 'production', 'requires_approval': True, 'cost_estimate': 25, 'finance_approved': False}}, {'step': 'blocked', 'data': {'rejected': True, 'reason': 'Re-evaluation required after 5 proposals; call evaluate()'}}, {'step': 'evaluation', 'data': {'pass_rate': 0.9, 'passed_gate': True}}, {'step': 'approval_requested', 'data': {'diagnosis': 'Config issue', 'proposed_action': 'rollback', 'rollback_plan': 'Restore known config', 'category': 'production', 'requires_approval': True, 'cost_estimate': 25, 'finance_approved': False}}]
PASS: fail-closed cost validation and periodic evaluation
```

