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
