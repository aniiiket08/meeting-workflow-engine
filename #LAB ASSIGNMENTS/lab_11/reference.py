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
