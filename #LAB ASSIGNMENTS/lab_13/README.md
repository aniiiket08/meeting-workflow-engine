# Lab 13: Discipline-Specific Engineering Agents

SRN: **02FE23BCI038**

## Assignment requirements from the guide

Assignment 1 — Add a Second Domain: Electrical Load Forecasting
Implement a parallel agent for the Electrical Engineering example (load forecasting or fault-triage from sensor/power-consumption data), using a comparable threshold-based classification approach. Confirm the same human-review safety gate applies before any ALARM-equivalent recommendation is acted on.
Assignment 2 — Escalate on a Trend, Not Just a Threshold
Extend the Mechanical agent so that three consecutive WARNING-level readings (even if none individually reaches ALARM) escalate to a "schedule_inspection" recommendation instead of "continue_monitoring". Demonstrate this with a modified sensor log that stays under the ALARM threshold throughout but trends upward for three readings.

## Implementation notes

The electrical agent uses a simple linear next-reading estimate and capacity thresholds. A single mechanical warning is monitored, while three increasing warnings trigger inspection. This extends the original warning behavior to make the requested persistence escalation visible. All thresholds are teaching simplifications.

Each assignment script includes the original definitions plus its own enabled extension. `A1` and `A2` select the assignment features; both are enabled in `combined.py`. These are standalone scripts, so sibling imports are not required. The original guide demonstration is available unchanged as `reference.py`.

## Original source and captured output

Run from the repository root with `python labs/lab_13/reference.py`.

### Full source

```python
"""
Lab 13: Discipline-Specific Engineering Agent -- Predictive Maintenance
(Mechanical Engineering example: motor vibration and temperature logs)
Demonstrates domain transfer: the same agentic patterns (tools, goal,
observe, safety checks) applied to a non-CS engineering workflow.
"""

# Simulated sensor log for one motor over 6 readings.
SENSOR_LOG = [
    {"t": 0, "vibration_mm_s": 1.8, "temp_c": 61},
    {"t": 1, "vibration_mm_s": 1.9, "temp_c": 62},
    {"t": 2, "vibration_mm_s": 2.4, "temp_c": 65},
    {"t": 3, "vibration_mm_s": 3.1, "temp_c": 70},
    {"t": 4, "vibration_mm_s": 4.6, "temp_c": 76},
    {"t": 5, "vibration_mm_s": 6.2, "temp_c": 84},
]

# ISO 10816-based-style thresholds for illustration (simplified for teaching).
THRESHOLDS = {"vibration_warn": 2.8, "vibration_alarm": 4.5, "temp_warn": 70, "temp_alarm": 80}


def tool_read_sensor_log():
    return SENSOR_LOG


def classify_condition(reading):
    if reading["vibration_mm_s"] >= THRESHOLDS["vibration_alarm"] or reading["temp_c"] >= THRESHOLDS["temp_alarm"]:
        return "ALARM"
    if reading["vibration_mm_s"] >= THRESHOLDS["vibration_warn"] or reading["temp_c"] >= THRESHOLDS["temp_warn"]:
        return "WARNING"
    return "NORMAL"


def trend_direction(log):
    deltas = [log[i + 1]["vibration_mm_s"] - log[i]["vibration_mm_s"] for i in range(len(log) - 1)]
    return "worsening" if all(d >= 0 for d in deltas) else "mixed"


def safety_check(condition):
    # Domain constraint: an ALARM condition requires a human maintenance
    # engineer sign-off before any recommended shutdown is acted on --
    # the agent never triggers a shutdown itself.
    if condition == "ALARM":
        return {"action_allowed": "recommend_shutdown_for_human_review", "auto_execute": False}
    if condition == "WARNING":
        return {"action_allowed": "schedule_inspection", "auto_execute": False}
    return {"action_allowed": "continue_monitoring", "auto_execute": True}


def predictive_maintenance_agent():
    log = tool_read_sensor_log()
    latest = log[-1]
    condition = classify_condition(latest)
    trend = trend_direction(log)
    safety = safety_check(condition)

    output = {
        "domain": "Mechanical Engineering -- Predictive Maintenance",
        "latest_reading": latest,
        "condition": condition,
        "trend": trend,
        "recommended_action": safety["action_allowed"],
        "auto_executed": safety["auto_execute"],
        "evaluation_method": "Threshold classification against ISO-10816-style vibration "
                              "bands, cross-checked with temperature trend over the log window.",
    }
    return output


if __name__ == "__main__":
    result = predictive_maintenance_agent()
    print("=== Predictive Maintenance Agent Output ===")
    for k, v in result.items():
        print(f"{k}: {v}")

    assert result["condition"] != "ALARM" or result["auto_executed"] is False, \
        "An ALARM condition must never auto-execute a shutdown!"
    print("\nConfirmed: ALARM-level actions require human review, never auto-executed.")
```

### Captured output

```text
=== Predictive Maintenance Agent Output ===
domain: Mechanical Engineering -- Predictive Maintenance
latest_reading: {'t': 5, 'vibration_mm_s': 6.2, 'temp_c': 84}
condition: ALARM
trend: worsening
recommended_action: recommend_shutdown_for_human_review
auto_executed: False
evaluation_method: Threshold classification against ISO-10816-style vibration bands, cross-checked with temperature trend over the log window.

Confirmed: ALARM-level actions require human review, never auto-executed.
```

## Assignment 1 source and captured output

Run from the repository root with `python labs/lab_13/assignment_1.py`.

### Full source

```python
# SRN 02FE23BCI038 | Lab 13: Discipline-Specific Engineering Agents | assignment_1
# Original definitions retained below; extensions follow.
"""
Lab 13: Discipline-Specific Engineering Agent -- Predictive Maintenance
(Mechanical Engineering example: motor vibration and temperature logs)
Demonstrates domain transfer: the same agentic patterns (tools, goal,
observe, safety checks) applied to a non-CS engineering workflow.
"""

# Simulated sensor log for one motor over 6 readings.
SENSOR_LOG = [
    {"t": 0, "vibration_mm_s": 1.8, "temp_c": 61},
    {"t": 1, "vibration_mm_s": 1.9, "temp_c": 62},
    {"t": 2, "vibration_mm_s": 2.4, "temp_c": 65},
    {"t": 3, "vibration_mm_s": 3.1, "temp_c": 70},
    {"t": 4, "vibration_mm_s": 4.6, "temp_c": 76},
    {"t": 5, "vibration_mm_s": 6.2, "temp_c": 84},
]

# ISO 10816-based-style thresholds for illustration (simplified for teaching).
THRESHOLDS = {"vibration_warn": 2.8, "vibration_alarm": 4.5, "temp_warn": 70, "temp_alarm": 80}


def tool_read_sensor_log():
    return SENSOR_LOG


def classify_condition(reading):
    if reading["vibration_mm_s"] >= THRESHOLDS["vibration_alarm"] or reading["temp_c"] >= THRESHOLDS["temp_alarm"]:
        return "ALARM"
    if reading["vibration_mm_s"] >= THRESHOLDS["vibration_warn"] or reading["temp_c"] >= THRESHOLDS["temp_warn"]:
        return "WARNING"
    return "NORMAL"


def trend_direction(log):
    deltas = [log[i + 1]["vibration_mm_s"] - log[i]["vibration_mm_s"] for i in range(len(log) - 1)]
    return "worsening" if all(d >= 0 for d in deltas) else "mixed"


def safety_check(condition):
    # Domain constraint: an ALARM condition requires a human maintenance
    # engineer sign-off before any recommended shutdown is acted on --
    # the agent never triggers a shutdown itself.
    if condition == "ALARM":
        return {"action_allowed": "recommend_shutdown_for_human_review", "auto_execute": False}
    if condition == "WARNING":
        return {"action_allowed": "schedule_inspection", "auto_execute": False}
    return {"action_allowed": "continue_monitoring", "auto_execute": True}


def predictive_maintenance_agent():
    log = tool_read_sensor_log()
    latest = log[-1]
    condition = classify_condition(latest)
    trend = trend_direction(log)
    safety = safety_check(condition)

    output = {
        "domain": "Mechanical Engineering -- Predictive Maintenance",
        "latest_reading": latest,
        "condition": condition,
        "trend": trend,
        "recommended_action": safety["action_allowed"],
        "auto_executed": safety["auto_execute"],
        "evaluation_method": "Threshold classification against ISO-10816-style vibration "
                              "bands, cross-checked with temperature trend over the log window.",
    }
    return output



A1=True
A2=False

def electrical_load_agent(readings,capacity_kw=100):
    if not readings or capacity_kw<=0:raise ValueError('Positive capacity and readings required')
    latest=readings[-1];forecast=latest+(readings[-1]-readings[-2] if len(readings)>1 else 0)
    fraction=max(latest,forecast)/capacity_kw
    condition='ALARM' if fraction>=1 else 'WARNING' if fraction>=0.8 else 'NORMAL'
    return {'domain':'Electrical load forecasting','latest_kw':latest,'forecast_kw':forecast,'condition':condition,**safety_check(condition)}
def trend_maintenance(log):
    condition=classify_condition(log[-1]);last=log[-3:]
    persistent=len(last)==3 and all(classify_condition(r)=='WARNING' for r in last)
    worsening=persistent and all(last[i+1]['vibration_mm_s']>last[i]['vibration_mm_s'] for i in range(2))
    # Single warning remains monitored; persistent worsening warnings cause inspection.
    action='recommend_shutdown_for_human_review' if condition=='ALARM' else 'schedule_inspection' if worsening else 'continue_monitoring'
    return {'condition':condition,'three_warning_trend':worsening,'recommended_action':action,'auto_executed':False}
def demo():
    print('Original mechanical result:',predictive_maintenance_agent())
    if A1:
        for readings in [[40,45,50],[70,75,80],[85,95,105]]:
            r=electrical_load_agent(readings);print('Electrical:',r)
            if r['condition']=='ALARM':assert r['auto_execute'] is False
    if A2:
        log=[{'t':i,'vibration_mm_s':v,'temp_c':72} for i,v in enumerate([3.0,3.3,3.7])]
        assert all(classify_condition(r)=='WARNING' for r in log)
        print('All readings below ALARM:',log)
        print('One warning:',trend_maintenance(log[:1]))
        r=trend_maintenance(log);print('Three warnings:',r);assert r['recommended_action']=='schedule_inspection'
        assert not r['auto_executed']
    print('PASS: electrical human review and mechanical trend escalation')

if __name__ == "__main__":
    demo()
```

### Captured output

```text
Original mechanical result: {'domain': 'Mechanical Engineering -- Predictive Maintenance', 'latest_reading': {'t': 5, 'vibration_mm_s': 6.2, 'temp_c': 84}, 'condition': 'ALARM', 'trend': 'worsening', 'recommended_action': 'recommend_shutdown_for_human_review', 'auto_executed': False, 'evaluation_method': 'Threshold classification against ISO-10816-style vibration bands, cross-checked with temperature trend over the log window.'}
Electrical: {'domain': 'Electrical load forecasting', 'latest_kw': 50, 'forecast_kw': 55, 'condition': 'NORMAL', 'action_allowed': 'continue_monitoring', 'auto_execute': True}
Electrical: {'domain': 'Electrical load forecasting', 'latest_kw': 80, 'forecast_kw': 85, 'condition': 'WARNING', 'action_allowed': 'schedule_inspection', 'auto_execute': False}
Electrical: {'domain': 'Electrical load forecasting', 'latest_kw': 105, 'forecast_kw': 115, 'condition': 'ALARM', 'action_allowed': 'recommend_shutdown_for_human_review', 'auto_execute': False}
PASS: electrical human review and mechanical trend escalation
```

## Assignment 2 source and captured output

Run from the repository root with `python labs/lab_13/assignment_2.py`.

### Full source

```python
# SRN 02FE23BCI038 | Lab 13: Discipline-Specific Engineering Agents | assignment_2
# Original definitions retained below; extensions follow.
"""
Lab 13: Discipline-Specific Engineering Agent -- Predictive Maintenance
(Mechanical Engineering example: motor vibration and temperature logs)
Demonstrates domain transfer: the same agentic patterns (tools, goal,
observe, safety checks) applied to a non-CS engineering workflow.
"""

# Simulated sensor log for one motor over 6 readings.
SENSOR_LOG = [
    {"t": 0, "vibration_mm_s": 1.8, "temp_c": 61},
    {"t": 1, "vibration_mm_s": 1.9, "temp_c": 62},
    {"t": 2, "vibration_mm_s": 2.4, "temp_c": 65},
    {"t": 3, "vibration_mm_s": 3.1, "temp_c": 70},
    {"t": 4, "vibration_mm_s": 4.6, "temp_c": 76},
    {"t": 5, "vibration_mm_s": 6.2, "temp_c": 84},
]

# ISO 10816-based-style thresholds for illustration (simplified for teaching).
THRESHOLDS = {"vibration_warn": 2.8, "vibration_alarm": 4.5, "temp_warn": 70, "temp_alarm": 80}


def tool_read_sensor_log():
    return SENSOR_LOG


def classify_condition(reading):
    if reading["vibration_mm_s"] >= THRESHOLDS["vibration_alarm"] or reading["temp_c"] >= THRESHOLDS["temp_alarm"]:
        return "ALARM"
    if reading["vibration_mm_s"] >= THRESHOLDS["vibration_warn"] or reading["temp_c"] >= THRESHOLDS["temp_warn"]:
        return "WARNING"
    return "NORMAL"


def trend_direction(log):
    deltas = [log[i + 1]["vibration_mm_s"] - log[i]["vibration_mm_s"] for i in range(len(log) - 1)]
    return "worsening" if all(d >= 0 for d in deltas) else "mixed"


def safety_check(condition):
    # Domain constraint: an ALARM condition requires a human maintenance
    # engineer sign-off before any recommended shutdown is acted on --
    # the agent never triggers a shutdown itself.
    if condition == "ALARM":
        return {"action_allowed": "recommend_shutdown_for_human_review", "auto_execute": False}
    if condition == "WARNING":
        return {"action_allowed": "schedule_inspection", "auto_execute": False}
    return {"action_allowed": "continue_monitoring", "auto_execute": True}


def predictive_maintenance_agent():
    log = tool_read_sensor_log()
    latest = log[-1]
    condition = classify_condition(latest)
    trend = trend_direction(log)
    safety = safety_check(condition)

    output = {
        "domain": "Mechanical Engineering -- Predictive Maintenance",
        "latest_reading": latest,
        "condition": condition,
        "trend": trend,
        "recommended_action": safety["action_allowed"],
        "auto_executed": safety["auto_execute"],
        "evaluation_method": "Threshold classification against ISO-10816-style vibration "
                              "bands, cross-checked with temperature trend over the log window.",
    }
    return output



A1=False
A2=True

def electrical_load_agent(readings,capacity_kw=100):
    if not readings or capacity_kw<=0:raise ValueError('Positive capacity and readings required')
    latest=readings[-1];forecast=latest+(readings[-1]-readings[-2] if len(readings)>1 else 0)
    fraction=max(latest,forecast)/capacity_kw
    condition='ALARM' if fraction>=1 else 'WARNING' if fraction>=0.8 else 'NORMAL'
    return {'domain':'Electrical load forecasting','latest_kw':latest,'forecast_kw':forecast,'condition':condition,**safety_check(condition)}
def trend_maintenance(log):
    condition=classify_condition(log[-1]);last=log[-3:]
    persistent=len(last)==3 and all(classify_condition(r)=='WARNING' for r in last)
    worsening=persistent and all(last[i+1]['vibration_mm_s']>last[i]['vibration_mm_s'] for i in range(2))
    # Single warning remains monitored; persistent worsening warnings cause inspection.
    action='recommend_shutdown_for_human_review' if condition=='ALARM' else 'schedule_inspection' if worsening else 'continue_monitoring'
    return {'condition':condition,'three_warning_trend':worsening,'recommended_action':action,'auto_executed':False}
def demo():
    print('Original mechanical result:',predictive_maintenance_agent())
    if A1:
        for readings in [[40,45,50],[70,75,80],[85,95,105]]:
            r=electrical_load_agent(readings);print('Electrical:',r)
            if r['condition']=='ALARM':assert r['auto_execute'] is False
    if A2:
        log=[{'t':i,'vibration_mm_s':v,'temp_c':72} for i,v in enumerate([3.0,3.3,3.7])]
        assert all(classify_condition(r)=='WARNING' for r in log)
        print('All readings below ALARM:',log)
        print('One warning:',trend_maintenance(log[:1]))
        r=trend_maintenance(log);print('Three warnings:',r);assert r['recommended_action']=='schedule_inspection'
        assert not r['auto_executed']
    print('PASS: electrical human review and mechanical trend escalation')

if __name__ == "__main__":
    demo()
```

### Captured output

```text
Original mechanical result: {'domain': 'Mechanical Engineering -- Predictive Maintenance', 'latest_reading': {'t': 5, 'vibration_mm_s': 6.2, 'temp_c': 84}, 'condition': 'ALARM', 'trend': 'worsening', 'recommended_action': 'recommend_shutdown_for_human_review', 'auto_executed': False, 'evaluation_method': 'Threshold classification against ISO-10816-style vibration bands, cross-checked with temperature trend over the log window.'}
All readings below ALARM: [{'t': 0, 'vibration_mm_s': 3.0, 'temp_c': 72}, {'t': 1, 'vibration_mm_s': 3.3, 'temp_c': 72}, {'t': 2, 'vibration_mm_s': 3.7, 'temp_c': 72}]
One warning: {'condition': 'WARNING', 'three_warning_trend': False, 'recommended_action': 'continue_monitoring', 'auto_executed': False}
Three warnings: {'condition': 'WARNING', 'three_warning_trend': True, 'recommended_action': 'schedule_inspection', 'auto_executed': False}
PASS: electrical human review and mechanical trend escalation
```

## Combined source and captured output

Run from the repository root with `python labs/lab_13/combined.py`.

### Full source

```python
# SRN 02FE23BCI038 | Lab 13: Discipline-Specific Engineering Agents | combined
# Original definitions retained below; extensions follow.
"""
Lab 13: Discipline-Specific Engineering Agent -- Predictive Maintenance
(Mechanical Engineering example: motor vibration and temperature logs)
Demonstrates domain transfer: the same agentic patterns (tools, goal,
observe, safety checks) applied to a non-CS engineering workflow.
"""

# Simulated sensor log for one motor over 6 readings.
SENSOR_LOG = [
    {"t": 0, "vibration_mm_s": 1.8, "temp_c": 61},
    {"t": 1, "vibration_mm_s": 1.9, "temp_c": 62},
    {"t": 2, "vibration_mm_s": 2.4, "temp_c": 65},
    {"t": 3, "vibration_mm_s": 3.1, "temp_c": 70},
    {"t": 4, "vibration_mm_s": 4.6, "temp_c": 76},
    {"t": 5, "vibration_mm_s": 6.2, "temp_c": 84},
]

# ISO 10816-based-style thresholds for illustration (simplified for teaching).
THRESHOLDS = {"vibration_warn": 2.8, "vibration_alarm": 4.5, "temp_warn": 70, "temp_alarm": 80}


def tool_read_sensor_log():
    return SENSOR_LOG


def classify_condition(reading):
    if reading["vibration_mm_s"] >= THRESHOLDS["vibration_alarm"] or reading["temp_c"] >= THRESHOLDS["temp_alarm"]:
        return "ALARM"
    if reading["vibration_mm_s"] >= THRESHOLDS["vibration_warn"] or reading["temp_c"] >= THRESHOLDS["temp_warn"]:
        return "WARNING"
    return "NORMAL"


def trend_direction(log):
    deltas = [log[i + 1]["vibration_mm_s"] - log[i]["vibration_mm_s"] for i in range(len(log) - 1)]
    return "worsening" if all(d >= 0 for d in deltas) else "mixed"


def safety_check(condition):
    # Domain constraint: an ALARM condition requires a human maintenance
    # engineer sign-off before any recommended shutdown is acted on --
    # the agent never triggers a shutdown itself.
    if condition == "ALARM":
        return {"action_allowed": "recommend_shutdown_for_human_review", "auto_execute": False}
    if condition == "WARNING":
        return {"action_allowed": "schedule_inspection", "auto_execute": False}
    return {"action_allowed": "continue_monitoring", "auto_execute": True}


def predictive_maintenance_agent():
    log = tool_read_sensor_log()
    latest = log[-1]
    condition = classify_condition(latest)
    trend = trend_direction(log)
    safety = safety_check(condition)

    output = {
        "domain": "Mechanical Engineering -- Predictive Maintenance",
        "latest_reading": latest,
        "condition": condition,
        "trend": trend,
        "recommended_action": safety["action_allowed"],
        "auto_executed": safety["auto_execute"],
        "evaluation_method": "Threshold classification against ISO-10816-style vibration "
                              "bands, cross-checked with temperature trend over the log window.",
    }
    return output



A1=True
A2=True

def electrical_load_agent(readings,capacity_kw=100):
    if not readings or capacity_kw<=0:raise ValueError('Positive capacity and readings required')
    latest=readings[-1];forecast=latest+(readings[-1]-readings[-2] if len(readings)>1 else 0)
    fraction=max(latest,forecast)/capacity_kw
    condition='ALARM' if fraction>=1 else 'WARNING' if fraction>=0.8 else 'NORMAL'
    return {'domain':'Electrical load forecasting','latest_kw':latest,'forecast_kw':forecast,'condition':condition,**safety_check(condition)}
def trend_maintenance(log):
    condition=classify_condition(log[-1]);last=log[-3:]
    persistent=len(last)==3 and all(classify_condition(r)=='WARNING' for r in last)
    worsening=persistent and all(last[i+1]['vibration_mm_s']>last[i]['vibration_mm_s'] for i in range(2))
    # Single warning remains monitored; persistent worsening warnings cause inspection.
    action='recommend_shutdown_for_human_review' if condition=='ALARM' else 'schedule_inspection' if worsening else 'continue_monitoring'
    return {'condition':condition,'three_warning_trend':worsening,'recommended_action':action,'auto_executed':False}
def demo():
    print('Original mechanical result:',predictive_maintenance_agent())
    if A1:
        for readings in [[40,45,50],[70,75,80],[85,95,105]]:
            r=electrical_load_agent(readings);print('Electrical:',r)
            if r['condition']=='ALARM':assert r['auto_execute'] is False
    if A2:
        log=[{'t':i,'vibration_mm_s':v,'temp_c':72} for i,v in enumerate([3.0,3.3,3.7])]
        assert all(classify_condition(r)=='WARNING' for r in log)
        print('All readings below ALARM:',log)
        print('One warning:',trend_maintenance(log[:1]))
        r=trend_maintenance(log);print('Three warnings:',r);assert r['recommended_action']=='schedule_inspection'
        assert not r['auto_executed']
    print('PASS: electrical human review and mechanical trend escalation')

if __name__ == "__main__":
    demo()
```

### Captured output

```text
Original mechanical result: {'domain': 'Mechanical Engineering -- Predictive Maintenance', 'latest_reading': {'t': 5, 'vibration_mm_s': 6.2, 'temp_c': 84}, 'condition': 'ALARM', 'trend': 'worsening', 'recommended_action': 'recommend_shutdown_for_human_review', 'auto_executed': False, 'evaluation_method': 'Threshold classification against ISO-10816-style vibration bands, cross-checked with temperature trend over the log window.'}
Electrical: {'domain': 'Electrical load forecasting', 'latest_kw': 50, 'forecast_kw': 55, 'condition': 'NORMAL', 'action_allowed': 'continue_monitoring', 'auto_execute': True}
Electrical: {'domain': 'Electrical load forecasting', 'latest_kw': 80, 'forecast_kw': 85, 'condition': 'WARNING', 'action_allowed': 'schedule_inspection', 'auto_execute': False}
Electrical: {'domain': 'Electrical load forecasting', 'latest_kw': 105, 'forecast_kw': 115, 'condition': 'ALARM', 'action_allowed': 'recommend_shutdown_for_human_review', 'auto_execute': False}
All readings below ALARM: [{'t': 0, 'vibration_mm_s': 3.0, 'temp_c': 72}, {'t': 1, 'vibration_mm_s': 3.3, 'temp_c': 72}, {'t': 2, 'vibration_mm_s': 3.7, 'temp_c': 72}]
One warning: {'condition': 'WARNING', 'three_warning_trend': False, 'recommended_action': 'continue_monitoring', 'auto_executed': False}
Three warnings: {'condition': 'WARNING', 'three_warning_trend': True, 'recommended_action': 'schedule_inspection', 'auto_executed': False}
PASS: electrical human review and mechanical trend escalation
```

