import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

_BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.agents.minutes import run_minutes_agent
from evals.gold_data import GOLD_MEETINGS
from evals.matching import match_items_one_to_one, is_action_match, is_decision_match

# Backwards compatibility alias
def _match_action(extracted_action: dict[str, Any], gold_actions: list[dict[str, Any]]) -> bool:
    return any(is_action_match(extracted_action, gold) for gold in gold_actions)


def run_evaluation_suite(custom_meetings: list[dict[str, Any]] | None = None) -> Dict[str, Any]:
    """Evaluation Harness:
    Evaluates benchmark meetings using 1-to-1 bipartite matching for Action Items and Decisions.
    Calculates exact TP, FP, FN, Precision, Recall, and F1 independently.
    Tracks Grounding Rate across extracted action quotes.
    Discloses benchmark is scripted.
    """
    meetings = custom_meetings or GOLD_MEETINGS
    
    all_extracted_actions: List[Dict[str, Any]] = []
    all_gold_actions: List[Dict[str, Any]] = []
    all_extracted_decisions: List[str] = []
    all_gold_decisions: List[str] = []

    grounded_actions = 0
    hallucinated_actions = 0
    per_meeting_details = []

    for m in meetings:
        raw_text = m["raw_transcript"]
        res = run_minutes_agent(raw_text)
        actions = res.get("action_items", [])
        decisions = [d["text"] if isinstance(d, dict) else str(d) for d in res.get("decisions", [])]

        meeting_gold_actions = m.get("gold_actions", [])
        meeting_gold_decisions = m.get("gold_decisions", [])

        # Grounding check for this meeting
        m_grounded = 0
        m_hallucinated = 0
        for a in actions:
            quote = a.get("source_quote", "")
            if quote and quote in raw_text:
                m_grounded += 1
                grounded_actions += 1
            else:
                m_hallucinated += 1
                hallucinated_actions += 1

        # One-to-one matching per meeting
        m_act_eval = match_items_one_to_one(actions, meeting_gold_actions, is_action_match)
        m_dec_eval = match_items_one_to_one(decisions, meeting_gold_decisions, is_decision_match)

        per_meeting_details.append({
            "id": m["id"],
            "name": m.get("name", f"Meeting {m['id']}"),
            "actions_eval": m_act_eval,
            "decisions_eval": m_dec_eval,
            "grounded_count": m_grounded,
            "hallucinated_count": m_hallucinated,
        })

        all_extracted_actions.extend(actions)
        all_gold_actions.extend(meeting_gold_actions)
        all_extracted_decisions.extend(decisions)
        all_gold_decisions.extend(meeting_gold_decisions)

    # Global 1-to-1 totals across entire benchmark suite
    total_action_eval = match_items_one_to_one(all_extracted_actions, all_gold_actions, is_action_match)
    total_decision_eval = match_items_one_to_one(all_extracted_decisions, all_gold_decisions, is_decision_match)

    total_extracted = len(all_extracted_actions)
    grounding_rate = (grounded_actions / total_extracted * 100) if total_extracted > 0 else 100.0
    hallucination_rate = (hallucinated_actions / total_extracted * 100) if total_extracted > 0 else 0.0

    return {
        "benchmark_type": "scripted_synthetic_edge_cases",
        "meeting_count": len(meetings),
        "action_metrics": total_action_eval,
        "decision_metrics": total_decision_eval,
        "grounding": {
            "grounded_actions": grounded_actions,
            "hallucinated_actions": hallucinated_actions,
            "grounding_rate_percent": round(grounding_rate, 2),
            "hallucination_rate_percent": round(hallucination_rate, 2),
        },
        "per_meeting": per_meeting_details,
        "benchmark_passed": total_action_eval["f1"] >= 0.75 and hallucination_rate < 5.0,
    }
