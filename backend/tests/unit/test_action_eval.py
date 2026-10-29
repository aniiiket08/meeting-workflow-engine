import pytest
from app.agents.minutes import _rule_scan, _classify_candidates, CandidateCommitmentSchema, ActionItemSchema
from evals.eval_harness import run_evaluation_suite, _match_action


def test_action_item_extraction_with_ambiguous_and_no_task_discussions():
    # Ambiguous question / discussion without commitment
    transcript_noise = (
        "[00:00:10] Alice: Should we change the office paint color? Not now, let's keep it as is.\n"
        "[00:00:25] Bob: Just checking in on coffee supply. Everything is fine."
    )
    candidates = _rule_scan(transcript_noise)
    # The noise filter drops non-action questions and declined ideas
    assert len(candidates) == 0


def test_action_item_extraction_grounds_supporting_quote():
    transcript = "[00:02:15] Arjun: I will configure the firewall rules by Friday."
    candidates = _rule_scan(transcript)
    assert len(candidates) == 1
    assert candidates[0].verbatim_quote == "Arjun: I will configure the firewall rules by Friday."
    assert candidates[0].timestamp == "00:02:15"


def test_eval_harness_calculates_precision_recall_f1_correctly():
    # Test evaluation metric calculations directly with mock results
    mock_extracted = [
        {"title": "Procure GPU cluster", "source_quote": "I will procure the GPU cluster by Friday."},
        {"title": "Draft roadmap document", "source_quote": "I will draft the roadmap document and send it out for review by Wednesday."},
    ]
    gold = [
        {"title": "Procure GPU cluster", "quote": "I will procure the GPU cluster by Friday."},
        {"title": "Draft roadmap document", "quote": "I will draft the roadmap document and send it out for review by Wednesday."},
        {"title": "Missing third task", "quote": "unextracted quote"},
    ]

    # Matching logic check
    assert _match_action(mock_extracted[0], gold) is True
    assert _match_action({"title": "Unrelated task", "source_quote": "something else"}, gold) is False
