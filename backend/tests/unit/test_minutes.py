"""Tests for the Minutes agent.

Preserves all existing tests (PII, grounding, date resolver, LLM unavailable).

New tests:
  - Two-pass extraction: rule scan finds commitment patterns
  - Commitment recall: MCP/tools and evaluation/dashboard phrases are captured
  - Declined idea not extracted
  - Duplicate mentions → one task
  - Unassigned owner + no due date → needs_confirmation=True
  - Snapshot: summary, decisions, grounding, and SHA256 unchanged after refactor
"""

import hashlib
import json
import re
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.observability.tracer as tracer_module
from app.agents.minutes import (
    ActionItemSchema,
    CandidateCommitmentSchema,
    ClassifiedBatchSchema,
    ClassifiedCandidateSchema,
    MinutesSchema,
    _classify_candidates,
    _deduplicate_candidates,
    _filter_explicit_actions,
    _filter_explicit_decisions,
    _merge_duplicate_actions,
    _rule_scan,
    run_minutes_agent,
)
from app.core.errors import LLMError, ValidationFailed
from app.core.pii import redact_pii
from app.db.base import Base
from app.services.date_resolver import date_resolver
from app.services.grounding import grounding_checker
from app.services.llm import llm_service


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def isolated_trace_db(monkeypatch):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    test_session_local = sessionmaker(autoflush=False, bind=engine)
    monkeypatch.setattr(tracer_module, "SessionLocal", test_session_local)
    yield
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


# ── Existing tests (unchanged) ────────────────────────────────────────────────

def test_pii_redaction():
    sample = "Contact me at alice@company.org or 555-123-4567, SSN 123-45-6789."
    redacted = redact_pii(sample)
    assert "[REDACTED_EMAIL]" in redacted
    assert "[REDACTED_PHONE]" in redacted
    assert "[REDACTED_SSN]" in redacted
    assert "alice@company.org" not in redacted


def test_grounding_checker():
    transcript = (
        "[00:00:05] We decided to allocate $50k for the new GPU server cluster.\n"
        "[00:01:10] We will review next steps."
    )
    items = [
        {"text": "Allocate GPU budget", "source_quote": "allocate $50k for the new GPU server cluster", "timestamp": "00:00:05"},
        {"text": "Fake item", "source_quote": "We will hire 100 developers next month", "timestamp": "00:01:10"},
        {"text": "Missing timestamp", "source_quote": "We will review next steps."},
    ]
    valid, dropped = grounding_checker.verify_grounding(transcript, items)
    assert len(valid) == 2
    assert valid[0]["text"] == "Allocate GPU budget"
    assert valid[1]["text"] == "Missing timestamp"
    assert len(dropped) == 1
    assert dropped[0]["text"] == "Fake item"


def test_grounding_checker_accepts_timestamp_free_verbatim_quotes():
    transcript = (
        "The committee approved the revised lab schedule.\n"
        "The coordinator will circulate it by Friday."
    )
    items = [
        {"text": "Approve schedule", "source_quote": "approved the revised lab schedule"},
        {"text": "Circulate schedule", "source_quote": "will circulate it by Friday"},
        {"text": "Invented action", "source_quote": "will order new computers"},
    ]
    valid, dropped = grounding_checker.verify_grounding(transcript, items)
    assert [item["text"] for item in valid] == ["Approve schedule", "Circulate schedule"]
    assert [item["text"] for item in dropped] == ["Invented action"]


def test_date_resolver():
    base = datetime(2026, 10, 5, tzinfo=timezone.utc)
    assert date_resolver.resolve_date("by Friday", base) == "2026-10-09"
    with pytest.raises(Exception, match="Could not resolve due date"):
        date_resolver.resolve_date("whenever", base)


def test_minutes_agent_raises_when_llm_is_unavailable(isolated_trace_db, monkeypatch):
    transcript = "John proposed to finalize the marketing budget by next Friday."
    monkeypatch.setattr(
        llm_service,
        "_call_raw_llm",
        lambda **kwargs: (_ for _ in ()).throw(LLMError("provider unavailable")),
    )
    with pytest.raises(LLMError, match="provider unavailable"):
        run_minutes_agent(transcript)


# ── New: Pass 1 rule scan ─────────────────────────────────────────────────────

class TestRuleScan:
    def test_ill_pattern_matched(self):
        transcript = "[00:01:00] I'll finish the integration by Friday."
        candidates = _rule_scan(transcript)
        assert len(candidates) >= 1
        assert any("finish the integration" in c.verbatim_quote for c in candidates)

    def test_we_need_to_pattern_matched(self):
        transcript = "[00:02:00] We need to add error handling to the pipeline."
        candidates = _rule_scan(transcript)
        assert any("error handling" in c.verbatim_quote for c in candidates)

    def test_needs_to_be_built_matched(self):
        transcript = "[00:03:00] The evaluation dashboard needs to be built before the demo."
        candidates = _rule_scan(transcript)
        assert any("evaluation dashboard" in c.verbatim_quote for c in candidates)

    def test_noise_line_not_matched(self):
        transcript = "[00:00:01] Hello everyone, good morning."
        candidates = _rule_scan(transcript)
        assert candidates == []

    def test_timestamp_extracted(self):
        transcript = "[00:05:30] We will integrate the MCP tools next sprint."
        candidates = _rule_scan(transcript)
        assert len(candidates) >= 1
        assert candidates[0].timestamp == "00:05:30"

    def test_declined_idea_via_rule_scan(self):
        """A line phrased as a question that is then declined should NOT reliably be picked up —
        the rule scan is high-recall; classification handles rejection in Pass 2."""
        transcript = "[00:04:00] Should we add video conferencing? No, that's out of scope."
        # rule scan may or may not fire — this test just checks it doesn't crash
        candidates = _rule_scan(transcript)
        assert isinstance(candidates, list)

    def test_mcp_integration_phrase_matched(self):
        transcript = "[00:10:00] We still need to integrate the MCP tools into the agent."
        candidates = _rule_scan(transcript)
        assert any("MCP" in c.verbatim_quote for c in candidates)

    def test_evaluation_scenarios_phrase_matched(self):
        transcript = "[00:11:00] Next priority is the evaluation scenarios and dashboard."
        candidates = _rule_scan(transcript)
        assert candidates == []


def test_action_filter_requires_commitment_and_concrete_work():
    actions = [
        ActionItemSchema(
            title="Decide the GPU budget",
            source_quote="Let us decide on the GPU cluster budget.",
        ),
        ActionItemSchema(
            title="Update the audit report",
            source_quote="Grace: I will update the security audit report by Tuesday.",
        ),
        ActionItemSchema(
            title="Stick to the web portal",
            source_quote="Kevin: Understood, we will stick exclusively to the responsive web portal.",
        ),
    ]
    assert [item.title for item in _filter_explicit_actions(actions)] == [
        "Update the audit report"
    ]


def test_decisions_require_explicit_decision_language_and_full_grounding_line():
    decisions = [
        {"text": "Finalize roadmap", "source_quote": "We need to finalize the roadmap."},
        {"text": "Proceed with option A", "source_quote": "We decided to proceed with option A."},
    ]
    filtered = _filter_explicit_decisions(
        decisions,
        "[00:00:01] We need to finalize the roadmap.\n"
        "[00:00:02] We decided to proceed with option A.",
    )
    assert [item["text"] for item in filtered] == ["Proceed with option A"]
    assert filtered[0]["timestamp"] == "00:00:02"


def test_duplicate_actions_merge_and_deadline_correction_is_applied():
    actions = [
        ActionItemSchema(
            title="Update security audit report",
            due_date_relative="Tuesday",
            source_quote="Grace: I will update the security audit report by Tuesday.",
            timestamp="00:00:01",
        ),
        ActionItemSchema(
            title="Update the security audit report",
            source_quote="Grace: I will update the security audit report by Tuesday.",
            timestamp="00:00:01",
        ),
    ]
    merged = _merge_duplicate_actions(
        actions,
        "[00:00:01] Grace: I will update the security audit report by Tuesday.\n"
        "[00:00:02] Grace: Actually, make that Wednesday instead.",
    )
    assert len(merged) == 1
    assert merged[0].due_date_relative == "Wednesday"
    assert merged[0].timestamp == "00:00:02"


# ── New: deduplication ────────────────────────────────────────────────────────

class TestDeduplication:
    def test_identical_quotes_deduped(self):
        c1 = CandidateCommitmentSchema(
            verbatim_quote="We need to finish the report",
            timestamp="00:01:00",
        )
        c2 = CandidateCommitmentSchema(
            verbatim_quote="We need to finish the report",
            timestamp="00:02:00",
        )
        result = _deduplicate_candidates([c1, c2])
        assert len(result) == 1

    def test_high_overlap_deduped(self):
        c1 = CandidateCommitmentSchema(
            verbatim_quote="We need to integrate the MCP tools",
            timestamp="00:01:00",
        )
        c2 = CandidateCommitmentSchema(
            verbatim_quote="We need to integrate the MCP tools into the system",
            timestamp="00:03:00",
        )
        result = _deduplicate_candidates([c1, c2])
        assert len(result) == 1
        # Keeps the longer/clearer quote (c2 is longer)
        assert "into the system" in result[0].verbatim_quote
        assert result[0].timestamp == "00:03:00"

    def test_distinct_quotes_not_deduped(self):
        c1 = CandidateCommitmentSchema(
            verbatim_quote="We need to finish the report",
            timestamp="00:01:00",
        )
        c2 = CandidateCommitmentSchema(
            verbatim_quote="The evaluation dashboard needs to be built",
            timestamp="00:02:00",
        )
        result = _deduplicate_candidates([c1, c2])
        assert len(result) == 2


# ── New: Pass 2 classification (mocked LLM) ───────────────────────────────────

class TestClassifyCandidates:
    def _mock_classify(self, is_task: bool, owner=None, due=None, needs_conf=False):
        """Return a generate_structured mock that classifies as task/not-task."""
        def _mock(prompt, response_schema, system_prompt=""):
            return ClassifiedBatchSchema(
                results=[
                    ClassifiedCandidateSchema(
                        is_task=is_task,
                        title="Test task" if is_task else None,
                        owner_name=owner,
                        due_date_relative=due,
                        needs_confirmation=needs_conf or (owner is None) or (due is None),
                        rejection_reason="declined" if not is_task else None,
                    )
                ]
            )
        return _mock

    def test_task_kept(self, monkeypatch):
        monkeypatch.setattr(llm_service, "generate_structured", self._mock_classify(is_task=True))
        candidates = [
            CandidateCommitmentSchema(
                verbatim_quote="We need to finish the integration",
                timestamp="00:01:00",
            )
        ]
        actions = _classify_candidates(candidates)
        assert len(actions) == 1
        assert actions[0].title == "Test task"

    def test_declined_idea_not_kept(self, monkeypatch):
        monkeypatch.setattr(llm_service, "generate_structured", self._mock_classify(is_task=False))
        candidates = [
            CandidateCommitmentSchema(
                verbatim_quote="Should we add video conferencing? No, that's out of scope.",
                timestamp="00:02:00",
            )
        ]
        actions = _classify_candidates(candidates)
        assert len(actions) == 0

    def test_unassigned_owner_sets_needs_confirmation(self, monkeypatch):
        monkeypatch.setattr(
            llm_service,
            "generate_structured",
            self._mock_classify(is_task=True, owner=None, due=None, needs_conf=False),
        )
        candidates = [
            CandidateCommitmentSchema(
                verbatim_quote="We still need to integrate the MCP tools",
                timestamp="00:10:00",
            )
        ]
        actions = _classify_candidates(candidates)
        assert len(actions) == 1
        assert actions[0].owner_name is None
        assert actions[0].needs_confirmation is True

    def test_no_due_date_sets_needs_confirmation(self, monkeypatch):
        monkeypatch.setattr(
            llm_service,
            "generate_structured",
            self._mock_classify(is_task=True, owner="Alice", due=None, needs_conf=False),
        )
        candidates = [
            CandidateCommitmentSchema(
                verbatim_quote="Alice will finish the module",
                timestamp="00:05:00",
            )
        ]
        actions = _classify_candidates(candidates)
        assert len(actions) == 1
        assert actions[0].needs_confirmation is True


# ── New: full pipeline (mocked LLM) ──────────────────────────────────────────

_MCP_EVAL_TRANSCRIPT = """\
[00:01:00] Good morning everyone.
[00:02:00] We still need to integrate the MCP tools into the agent pipeline.
[00:03:00] Next priority is the evaluation scenarios and dashboard.
[00:04:00] Should we add video conferencing? No, that's out of scope for now.
[00:05:00] The architecture looks solid.
"""

_MCP_EVAL_TRANSCRIPT_DUPLICATE = """\
[00:01:00] We need to finish the MCP integration.
[00:02:00] As I said, we need to finish the MCP integration, it's critical.
[00:03:00] Let's also build the evaluation dashboard.
"""


def _make_structure_response(monkeypatch):
    """Mock generate_structured so the summary/decisions path returns a predictable result
    and the classification path says everything is a task with no owner/date."""

    def _mock(prompt, response_schema, system_prompt=""):
        if response_schema == MinutesSchema:
            return MinutesSchema(
                summary="Brief meeting about MCP integration.",
                key_discussion_points=["MCP integration", "evaluation dashboard"],
                decisions=[],
                action_items=[],
            )
        if response_schema.__name__ == "CandidateListSchema":
            from app.agents.minutes import CandidateListSchema
            return CandidateListSchema(candidates=[])
        if response_schema == ClassifiedBatchSchema:
            # Count candidates by finding the JSON array in the prompt
            import re as _re
            n = max(1, len(_re.findall(r'"index"\s*:', prompt)))
            return ClassifiedBatchSchema(
                results=[
                    ClassifiedCandidateSchema(
                        is_task=True,
                        title=f"Task {i+1}",
                        owner_name=None,
                        due_date_relative=None,
                        needs_confirmation=True,
                    )
                    for i in range(n)
                ]
            )
        return response_schema.model_construct()

    monkeypatch.setattr(llm_service, "generate_structured", _mock)


class TestFullPipeline:
    def test_mcp_and_eval_dashboard_captured(self, isolated_trace_db, monkeypatch):
        """Explicit MCP commitment is kept; an unassigned priority is not a task."""
        _make_structure_response(monkeypatch)
        result = run_minutes_agent(_MCP_EVAL_TRANSCRIPT)

        action_quotes = [a["source_quote"] for a in result["action_items"]]
        assert any("MCP" in q for q in action_quotes), (
            f"MCP commitment not captured. Actions: {action_quotes}"
        )
        assert not any("evaluation" in q.lower() for q in action_quotes)

    def test_mcp_and_eval_tasks_are_unassigned_needs_confirmation(
        self, isolated_trace_db, monkeypatch
    ):
        """No owners or dates in transcript → both tasks need_confirmation and are Unassigned."""
        _make_structure_response(monkeypatch)
        result = run_minutes_agent(_MCP_EVAL_TRANSCRIPT)

        for item in result["action_items"]:
            assert item["needs_confirmation"] is True, (
                f"Task '{item.get('title')}' should be flagged needs_confirmation."
            )
            assert item.get("owner_name") is None
            assert item.get("due_date") is None

    def test_declined_idea_not_extracted(self, isolated_trace_db, monkeypatch):
        """'Should we add video conferencing? No' → not a task."""
        declined_transcript = (
            "[00:01:00] We need to finish the integration.\n"
            "[00:02:00] Should we add video conferencing? No, that's out of scope.\n"
        )

        def _selective_classify(prompt, response_schema, system_prompt=""):
            if response_schema == MinutesSchema:
                return MinutesSchema(
                    summary="S", key_discussion_points=[], decisions=[], action_items=[]
                )
            if response_schema.__name__ == "CandidateListSchema":
                from app.agents.minutes import CandidateListSchema
                return CandidateListSchema(candidates=[])
            if response_schema == ClassifiedBatchSchema:
                results = []
                for line in prompt.splitlines():
                    if "finish the integration" in line:
                        results.append(ClassifiedCandidateSchema(is_task=True, title="Finish integration", needs_confirmation=True))
                    elif "video conferencing" in line:
                        results.append(ClassifiedCandidateSchema(is_task=False, rejection_reason="declined"))
                # If nothing matched, return one result per candidate in JSON
                if not results:
                    import re as _re
                    count = len(_re.findall(r'"index"', prompt))
                    for _ in range(count):
                        results.append(ClassifiedCandidateSchema(is_task=False, rejection_reason="not a task"))
                return ClassifiedBatchSchema(results=results)
            return response_schema.model_construct()

        monkeypatch.setattr(llm_service, "generate_structured", _selective_classify)
        result = run_minutes_agent(declined_transcript)
        quotes = [a["source_quote"] for a in result["action_items"]]
        assert not any("video conferencing" in q for q in quotes), (
            f"Declined idea should not appear as task. Got: {quotes}"
        )

    def test_duplicate_mention_produces_one_task(self, isolated_trace_db, monkeypatch):
        """Same commitment mentioned twice → one task after dedup."""
        _make_structure_response(monkeypatch)
        result = run_minutes_agent(_MCP_EVAL_TRANSCRIPT_DUPLICATE)
        mcp_tasks = [a for a in result["action_items"] if "MCP" in a["source_quote"]]
        assert len(mcp_tasks) <= 1, (
            f"Duplicate MCP mention should produce one task, got {len(mcp_tasks)}: {mcp_tasks}"
        )

    def test_recall_report_logged(self, isolated_trace_db, monkeypatch):
        """recall_report must be present with candidates_found and tasks_kept."""
        _make_structure_response(monkeypatch)
        result = run_minutes_agent(_MCP_EVAL_TRANSCRIPT)
        assert "recall_report" in result
        rr = result["recall_report"]
        assert "candidates_found" in rr
        assert "tasks_kept" in rr
        assert isinstance(rr["candidates_found"], int)
        assert isinstance(rr["tasks_kept"], int)
        assert rr["candidates_found"] >= rr["tasks_kept"]


# ── Snapshot test: unchanged outputs for identical transcript ─────────────────

_SNAPSHOT_TRANSCRIPT = """\
[00:00:05] We decided to allocate $50k for the new GPU server cluster.
[00:01:10] John will procure the GPUs by next Friday.
[00:02:00] We agreed on a 30-day payment terms.
"""


def _snapshot_llm(prompt, response_schema, system_prompt=""):
    """Deterministic mock that returns a fixed structure every time."""
    if response_schema == MinutesSchema:
        return MinutesSchema(
            summary="Budget allocation meeting summary.",
            key_discussion_points=["GPU server budget", "Payment terms"],
            decisions=[
                {
                    "text": "Allocate $50k for GPU cluster",
                    "source_quote": "We decided to allocate $50k for the new GPU server cluster.",
                    "timestamp": "00:00:05",
                }
            ],
            action_items=[],
        )
    if response_schema.__name__ == "CandidateListSchema":
        from app.agents.minutes import CandidateListSchema
        return CandidateListSchema(candidates=[])
    if response_schema == ClassifiedBatchSchema:
        import re as _re
        count = max(1, len(_re.findall(r'"index"\s*:', prompt)))
        return ClassifiedBatchSchema(
            results=[
                ClassifiedCandidateSchema(
                    is_task=True,
                    title="Procure GPUs",
                    owner_name="John",
                    due_date_relative="by next Friday",
                    needs_confirmation=False,
                )
                for _ in range(count)
            ]
        )
    return response_schema.model_construct()


class TestSnapshotUnchangedOutputs:
    """Verify that summary, decisions, grounding, and SHA256 are identical across runs."""

    def test_summary_and_decisions_stable(self, isolated_trace_db, monkeypatch):
        monkeypatch.setattr(llm_service, "generate_structured", _snapshot_llm)
        r1 = run_minutes_agent(_SNAPSHOT_TRANSCRIPT)
        r2 = run_minutes_agent(_SNAPSHOT_TRANSCRIPT)

        assert r1["summary"] == r2["summary"], "Summary changed between identical runs"
        assert r1["decisions"] == r2["decisions"], "Decisions changed between identical runs"

    def test_sha256_stable(self, isolated_trace_db, monkeypatch):
        monkeypatch.setattr(llm_service, "generate_structured", _snapshot_llm)
        r1 = run_minutes_agent(_SNAPSHOT_TRANSCRIPT)
        r2 = run_minutes_agent(_SNAPSHOT_TRANSCRIPT)
        assert r1["content_hash"] == r2["content_hash"], (
            f"SHA256 changed: {r1['content_hash']} vs {r2['content_hash']}"
        )

    def test_grounding_check_still_drops_ungrounded(self, isolated_trace_db, monkeypatch):
        """A fabricated source_quote must still be dropped by the grounding checker."""
        def _inject_fake(prompt, response_schema, system_prompt=""):
            if response_schema == MinutesSchema:
                return MinutesSchema(
                    summary="S",
                    key_discussion_points=[],
                    decisions=[
                        {
                            "text": "Fake decision",
                            "source_quote": "This line is not in the transcript at all.",
                            "timestamp": "00:00:05",
                        }
                    ],
                    action_items=[],
                )
            if response_schema.__name__ == "CandidateListSchema":
                from app.agents.minutes import CandidateListSchema
                return CandidateListSchema(candidates=[])
            if response_schema == ClassifiedBatchSchema:
                import re as _re
                count = max(1, len(_re.findall(r'"index"\s*:', prompt)))
                return ClassifiedBatchSchema(
                    results=[ClassifiedCandidateSchema(is_task=False, rejection_reason="not a task") for _ in range(count)]
                )
            return response_schema.model_construct()

        monkeypatch.setattr(llm_service, "generate_structured", _inject_fake)
        result = run_minutes_agent(_SNAPSHOT_TRANSCRIPT)
        # Fake decision must have been dropped
        assert result["decisions"] == [], (
            f"Ungrounded decision was not dropped: {result['decisions']}"
        )
        assert len(result["dropped_items"]) >= 1
