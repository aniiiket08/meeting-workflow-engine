"""
Lab 2: Tool-Using Agent -- Campus Data Assistant
Three tools (calculator, csv reader, mock events API) with structured
contracts, planner-driven tool selection, and output validation.
"""
import csv
import io

SIGNUPS_CSV = """event,signups
AI Club Talk,12
Hackathon Kickoff,9
Robotics Demo,15
GenAI Workshop,7
Capstone Expo,20
Career Panel,11
"""

MOCK_EVENTS_API_DB = {
    "AI Club Talk": {"date": "2026-07-02", "location": "CS Block Auditorium"},
    "Hackathon Kickoff": {"date": "2026-07-05", "location": "Innovation Lab"},
}


def calculator(operation, values):
    if operation == "average":
        if not values:
            return {"error": "no values supplied"}
        return {"result": sum(values) / len(values)}
    if operation == "sum":
        return {"result": sum(values)}
    return {"error": f"unsupported operation: {operation}"}


def read_csv(source_text=SIGNUPS_CSV):
    reader = csv.DictReader(io.StringIO(source_text))
    rows = list(reader)
    if not rows:
        return {"error": "empty file", "rows": [], "row_count": 0}
    return {"rows": rows, "row_count": len(rows)}


def mock_events_api(event_name):
    record = MOCK_EVENTS_API_DB.get(event_name)
    if record is None:
        return {"error": f"no event metadata found for '{event_name}'"}
    return record


TOOLS = {"calculator": calculator, "read_csv": read_csv, "events_api": mock_events_api}


class CampusDataAssistant:
    def __init__(self):
        self.trace = []

    def _call(self, tool_name, reason, **kwargs):
        result = TOOLS[tool_name](**kwargs)
        entry = {"tool": tool_name, "reason": reason, "input": kwargs, "output": result}
        self.trace.append(entry)
        if "error" in result:
            raise RuntimeError(f"{tool_name} failed: {result['error']}")
        return result

    def answer(self, question):
        q = question.lower()

        if "average" in q and "sign" in q:
            csv_result = self._call(
                "read_csv", "sign-up counts live in the CSV export, not the events API")
            values = [int(r["signups"]) for r in csv_result["rows"]]
            total = self._call("calculator", "sum the extracted signup column",
                                operation="sum", values=values)
            avg = self._call("calculator", "compute average over the same column",
                              operation="average", values=values)
            return (f"Total sign-ups: {total['result']}. "
                    f"Average per event: {avg['result']:.2f} "
                    f"(across {csv_result['row_count']} events).")

        if "where" in q and "hackathon" in q:
            meta = self._call(
                "events_api", "location/date metadata lives in the events API, not the CSV",
                event_name="Hackathon Kickoff")
            return f"Hackathon Kickoff is at {meta['location']} on {meta['date']}."

        if "where" in q and "capstone" in q:
            try:
                meta = self._call(
                    "events_api", "checking events API for Capstone Expo metadata",
                    event_name="Capstone Expo")
                return f"Capstone Expo is at {meta['location']} on {meta['date']}."
            except RuntimeError:
                return "I don't have location/date metadata for Capstone Expo in the events API."

        return "I don't have a tool path configured for that question."


if __name__ == "__main__":
    assistant = CampusDataAssistant()
    questions = [
        "How many students signed up for events this month, and what's the average per event?",
        "Where and when is the Hackathon Kickoff?",
        "Where and when is the Capstone Expo?",
    ]
    for q in questions:
        print(f"\nQ: {q}")
        print(f"A: {assistant.answer(q)}")

    print("\n=== Full tool trace ===")
    for i, entry in enumerate(assistant.trace, 1):
        print(f"{i}. tool={entry['tool']}  reason=\"{entry['reason']}\"")
        print(f"   input={entry['input']}")
        print(f"   output={entry['output']}")
