# Lab 11: Agentic SDLC Factory

SRN: **02FE23BCI038**

## Assignment requirements from the guide

Assignment 1 — A Second, Concurrent Story
Add a second story (e.g. "export to PDF in addition to CSV") processed through the same pipeline. Extend the lineage trace so it correctly attributes each design/code/test artifact to the right story when two stories exist side by side.
Assignment 2 — Prove Test Independence With a Deliberate Bug
Introduce a deliberate bug into `coding_agent`'s filter logic (e.g. an off-by-one or inverted comparison) without changing `testing_agent`. Run the pipeline and confirm the independently-generated tests catch the regression — submit the failing test output as evidence that the tests were not simply validating whatever the code happened to do.

## Implementation notes

A second CSV-export story is used, since PDF is an example rather than a mandatory format in the assignment. Both story artifacts coexist with distinct lineage IDs. The unchanged instructor tests and stronger exact-row tests reject the inverted-filter mutant. Expected FAIL lines are evidence of successful mutation detection.

Each assignment script includes the original definitions plus its own enabled extension. `A1` and `A2` select the assignment features; both are enabled in `combined.py`. These are standalone scripts, so sibling imports are not required. The original guide demonstration is available unchanged as `reference.py`.

## Original source and captured output

Run from the repository root with `python labs/lab_11/reference.py`.

### Full source

```python
"""
Lab 11: Agentic SDLC Factory -- CSV Export Feature
Requirement -> Design -> Code -> Test -> Review -> Docs -> Release,
with tests generated independently from the implementation (from the
story's acceptance criteria only), and a human checkpoint after
stories and after review.
"""

FEATURE_REQUEST = "Add CSV export to the reports page, preserving applied filters."


def requirement_agent(request):
    stories = [{
        "id": "US-1",
        "text": "As a user, I can export the current report view as a CSV file, "
                "preserving the applied filters.",
        "acceptance_criteria": [
            "clicking Export produces a .csv file",
            "the CSV contains only rows matching the currently applied filters",
            "the CSV header row matches the visible column names",
        ],
    }]
    return stories


def human_confirms_stories(stories):
    # Simulated human review -- in a real course this is a manual step.
    print("[HUMAN CHECKPOINT] Reviewing stories for real user intent...")
    for s in stories:
        print(f"  Confirmed: {s['text']}")
    return True


def design_agent(stories):
    return {
        "story_id": stories[0]["id"],
        "components": ["export_endpoint", "csv_serializer", "export_button (UI)"],
    }


def coding_agent(design, stories):
    # Implementation derived from design + story ONLY -- no access to tests.
    story = stories[0]

    def export_endpoint(rows, applied_filters, columns):
        filtered = [r for r in rows if all(r.get(k) == v for k, v in applied_filters.items())]
        lines = [",".join(columns)]
        for r in filtered:
            lines.append(",".join(str(r.get(c, "")) for c in columns))
        return "\n".join(lines)

    return {"design_ref": design["components"], "export_endpoint": export_endpoint}


def testing_agent(stories):
    """Generates tests from the STORY's acceptance criteria ONLY.
    Does not import or inspect the implementation module."""
    ac = stories[0]["acceptance_criteria"]

    def test_suite(export_fn):
        rows = [
            {"region": "North", "sales": 100}, {"region": "South", "sales": 200},
            {"region": "North", "sales": 150},
        ]
        columns = ["region", "sales"]
        csv_out = export_fn(rows, {"region": "North"}, columns)
        results = []
        results.append(("produces output", len(csv_out) > 0))
        results.append(("header matches columns", csv_out.splitlines()[0] == "region,sales"))
        results.append(("only filtered rows present",
                         all("South" not in line for line in csv_out.splitlines()[1:])))
        return results, ac

    return test_suite


def review_agent(design, code, test_results):
    issues = []
    if len(code["design_ref"]) < 2:
        issues.append("design under-specified: fewer than 2 components")
    if not all(passed for _, passed in test_results):
        issues.append("one or more tests failed")
    return {"issues": issues, "clean": len(issues) == 0}


def human_final_decision(review):
    print("[HUMAN CHECKPOINT] Final accept/reject based on review + tests...")
    decision = "accept" if review["clean"] else "reject"
    print(f"  Decision: {decision}")
    return decision


def docs_agent(stories):
    return f"Usage: click 'Export' on the reports page to download the filtered view as CSV. ({stories[0]['id']})"


def release_agent(decision, stories):
    if decision != "accept":
        return {"released": False, "reason": "review did not pass"}
    return {"released": True, "release_note": f"Added CSV export ({stories[0]['id']}).",
            "rollback_plan": "Revert to previous reports-page build if export errors spike post-release."}


if __name__ == "__main__":
    stories = requirement_agent(FEATURE_REQUEST)
    human_confirms_stories(stories)

    design = design_agent(stories)
    print(f"\nDesign: {design}")

    code = coding_agent(design, stories)
    test_suite = testing_agent(stories)   # built from stories, not from `code`
    test_results, acceptance_criteria = test_suite(code["export_endpoint"])

    print("\n=== Test results (derived from acceptance criteria, not implementation) ===")
    print(f"Acceptance criteria tested: {acceptance_criteria}")
    for name, passed in test_results:
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}")

    review = review_agent(design, code, test_results)
    print(f"\nReview: {review}")

    decision = human_final_decision(review)
    docs = docs_agent(stories)
    release = release_agent(decision, stories)

    print(f"\nDocs: {docs}")
    print(f"Release: {release}")

    print("\n=== Lineage ===")
    print("stories        <- requirement_agent(feature_request)")
    print("design         <- design_agent(stories)")
    print("code           <- coding_agent(design, stories)")
    print("tests          <- testing_agent(stories)   [independent of code]")
    print("review         <- review_agent(design, code, tests)")
    print("release        <- release_agent(human_decision, stories)")
```

### Captured output

```text
[HUMAN CHECKPOINT] Reviewing stories for real user intent...
  Confirmed: As a user, I can export the current report view as a CSV file, preserving the applied filters.

Design: {'story_id': 'US-1', 'components': ['export_endpoint', 'csv_serializer', 'export_button (UI)']}

=== Test results (derived from acceptance criteria, not implementation) ===
Acceptance criteria tested: ['clicking Export produces a .csv file', 'the CSV contains only rows matching the currently applied filters', 'the CSV header row matches the visible column names']
  [PASS] produces output
  [PASS] header matches columns
  [PASS] only filtered rows present

Review: {'issues': [], 'clean': True}
[HUMAN CHECKPOINT] Final accept/reject based on review + tests...
  Decision: accept

Docs: Usage: click 'Export' on the reports page to download the filtered view as CSV. (US-1)
Release: {'released': True, 'release_note': 'Added CSV export (US-1).', 'rollback_plan': 'Revert to previous reports-page build if export errors spike post-release.'}

=== Lineage ===
stories        <- requirement_agent(feature_request)
design         <- design_agent(stories)
code           <- coding_agent(design, stories)
tests          <- testing_agent(stories)   [independent of code]
review         <- review_agent(design, code, tests)
release        <- release_agent(human_decision, stories)
```

## Assignment 1 source and captured output

Run from the repository root with `python labs/lab_11/assignment_1.py`.

### Full source

```python
# SRN 02FE23BCI038 | Lab 11: Agentic SDLC Factory | assignment_1
# Original definitions retained below; extensions follow.
"""
Lab 11: Agentic SDLC Factory -- CSV Export Feature
Requirement -> Design -> Code -> Test -> Review -> Docs -> Release,
with tests generated independently from the implementation (from the
story's acceptance criteria only), and a human checkpoint after
stories and after review.
"""

FEATURE_REQUEST = "Add CSV export to the reports page, preserving applied filters."


def requirement_agent(request):
    stories = [{
        "id": "US-1",
        "text": "As a user, I can export the current report view as a CSV file, "
                "preserving the applied filters.",
        "acceptance_criteria": [
            "clicking Export produces a .csv file",
            "the CSV contains only rows matching the currently applied filters",
            "the CSV header row matches the visible column names",
        ],
    }]
    return stories


def human_confirms_stories(stories):
    # Simulated human review -- in a real course this is a manual step.
    print("[HUMAN CHECKPOINT] Reviewing stories for real user intent...")
    for s in stories:
        print(f"  Confirmed: {s['text']}")
    return True


def design_agent(stories):
    return {
        "story_id": stories[0]["id"],
        "components": ["export_endpoint", "csv_serializer", "export_button (UI)"],
    }


def coding_agent(design, stories):
    # Implementation derived from design + story ONLY -- no access to tests.
    story = stories[0]

    def export_endpoint(rows, applied_filters, columns):
        filtered = [r for r in rows if all(r.get(k) == v for k, v in applied_filters.items())]
        lines = [",".join(columns)]
        for r in filtered:
            lines.append(",".join(str(r.get(c, "")) for c in columns))
        return "\n".join(lines)

    return {"design_ref": design["components"], "export_endpoint": export_endpoint}


def testing_agent(stories):
    """Generates tests from the STORY's acceptance criteria ONLY.
    Does not import or inspect the implementation module."""
    ac = stories[0]["acceptance_criteria"]

    def test_suite(export_fn):
        rows = [
            {"region": "North", "sales": 100}, {"region": "South", "sales": 200},
            {"region": "North", "sales": 150},
        ]
        columns = ["region", "sales"]
        csv_out = export_fn(rows, {"region": "North"}, columns)
        results = []
        results.append(("produces output", len(csv_out) > 0))
        results.append(("header matches columns", csv_out.splitlines()[0] == "region,sales"))
        results.append(("only filtered rows present",
                         all("South" not in line for line in csv_out.splitlines()[1:])))
        return results, ac

    return test_suite


def review_agent(design, code, test_results):
    issues = []
    if len(code["design_ref"]) < 2:
        issues.append("design under-specified: fewer than 2 components")
    if not all(passed for _, passed in test_results):
        issues.append("one or more tests failed")
    return {"issues": issues, "clean": len(issues) == 0}


def human_final_decision(review):
    print("[HUMAN CHECKPOINT] Final accept/reject based on review + tests...")
    decision = "accept" if review["clean"] else "reject"
    print(f"  Decision: {decision}")
    return decision


def docs_agent(stories):
    return f"Usage: click 'Export' on the reports page to download the filtered view as CSV. ({stories[0]['id']})"


def release_agent(decision, stories):
    if decision != "accept":
        return {"released": False, "reason": "review did not pass"}
    return {"released": True, "release_note": f"Added CSV export ({stories[0]['id']}).",
            "rollback_plan": "Revert to previous reports-page build if export errors spike post-release."}



A1=True
A2=False

import csv,io
from concurrent.futures import ThreadPoolExecutor

def strong_story_tests(export_fn):
    # Expected rows come from acceptance criteria and fixed input, never implementation.
    rows=[{'region':'North','sales':100},{'region':'South','sales':200},{'region':'North','sales':150}]
    text=export_fn(rows,{'region':'North'},['region','sales'])
    actual=list(csv.DictReader(io.StringIO(text)))
    expected=[{'region':'North','sales':'100'},{'region':'North','sales':'150'}]
    return [('exact matching rows preserved',actual==expected),('correct header',text.splitlines()[0]=='region,sales')]
_ORIGINAL_CODE=coding_agent

def coding_agent(design,stories,bug=False):
    code=_ORIGINAL_CODE(design,stories)
    if bug:
        def wrong_export(rows,filters,columns):
            kept=[r for r in rows if not all(r.get(k)==v for k,v in filters.items())]
            return '\n'.join([','.join(columns)]+[','.join(str(r[c]) for c in columns) for r in kept])
        code['export_endpoint']=wrong_export
    return code

def pipeline(story,bug=False):
    design=design_agent([story]);code=coding_agent(design,[story],bug)
    results,_=testing_agent([story])(code['export_endpoint'])
    results+=strong_story_tests(code['export_endpoint'])
    review=review_agent(design,code,results);decision='accept' if review['clean'] else 'reject'
    lineage=[{'story_id':story['id'],'artifact':stage,'parent':parent} for stage,parent in [('design','story'),('code','design'),('tests','acceptance_criteria'),('review','code_and_tests'),('docs','story'),('release','review')]]
    return {'story_id':story['id'],'tests':results,'review':review,'release':release_agent(decision,[story]),'docs':docs_agent([story]),'lineage':lineage}

def demo():
    stories=requirement_agent(FEATURE_REQUEST)
    if A1:
        # A second CSV story is explicitly allowed by the assignment's "e.g." wording.
        stories.append({'id':'US-2','text':'Export filtered regional sales as CSV with selected visible columns','acceptance_criteria':['only matching regional rows','preserve visible header','produce CSV output']})
    with ThreadPoolExecutor(max_workers=len(stories)) as pool:
        artifacts=list(pool.map(pipeline,stories))
    for story,r in zip(stories,artifacts):
        print('Concurrent story artifact:',r)
        assert r['release']['released'] and all(e['story_id']==story['id'] for e in r['lineage'])
    if A2:
        r=pipeline(stories[0],bug=True);print('DELIBERATE MUTANT evidence:',r)
        assert not r['release']['released'] and not all(p for _,p in r['tests'])
        for name,passed in r['tests']: print('[PASS]' if passed else '[FAIL — expected mutant detection]',name)
    print('PASS: story lineage isolated; deliberate regression blocks release')

if __name__ == "__main__":
    demo()
```

### Captured output

```text
Concurrent story artifact: {'story_id': 'US-1', 'tests': [('produces output', True), ('header matches columns', True), ('only filtered rows present', True), ('exact matching rows preserved', True), ('correct header', True)], 'review': {'issues': [], 'clean': True}, 'release': {'released': True, 'release_note': 'Added CSV export (US-1).', 'rollback_plan': 'Revert to previous reports-page build if export errors spike post-release.'}, 'docs': "Usage: click 'Export' on the reports page to download the filtered view as CSV. (US-1)", 'lineage': [{'story_id': 'US-1', 'artifact': 'design', 'parent': 'story'}, {'story_id': 'US-1', 'artifact': 'code', 'parent': 'design'}, {'story_id': 'US-1', 'artifact': 'tests', 'parent': 'acceptance_criteria'}, {'story_id': 'US-1', 'artifact': 'review', 'parent': 'code_and_tests'}, {'story_id': 'US-1', 'artifact': 'docs', 'parent': 'story'}, {'story_id': 'US-1', 'artifact': 'release', 'parent': 'review'}]}
Concurrent story artifact: {'story_id': 'US-2', 'tests': [('produces output', True), ('header matches columns', True), ('only filtered rows present', True), ('exact matching rows preserved', True), ('correct header', True)], 'review': {'issues': [], 'clean': True}, 'release': {'released': True, 'release_note': 'Added CSV export (US-2).', 'rollback_plan': 'Revert to previous reports-page build if export errors spike post-release.'}, 'docs': "Usage: click 'Export' on the reports page to download the filtered view as CSV. (US-2)", 'lineage': [{'story_id': 'US-2', 'artifact': 'design', 'parent': 'story'}, {'story_id': 'US-2', 'artifact': 'code', 'parent': 'design'}, {'story_id': 'US-2', 'artifact': 'tests', 'parent': 'acceptance_criteria'}, {'story_id': 'US-2', 'artifact': 'review', 'parent': 'code_and_tests'}, {'story_id': 'US-2', 'artifact': 'docs', 'parent': 'story'}, {'story_id': 'US-2', 'artifact': 'release', 'parent': 'review'}]}
PASS: story lineage isolated; deliberate regression blocks release
```

## Assignment 2 source and captured output

Run from the repository root with `python labs/lab_11/assignment_2.py`.

### Full source

```python
# SRN 02FE23BCI038 | Lab 11: Agentic SDLC Factory | assignment_2
# Original definitions retained below; extensions follow.
"""
Lab 11: Agentic SDLC Factory -- CSV Export Feature
Requirement -> Design -> Code -> Test -> Review -> Docs -> Release,
with tests generated independently from the implementation (from the
story's acceptance criteria only), and a human checkpoint after
stories and after review.
"""

FEATURE_REQUEST = "Add CSV export to the reports page, preserving applied filters."


def requirement_agent(request):
    stories = [{
        "id": "US-1",
        "text": "As a user, I can export the current report view as a CSV file, "
                "preserving the applied filters.",
        "acceptance_criteria": [
            "clicking Export produces a .csv file",
            "the CSV contains only rows matching the currently applied filters",
            "the CSV header row matches the visible column names",
        ],
    }]
    return stories


def human_confirms_stories(stories):
    # Simulated human review -- in a real course this is a manual step.
    print("[HUMAN CHECKPOINT] Reviewing stories for real user intent...")
    for s in stories:
        print(f"  Confirmed: {s['text']}")
    return True


def design_agent(stories):
    return {
        "story_id": stories[0]["id"],
        "components": ["export_endpoint", "csv_serializer", "export_button (UI)"],
    }


def coding_agent(design, stories):
    # Implementation derived from design + story ONLY -- no access to tests.
    story = stories[0]

    def export_endpoint(rows, applied_filters, columns):
        filtered = [r for r in rows if all(r.get(k) == v for k, v in applied_filters.items())]
        lines = [",".join(columns)]
        for r in filtered:
            lines.append(",".join(str(r.get(c, "")) for c in columns))
        return "\n".join(lines)

    return {"design_ref": design["components"], "export_endpoint": export_endpoint}


def testing_agent(stories):
    """Generates tests from the STORY's acceptance criteria ONLY.
    Does not import or inspect the implementation module."""
    ac = stories[0]["acceptance_criteria"]

    def test_suite(export_fn):
        rows = [
            {"region": "North", "sales": 100}, {"region": "South", "sales": 200},
            {"region": "North", "sales": 150},
        ]
        columns = ["region", "sales"]
        csv_out = export_fn(rows, {"region": "North"}, columns)
        results = []
        results.append(("produces output", len(csv_out) > 0))
        results.append(("header matches columns", csv_out.splitlines()[0] == "region,sales"))
        results.append(("only filtered rows present",
                         all("South" not in line for line in csv_out.splitlines()[1:])))
        return results, ac

    return test_suite


def review_agent(design, code, test_results):
    issues = []
    if len(code["design_ref"]) < 2:
        issues.append("design under-specified: fewer than 2 components")
    if not all(passed for _, passed in test_results):
        issues.append("one or more tests failed")
    return {"issues": issues, "clean": len(issues) == 0}


def human_final_decision(review):
    print("[HUMAN CHECKPOINT] Final accept/reject based on review + tests...")
    decision = "accept" if review["clean"] else "reject"
    print(f"  Decision: {decision}")
    return decision


def docs_agent(stories):
    return f"Usage: click 'Export' on the reports page to download the filtered view as CSV. ({stories[0]['id']})"


def release_agent(decision, stories):
    if decision != "accept":
        return {"released": False, "reason": "review did not pass"}
    return {"released": True, "release_note": f"Added CSV export ({stories[0]['id']}).",
            "rollback_plan": "Revert to previous reports-page build if export errors spike post-release."}



A1=False
A2=True

import csv,io
from concurrent.futures import ThreadPoolExecutor

def strong_story_tests(export_fn):
    # Expected rows come from acceptance criteria and fixed input, never implementation.
    rows=[{'region':'North','sales':100},{'region':'South','sales':200},{'region':'North','sales':150}]
    text=export_fn(rows,{'region':'North'},['region','sales'])
    actual=list(csv.DictReader(io.StringIO(text)))
    expected=[{'region':'North','sales':'100'},{'region':'North','sales':'150'}]
    return [('exact matching rows preserved',actual==expected),('correct header',text.splitlines()[0]=='region,sales')]
_ORIGINAL_CODE=coding_agent

def coding_agent(design,stories,bug=False):
    code=_ORIGINAL_CODE(design,stories)
    if bug:
        def wrong_export(rows,filters,columns):
            kept=[r for r in rows if not all(r.get(k)==v for k,v in filters.items())]
            return '\n'.join([','.join(columns)]+[','.join(str(r[c]) for c in columns) for r in kept])
        code['export_endpoint']=wrong_export
    return code

def pipeline(story,bug=False):
    design=design_agent([story]);code=coding_agent(design,[story],bug)
    results,_=testing_agent([story])(code['export_endpoint'])
    results+=strong_story_tests(code['export_endpoint'])
    review=review_agent(design,code,results);decision='accept' if review['clean'] else 'reject'
    lineage=[{'story_id':story['id'],'artifact':stage,'parent':parent} for stage,parent in [('design','story'),('code','design'),('tests','acceptance_criteria'),('review','code_and_tests'),('docs','story'),('release','review')]]
    return {'story_id':story['id'],'tests':results,'review':review,'release':release_agent(decision,[story]),'docs':docs_agent([story]),'lineage':lineage}

def demo():
    stories=requirement_agent(FEATURE_REQUEST)
    if A1:
        # A second CSV story is explicitly allowed by the assignment's "e.g." wording.
        stories.append({'id':'US-2','text':'Export filtered regional sales as CSV with selected visible columns','acceptance_criteria':['only matching regional rows','preserve visible header','produce CSV output']})
    with ThreadPoolExecutor(max_workers=len(stories)) as pool:
        artifacts=list(pool.map(pipeline,stories))
    for story,r in zip(stories,artifacts):
        print('Concurrent story artifact:',r)
        assert r['release']['released'] and all(e['story_id']==story['id'] for e in r['lineage'])
    if A2:
        r=pipeline(stories[0],bug=True);print('DELIBERATE MUTANT evidence:',r)
        assert not r['release']['released'] and not all(p for _,p in r['tests'])
        for name,passed in r['tests']: print('[PASS]' if passed else '[FAIL — expected mutant detection]',name)
    print('PASS: story lineage isolated; deliberate regression blocks release')

if __name__ == "__main__":
    demo()
```

### Captured output

```text
Concurrent story artifact: {'story_id': 'US-1', 'tests': [('produces output', True), ('header matches columns', True), ('only filtered rows present', True), ('exact matching rows preserved', True), ('correct header', True)], 'review': {'issues': [], 'clean': True}, 'release': {'released': True, 'release_note': 'Added CSV export (US-1).', 'rollback_plan': 'Revert to previous reports-page build if export errors spike post-release.'}, 'docs': "Usage: click 'Export' on the reports page to download the filtered view as CSV. (US-1)", 'lineage': [{'story_id': 'US-1', 'artifact': 'design', 'parent': 'story'}, {'story_id': 'US-1', 'artifact': 'code', 'parent': 'design'}, {'story_id': 'US-1', 'artifact': 'tests', 'parent': 'acceptance_criteria'}, {'story_id': 'US-1', 'artifact': 'review', 'parent': 'code_and_tests'}, {'story_id': 'US-1', 'artifact': 'docs', 'parent': 'story'}, {'story_id': 'US-1', 'artifact': 'release', 'parent': 'review'}]}
DELIBERATE MUTANT evidence: {'story_id': 'US-1', 'tests': [('produces output', True), ('header matches columns', True), ('only filtered rows present', False), ('exact matching rows preserved', False), ('correct header', True)], 'review': {'issues': ['one or more tests failed'], 'clean': False}, 'release': {'released': False, 'reason': 'review did not pass'}, 'docs': "Usage: click 'Export' on the reports page to download the filtered view as CSV. (US-1)", 'lineage': [{'story_id': 'US-1', 'artifact': 'design', 'parent': 'story'}, {'story_id': 'US-1', 'artifact': 'code', 'parent': 'design'}, {'story_id': 'US-1', 'artifact': 'tests', 'parent': 'acceptance_criteria'}, {'story_id': 'US-1', 'artifact': 'review', 'parent': 'code_and_tests'}, {'story_id': 'US-1', 'artifact': 'docs', 'parent': 'story'}, {'story_id': 'US-1', 'artifact': 'release', 'parent': 'review'}]}
[PASS] produces output
[PASS] header matches columns
[FAIL — expected mutant detection] only filtered rows present
[FAIL — expected mutant detection] exact matching rows preserved
[PASS] correct header
PASS: story lineage isolated; deliberate regression blocks release
```

## Combined source and captured output

Run from the repository root with `python labs/lab_11/combined.py`.

### Full source

```python
# SRN 02FE23BCI038 | Lab 11: Agentic SDLC Factory | combined
# Original definitions retained below; extensions follow.
"""
Lab 11: Agentic SDLC Factory -- CSV Export Feature
Requirement -> Design -> Code -> Test -> Review -> Docs -> Release,
with tests generated independently from the implementation (from the
story's acceptance criteria only), and a human checkpoint after
stories and after review.
"""

FEATURE_REQUEST = "Add CSV export to the reports page, preserving applied filters."


def requirement_agent(request):
    stories = [{
        "id": "US-1",
        "text": "As a user, I can export the current report view as a CSV file, "
                "preserving the applied filters.",
        "acceptance_criteria": [
            "clicking Export produces a .csv file",
            "the CSV contains only rows matching the currently applied filters",
            "the CSV header row matches the visible column names",
        ],
    }]
    return stories


def human_confirms_stories(stories):
    # Simulated human review -- in a real course this is a manual step.
    print("[HUMAN CHECKPOINT] Reviewing stories for real user intent...")
    for s in stories:
        print(f"  Confirmed: {s['text']}")
    return True


def design_agent(stories):
    return {
        "story_id": stories[0]["id"],
        "components": ["export_endpoint", "csv_serializer", "export_button (UI)"],
    }


def coding_agent(design, stories):
    # Implementation derived from design + story ONLY -- no access to tests.
    story = stories[0]

    def export_endpoint(rows, applied_filters, columns):
        filtered = [r for r in rows if all(r.get(k) == v for k, v in applied_filters.items())]
        lines = [",".join(columns)]
        for r in filtered:
            lines.append(",".join(str(r.get(c, "")) for c in columns))
        return "\n".join(lines)

    return {"design_ref": design["components"], "export_endpoint": export_endpoint}


def testing_agent(stories):
    """Generates tests from the STORY's acceptance criteria ONLY.
    Does not import or inspect the implementation module."""
    ac = stories[0]["acceptance_criteria"]

    def test_suite(export_fn):
        rows = [
            {"region": "North", "sales": 100}, {"region": "South", "sales": 200},
            {"region": "North", "sales": 150},
        ]
        columns = ["region", "sales"]
        csv_out = export_fn(rows, {"region": "North"}, columns)
        results = []
        results.append(("produces output", len(csv_out) > 0))
        results.append(("header matches columns", csv_out.splitlines()[0] == "region,sales"))
        results.append(("only filtered rows present",
                         all("South" not in line for line in csv_out.splitlines()[1:])))
        return results, ac

    return test_suite


def review_agent(design, code, test_results):
    issues = []
    if len(code["design_ref"]) < 2:
        issues.append("design under-specified: fewer than 2 components")
    if not all(passed for _, passed in test_results):
        issues.append("one or more tests failed")
    return {"issues": issues, "clean": len(issues) == 0}


def human_final_decision(review):
    print("[HUMAN CHECKPOINT] Final accept/reject based on review + tests...")
    decision = "accept" if review["clean"] else "reject"
    print(f"  Decision: {decision}")
    return decision


def docs_agent(stories):
    return f"Usage: click 'Export' on the reports page to download the filtered view as CSV. ({stories[0]['id']})"


def release_agent(decision, stories):
    if decision != "accept":
        return {"released": False, "reason": "review did not pass"}
    return {"released": True, "release_note": f"Added CSV export ({stories[0]['id']}).",
            "rollback_plan": "Revert to previous reports-page build if export errors spike post-release."}



A1=True
A2=True

import csv,io
from concurrent.futures import ThreadPoolExecutor

def strong_story_tests(export_fn):
    # Expected rows come from acceptance criteria and fixed input, never implementation.
    rows=[{'region':'North','sales':100},{'region':'South','sales':200},{'region':'North','sales':150}]
    text=export_fn(rows,{'region':'North'},['region','sales'])
    actual=list(csv.DictReader(io.StringIO(text)))
    expected=[{'region':'North','sales':'100'},{'region':'North','sales':'150'}]
    return [('exact matching rows preserved',actual==expected),('correct header',text.splitlines()[0]=='region,sales')]
_ORIGINAL_CODE=coding_agent

def coding_agent(design,stories,bug=False):
    code=_ORIGINAL_CODE(design,stories)
    if bug:
        def wrong_export(rows,filters,columns):
            kept=[r for r in rows if not all(r.get(k)==v for k,v in filters.items())]
            return '\n'.join([','.join(columns)]+[','.join(str(r[c]) for c in columns) for r in kept])
        code['export_endpoint']=wrong_export
    return code

def pipeline(story,bug=False):
    design=design_agent([story]);code=coding_agent(design,[story],bug)
    results,_=testing_agent([story])(code['export_endpoint'])
    results+=strong_story_tests(code['export_endpoint'])
    review=review_agent(design,code,results);decision='accept' if review['clean'] else 'reject'
    lineage=[{'story_id':story['id'],'artifact':stage,'parent':parent} for stage,parent in [('design','story'),('code','design'),('tests','acceptance_criteria'),('review','code_and_tests'),('docs','story'),('release','review')]]
    return {'story_id':story['id'],'tests':results,'review':review,'release':release_agent(decision,[story]),'docs':docs_agent([story]),'lineage':lineage}

def demo():
    stories=requirement_agent(FEATURE_REQUEST)
    if A1:
        # A second CSV story is explicitly allowed by the assignment's "e.g." wording.
        stories.append({'id':'US-2','text':'Export filtered regional sales as CSV with selected visible columns','acceptance_criteria':['only matching regional rows','preserve visible header','produce CSV output']})
    with ThreadPoolExecutor(max_workers=len(stories)) as pool:
        artifacts=list(pool.map(pipeline,stories))
    for story,r in zip(stories,artifacts):
        print('Concurrent story artifact:',r)
        assert r['release']['released'] and all(e['story_id']==story['id'] for e in r['lineage'])
    if A2:
        r=pipeline(stories[0],bug=True);print('DELIBERATE MUTANT evidence:',r)
        assert not r['release']['released'] and not all(p for _,p in r['tests'])
        for name,passed in r['tests']: print('[PASS]' if passed else '[FAIL — expected mutant detection]',name)
    print('PASS: story lineage isolated; deliberate regression blocks release')

if __name__ == "__main__":
    demo()
```

### Captured output

```text
Concurrent story artifact: {'story_id': 'US-1', 'tests': [('produces output', True), ('header matches columns', True), ('only filtered rows present', True), ('exact matching rows preserved', True), ('correct header', True)], 'review': {'issues': [], 'clean': True}, 'release': {'released': True, 'release_note': 'Added CSV export (US-1).', 'rollback_plan': 'Revert to previous reports-page build if export errors spike post-release.'}, 'docs': "Usage: click 'Export' on the reports page to download the filtered view as CSV. (US-1)", 'lineage': [{'story_id': 'US-1', 'artifact': 'design', 'parent': 'story'}, {'story_id': 'US-1', 'artifact': 'code', 'parent': 'design'}, {'story_id': 'US-1', 'artifact': 'tests', 'parent': 'acceptance_criteria'}, {'story_id': 'US-1', 'artifact': 'review', 'parent': 'code_and_tests'}, {'story_id': 'US-1', 'artifact': 'docs', 'parent': 'story'}, {'story_id': 'US-1', 'artifact': 'release', 'parent': 'review'}]}
Concurrent story artifact: {'story_id': 'US-2', 'tests': [('produces output', True), ('header matches columns', True), ('only filtered rows present', True), ('exact matching rows preserved', True), ('correct header', True)], 'review': {'issues': [], 'clean': True}, 'release': {'released': True, 'release_note': 'Added CSV export (US-2).', 'rollback_plan': 'Revert to previous reports-page build if export errors spike post-release.'}, 'docs': "Usage: click 'Export' on the reports page to download the filtered view as CSV. (US-2)", 'lineage': [{'story_id': 'US-2', 'artifact': 'design', 'parent': 'story'}, {'story_id': 'US-2', 'artifact': 'code', 'parent': 'design'}, {'story_id': 'US-2', 'artifact': 'tests', 'parent': 'acceptance_criteria'}, {'story_id': 'US-2', 'artifact': 'review', 'parent': 'code_and_tests'}, {'story_id': 'US-2', 'artifact': 'docs', 'parent': 'story'}, {'story_id': 'US-2', 'artifact': 'release', 'parent': 'review'}]}
DELIBERATE MUTANT evidence: {'story_id': 'US-1', 'tests': [('produces output', True), ('header matches columns', True), ('only filtered rows present', False), ('exact matching rows preserved', False), ('correct header', True)], 'review': {'issues': ['one or more tests failed'], 'clean': False}, 'release': {'released': False, 'reason': 'review did not pass'}, 'docs': "Usage: click 'Export' on the reports page to download the filtered view as CSV. (US-1)", 'lineage': [{'story_id': 'US-1', 'artifact': 'design', 'parent': 'story'}, {'story_id': 'US-1', 'artifact': 'code', 'parent': 'design'}, {'story_id': 'US-1', 'artifact': 'tests', 'parent': 'acceptance_criteria'}, {'story_id': 'US-1', 'artifact': 'review', 'parent': 'code_and_tests'}, {'story_id': 'US-1', 'artifact': 'docs', 'parent': 'story'}, {'story_id': 'US-1', 'artifact': 'release', 'parent': 'review'}]}
[PASS] produces output
[PASS] header matches columns
[FAIL — expected mutant detection] only filtered rows present
[FAIL — expected mutant detection] exact matching rows preserved
[PASS] correct header
PASS: story lineage isolated; deliberate regression blocks release
```

