"""
Phase 5 — LLM Quality Evaluation
Measures: action-item precision/recall/F1, grounding rate, hallucination rate.
Uses the x-goog-api-key request header; credentials are never added to URLs.
"""
import hashlib
import json
import re
import statistics
import sys
import time
from pathlib import Path

import httpx

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.config import settings
# Monkey-patch LLMService to measure uncached request latency.
import app.services.llm as llm_module

_original_call = llm_module.LLMService._call_raw_llm
_llm_latencies_ms: list[float] = []
_llm_token_counts: list[dict] = []
_llm_retry_counts: list[int] = []


def _patched_call(self, prompt: str, system_prompt: str = "") -> str:
    """Call Gemini with header-only authentication and record request metrics."""
    if not self.gemini_key or self.gemini_key == "your_gemini_api_key_here":
        from app.core.errors import LLMError
        raise LLMError("No API key", model=self.model)

    import json as _json

    body: dict = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json",
        },
    }
    if system_prompt:
        body["systemInstruction"] = {"parts": [{"text": system_prompt}]}

    from app.core.errors import LLMError

    endpoint = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{self.model}:generateContent"
    )
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": self.gemini_key,
    }

    t0 = time.perf_counter()
    retry_count = 0
    for attempt in range(3):
        try:
            response = httpx.post(endpoint, json=body, headers=headers, timeout=60.0)
            response.raise_for_status()
            break
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code not in {429, 500, 502, 503, 504} or attempt == 2:
                raise
            retry_count += 1
            time.sleep(2 ** attempt)
        except httpx.TransportError:
            if attempt == 2:
                raise
            retry_count += 1
            time.sleep(2 ** attempt)

    elapsed_ms = (time.perf_counter() - t0) * 1000
    _llm_latencies_ms.append(elapsed_ms)
    _llm_retry_counts.append(retry_count)

    data = response.json()
    candidates = data.get("candidates", [])
    content = "".join(
        part.get("text", "")
        for candidate in candidates
        for part in candidate.get("content", {}).get("parts", [])
        if isinstance(part.get("text"), str)
    )

    usage = data.get("usageMetadata", {})
    _llm_token_counts.append({
        "prompt_tokens": usage.get("promptTokenCount"),
        "completion_tokens": usage.get("candidatesTokenCount"),
        "total_tokens": usage.get("totalTokenCount"),
    })

    if not content.strip():
        from app.core.errors import LLMError
        raise LLMError("No response text", model=self.model)

    return content


llm_module.LLMService._call_raw_llm = _patched_call

# ── Now import minutes agent (after patch) ───────────────────────────────────
from app.agents.minutes import run_minutes_agent
from app.services.grounding import grounding_checker

from evals.gold_data import GOLD_MEETINGS
from evals.matching import match_items_one_to_one, is_action_match, is_decision_match


print("Running AI quality evaluation (live LLM calls on 10 gold meetings)...")
print("=" * 60)

all_extracted_actions = []
all_gold_actions = []
all_extracted_decisions = []
all_gold_decisions = []

total_extracted_actions = 0
grounded_actions = 0
hallucinated_actions = 0
per_meeting_results = []

for m in GOLD_MEETINGS:
    print(f"\nMeeting {m['id']} ({m.get('name', '')}): running run_minutes_agent...")
    t0 = time.perf_counter()
    try:
        res = run_minutes_agent(m["raw_transcript"])
        elapsed_ms = (time.perf_counter() - t0) * 1000
        print(f"  Completed in {elapsed_ms:.0f}ms")
        actions = res.get("action_items", [])
        decisions = [d["text"] if isinstance(d, dict) else str(d) for d in res.get("decisions", [])]
        summary = res.get("summary", "")

        print(f"  Summary: {summary[:80]}...")
        print(f"  Decisions extracted: {len(decisions)} (gold: {len(m['gold_decisions'])})")
        print(f"  Actions extracted: {len(actions)} (gold: {len(m['gold_actions'])})")

        raw_text = m["raw_transcript"]
        m_grounded = 0
        m_hallucinated = 0
        for a in actions:
            quote = a.get("source_quote", "")
            if quote and quote.strip() in raw_text:
                grounded_actions += 1
                m_grounded += 1
            else:
                hallucinated_actions += 1
                m_hallucinated += 1

        total_extracted_actions += len(actions)
        all_extracted_actions.extend(actions)
        all_gold_actions.extend(m["gold_actions"])
        all_extracted_decisions.extend(decisions)
        all_gold_decisions.extend(m["gold_decisions"])

        # Per-meeting 1-to-1 evaluation
        m_act_eval = match_items_one_to_one(actions, m["gold_actions"], is_action_match)
        m_dec_eval = match_items_one_to_one(decisions, m["gold_decisions"], is_decision_match)

        per_meeting_results.append({
            "meeting_id": m["id"],
            "name": m.get("name", f"Meeting {m['id']}"),
            "elapsed_ms": round(elapsed_ms, 2),
            "actions": m_act_eval,
            "decisions": m_dec_eval,
            "grounded_count": m_grounded,
            "hallucinated_count": m_hallucinated,
            "summary_length": len(summary),
        })

    except Exception as exc:
        elapsed_ms = (time.perf_counter() - t0) * 1000
        print(f"  FAILED after {elapsed_ms:.0f}ms: {type(exc).__name__}: {exc}")
        per_meeting_results.append({
            "meeting_id": m["id"],
            "elapsed_ms": round(elapsed_ms, 2),
            "error": str(exc),
        })

# ── Compute overall 1-to-1 metrics ───────────────────────────────────────────
action_eval = match_items_one_to_one(all_extracted_actions, all_gold_actions, is_action_match)
decision_eval = match_items_one_to_one(all_extracted_decisions, all_gold_decisions, is_decision_match)
failed_meetings = [row for row in per_meeting_results if "error" in row]
completed_meetings = len(per_meeting_results) - len(failed_meetings)

grounding_rate = (grounded_actions / total_extracted_actions * 100) if total_extracted_actions > 0 else 100.0
hallucination_rate = (hallucinated_actions / total_extracted_actions * 100) if total_extracted_actions > 0 else 0.0
benchmark_passed = (
    not failed_meetings
    and action_eval["f1"] >= 0.75
    and hallucination_rate < 5.0
)

# ── LLM performance stats ────────────────────────────────────────────────────
llm_stats = {}
if _llm_latencies_ms:
    s = sorted(_llm_latencies_ms)
    llm_stats = {
        "call_count": len(s),
        "total_retry_count": sum(_llm_retry_counts),
        "latency_min_ms": round(min(s), 2),
        "latency_p50_ms": round(statistics.median(s), 2),
        "latency_p90_ms": round(s[int(len(s) * 0.9)], 2) if s else 0,
        "latency_max_ms": round(max(s), 2),
        "latency_mean_ms": round(statistics.mean(s), 2),
        "prompt_tokens": [t["prompt_tokens"] for t in _llm_token_counts if t["prompt_tokens"]],
        "completion_tokens": [t["completion_tokens"] for t in _llm_token_counts if t["completion_tokens"]],
        "total_tokens": [t["total_tokens"] for t in _llm_token_counts if t["total_tokens"]],
    }
    if llm_stats["total_tokens"]:
        llm_stats["total_tokens_sum"] = sum(llm_stats["total_tokens"])

results = {
    "model": settings.LLM_MODEL,
    "provider": "Google AI Studio (Gemini)",
    "benchmark_type": "scripted_synthetic_edge_cases",
    "sample_size": len(GOLD_MEETINGS),
    "run_status": "partial" if failed_meetings else "complete",
    "completed_meetings": completed_meetings,
    "failed_meetings": len(failed_meetings),
    "action_item_metrics": {
        "true_positives": action_eval["true_positives"],
        "false_positives": action_eval["false_positives"],
        "false_negatives": action_eval["false_negatives"],
        "precision": action_eval["precision"],
        "recall": action_eval["recall"],
        "f1_score": action_eval["f1"],
        "total_gold": action_eval["total_gold"],
        "total_extracted": action_eval["total_extracted"],
        "grounded_actions": grounded_actions,
        "hallucinated_actions": hallucinated_actions,
        "grounding_rate_percent": round(grounding_rate, 2),
        "hallucination_rate_percent": round(hallucination_rate, 2),
        "benchmark_passed": benchmark_passed,
    },
    "decision_metrics": {
        "true_positives": decision_eval["true_positives"],
        "false_positives": decision_eval["false_positives"],
        "false_negatives": decision_eval["false_negatives"],
        "precision": decision_eval["precision"],
        "recall": decision_eval["recall"],
        "f1_score": decision_eval["f1"],
        "total_gold": decision_eval["total_gold"],
        "total_extracted": decision_eval["total_extracted"],
    },
    "llm_performance": llm_stats,
    "per_meeting": per_meeting_results,
}

print()
print("=" * 60)
print("AI QUALITY EVALUATION RESULTS (JSON)")
print("=" * 60)
print(json.dumps(results, indent=2))

with open("evaluation/baseline_llm_quality.json", "w") as f:
    json.dump(results, f, indent=2)
print("\nSaved -> evaluation/baseline_llm_quality.json")
