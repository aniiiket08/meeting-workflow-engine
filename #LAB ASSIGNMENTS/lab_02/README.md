# Lab 2: Tool-Using Agent

SRN: **02FE23BCI038**

## Assignment requirements from the guide

Assignment 1 — Add a Notification Tool with Justified Use
Add a fourth tool, `send_notification(message)`, that only drafts a message (it must not actually send anything). Extend the assistant so that when the computed average sign-ups falls below a threshold you define (e.g. 10), it calls this tool to draft a low-turnout notice, and states in the trace why the tool was needed. Submit the updated code and a transcript showing the notification being drafted with its justification.
Assignment 2 — A Three-Tool Chain
Add a category field to the CSV data (e.g. "technical" vs "social") and implement a new question ("What's the average sign-up for technical events only?") that requires three steps: read the CSV, filter rows by category, then compute the average over the filtered subset. Validate the filter step's output (non-empty) before computing the average. Submit the updated code and the trace for this new question.

## Implementation notes

The notification is a draft only. A category CSV supplies a low-turnout fixture. The filter is an explicit validated tool between CSV reading and calculation.

Each assignment script includes the original definitions plus its own enabled extension. `A1` and `A2` select the assignment features; both are enabled in `combined.py`. These are standalone scripts, so sibling imports are not required. The original guide demonstration is available unchanged as `reference.py`.

## Original source and captured output

Run from the repository root with `python labs/lab_02/reference.py`.

### Full source

```python
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
```

### Captured output

```text

Q: How many students signed up for events this month, and what's the average per event?
A: Total sign-ups: 74. Average per event: 12.33 (across 6 events).

Q: Where and when is the Hackathon Kickoff?
A: Hackathon Kickoff is at Innovation Lab on 2026-07-05.

Q: Where and when is the Capstone Expo?
A: I don't have location/date metadata for Capstone Expo in the events API.

=== Full tool trace ===
1. tool=read_csv  reason="sign-up counts live in the CSV export, not the events API"
   input={}
   output={'rows': [{'event': 'AI Club Talk', 'signups': '12'}, {'event': 'Hackathon Kickoff', 'signups': '9'}, {'event': 'Robotics Demo', 'signups': '15'}, {'event': 'GenAI Workshop', 'signups': '7'}, {'event': 'Capstone Expo', 'signups': '20'}, {'event': 'Career Panel', 'signups': '11'}], 'row_count': 6}
2. tool=calculator  reason="sum the extracted signup column"
   input={'operation': 'sum', 'values': [12, 9, 15, 7, 20, 11]}
   output={'result': 74}
3. tool=calculator  reason="compute average over the same column"
   input={'operation': 'average', 'values': [12, 9, 15, 7, 20, 11]}
   output={'result': 12.333333333333334}
4. tool=events_api  reason="location/date metadata lives in the events API, not the CSV"
   input={'event_name': 'Hackathon Kickoff'}
   output={'date': '2026-07-05', 'location': 'Innovation Lab'}
5. tool=events_api  reason="checking events API for Capstone Expo metadata"
   input={'event_name': 'Capstone Expo'}
   output={'error': "no event metadata found for 'Capstone Expo'"}
```

## Assignment 1 source and captured output

Run from the repository root with `python labs/lab_02/assignment_1.py`.

### Full source

```python
# SRN 02FE23BCI038 | Lab 2: Tool-Using Agent | assignment_1
# Original definitions retained below; extensions follow.
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



A1=True
A2=False

import json
CATEGORY_CSV = "event,signups,category\nAI Talk,6,technical\nHackathon,8,technical\nSocial Mixer,12,social\n"
def send_notification(message):
    return {'draft': message, 'sent': False}
def filter_category(rows, category):
    matches = [r for r in rows if r.get('category') == category]
    return {'rows': matches} if matches else {'error': 'no matching rows'}
TOOLS.update(send_notification=send_notification, filter_category=filter_category)
TOOL_SCHEMAS = {
    'read_csv': {'input': {'source_text': 'str'}, 'output': {'rows': 'list', 'row_count': 'int'}},
    'filter_category': {'input': {'rows': 'list', 'category': 'str'}, 'output': {'rows': 'nonempty list OR error'}},
    'calculator': {'input': {'operation': 'sum|average', 'values': 'list[number]'}, 'output': {'result': 'number OR error'}},
    'events_api': {'input': {'event_name': 'str'}, 'output': {'date': 'str', 'location': 'str OR error'}},
    'send_notification': {'input': {'message': 'str'}, 'output': {'draft': 'str', 'sent': 'false'}}}
class ExtendedCampusAssistant(CampusDataAssistant):
    def answer(self, question):
        if 'average' not in question.lower():
            return super().answer(question)
        rows = self._call('read_csv', 'Load signups and categories from CSV', source_text=CATEGORY_CSV)['rows']
        if A2 and 'technical' in question.lower():
            rows = self._call('filter_category', 'Restrict calculation to requested technical category', rows=rows, category='technical')['rows']
        avg = self._call('calculator', 'Average validated nonempty numeric signup subset', operation='average', values=[int(r['signups']) for r in rows])['result']
        result = {'average': avg, 'event_count': len(rows)}
        if A1 and avg < 10:
            result['notification'] = self._call('send_notification', f'Average {avg:.2f} is below defined threshold 10', message=f'Low turnout: average signups {avg:.2f}; consider publicity.')
        return result

def demo():
    a = ExtendedCampusAssistant()
    print('Tool schemas:', json.dumps(TOOL_SCHEMAS, indent=2))
    q = "What's the average sign-up for technical events only?" if A2 else "What's the average sign-up?"
    print('Question:', q)
    r = a.answer(q); print('Answer:', r)
    assert r['average'] == (7 if A2 else 26/3)
    if A1: assert r['notification']['sent'] is False
    if A2:
        assert [x['tool'] for x in a.trace][:3] == ['read_csv','filter_category','calculator']
        try: a._call('filter_category','Validate absent category', rows=[], category='technical')
        except RuntimeError as e: print('Empty subset blocked:', e)
        else: raise AssertionError('Empty subset accepted')
    print('Trace:', json.dumps(a.trace, indent=2))
    print('PASS: justified drafting and validated tool chain')

if __name__ == "__main__":
    demo()
```

### Captured output

```text
Tool schemas: {
  "read_csv": {
    "input": {
      "source_text": "str"
    },
    "output": {
      "rows": "list",
      "row_count": "int"
    }
  },
  "filter_category": {
    "input": {
      "rows": "list",
      "category": "str"
    },
    "output": {
      "rows": "nonempty list OR error"
    }
  },
  "calculator": {
    "input": {
      "operation": "sum|average",
      "values": "list[number]"
    },
    "output": {
      "result": "number OR error"
    }
  },
  "events_api": {
    "input": {
      "event_name": "str"
    },
    "output": {
      "date": "str",
      "location": "str OR error"
    }
  },
  "send_notification": {
    "input": {
      "message": "str"
    },
    "output": {
      "draft": "str",
      "sent": "false"
    }
  }
}
Question: What's the average sign-up?
Answer: {'average': 8.666666666666666, 'event_count': 3, 'notification': {'draft': 'Low turnout: average signups 8.67; consider publicity.', 'sent': False}}
Trace: [
  {
    "tool": "read_csv",
    "reason": "Load signups and categories from CSV",
    "input": {
      "source_text": "event,signups,category\nAI Talk,6,technical\nHackathon,8,technical\nSocial Mixer,12,social\n"
    },
    "output": {
      "rows": [
        {
          "event": "AI Talk",
          "signups": "6",
          "category": "technical"
        },
        {
          "event": "Hackathon",
          "signups": "8",
          "category": "technical"
        },
        {
          "event": "Social Mixer",
          "signups": "12",
          "category": "social"
        }
      ],
      "row_count": 3
    }
  },
  {
    "tool": "calculator",
    "reason": "Average validated nonempty numeric signup subset",
    "input": {
      "operation": "average",
      "values": [
        6,
        8,
        12
      ]
    },
    "output": {
      "result": 8.666666666666666
    }
  },
  {
    "tool": "send_notification",
    "reason": "Average 8.67 is below defined threshold 10",
    "input": {
      "message": "Low turnout: average signups 8.67; consider publicity."
    },
    "output": {
      "draft": "Low turnout: average signups 8.67; consider publicity.",
      "sent": false
    }
  }
]
PASS: justified drafting and validated tool chain
```

## Assignment 2 source and captured output

Run from the repository root with `python labs/lab_02/assignment_2.py`.

### Full source

```python
# SRN 02FE23BCI038 | Lab 2: Tool-Using Agent | assignment_2
# Original definitions retained below; extensions follow.
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



A1=False
A2=True

import json
CATEGORY_CSV = "event,signups,category\nAI Talk,6,technical\nHackathon,8,technical\nSocial Mixer,12,social\n"
def send_notification(message):
    return {'draft': message, 'sent': False}
def filter_category(rows, category):
    matches = [r for r in rows if r.get('category') == category]
    return {'rows': matches} if matches else {'error': 'no matching rows'}
TOOLS.update(send_notification=send_notification, filter_category=filter_category)
TOOL_SCHEMAS = {
    'read_csv': {'input': {'source_text': 'str'}, 'output': {'rows': 'list', 'row_count': 'int'}},
    'filter_category': {'input': {'rows': 'list', 'category': 'str'}, 'output': {'rows': 'nonempty list OR error'}},
    'calculator': {'input': {'operation': 'sum|average', 'values': 'list[number]'}, 'output': {'result': 'number OR error'}},
    'events_api': {'input': {'event_name': 'str'}, 'output': {'date': 'str', 'location': 'str OR error'}},
    'send_notification': {'input': {'message': 'str'}, 'output': {'draft': 'str', 'sent': 'false'}}}
class ExtendedCampusAssistant(CampusDataAssistant):
    def answer(self, question):
        if 'average' not in question.lower():
            return super().answer(question)
        rows = self._call('read_csv', 'Load signups and categories from CSV', source_text=CATEGORY_CSV)['rows']
        if A2 and 'technical' in question.lower():
            rows = self._call('filter_category', 'Restrict calculation to requested technical category', rows=rows, category='technical')['rows']
        avg = self._call('calculator', 'Average validated nonempty numeric signup subset', operation='average', values=[int(r['signups']) for r in rows])['result']
        result = {'average': avg, 'event_count': len(rows)}
        if A1 and avg < 10:
            result['notification'] = self._call('send_notification', f'Average {avg:.2f} is below defined threshold 10', message=f'Low turnout: average signups {avg:.2f}; consider publicity.')
        return result

def demo():
    a = ExtendedCampusAssistant()
    print('Tool schemas:', json.dumps(TOOL_SCHEMAS, indent=2))
    q = "What's the average sign-up for technical events only?" if A2 else "What's the average sign-up?"
    print('Question:', q)
    r = a.answer(q); print('Answer:', r)
    assert r['average'] == (7 if A2 else 26/3)
    if A1: assert r['notification']['sent'] is False
    if A2:
        assert [x['tool'] for x in a.trace][:3] == ['read_csv','filter_category','calculator']
        try: a._call('filter_category','Validate absent category', rows=[], category='technical')
        except RuntimeError as e: print('Empty subset blocked:', e)
        else: raise AssertionError('Empty subset accepted')
    print('Trace:', json.dumps(a.trace, indent=2))
    print('PASS: justified drafting and validated tool chain')

if __name__ == "__main__":
    demo()
```

### Captured output

```text
Tool schemas: {
  "read_csv": {
    "input": {
      "source_text": "str"
    },
    "output": {
      "rows": "list",
      "row_count": "int"
    }
  },
  "filter_category": {
    "input": {
      "rows": "list",
      "category": "str"
    },
    "output": {
      "rows": "nonempty list OR error"
    }
  },
  "calculator": {
    "input": {
      "operation": "sum|average",
      "values": "list[number]"
    },
    "output": {
      "result": "number OR error"
    }
  },
  "events_api": {
    "input": {
      "event_name": "str"
    },
    "output": {
      "date": "str",
      "location": "str OR error"
    }
  },
  "send_notification": {
    "input": {
      "message": "str"
    },
    "output": {
      "draft": "str",
      "sent": "false"
    }
  }
}
Question: What's the average sign-up for technical events only?
Answer: {'average': 7.0, 'event_count': 2}
Empty subset blocked: filter_category failed: no matching rows
Trace: [
  {
    "tool": "read_csv",
    "reason": "Load signups and categories from CSV",
    "input": {
      "source_text": "event,signups,category\nAI Talk,6,technical\nHackathon,8,technical\nSocial Mixer,12,social\n"
    },
    "output": {
      "rows": [
        {
          "event": "AI Talk",
          "signups": "6",
          "category": "technical"
        },
        {
          "event": "Hackathon",
          "signups": "8",
          "category": "technical"
        },
        {
          "event": "Social Mixer",
          "signups": "12",
          "category": "social"
        }
      ],
      "row_count": 3
    }
  },
  {
    "tool": "filter_category",
    "reason": "Restrict calculation to requested technical category",
    "input": {
      "rows": [
        {
          "event": "AI Talk",
          "signups": "6",
          "category": "technical"
        },
        {
          "event": "Hackathon",
          "signups": "8",
          "category": "technical"
        },
        {
          "event": "Social Mixer",
          "signups": "12",
          "category": "social"
        }
      ],
      "category": "technical"
    },
    "output": {
      "rows": [
        {
          "event": "AI Talk",
          "signups": "6",
          "category": "technical"
        },
        {
          "event": "Hackathon",
          "signups": "8",
          "category": "technical"
        }
      ]
    }
  },
  {
    "tool": "calculator",
    "reason": "Average validated nonempty numeric signup subset",
    "input": {
      "operation": "average",
      "values": [
        6,
        8
      ]
    },
    "output": {
      "result": 7.0
    }
  },
  {
    "tool": "filter_category",
    "reason": "Validate absent category",
    "input": {
      "rows": [],
      "category": "technical"
    },
    "output": {
      "error": "no matching rows"
    }
  }
]
PASS: justified drafting and validated tool chain
```

## Combined source and captured output

Run from the repository root with `python labs/lab_02/combined.py`.

### Full source

```python
# SRN 02FE23BCI038 | Lab 2: Tool-Using Agent | combined
# Original definitions retained below; extensions follow.
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



A1=True
A2=True

import json
CATEGORY_CSV = "event,signups,category\nAI Talk,6,technical\nHackathon,8,technical\nSocial Mixer,12,social\n"
def send_notification(message):
    return {'draft': message, 'sent': False}
def filter_category(rows, category):
    matches = [r for r in rows if r.get('category') == category]
    return {'rows': matches} if matches else {'error': 'no matching rows'}
TOOLS.update(send_notification=send_notification, filter_category=filter_category)
TOOL_SCHEMAS = {
    'read_csv': {'input': {'source_text': 'str'}, 'output': {'rows': 'list', 'row_count': 'int'}},
    'filter_category': {'input': {'rows': 'list', 'category': 'str'}, 'output': {'rows': 'nonempty list OR error'}},
    'calculator': {'input': {'operation': 'sum|average', 'values': 'list[number]'}, 'output': {'result': 'number OR error'}},
    'events_api': {'input': {'event_name': 'str'}, 'output': {'date': 'str', 'location': 'str OR error'}},
    'send_notification': {'input': {'message': 'str'}, 'output': {'draft': 'str', 'sent': 'false'}}}
class ExtendedCampusAssistant(CampusDataAssistant):
    def answer(self, question):
        if 'average' not in question.lower():
            return super().answer(question)
        rows = self._call('read_csv', 'Load signups and categories from CSV', source_text=CATEGORY_CSV)['rows']
        if A2 and 'technical' in question.lower():
            rows = self._call('filter_category', 'Restrict calculation to requested technical category', rows=rows, category='technical')['rows']
        avg = self._call('calculator', 'Average validated nonempty numeric signup subset', operation='average', values=[int(r['signups']) for r in rows])['result']
        result = {'average': avg, 'event_count': len(rows)}
        if A1 and avg < 10:
            result['notification'] = self._call('send_notification', f'Average {avg:.2f} is below defined threshold 10', message=f'Low turnout: average signups {avg:.2f}; consider publicity.')
        return result

def demo():
    a = ExtendedCampusAssistant()
    print('Tool schemas:', json.dumps(TOOL_SCHEMAS, indent=2))
    q = "What's the average sign-up for technical events only?" if A2 else "What's the average sign-up?"
    print('Question:', q)
    r = a.answer(q); print('Answer:', r)
    assert r['average'] == (7 if A2 else 26/3)
    if A1: assert r['notification']['sent'] is False
    if A2:
        assert [x['tool'] for x in a.trace][:3] == ['read_csv','filter_category','calculator']
        try: a._call('filter_category','Validate absent category', rows=[], category='technical')
        except RuntimeError as e: print('Empty subset blocked:', e)
        else: raise AssertionError('Empty subset accepted')
    print('Trace:', json.dumps(a.trace, indent=2))
    print('PASS: justified drafting and validated tool chain')

if __name__ == "__main__":
    demo()
```

### Captured output

```text
Tool schemas: {
  "read_csv": {
    "input": {
      "source_text": "str"
    },
    "output": {
      "rows": "list",
      "row_count": "int"
    }
  },
  "filter_category": {
    "input": {
      "rows": "list",
      "category": "str"
    },
    "output": {
      "rows": "nonempty list OR error"
    }
  },
  "calculator": {
    "input": {
      "operation": "sum|average",
      "values": "list[number]"
    },
    "output": {
      "result": "number OR error"
    }
  },
  "events_api": {
    "input": {
      "event_name": "str"
    },
    "output": {
      "date": "str",
      "location": "str OR error"
    }
  },
  "send_notification": {
    "input": {
      "message": "str"
    },
    "output": {
      "draft": "str",
      "sent": "false"
    }
  }
}
Question: What's the average sign-up for technical events only?
Answer: {'average': 7.0, 'event_count': 2, 'notification': {'draft': 'Low turnout: average signups 7.00; consider publicity.', 'sent': False}}
Empty subset blocked: filter_category failed: no matching rows
Trace: [
  {
    "tool": "read_csv",
    "reason": "Load signups and categories from CSV",
    "input": {
      "source_text": "event,signups,category\nAI Talk,6,technical\nHackathon,8,technical\nSocial Mixer,12,social\n"
    },
    "output": {
      "rows": [
        {
          "event": "AI Talk",
          "signups": "6",
          "category": "technical"
        },
        {
          "event": "Hackathon",
          "signups": "8",
          "category": "technical"
        },
        {
          "event": "Social Mixer",
          "signups": "12",
          "category": "social"
        }
      ],
      "row_count": 3
    }
  },
  {
    "tool": "filter_category",
    "reason": "Restrict calculation to requested technical category",
    "input": {
      "rows": [
        {
          "event": "AI Talk",
          "signups": "6",
          "category": "technical"
        },
        {
          "event": "Hackathon",
          "signups": "8",
          "category": "technical"
        },
        {
          "event": "Social Mixer",
          "signups": "12",
          "category": "social"
        }
      ],
      "category": "technical"
    },
    "output": {
      "rows": [
        {
          "event": "AI Talk",
          "signups": "6",
          "category": "technical"
        },
        {
          "event": "Hackathon",
          "signups": "8",
          "category": "technical"
        }
      ]
    }
  },
  {
    "tool": "calculator",
    "reason": "Average validated nonempty numeric signup subset",
    "input": {
      "operation": "average",
      "values": [
        6,
        8
      ]
    },
    "output": {
      "result": 7.0
    }
  },
  {
    "tool": "send_notification",
    "reason": "Average 7.00 is below defined threshold 10",
    "input": {
      "message": "Low turnout: average signups 7.00; consider publicity."
    },
    "output": {
      "draft": "Low turnout: average signups 7.00; consider publicity.",
      "sent": false
    }
  },
  {
    "tool": "filter_category",
    "reason": "Validate absent category",
    "input": {
      "rows": [],
      "category": "technical"
    },
    "output": {
      "error": "no matching rows"
    }
  }
]
PASS: justified drafting and validated tool chain
```

