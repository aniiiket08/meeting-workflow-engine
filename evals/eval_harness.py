import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

_BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.agents.minutes import run_minutes_agent
from app.services.grounding import grounding_checker

GOLD_MEETINGS = [
    {
        "id": 1,
        "raw_transcript": "[00:00:10] Alice: Welcome everyone. Let's decide on the GPU cluster budget.\n[00:00:20] Bob: I suggest $50k.\n[00:00:30] Alice: Agreed, $50k is approved for the GPU cluster.\n[00:00:40] Bob: I will procure the GPU cluster by Friday.",
        "gold_decisions": ["$50k approved for the GPU cluster"],
        "gold_actions": [{"title": "Procure GPU cluster", "owner": "Bob", "due": "by Friday", "quote": "I will procure the GPU cluster by Friday."}],
    },
    {
        "id": 2,
        "raw_transcript": "[00:01:00] Charlie: We need to finalize the quarterly roadmap by next Friday.\n[00:01:10] David: I will draft the roadmap document and send it out for review by Wednesday.",
        "gold_decisions": [],
        "gold_actions": [
            {"title": "Finalize quarterly roadmap", "owner": None, "due": "by next Friday", "quote": "We need to finalize the quarterly roadmap by next Friday."},
            {"title": "Draft roadmap document", "owner": "David", "due": "by Wednesday", "quote": "I will draft the roadmap document and send it out for review by Wednesday."},
        ],
    },
    {
        "id": 3,
        "raw_transcript": "[00:02:00] Elena: Should we buy additional smartboards for the lab? No, that's out of scope right now.\n[00:02:15] Frank: Just general discussion, nothing to take action on.",
        "gold_decisions": [],
        "gold_actions": [],
    },
]


def _match_action(extracted_action: dict[str, Any], gold_actions: list[dict[str, Any]]) -> bool:
    """Check if an extracted action matches any gold action by quote or core title semantic tokens."""
    ext_quote = extracted_action.get("source_quote", "").lower()
    ext_tokens = set(re.findall(r"\w+", extracted_action.get("title", "").lower()))

    for gold in gold_actions:
        gold_quote = gold.get("quote", "").lower()
        if gold_quote and (gold_quote in ext_quote or ext_quote in gold_quote):
            return True
        gold_tokens = set(re.findall(r"\w+", gold.get("title", "").lower()))
        if gold_tokens and len(gold_tokens & ext_tokens) / len(gold_tokens) >= 0.5:
            return True
    return False


def run_evaluation_suite(custom_meetings: list[dict[str, Any]] | None = None) -> Dict[str, Any]:
    """Evaluation Harness:
    Evaluates benchmark meetings for Action Item Precision, Recall, F1, and Grounding Rate.
    Calculates metrics dynamically against ground-truth data.
    """
    meetings = custom_meetings or GOLD_MEETINGS
    total_gold_actions = sum(len(m.get("gold_actions", [])) for m in meetings)
    total_extracted_actions = 0
    true_positives = 0
    grounded_actions = 0
    hallucinated_actions = 0

    for m in meetings:
        res = run_minutes_agent(m["raw_transcript"])
        actions = res.get("action_items", [])
        gold_actions = m.get("gold_actions", [])
        raw_text = m["raw_transcript"]

        total_extracted_actions += len(actions)
        for a in actions:
            # Check grounding in raw transcript
            quote = a.get("source_quote", "")
            if quote and quote in raw_text:
                grounded_actions += 1
            else:
                hallucinated_actions += 1

            # Match against gold targets
            if _match_action(a, gold_actions):
                true_positives += 1

    precision = (true_positives / total_extracted_actions) if total_extracted_actions > 0 else 1.0
    recall = (true_positives / total_gold_actions) if total_gold_actions > 0 else 1.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    grounding_rate = (grounded_actions / total_extracted_actions * 100) if total_extracted_actions > 0 else 100.0
    hallucination_rate = (hallucinated_actions / total_extracted_actions * 100) if total_extracted_actions > 0 else 0.0

    return {
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1_score": round(f1, 3),
        "total_gold_actions": total_gold_actions,
        "total_extracted_actions": total_extracted_actions,
        "true_positives": true_positives,
        "grounding_rate_percent": round(grounding_rate, 2),
        "hallucination_rate_percent": round(hallucination_rate, 2),
        "benchmark_passed": f1 >= 0.75 and hallucination_rate < 5.0,
    }
