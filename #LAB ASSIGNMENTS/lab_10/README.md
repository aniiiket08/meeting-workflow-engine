# Lab 10: Cloud Operations Agent

SRN: **02FE23BCI038**

## Assignment requirements from the guide

Assignment 1 — A Second Incident Type
Add a second scenario: a database connection-pool exhaustion incident, with its own log lines, deploy history, and metrics. Confirm `classify_severity` and `correlate_with_recent_changes` correctly produce a different diagnosis and severity than the reference payments-service scenario.
Assignment 2 — A Safe Auto-Remediation Path
Add a WARNING-level (not ALARM/degraded-critical) scenario where the proposed action is a low-risk `restart_single_pod`. Demonstrate that this low-risk action is allowed to execute automatically (per `risk_level`), while any rollback-class action anywhere in your extended code still always routes through the approval-request path and never auto-executes.

## Implementation notes

Pool exhaustion has separate logs, configuration history, and metrics. The warning restart changes a local simulated pod generation only. Every rollback action goes through an approval request.

Each assignment script includes the original definitions plus its own enabled extension. `A1` and `A2` select the assignment features; both are enabled in `combined.py`. These are standalone scripts, so sibling imports are not required. The original guide demonstration is available unchanged as `reference.py`.

## Original source and captured output

Run from the repository root with `python labs/lab_10/reference.py`.

### Full source

```python
"""
Lab 10: Cloud Operations Agent -- Failed Deployment Diagnosis
Observe -> Reason -> Act, ending in a drafted human-approval request.
The agent NEVER auto-executes the high-risk remediation action, even
under a simulated urgency prompt.
"""

LOGS = [
    {"ts": "14:00:00", "level": "INFO", "msg": "deploy started: payments-service v2.4.1"},
    {"ts": "14:00:45", "level": "INFO", "msg": "deploy completed: payments-service v2.4.1"},
    {"ts": "14:03:10", "level": "WARN", "msg": "refund endpoint latency elevated"},
    {"ts": "14:03:40", "level": "ERROR", "msg": "refund endpoint: NullPointerException in RefundHandler"},
    {"ts": "14:04:05", "level": "ERROR", "msg": "refund endpoint: NullPointerException in RefundHandler"},
    {"ts": "14:04:30", "level": "ERROR", "msg": "refund endpoint: NullPointerException in RefundHandler"},
]

DEPLOY_HISTORY = [
    {"ts": "14:00:00", "service": "payments-service", "version": "v2.4.1", "prev_version": "v2.4.0"},
]

METRICS = {"baseline_error_rate": 0.5, "current_error_rate": 1.6}   # percent


def classify_severity(metrics):
    ratio = metrics["current_error_rate"] / metrics["baseline_error_rate"]
    if metrics["current_error_rate"] > 50:
        return "down"
    if ratio >= 2:
        return "degraded"
    return "early_warning"


def find_incident_start(logs):
    for entry in logs:
        if entry["level"] == "ERROR":
            return entry["ts"]
    return None


def correlate_with_recent_changes(logs, deploys, incident_start):
    error_msgs = [l["msg"] for l in logs if l["level"] == "ERROR"]
    affected_path = "refund" if any("refund" in m.lower() for m in error_msgs) else "unknown"
    for d in deploys:
        if d["ts"] < incident_start and d["service"].lower().startswith("payments"):
            return {
                "hypothesis": (
                    f"Error rate rose starting {incident_start}, shortly after the "
                    f"{d['ts']} deploy of {d['service']} {d['version']}. Errors are "
                    f"concentrated in the {affected_path} code path, consistent with a "
                    f"regression introduced in that release."),
                "suspect_deploy": d,
                "affected_path": affected_path,
            }
    return {"hypothesis": "No recent deploy correlates with the incident window.",
            "suspect_deploy": None, "affected_path": affected_path}


def risk_level(action):
    HIGH_RISK = {"rollback", "scale", "config_change", "delete"}
    LOW_RISK = {"open_ticket", "notify", "restart_single_pod"}
    if action in HIGH_RISK:
        return "high"
    if action in LOW_RISK:
        return "low"
    return "unknown"


def draft_approval_request(hypothesis, action, rollback_plan):
    return {
        "diagnosis": hypothesis["hypothesis"],
        "proposed_action": action,
        "risk_if_wrong": "Brief service interruption (~30s) during rollback if hypothesis is incorrect.",
        "rollback_plan": rollback_plan,
        "status": "AWAITING HUMAN APPROVAL -- NOT EXECUTED",
    }


def diagnose_and_propose(logs, deploys, metrics, urgency_prompt=False):
    severity = classify_severity(metrics)
    incident_start = find_incident_start(logs)
    hypothesis = correlate_with_recent_changes(logs, deploys, incident_start)

    proposed_action = "rollback"
    risk = risk_level(proposed_action)

    if risk == "high":
        request = draft_approval_request(
            hypothesis, proposed_action,
            rollback_plan=f"Revert to {hypothesis['suspect_deploy']['prev_version']}; "
                           f"if that also errors, re-deploy {hypothesis['suspect_deploy']['version']}.")
        if urgency_prompt:
            request["note"] = ("Urgency noted, but high-risk action still requires human "
                                "approval -- not bypassing the gate.")
        return {"severity": severity, "incident_start": incident_start, **request}

    # low-risk path would execute directly; not reached in this scenario
    return {"severity": severity, "incident_start": incident_start,
            "action_executed": proposed_action}


if __name__ == "__main__":
    result = diagnose_and_propose(LOGS, DEPLOY_HISTORY, METRICS, urgency_prompt=True)
    print("=== Diagnostic + Approval Request ===")
    for k, v in result.items():
        print(f"{k}: {v}")

    assert "action_executed" not in result, "High-risk action must never auto-execute!"
    print("\nConfirmed: no destructive action was executed automatically.")
```

### Captured output

```text
=== Diagnostic + Approval Request ===
severity: degraded
incident_start: 14:03:40
diagnosis: Error rate rose starting 14:03:40, shortly after the 14:00:00 deploy of payments-service v2.4.1. Errors are concentrated in the refund code path, consistent with a regression introduced in that release.
proposed_action: rollback
risk_if_wrong: Brief service interruption (~30s) during rollback if hypothesis is incorrect.
rollback_plan: Revert to v2.4.0; if that also errors, re-deploy v2.4.1.
status: AWAITING HUMAN APPROVAL -- NOT EXECUTED
note: Urgency noted, but high-risk action still requires human approval -- not bypassing the gate.

Confirmed: no destructive action was executed automatically.
```

## Assignment 1 source and captured output

Run from the repository root with `python labs/lab_10/assignment_1.py`.

### Full source

```python
# SRN 02FE23BCI038 | Lab 10: Cloud Operations Agent | assignment_1
# Original definitions retained below; extensions follow.
"""
Lab 10: Cloud Operations Agent -- Failed Deployment Diagnosis
Observe -> Reason -> Act, ending in a drafted human-approval request.
The agent NEVER auto-executes the high-risk remediation action, even
under a simulated urgency prompt.
"""

LOGS = [
    {"ts": "14:00:00", "level": "INFO", "msg": "deploy started: payments-service v2.4.1"},
    {"ts": "14:00:45", "level": "INFO", "msg": "deploy completed: payments-service v2.4.1"},
    {"ts": "14:03:10", "level": "WARN", "msg": "refund endpoint latency elevated"},
    {"ts": "14:03:40", "level": "ERROR", "msg": "refund endpoint: NullPointerException in RefundHandler"},
    {"ts": "14:04:05", "level": "ERROR", "msg": "refund endpoint: NullPointerException in RefundHandler"},
    {"ts": "14:04:30", "level": "ERROR", "msg": "refund endpoint: NullPointerException in RefundHandler"},
]

DEPLOY_HISTORY = [
    {"ts": "14:00:00", "service": "payments-service", "version": "v2.4.1", "prev_version": "v2.4.0"},
]

METRICS = {"baseline_error_rate": 0.5, "current_error_rate": 1.6}   # percent


def classify_severity(metrics):
    ratio = metrics["current_error_rate"] / metrics["baseline_error_rate"]
    if metrics["current_error_rate"] > 50:
        return "down"
    if ratio >= 2:
        return "degraded"
    return "early_warning"


def find_incident_start(logs):
    for entry in logs:
        if entry["level"] == "ERROR":
            return entry["ts"]
    return None


def correlate_with_recent_changes(logs, deploys, incident_start):
    error_msgs = [l["msg"] for l in logs if l["level"] == "ERROR"]
    affected_path = "refund" if any("refund" in m.lower() for m in error_msgs) else "unknown"
    for d in deploys:
        if d["ts"] < incident_start and d["service"].lower().startswith("payments"):
            return {
                "hypothesis": (
                    f"Error rate rose starting {incident_start}, shortly after the "
                    f"{d['ts']} deploy of {d['service']} {d['version']}. Errors are "
                    f"concentrated in the {affected_path} code path, consistent with a "
                    f"regression introduced in that release."),
                "suspect_deploy": d,
                "affected_path": affected_path,
            }
    return {"hypothesis": "No recent deploy correlates with the incident window.",
            "suspect_deploy": None, "affected_path": affected_path}


def risk_level(action):
    HIGH_RISK = {"rollback", "scale", "config_change", "delete"}
    LOW_RISK = {"open_ticket", "notify", "restart_single_pod"}
    if action in HIGH_RISK:
        return "high"
    if action in LOW_RISK:
        return "low"
    return "unknown"


def draft_approval_request(hypothesis, action, rollback_plan):
    return {
        "diagnosis": hypothesis["hypothesis"],
        "proposed_action": action,
        "risk_if_wrong": "Brief service interruption (~30s) during rollback if hypothesis is incorrect.",
        "rollback_plan": rollback_plan,
        "status": "AWAITING HUMAN APPROVAL -- NOT EXECUTED",
    }


def diagnose_and_propose(logs, deploys, metrics, urgency_prompt=False):
    severity = classify_severity(metrics)
    incident_start = find_incident_start(logs)
    hypothesis = correlate_with_recent_changes(logs, deploys, incident_start)

    proposed_action = "rollback"
    risk = risk_level(proposed_action)

    if risk == "high":
        request = draft_approval_request(
            hypothesis, proposed_action,
            rollback_plan=f"Revert to {hypothesis['suspect_deploy']['prev_version']}; "
                           f"if that also errors, re-deploy {hypothesis['suspect_deploy']['version']}.")
        if urgency_prompt:
            request["note"] = ("Urgency noted, but high-risk action still requires human "
                                "approval -- not bypassing the gate.")
        return {"severity": severity, "incident_start": incident_start, **request}

    # low-risk path would execute directly; not reached in this scenario
    return {"severity": severity, "incident_start": incident_start,
            "action_executed": proposed_action}



A1=True
A2=False

POOL_LOGS=[{'ts':'15:00:00','level':'INFO','msg':'database-service pool limit changed to 5'}, {'ts':'15:03:00','level':'ERROR','msg':'connection pool exhausted; checkout timeout'}]
POOL_DEPLOYS=[{'ts':'15:00:00','service':'database-service','version':'pool-5','prev_version':'pool-20'}]
POOL_METRICS={'baseline_error_rate':1,'current_error_rate':60}
_BASE_CORRELATE=correlate_with_recent_changes

def correlate_with_recent_changes(logs,deploys,incident_start):
    if any('pool exhausted' in e['msg'] for e in logs):
        candidates=[d for d in deploys if incident_start and d['ts']<incident_start and d['service']=='database-service']
        change=candidates[-1] if candidates else None
        return {'hypothesis':'Connection-pool exhaustion after pool-limit change; correlation needs confirmation.', 'suspect_deploy':change,'affected_path':'database connection checkout'}
    return _BASE_CORRELATE(logs,deploys,incident_start)

def dispatch_action(hypothesis,action,severity):
    if risk_level(action)=='high':
        return draft_approval_request(hypothesis,action,'Restore previous known working configuration after approval')
    if risk_level(action)=='low' and action=='restart_single_pod' and severity=='early_warning':
        # Sandbox executor mutates local pod state; never contacts a cluster.
        pod={'name':'demo-pod','generation':1};pod['generation']+=1
        return {'action_executed':action,'environment':'local simulation','pod':pod}
    return {'status':'blocked','reason':'Action not allowed for this severity or risk'}

def demo():
    reference=diagnose_and_propose(LOGS,DEPLOY_HISTORY,METRICS,True);print('Payments incident:',reference)
    assert 'action_executed' not in reference
    if A1:
        r=diagnose_and_propose(POOL_LOGS,POOL_DEPLOYS,POOL_METRICS);print('Pool logs:',POOL_LOGS);print('Pool history:',POOL_DEPLOYS);print('Pool metrics:',POOL_METRICS);print('Pool incident:',r)
        assert r['severity']!=reference['severity'] and 'pool exhaustion' in r['diagnosis'].lower()
    if A2:
        warning_metrics={'baseline_error_rate':1,'current_error_rate':1.5}
        severity=classify_severity(warning_metrics);h={'hypothesis':'A single unhealthy pod; redundant replicas healthy'}
        r=dispatch_action(h,'restart_single_pod',severity);print('WARNING scenario:',warning_metrics,r);assert r['pod']['generation']==2
        for level in ['early_warning','degraded','down']:
            r=dispatch_action(h,'rollback',level);print('Rollback gate:',level,r);assert 'action_executed' not in r
    print('PASS: scenario-specific diagnosis and risk gate; all operations simulated')

if __name__ == "__main__":
    demo()
```

### Captured output

```text
Payments incident: {'severity': 'degraded', 'incident_start': '14:03:40', 'diagnosis': 'Error rate rose starting 14:03:40, shortly after the 14:00:00 deploy of payments-service v2.4.1. Errors are concentrated in the refund code path, consistent with a regression introduced in that release.', 'proposed_action': 'rollback', 'risk_if_wrong': 'Brief service interruption (~30s) during rollback if hypothesis is incorrect.', 'rollback_plan': 'Revert to v2.4.0; if that also errors, re-deploy v2.4.1.', 'status': 'AWAITING HUMAN APPROVAL -- NOT EXECUTED', 'note': 'Urgency noted, but high-risk action still requires human approval -- not bypassing the gate.'}
Pool logs: [{'ts': '15:00:00', 'level': 'INFO', 'msg': 'database-service pool limit changed to 5'}, {'ts': '15:03:00', 'level': 'ERROR', 'msg': 'connection pool exhausted; checkout timeout'}]
Pool history: [{'ts': '15:00:00', 'service': 'database-service', 'version': 'pool-5', 'prev_version': 'pool-20'}]
Pool metrics: {'baseline_error_rate': 1, 'current_error_rate': 60}
Pool incident: {'severity': 'down', 'incident_start': '15:03:00', 'diagnosis': 'Connection-pool exhaustion after pool-limit change; correlation needs confirmation.', 'proposed_action': 'rollback', 'risk_if_wrong': 'Brief service interruption (~30s) during rollback if hypothesis is incorrect.', 'rollback_plan': 'Revert to pool-20; if that also errors, re-deploy pool-5.', 'status': 'AWAITING HUMAN APPROVAL -- NOT EXECUTED'}
PASS: scenario-specific diagnosis and risk gate; all operations simulated
```

## Assignment 2 source and captured output

Run from the repository root with `python labs/lab_10/assignment_2.py`.

### Full source

```python
# SRN 02FE23BCI038 | Lab 10: Cloud Operations Agent | assignment_2
# Original definitions retained below; extensions follow.
"""
Lab 10: Cloud Operations Agent -- Failed Deployment Diagnosis
Observe -> Reason -> Act, ending in a drafted human-approval request.
The agent NEVER auto-executes the high-risk remediation action, even
under a simulated urgency prompt.
"""

LOGS = [
    {"ts": "14:00:00", "level": "INFO", "msg": "deploy started: payments-service v2.4.1"},
    {"ts": "14:00:45", "level": "INFO", "msg": "deploy completed: payments-service v2.4.1"},
    {"ts": "14:03:10", "level": "WARN", "msg": "refund endpoint latency elevated"},
    {"ts": "14:03:40", "level": "ERROR", "msg": "refund endpoint: NullPointerException in RefundHandler"},
    {"ts": "14:04:05", "level": "ERROR", "msg": "refund endpoint: NullPointerException in RefundHandler"},
    {"ts": "14:04:30", "level": "ERROR", "msg": "refund endpoint: NullPointerException in RefundHandler"},
]

DEPLOY_HISTORY = [
    {"ts": "14:00:00", "service": "payments-service", "version": "v2.4.1", "prev_version": "v2.4.0"},
]

METRICS = {"baseline_error_rate": 0.5, "current_error_rate": 1.6}   # percent


def classify_severity(metrics):
    ratio = metrics["current_error_rate"] / metrics["baseline_error_rate"]
    if metrics["current_error_rate"] > 50:
        return "down"
    if ratio >= 2:
        return "degraded"
    return "early_warning"


def find_incident_start(logs):
    for entry in logs:
        if entry["level"] == "ERROR":
            return entry["ts"]
    return None


def correlate_with_recent_changes(logs, deploys, incident_start):
    error_msgs = [l["msg"] for l in logs if l["level"] == "ERROR"]
    affected_path = "refund" if any("refund" in m.lower() for m in error_msgs) else "unknown"
    for d in deploys:
        if d["ts"] < incident_start and d["service"].lower().startswith("payments"):
            return {
                "hypothesis": (
                    f"Error rate rose starting {incident_start}, shortly after the "
                    f"{d['ts']} deploy of {d['service']} {d['version']}. Errors are "
                    f"concentrated in the {affected_path} code path, consistent with a "
                    f"regression introduced in that release."),
                "suspect_deploy": d,
                "affected_path": affected_path,
            }
    return {"hypothesis": "No recent deploy correlates with the incident window.",
            "suspect_deploy": None, "affected_path": affected_path}


def risk_level(action):
    HIGH_RISK = {"rollback", "scale", "config_change", "delete"}
    LOW_RISK = {"open_ticket", "notify", "restart_single_pod"}
    if action in HIGH_RISK:
        return "high"
    if action in LOW_RISK:
        return "low"
    return "unknown"


def draft_approval_request(hypothesis, action, rollback_plan):
    return {
        "diagnosis": hypothesis["hypothesis"],
        "proposed_action": action,
        "risk_if_wrong": "Brief service interruption (~30s) during rollback if hypothesis is incorrect.",
        "rollback_plan": rollback_plan,
        "status": "AWAITING HUMAN APPROVAL -- NOT EXECUTED",
    }


def diagnose_and_propose(logs, deploys, metrics, urgency_prompt=False):
    severity = classify_severity(metrics)
    incident_start = find_incident_start(logs)
    hypothesis = correlate_with_recent_changes(logs, deploys, incident_start)

    proposed_action = "rollback"
    risk = risk_level(proposed_action)

    if risk == "high":
        request = draft_approval_request(
            hypothesis, proposed_action,
            rollback_plan=f"Revert to {hypothesis['suspect_deploy']['prev_version']}; "
                           f"if that also errors, re-deploy {hypothesis['suspect_deploy']['version']}.")
        if urgency_prompt:
            request["note"] = ("Urgency noted, but high-risk action still requires human "
                                "approval -- not bypassing the gate.")
        return {"severity": severity, "incident_start": incident_start, **request}

    # low-risk path would execute directly; not reached in this scenario
    return {"severity": severity, "incident_start": incident_start,
            "action_executed": proposed_action}



A1=False
A2=True

POOL_LOGS=[{'ts':'15:00:00','level':'INFO','msg':'database-service pool limit changed to 5'}, {'ts':'15:03:00','level':'ERROR','msg':'connection pool exhausted; checkout timeout'}]
POOL_DEPLOYS=[{'ts':'15:00:00','service':'database-service','version':'pool-5','prev_version':'pool-20'}]
POOL_METRICS={'baseline_error_rate':1,'current_error_rate':60}
_BASE_CORRELATE=correlate_with_recent_changes

def correlate_with_recent_changes(logs,deploys,incident_start):
    if any('pool exhausted' in e['msg'] for e in logs):
        candidates=[d for d in deploys if incident_start and d['ts']<incident_start and d['service']=='database-service']
        change=candidates[-1] if candidates else None
        return {'hypothesis':'Connection-pool exhaustion after pool-limit change; correlation needs confirmation.', 'suspect_deploy':change,'affected_path':'database connection checkout'}
    return _BASE_CORRELATE(logs,deploys,incident_start)

def dispatch_action(hypothesis,action,severity):
    if risk_level(action)=='high':
        return draft_approval_request(hypothesis,action,'Restore previous known working configuration after approval')
    if risk_level(action)=='low' and action=='restart_single_pod' and severity=='early_warning':
        # Sandbox executor mutates local pod state; never contacts a cluster.
        pod={'name':'demo-pod','generation':1};pod['generation']+=1
        return {'action_executed':action,'environment':'local simulation','pod':pod}
    return {'status':'blocked','reason':'Action not allowed for this severity or risk'}

def demo():
    reference=diagnose_and_propose(LOGS,DEPLOY_HISTORY,METRICS,True);print('Payments incident:',reference)
    assert 'action_executed' not in reference
    if A1:
        r=diagnose_and_propose(POOL_LOGS,POOL_DEPLOYS,POOL_METRICS);print('Pool logs:',POOL_LOGS);print('Pool history:',POOL_DEPLOYS);print('Pool metrics:',POOL_METRICS);print('Pool incident:',r)
        assert r['severity']!=reference['severity'] and 'pool exhaustion' in r['diagnosis'].lower()
    if A2:
        warning_metrics={'baseline_error_rate':1,'current_error_rate':1.5}
        severity=classify_severity(warning_metrics);h={'hypothesis':'A single unhealthy pod; redundant replicas healthy'}
        r=dispatch_action(h,'restart_single_pod',severity);print('WARNING scenario:',warning_metrics,r);assert r['pod']['generation']==2
        for level in ['early_warning','degraded','down']:
            r=dispatch_action(h,'rollback',level);print('Rollback gate:',level,r);assert 'action_executed' not in r
    print('PASS: scenario-specific diagnosis and risk gate; all operations simulated')

if __name__ == "__main__":
    demo()
```

### Captured output

```text
Payments incident: {'severity': 'degraded', 'incident_start': '14:03:40', 'diagnosis': 'Error rate rose starting 14:03:40, shortly after the 14:00:00 deploy of payments-service v2.4.1. Errors are concentrated in the refund code path, consistent with a regression introduced in that release.', 'proposed_action': 'rollback', 'risk_if_wrong': 'Brief service interruption (~30s) during rollback if hypothesis is incorrect.', 'rollback_plan': 'Revert to v2.4.0; if that also errors, re-deploy v2.4.1.', 'status': 'AWAITING HUMAN APPROVAL -- NOT EXECUTED', 'note': 'Urgency noted, but high-risk action still requires human approval -- not bypassing the gate.'}
WARNING scenario: {'baseline_error_rate': 1, 'current_error_rate': 1.5} {'action_executed': 'restart_single_pod', 'environment': 'local simulation', 'pod': {'name': 'demo-pod', 'generation': 2}}
Rollback gate: early_warning {'diagnosis': 'A single unhealthy pod; redundant replicas healthy', 'proposed_action': 'rollback', 'risk_if_wrong': 'Brief service interruption (~30s) during rollback if hypothesis is incorrect.', 'rollback_plan': 'Restore previous known working configuration after approval', 'status': 'AWAITING HUMAN APPROVAL -- NOT EXECUTED'}
Rollback gate: degraded {'diagnosis': 'A single unhealthy pod; redundant replicas healthy', 'proposed_action': 'rollback', 'risk_if_wrong': 'Brief service interruption (~30s) during rollback if hypothesis is incorrect.', 'rollback_plan': 'Restore previous known working configuration after approval', 'status': 'AWAITING HUMAN APPROVAL -- NOT EXECUTED'}
Rollback gate: down {'diagnosis': 'A single unhealthy pod; redundant replicas healthy', 'proposed_action': 'rollback', 'risk_if_wrong': 'Brief service interruption (~30s) during rollback if hypothesis is incorrect.', 'rollback_plan': 'Restore previous known working configuration after approval', 'status': 'AWAITING HUMAN APPROVAL -- NOT EXECUTED'}
PASS: scenario-specific diagnosis and risk gate; all operations simulated
```

## Combined source and captured output

Run from the repository root with `python labs/lab_10/combined.py`.

### Full source

```python
# SRN 02FE23BCI038 | Lab 10: Cloud Operations Agent | combined
# Original definitions retained below; extensions follow.
"""
Lab 10: Cloud Operations Agent -- Failed Deployment Diagnosis
Observe -> Reason -> Act, ending in a drafted human-approval request.
The agent NEVER auto-executes the high-risk remediation action, even
under a simulated urgency prompt.
"""

LOGS = [
    {"ts": "14:00:00", "level": "INFO", "msg": "deploy started: payments-service v2.4.1"},
    {"ts": "14:00:45", "level": "INFO", "msg": "deploy completed: payments-service v2.4.1"},
    {"ts": "14:03:10", "level": "WARN", "msg": "refund endpoint latency elevated"},
    {"ts": "14:03:40", "level": "ERROR", "msg": "refund endpoint: NullPointerException in RefundHandler"},
    {"ts": "14:04:05", "level": "ERROR", "msg": "refund endpoint: NullPointerException in RefundHandler"},
    {"ts": "14:04:30", "level": "ERROR", "msg": "refund endpoint: NullPointerException in RefundHandler"},
]

DEPLOY_HISTORY = [
    {"ts": "14:00:00", "service": "payments-service", "version": "v2.4.1", "prev_version": "v2.4.0"},
]

METRICS = {"baseline_error_rate": 0.5, "current_error_rate": 1.6}   # percent


def classify_severity(metrics):
    ratio = metrics["current_error_rate"] / metrics["baseline_error_rate"]
    if metrics["current_error_rate"] > 50:
        return "down"
    if ratio >= 2:
        return "degraded"
    return "early_warning"


def find_incident_start(logs):
    for entry in logs:
        if entry["level"] == "ERROR":
            return entry["ts"]
    return None


def correlate_with_recent_changes(logs, deploys, incident_start):
    error_msgs = [l["msg"] for l in logs if l["level"] == "ERROR"]
    affected_path = "refund" if any("refund" in m.lower() for m in error_msgs) else "unknown"
    for d in deploys:
        if d["ts"] < incident_start and d["service"].lower().startswith("payments"):
            return {
                "hypothesis": (
                    f"Error rate rose starting {incident_start}, shortly after the "
                    f"{d['ts']} deploy of {d['service']} {d['version']}. Errors are "
                    f"concentrated in the {affected_path} code path, consistent with a "
                    f"regression introduced in that release."),
                "suspect_deploy": d,
                "affected_path": affected_path,
            }
    return {"hypothesis": "No recent deploy correlates with the incident window.",
            "suspect_deploy": None, "affected_path": affected_path}


def risk_level(action):
    HIGH_RISK = {"rollback", "scale", "config_change", "delete"}
    LOW_RISK = {"open_ticket", "notify", "restart_single_pod"}
    if action in HIGH_RISK:
        return "high"
    if action in LOW_RISK:
        return "low"
    return "unknown"


def draft_approval_request(hypothesis, action, rollback_plan):
    return {
        "diagnosis": hypothesis["hypothesis"],
        "proposed_action": action,
        "risk_if_wrong": "Brief service interruption (~30s) during rollback if hypothesis is incorrect.",
        "rollback_plan": rollback_plan,
        "status": "AWAITING HUMAN APPROVAL -- NOT EXECUTED",
    }


def diagnose_and_propose(logs, deploys, metrics, urgency_prompt=False):
    severity = classify_severity(metrics)
    incident_start = find_incident_start(logs)
    hypothesis = correlate_with_recent_changes(logs, deploys, incident_start)

    proposed_action = "rollback"
    risk = risk_level(proposed_action)

    if risk == "high":
        request = draft_approval_request(
            hypothesis, proposed_action,
            rollback_plan=f"Revert to {hypothesis['suspect_deploy']['prev_version']}; "
                           f"if that also errors, re-deploy {hypothesis['suspect_deploy']['version']}.")
        if urgency_prompt:
            request["note"] = ("Urgency noted, but high-risk action still requires human "
                                "approval -- not bypassing the gate.")
        return {"severity": severity, "incident_start": incident_start, **request}

    # low-risk path would execute directly; not reached in this scenario
    return {"severity": severity, "incident_start": incident_start,
            "action_executed": proposed_action}



A1=True
A2=True

POOL_LOGS=[{'ts':'15:00:00','level':'INFO','msg':'database-service pool limit changed to 5'}, {'ts':'15:03:00','level':'ERROR','msg':'connection pool exhausted; checkout timeout'}]
POOL_DEPLOYS=[{'ts':'15:00:00','service':'database-service','version':'pool-5','prev_version':'pool-20'}]
POOL_METRICS={'baseline_error_rate':1,'current_error_rate':60}
_BASE_CORRELATE=correlate_with_recent_changes

def correlate_with_recent_changes(logs,deploys,incident_start):
    if any('pool exhausted' in e['msg'] for e in logs):
        candidates=[d for d in deploys if incident_start and d['ts']<incident_start and d['service']=='database-service']
        change=candidates[-1] if candidates else None
        return {'hypothesis':'Connection-pool exhaustion after pool-limit change; correlation needs confirmation.', 'suspect_deploy':change,'affected_path':'database connection checkout'}
    return _BASE_CORRELATE(logs,deploys,incident_start)

def dispatch_action(hypothesis,action,severity):
    if risk_level(action)=='high':
        return draft_approval_request(hypothesis,action,'Restore previous known working configuration after approval')
    if risk_level(action)=='low' and action=='restart_single_pod' and severity=='early_warning':
        # Sandbox executor mutates local pod state; never contacts a cluster.
        pod={'name':'demo-pod','generation':1};pod['generation']+=1
        return {'action_executed':action,'environment':'local simulation','pod':pod}
    return {'status':'blocked','reason':'Action not allowed for this severity or risk'}

def demo():
    reference=diagnose_and_propose(LOGS,DEPLOY_HISTORY,METRICS,True);print('Payments incident:',reference)
    assert 'action_executed' not in reference
    if A1:
        r=diagnose_and_propose(POOL_LOGS,POOL_DEPLOYS,POOL_METRICS);print('Pool logs:',POOL_LOGS);print('Pool history:',POOL_DEPLOYS);print('Pool metrics:',POOL_METRICS);print('Pool incident:',r)
        assert r['severity']!=reference['severity'] and 'pool exhaustion' in r['diagnosis'].lower()
    if A2:
        warning_metrics={'baseline_error_rate':1,'current_error_rate':1.5}
        severity=classify_severity(warning_metrics);h={'hypothesis':'A single unhealthy pod; redundant replicas healthy'}
        r=dispatch_action(h,'restart_single_pod',severity);print('WARNING scenario:',warning_metrics,r);assert r['pod']['generation']==2
        for level in ['early_warning','degraded','down']:
            r=dispatch_action(h,'rollback',level);print('Rollback gate:',level,r);assert 'action_executed' not in r
    print('PASS: scenario-specific diagnosis and risk gate; all operations simulated')

if __name__ == "__main__":
    demo()
```

### Captured output

```text
Payments incident: {'severity': 'degraded', 'incident_start': '14:03:40', 'diagnosis': 'Error rate rose starting 14:03:40, shortly after the 14:00:00 deploy of payments-service v2.4.1. Errors are concentrated in the refund code path, consistent with a regression introduced in that release.', 'proposed_action': 'rollback', 'risk_if_wrong': 'Brief service interruption (~30s) during rollback if hypothesis is incorrect.', 'rollback_plan': 'Revert to v2.4.0; if that also errors, re-deploy v2.4.1.', 'status': 'AWAITING HUMAN APPROVAL -- NOT EXECUTED', 'note': 'Urgency noted, but high-risk action still requires human approval -- not bypassing the gate.'}
Pool logs: [{'ts': '15:00:00', 'level': 'INFO', 'msg': 'database-service pool limit changed to 5'}, {'ts': '15:03:00', 'level': 'ERROR', 'msg': 'connection pool exhausted; checkout timeout'}]
Pool history: [{'ts': '15:00:00', 'service': 'database-service', 'version': 'pool-5', 'prev_version': 'pool-20'}]
Pool metrics: {'baseline_error_rate': 1, 'current_error_rate': 60}
Pool incident: {'severity': 'down', 'incident_start': '15:03:00', 'diagnosis': 'Connection-pool exhaustion after pool-limit change; correlation needs confirmation.', 'proposed_action': 'rollback', 'risk_if_wrong': 'Brief service interruption (~30s) during rollback if hypothesis is incorrect.', 'rollback_plan': 'Revert to pool-20; if that also errors, re-deploy pool-5.', 'status': 'AWAITING HUMAN APPROVAL -- NOT EXECUTED'}
WARNING scenario: {'baseline_error_rate': 1, 'current_error_rate': 1.5} {'action_executed': 'restart_single_pod', 'environment': 'local simulation', 'pod': {'name': 'demo-pod', 'generation': 2}}
Rollback gate: early_warning {'diagnosis': 'A single unhealthy pod; redundant replicas healthy', 'proposed_action': 'rollback', 'risk_if_wrong': 'Brief service interruption (~30s) during rollback if hypothesis is incorrect.', 'rollback_plan': 'Restore previous known working configuration after approval', 'status': 'AWAITING HUMAN APPROVAL -- NOT EXECUTED'}
Rollback gate: degraded {'diagnosis': 'A single unhealthy pod; redundant replicas healthy', 'proposed_action': 'rollback', 'risk_if_wrong': 'Brief service interruption (~30s) during rollback if hypothesis is incorrect.', 'rollback_plan': 'Restore previous known working configuration after approval', 'status': 'AWAITING HUMAN APPROVAL -- NOT EXECUTED'}
Rollback gate: down {'diagnosis': 'A single unhealthy pod; redundant replicas healthy', 'proposed_action': 'rollback', 'risk_if_wrong': 'Brief service interruption (~30s) during rollback if hypothesis is incorrect.', 'rollback_plan': 'Restore previous known working configuration after approval', 'status': 'AWAITING HUMAN APPROVAL -- NOT EXECUTED'}
PASS: scenario-specific diagnosis and risk gate; all operations simulated
```

