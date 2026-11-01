import logging
from unittest.mock import patch, MagicMock
import httpx
import pytest

from app.core.errors import LLMError
from app.services.llm import LLMService


def test_gemini_api_key_sent_in_header_only():
    service = LLMService(use_cache=False)
    service.gemini_key = "secret_api_key_12345"
    service.model = "gemini-3.1-flash-lite"

    with patch("httpx.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "candidates": [
                {"content": {"parts": [{"text": '{"result": "ok"}'}]}}
            ],
            "usageMetadata": {"totalTokenCount": 10},
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        result = service._call_raw_llm("test prompt")
        assert result == '{"result": "ok"}'

        mock_post.assert_called_once()
        called_args, called_kwargs = mock_post.call_args
        called_url = called_args[0]
        called_headers = called_kwargs.get("headers", {})

        # URL must NOT contain key parameter
        assert "key=" not in called_url
        assert "secret_api_key_12345" not in called_url
        assert called_url == "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent"

        # Key must be sent strictly in x-goog-api-key header
        assert called_headers.get("x-goog-api-key") == "secret_api_key_12345"


def test_credentials_not_exposed_in_logs_on_timeout(caplog):
    service = LLMService(use_cache=False)
    secret_key = "super_secret_token_abcdef"
    service.gemini_key = secret_key

    with patch("httpx.post", side_effect=httpx.TimeoutException("Connection timed out")):
        with caplog.at_level(logging.DEBUG):
            with pytest.raises(LLMError) as exc_info:
                service._call_raw_llm("test prompt")

            assert "timed out" in str(exc_info.value)
            # Ensure the secret key NEVER appears in captured log text
            for record in caplog.records:
                assert secret_key not in record.message
                assert secret_key not in str(record)


def test_credentials_not_exposed_in_logs_on_http_error(caplog):
    service = LLMService(use_cache=False)
    secret_key = "super_secret_token_abcdef"
    service.gemini_key = secret_key

    req = httpx.Request("POST", "https://generativelanguage.googleapis.com/v1beta/models/gemini:generateContent", headers={"x-goog-api-key": secret_key})
    resp = httpx.Response(status_code=403, request=req)

    with patch("httpx.post", side_effect=httpx.HTTPStatusError("Forbidden", request=req, response=resp)):
        with caplog.at_level(logging.DEBUG):
            with pytest.raises(LLMError):
                service._call_raw_llm("test prompt")

            # Check all log records do not expose secret key
            for record in caplog.records:
                assert secret_key not in record.message
                assert secret_key not in str(record)
