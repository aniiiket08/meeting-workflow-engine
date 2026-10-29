import json
import pytest
from pydantic import BaseModel, Field

from app.core.errors import LLMError
from app.services.llm import LLMService


class SimpleTaskSchema(BaseModel):
    task: str = Field(min_length=1)
    priority: str = "medium"


def test_llm_extract_json_markdown_blocks():
    service = LLMService()
    raw = "Here is the response:\n```json\n{\"task\": \"Review document\", \"priority\": \"high\"}\n```\nHope that helps!"
    res = service._extract_json_substring(raw)
    assert json.loads(res) == {"task": "Review document", "priority": "high"}


def test_llm_extract_json_embedded_braces():
    service = LLMService()
    raw = "Sure, I have prepared the result: {\"task\": \"Setup projector\", \"priority\": \"low\"}. Let me know if you need more."
    res = service._extract_json_substring(raw)
    assert json.loads(res) == {"task": "Setup projector", "priority": "low"}


def test_llm_handles_timeout_and_transport_retry(monkeypatch):
    import httpx

    service = LLMService()
    service.gemini_key = "test-key"
    attempts = 0

    def mock_post(*args, **kwargs):
        nonlocal attempts
        attempts += 1
        req = httpx.Request("POST", "https://generativelanguage.googleapis.com")
        if attempts < 2:
            raise httpx.ReadTimeout("Connection timed out")
        # Second attempt succeeds
        return httpx.Response(
            200,
            request=req,
            json={
                "candidates": [{"content": {"parts": [{"text": "{\"task\": \"Fixed\", \"priority\": \"high\"}"}]}}],
                "usageMetadata": {"totalTokenCount": 25},
            },
        )

    monkeypatch.setattr(httpx, "post", mock_post)
    output = service.generate_structured("prompt", SimpleTaskSchema)
    assert output.task == "Fixed"
    assert attempts == 2


def test_llm_handles_rate_limit_429_retry(monkeypatch):
    import httpx

    service = LLMService()
    service.gemini_key = "test-key"
    attempts = 0

    def mock_post(*args, **kwargs):
        nonlocal attempts
        attempts += 1
        req = httpx.Request("POST", "https://generativelanguage.googleapis.com")
        if attempts == 1:
            resp = httpx.Response(429, headers={"retry-after": "0.1"}, request=req)
            raise httpx.HTTPStatusError("Rate limited", request=req, response=resp)
        return httpx.Response(
            200,
            request=req,
            json={
                "candidates": [{"content": {"parts": [{"text": "{\"task\": \"Recovered\", \"priority\": \"medium\"}"}]}}],
                "usageMetadata": {"totalTokenCount": 20},
            },
        )

    monkeypatch.setattr(httpx, "post", mock_post)
    output = service.generate_structured("prompt", SimpleTaskSchema)
    assert output.task == "Recovered"
    assert attempts == 2


def test_llm_handles_malformed_response_with_repair_retry(monkeypatch):
    service = LLMService()
    call_count = 0

    def mock_call_raw_llm(prompt, system_prompt=""):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return "not a valid json string {"
        return "{\"task\": \"Repaired task\", \"priority\": \"high\"}"

    monkeypatch.setattr(service, "_call_raw_llm", mock_call_raw_llm)
    result = service.generate_structured("create task", SimpleTaskSchema)
    assert result.task == "Repaired task"
    assert call_count == 2
