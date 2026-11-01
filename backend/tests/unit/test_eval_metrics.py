import pytest
from evals.matching import match_items_one_to_one, is_action_match, is_decision_match


def test_one_to_one_matching_prevents_duplicate_matching():
    extracted = [
        {"title": "Procure GPU cluster", "source_quote": "I will procure the GPU cluster by Friday."},
        {"title": "Procure GPU cluster again", "source_quote": "I will procure the GPU cluster by Friday."},
    ]
    gold = [
        {"title": "Procure GPU cluster", "quote": "I will procure the GPU cluster by Friday."},
    ]

    result = match_items_one_to_one(extracted, gold, is_action_match)
    # Even though both extracted items match the gold item, only 1 TP can be granted
    assert result["true_positives"] == 1
    assert result["false_positives"] == 1
    assert result["false_negatives"] == 0
    assert result["precision"] == 0.5
    assert result["recall"] == 1.0
    assert result["true_positives"] <= min(len(extracted), len(gold))


def test_missing_actions():
    extracted = [
        {"title": "Draft roadmap document", "source_quote": "I will draft the roadmap"},
    ]
    gold = [
        {"title": "Draft roadmap document", "quote": "I will draft the roadmap"},
        {"title": "Finalize quarterly roadmap", "quote": "finalize quarterly roadmap"},
    ]
    result = match_items_one_to_one(extracted, gold, is_action_match)
    assert result["true_positives"] == 1
    assert result["false_positives"] == 0
    assert result["false_negatives"] == 1
    assert result["precision"] == 1.0
    assert result["recall"] == 0.5


def test_extra_actions():
    extracted = [
        {"title": "Draft roadmap document", "source_quote": "I will draft the roadmap"},
        {"title": "Unrelated action not in gold", "source_quote": "random quote"},
    ]
    gold = [
        {"title": "Draft roadmap document", "quote": "I will draft the roadmap"},
    ]
    result = match_items_one_to_one(extracted, gold, is_action_match)
    assert result["true_positives"] == 1
    assert result["false_positives"] == 1
    assert result["false_negatives"] == 0
    assert result["precision"] == 0.5
    assert result["recall"] == 1.0


def test_empty_predictions_with_gold():
    extracted = []
    gold = [{"title": "Action", "quote": "quote"}]
    result = match_items_one_to_one(extracted, gold, is_action_match)
    assert result["true_positives"] == 0
    assert result["false_positives"] == 0
    assert result["false_negatives"] == 1
    assert result["precision"] == 1.0
    assert result["recall"] == 0.0
    assert result["f1"] == 0.0


def test_empty_gold_with_predictions():
    extracted = [{"title": "Hallucinated Action", "quote": "quote"}]
    gold = []
    result = match_items_one_to_one(extracted, gold, is_action_match)
    assert result["true_positives"] == 0
    assert result["false_positives"] == 1
    assert result["false_negatives"] == 0
    assert result["precision"] == 0.0
    assert result["recall"] == 1.0
    assert result["f1"] == 0.0


def test_both_empty():
    extracted = []
    gold = []
    result = match_items_one_to_one(extracted, gold, is_action_match)
    assert result["true_positives"] == 0
    assert result["false_positives"] == 0
    assert result["false_negatives"] == 0
    assert result["precision"] == 1.0
    assert result["recall"] == 1.0
    assert result["f1"] == 1.0


def test_decision_matching_separate():
    extracted = ["$50k approved for GPU cluster", "Extra decision"]
    gold = ["$50k approved for the GPU cluster"]
    result = match_items_one_to_one(extracted, gold, is_decision_match)
    assert result["true_positives"] == 1
    assert result["false_positives"] == 1
    assert result["false_negatives"] == 0
    assert result["precision"] == 0.5
    assert result["recall"] == 1.0

