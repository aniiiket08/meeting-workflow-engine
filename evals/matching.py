import re
from typing import Any, Callable, Dict, List, Set, Tuple


def match_items_one_to_one(
    extracted_items: List[Any],
    gold_items: List[Any],
    match_fn: Callable[[Any, Any], bool],
) -> Dict[str, Any]:
    """Greedy one-to-one bipartite matching algorithm.
    
    Guarantees:
    - A single extracted item cannot match multiple gold items.
    - A single gold item cannot match multiple extracted items.
    - True Positives <= min(len(extracted_items), len(gold_items)).
    - Correct handling of empty extracted items and empty gold items.
    """
    matched_gold_indices: Set[int] = set()
    true_positives = 0

    for ext in extracted_items:
        for g_idx, gold in enumerate(gold_items):
            if g_idx not in matched_gold_indices and match_fn(ext, gold):
                matched_gold_indices.add(g_idx)
                true_positives += 1
                break

    n_ext = len(extracted_items)
    n_gold = len(gold_items)
    fp = n_ext - true_positives
    fn = n_gold - true_positives

    if n_gold == 0 and n_ext == 0:
        precision = 1.0
        recall = 1.0
        f1 = 1.0
    elif n_ext == 0:
        precision = 1.0
        recall = 0.0
        f1 = 0.0
    elif n_gold == 0:
        precision = 0.0
        recall = 1.0
        f1 = 0.0
    else:
        precision = true_positives / n_ext
        recall = true_positives / n_gold
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    return {
        "true_positives": true_positives,
        "false_positives": fp,
        "false_negatives": fn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "total_extracted": n_ext,
        "total_gold": n_gold,
    }


def is_action_match(extracted: Dict[str, Any], gold: Dict[str, Any]) -> bool:
    """Check if an extracted action matches a gold action.
    
    Criteria:
    1. Quote overlap if gold has quote, OR Title token overlap (>= 50% of gold title tokens).
    2. If gold specifies an owner, extracted owner must match case-insensitively if present.
    """
    ext_quote = (extracted.get("source_quote") or "").lower()
    gold_quote = (gold.get("quote") or "").lower()
    ext_title = (extracted.get("title") or "").lower()
    gold_title = (gold.get("title") or "").lower()

    quote_match = bool(gold_quote and (gold_quote in ext_quote or ext_quote in gold_quote))
    
    ext_tokens = set(re.findall(r"\w+", ext_title))
    gold_tokens = set(re.findall(r"\w+", gold_title))
    title_match = bool(gold_tokens and len(gold_tokens & ext_tokens) / len(gold_tokens) >= 0.5)

    if not (quote_match or title_match):
        return False

    gold_owner = gold.get("owner")
    ext_owner = extracted.get("owner") or extracted.get("owner_email")
    if gold_owner and ext_owner:
        if gold_owner.lower() not in ext_owner.lower() and ext_owner.lower() not in gold_owner.lower():
            return False

    return True


def is_decision_match(extracted_decision: Any, gold_decision: Any) -> bool:
    """Check if an extracted decision matches a gold decision by token overlap."""
    ext_text = extracted_decision if isinstance(extracted_decision, str) else extracted_decision.get("text", "")
    gold_text = gold_decision if isinstance(gold_decision, str) else gold_decision.get("text", "")

    ext_tokens = set(re.findall(r"\w+", ext_text.lower()))
    gold_tokens = set(re.findall(r"\w+", gold_text.lower()))
    if not gold_tokens or not ext_tokens:
        return False

    overlap = len(gold_tokens & ext_tokens)
    return (overlap / len(gold_tokens)) >= 0.4

