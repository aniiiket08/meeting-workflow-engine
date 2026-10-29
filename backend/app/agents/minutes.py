"""Minutes Agent — two-pass extraction with high recall.

Pass 1 (candidate sweep):
  Rule-based scan every ~10-line chunk for commitment patterns, then LLM sweeps
  for anything the rules missed.  All candidates carry a verbatim quote + timestamp.

Pass 2 (classify):
  LLM decides task / not-task per candidate.  When unsure → keep and flag
  needs_confirmation.  Declined ideas and past events are dropped.

Owner / due-date rules:
  - owner_name only when the speaker explicitly names a person ("I'll", "Arjun will").
  - due_date_relative only when stated or resolvable from the transcript.
  - Unassigned / No due date → needs_confirmation = True.
  - Never default to meeting date or "now".

Unchanged from before:
  - Summary generation.
  - Decisions list and how it is built.
  - Source-transcript grounding check (SHA256 hash, traceability).
"""

import hashlib
import json
import logging
import re
from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field

from app.core.errors import ValidationFailed
from app.core.pii import redact_pii
from app.observability.tracer import record_tool_call, trace_agent
from app.services.date_resolver import date_resolver
from app.services.grounding import grounding_checker
from app.services.llm import llm_service

logger = logging.getLogger("meeting_organizer")

# ── Commitment-signal patterns (rule-based Pass 1) ──────────────────────────
# Anchored to line starts; case-insensitive.  When a line matches, the whole
# line becomes a candidate verbatim quote.
_COMMITMENT_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"i(?:\'?ll|\'?m going to|\'? will)\b", re.IGNORECASE),
    re.compile(r"\bwe(?:\'?ll|\'? will| need to| should| are going to)\b", re.IGNORECASE),
    re.compile(r"\bneeds? to\b", re.IGNORECASE),
    re.compile(r"\bhas to\b", re.IGNORECASE),
    re.compile(r"\bmust\b", re.IGNORECASE),
    re.compile(r"\bnext (?:step|priority|we)\b", re.IGNORECASE),
    re.compile(r"\bpriority\b", re.IGNORECASE),
    re.compile(r"\blet(?:\'?s)?\s+(?:build|add|finish|complete|integrate|create|make)\b", re.IGNORECASE),
    re.compile(r"\b(?:build|add|finish|complete|integrate|create)\s+\w", re.IGNORECASE),
    re.compile(r"\b(?:will be|needs to be|has to be)\s+(?:built|finished|integrated|added|completed|done)\b", re.IGNORECASE),
    re.compile(r"\b(?:action|task|todo|to-do|follow.?up)\b", re.IGNORECASE),
    re.compile(r"\bby\s+(?:friday|monday|tuesday|wednesday|thursday|saturday|sunday|end of|next week|eod|eow)\b", re.IGNORECASE),
]

_NOISE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"^\s*\[\d{2}:\d{2}:\d{2}\]\s*(?:hi|hello|good (?:morning|afternoon|evening)|thank(?:s| you)|welcome|alright|okay|ok|sure|great|sounds good)\W*$", re.IGNORECASE),
    re.compile(r"^\s*\[\d{2}:\d{2}:\d{2}\]\s*.*\?\s*(?:no|nope|not now|declined|skip|out of scope)\W*$", re.IGNORECASE),
]

_TIMESTAMP_RE = re.compile(r"^\[?(\d{2}:\d{2}:\d{2})\]?\s*")


def _extract_timestamp(line: str) -> str | None:
    m = _TIMESTAMP_RE.match(line)
    return m.group(1) if m else None


def _strip_timestamp(line: str) -> str:
    return _TIMESTAMP_RE.sub("", line).strip()


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class CandidateCommitmentSchema(BaseModel):
    """A raw candidate commitment from Pass 1."""
    verbatim_quote: str = Field(min_length=1, description="Exact line from transcript")
    timestamp: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}:\d{2}$")
    rule_matched: str | None = Field(default=None, description="Which regex matched, if any")


class CandidateListSchema(BaseModel):
    candidates: list[CandidateCommitmentSchema] = Field(default_factory=list)


class ActionItemSchema(BaseModel):
    title: str
    owner_email: EmailStr | None = None
    owner_name: str | None = None
    due_date_relative: str | None = None
    priority: Literal["low", "medium", "high"] = "medium"
    source_quote: str
    timestamp: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}:\d{2}$")
    needs_confirmation: bool = Field(
        default=False,
        description="True when owner or due date is unassigned/unknown",
    )


class DecisionSchema(BaseModel):
    text: str
    source_quote: str
    timestamp: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}:\d{2}$")


class ClassifiedCandidateSchema(BaseModel):
    """Pass 2 classifier output for one candidate."""
    is_task: bool
    title: str | None = None
    owner_name: str | None = None
    owner_email: EmailStr | None = None
    due_date_relative: str | None = None
    priority: Literal["low", "medium", "high"] = "medium"
    needs_confirmation: bool = False
    rejection_reason: str | None = None  # only when is_task=False


class ClassifiedBatchSchema(BaseModel):
    results: list[ClassifiedCandidateSchema]


class MinutesSchema(BaseModel):
    summary: str
    key_discussion_points: list[str]
    decisions: list[DecisionSchema]
    # action_items is now populated by our two-pass pipeline, not from here
    action_items: list[ActionItemSchema] = Field(default_factory=list)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _chunk_lines(lines: list[str], chunk_size: int = 10) -> list[list[str]]:
    return [lines[i : i + chunk_size] for i in range(0, len(lines), chunk_size)]


def _rule_scan(transcript: str) -> list[CandidateCommitmentSchema]:
    """Pass 1a — iterate every line, apply pattern list, collect candidates."""
    candidates: list[CandidateCommitmentSchema] = []
    seen_quotes: set[str] = set()
    for line in transcript.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        # Skip obvious noise
        if any(p.search(stripped) for p in _NOISE_PATTERNS):
            continue
        ts = _extract_timestamp(stripped)
        text_only = _strip_timestamp(stripped)
        for pat in _COMMITMENT_PATTERNS:
            if pat.search(text_only):
                quote_key = " ".join(text_only.lower().split())
                if quote_key not in seen_quotes:
                    seen_quotes.add(quote_key)
                    candidates.append(
                        CandidateCommitmentSchema(
                            verbatim_quote=text_only,
                            timestamp=ts,
                            rule_matched=pat.pattern,
                        )
                    )
                break  # one match per line is enough
    return candidates


def _llm_sweep(
    chunks: list[list[str]],
    already_found: list[CandidateCommitmentSchema],
) -> list[CandidateCommitmentSchema]:
    """Pass 1b — LLM sweeps each chunk for commitments the rules might have missed."""
    already_quotes = {" ".join(c.verbatim_quote.lower().split()) for c in already_found}
    new_candidates: list[CandidateCommitmentSchema] = []

    for chunk in chunks:
        chunk_text = "\n".join(chunk)
        if not chunk_text.strip():
            continue
        prompt = (
            f"Review these transcript lines and list every commitment, development priority, "
            f"or statement that implies future work that was NOT already caught by keyword scanning.\n"
            f"Already-found quotes (do not repeat):\n"
            + (
                "\n".join(f"- {c.verbatim_quote}" for c in already_found[:20])
                if already_found
                else "(none yet)"
            )
            + f"\n\nTranscript chunk:\n{chunk_text}\n\n"
            f"Return ONLY new candidates the rule scanner would miss (implicit commitments, "
            f"indirect priorities, etc.). If none, return an empty candidates list."
        )
        try:
            result = llm_service.generate_structured(
                prompt=prompt,
                response_schema=CandidateListSchema,
                system_prompt=(
                    "You are a high-recall commitment extractor. "
                    "List every implicit future-work statement. "
                    "Use exact verbatim quotes from the chunk."
                ),
            )
            for c in result.candidates:
                key = " ".join(c.verbatim_quote.lower().split())
                if key not in already_quotes:
                    already_quotes.add(key)
                    new_candidates.append(c)
        except Exception:
            logger.warning("LLM sweep chunk failed; continuing with rule candidates only.")

    return new_candidates


def _deduplicate_candidates(
    candidates: list[CandidateCommitmentSchema],
) -> list[CandidateCommitmentSchema]:
    """Merge candidates whose normalised quotes overlap significantly.

    Two candidates are merged if either:
    - Jaccard token similarity ≥ 0.5 (same idea, slightly different wording), OR
    - One quote is a substring of the other (repetition with added context).
    """
    deduped: list[CandidateCommitmentSchema] = []
    used: list[bool] = [False] * len(candidates)

    def tokens(text: str) -> set[str]:
        return set(re.findall(r"\w+", text.lower()))

    def normalised(text: str) -> str:
        return " ".join(re.findall(r"\w+", text.lower()))

    for i, c in enumerate(candidates):
        if used[i]:
            continue
        c_toks = tokens(c.verbatim_quote)
        c_norm = normalised(c.verbatim_quote)
        for j in range(i + 1, len(candidates)):
            if used[j]:
                continue
            d = candidates[j]
            d_toks = tokens(d.verbatim_quote)
            d_norm = normalised(d.verbatim_quote)
            union = c_toks | d_toks
            inter = c_toks & d_toks
            jaccard = len(inter) / len(union) if union else 0
            substring_match = c_norm in d_norm or d_norm in c_norm
            if jaccard >= 0.5 or substring_match:
                used[j] = True
                # Keep the longer/clearer quote
                if len(d.verbatim_quote) > len(c.verbatim_quote):
                    c = d.model_copy(
                        update={"timestamp": c.timestamp or d.timestamp}
                    )
        deduped.append(c)
    return deduped


def _classify_candidates(
    candidates: list[CandidateCommitmentSchema],
    meeting_date_iso: str | None = None,
) -> list[ActionItemSchema]:
    """Pass 2 — classify each candidate as task / not-task."""
    if not candidates:
        return []

    candidates_json = json.dumps(
        [
            {
                "index": i,
                "verbatim_quote": c.verbatim_quote,
                "timestamp": c.timestamp,
            }
            for i, c in enumerate(candidates)
        ],
        indent=2,
    )
    meeting_date_note = (
        f"The meeting date is {meeting_date_iso}. "
        "Use it only for resolving relative due dates that are stated in the transcript."
        if meeting_date_iso
        else "The meeting date is unknown; do not infer due dates from context."
    )

    prompt = (
        f"Classify each candidate commitment as a task or not.\n\n"
        f"{meeting_date_note}\n\n"
        f"Rules:\n"
        f"- is_task = true unless the statement is clearly a question, a declined/rejected idea, "
        f"or a report of something already completed in the past.\n"
        f"- When unsure → is_task = true, needs_confirmation = true.\n"
        f"- owner_name: ONLY if the speaker names a person ('I\\'ll', 'Arjun will', 'you handle'). "
        f"Never infer from who was speaking. Otherwise leave null.\n"
        f"- owner_email: ONLY if explicitly stated in the transcript. Otherwise null.\n"
        f"- due_date_relative: ONLY if stated ('by Friday', 'next Monday'). Never default to today or meeting date. Otherwise null.\n"
        f"- needs_confirmation = true whenever owner_name is null OR due_date_relative is null.\n"
        f"- title: concise action phrase summarising the commitment.\n\n"
        f"Candidates (return one result per candidate in the same order):\n{candidates_json}"
    )

    result = llm_service.generate_structured(
        prompt=prompt,
        response_schema=ClassifiedBatchSchema,
        system_prompt=(
            "You are a precise meeting scribe. "
            "Favour inclusion: keep anything that could be an action item. "
            "Never invent owners, emails, or due dates."
        ),
    )

    actions: list[ActionItemSchema] = []
    for i, cls in enumerate(result.results):
        if not cls.is_task:
            logger.debug(
                "Candidate %d rejected as non-task: %s",
                i,
                cls.rejection_reason or "no reason given",
            )
            continue
        cand = candidates[i] if i < len(candidates) else None
        if cand is None:
            continue
        needs_conf = cls.needs_confirmation or (
            cls.owner_name is None and cls.owner_email is None
        ) or (
            cls.due_date_relative is None
        )
        actions.append(
            ActionItemSchema(
                title=cls.title or cand.verbatim_quote[:120],
                owner_name=cls.owner_name,
                owner_email=cls.owner_email,
                due_date_relative=cls.due_date_relative,
                priority=cls.priority,
                source_quote=cand.verbatim_quote,
                timestamp=cand.timestamp,
                needs_confirmation=needs_conf,
            )
        )
    return actions


# ── Main entry point ─────────────────────────────────────────────────────────

@trace_agent(agent_name="minutes_agent")
def run_minutes_agent(
    transcript_text: str,
    meeting_id: int | None = None,
    meeting_date_iso: str | None = None,
) -> dict[str, Any]:
    """Minutes Agent — two-pass extraction.

    Unchanged outputs:
      summary, key_discussion_points, decisions, content_hash, dropped_items

    New outputs:
      action_items  — higher recall; owner/date never inferred
      recall_report — {"candidates_found": N, "tasks_kept": M}
    """
    if not transcript_text.strip():
        raise ValidationFailed("Transcript text cannot be empty.")

    redacted_text = redact_pii(transcript_text)

    # ── Extract summary, discussion points, and decisions (unchanged) ─────────
    structure_prompt = f"""Extract executive meeting minutes from this transcript:
---
{redacted_text}
---

Output JSON with:
- summary
- key_discussion_points
- decisions (each with text, verbatim source_quote from transcript line, and timestamp if present)
- action_items (leave this as an empty list — actions are extracted separately)

Every decision MUST include a verbatim source_quote from one transcript line.
Include the exact timestamp only when one is present on that source line; otherwise set timestamp to null.
Do not infer timestamps, owners, due dates, decisions, or actions.
Use null for unknown values."""

    result = llm_service.generate_structured(
        prompt=structure_prompt,
        response_schema=MinutesSchema,
        system_prompt=(
            "You are a professional meeting scribe producing accurate, grounded minutes. "
            "Action item priority must be low, medium, or high; use medium when the transcript "
            "does not establish a priority."
        ),
    )

    decisions_dict = [d.model_dump() for d in result.decisions]

    # Grounding check for decisions (unchanged)
    valid_decisions, dropped_decisions = grounding_checker.verify_grounding(
        redacted_text, decisions_dict
    )
    record_tool_call(
        "grounding_checker.verify_grounding",
        {"decisions": len(decisions_dict)},
        {"valid_decisions": len(valid_decisions)},
    )

    # ── Pass 1: candidate sweep ───────────────────────────────────────────────
    rule_candidates = _rule_scan(redacted_text)
    lines = redacted_text.splitlines()
    chunks = _chunk_lines(lines, chunk_size=10)
    llm_candidates = _llm_sweep(chunks, rule_candidates)
    all_candidates_raw = rule_candidates + llm_candidates
    all_candidates = _deduplicate_candidates(all_candidates_raw)

    record_tool_call(
        "minutes_agent.pass1_sweep",
        {"transcript_lines": len(lines), "chunks": len(chunks)},
        {
            "rule_candidates": len(rule_candidates),
            "llm_candidates": len(llm_candidates),
            "after_dedup": len(all_candidates),
        },
    )
    logger.info(
        "Minutes Pass 1: rule=%d  llm=%d  after_dedup=%d",
        len(rule_candidates),
        len(llm_candidates),
        len(all_candidates),
    )

    # ── Pass 2: classify ──────────────────────────────────────────────────────
    classified_actions = _classify_candidates(all_candidates, meeting_date_iso)

    record_tool_call(
        "minutes_agent.pass2_classify",
        {"candidates_in": len(all_candidates)},
        {"tasks_kept": len(classified_actions)},
    )
    logger.info(
        "Minutes Pass 2: candidates_in=%d  tasks_kept=%d",
        len(all_candidates),
        len(classified_actions),
    )

    # ── Grounding check for actions ───────────────────────────────────────────
    actions_dict = [a.model_dump() for a in classified_actions]
    valid_actions, dropped_actions = grounding_checker.verify_grounding(
        redacted_text, actions_dict
    )
    record_tool_call(
        "grounding_checker.verify_grounding",
        {"actions": len(actions_dict)},
        {"valid_actions": len(valid_actions)},
    )

    # ── Resolve due dates ─────────────────────────────────────────────────────
    for item in valid_actions:
        if item.get("due_date_relative"):
            try:
                item["due_date"] = date_resolver.resolve_date(item["due_date_relative"])
                record_tool_call(
                    "date_resolver.resolve_date",
                    {"relative_text": item["due_date_relative"]},
                    {"due_date": item["due_date"]},
                )
            except Exception:
                item["due_date"] = None
                item["needs_confirmation"] = True
        else:
            item["due_date"] = None

    # ── SHA-256 hash (unchanged) ──────────────────────────────────────────────
    # Hash the full structured result so approvals are traceable.
    hashable = result.model_dump()
    hashable["action_items"] = valid_actions  # include resolved actions in hash
    content_hash = hashlib.sha256(
        json.dumps(hashable, sort_keys=True).encode("utf-8")
    ).hexdigest()

    if dropped_decisions or dropped_actions:
        logger.warning(
            "Minutes grounding dropped %d decisions and %d action items.",
            len(dropped_decisions),
            len(dropped_actions),
        )

    recall_report = {
        "candidates_found": len(all_candidates),
        "tasks_kept": len(valid_actions),
        "rule_candidates": len(rule_candidates),
        "llm_candidates": len(llm_candidates),
    }
    logger.info("Minutes recall report: %s", recall_report)

    return {
        "summary": result.summary,
        "key_discussion_points": result.key_discussion_points,
        "decisions": valid_decisions,
        "action_items": valid_actions,
        "dropped_items": dropped_decisions + dropped_actions,
        "content_hash": content_hash,
        "recall_report": recall_report,
    }
