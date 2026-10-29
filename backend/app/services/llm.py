import json
import time
from typing import Any, Type, TypeVar
import httpx
from pydantic import BaseModel, ValidationError

from app.config import settings
from app.core.errors import LLMError
from app.core.logging import setup_logging
from app.observability.tracer import record_prompt, record_token_usage, record_tool_call

logger = setup_logging()

T = TypeVar("T", bound=BaseModel)


class LLMService:
    """Provider-agnostic LLM client wrapper with Pydantic schema validation and repair retry."""

    def __init__(self):
        self.model = settings.LLM_MODEL
        self.gemini_key = settings.GEMINI_API_KEY

    def _call_raw_llm(self, prompt: str, system_prompt: str = "") -> str:
        """Call Google Gemini and return its generated text."""
        if not self.gemini_key or self.gemini_key == "your_gemini_api_key_here":
            message = "Gemini API key is not configured. Set GEMINI_API_KEY in .env."
            logger.error(message)
            record_tool_call("llm.gemini", {"model": self.model}, {"error": message}, "failed")
            raise LLMError(message, model=self.model)

        body: dict[str, Any] = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json",
            },
        }
        if system_prompt:
            body["systemInstruction"] = {"parts": [{"text": system_prompt}]}

        try:
            endpoint = (
                "https://generativelanguage.googleapis.com/v1beta/models/"
                f"{self.model}:generateContent"
            )
            for attempt in range(3):
                try:
                    response = httpx.post(
                        endpoint,
                        headers={"x-goog-api-key": self.gemini_key},
                        json=body,
                        timeout=60.0,
                    )
                    response.raise_for_status()
                    break
                except httpx.HTTPStatusError as exc:
                    if exc.response.status_code not in {429, 500, 502, 503, 504} or attempt == 2:
                        raise
                    retry_after = exc.response.headers.get("retry-after")
                    try:
                        delay = min(float(retry_after), 10.0) if retry_after else 2**attempt
                    except ValueError:
                        delay = 2**attempt
                    time.sleep(delay)
                except httpx.TransportError:
                    if attempt == 2:
                        raise
                    time.sleep(2**attempt)

            data = response.json()
            candidates = data.get("candidates", [])
            content = "".join(
                part.get("text", "")
                for candidate in candidates
                for part in candidate.get("content", {}).get("parts", [])
                if isinstance(part.get("text"), str)
            )
            if not content.strip():
                raise LLMError("Gemini returned no response text.", model=self.model)

            usage = data.get("usageMetadata", {})
            usage_tokens = usage.get("totalTokenCount")
            reasoning_tokens = usage.get("thoughtsTokenCount")
            record_token_usage(usage_tokens, reasoning_tokens)
            record_tool_call(
                "llm.gemini",
                {"model": self.model},
                {"usage_tokens": usage_tokens, "reasoning_tokens": reasoning_tokens},
            )
            return content
        except LLMError:
            raise
        except Exception as exc:
            logger.exception("Gemini API call failed")
            record_tool_call(
                "llm.gemini",
                {"model": self.model},
                {"error": type(exc).__name__},
                "failed",
            )
            status_code = getattr(getattr(exc, "response", None), "status_code", None)
            error = f"Gemini API returned HTTP {status_code}." if status_code else "Gemini API request failed."
            raise LLMError(error, model=self.model) from exc

    def generate_structured(
        self,
        prompt: str,
        response_schema: Type[T],
        system_prompt: str = "",
    ) -> T:
        """Generate LLM output and enforce Pydantic schema validation with 1 repair retry attempt."""
        schema_instruction = f"\nReturn strictly valid JSON matching this schema: {json.dumps(response_schema.model_json_schema())}"
        full_system = f"{system_prompt}{schema_instruction}"

        record_prompt(full_system, prompt)
        raw_output = self._call_raw_llm(prompt=prompt, system_prompt=full_system)

        # First Attempt Parsing
        try:
            cleaned_json = self._extract_json_substring(raw_output)
            return response_schema.model_validate_json(cleaned_json)
        except (ValidationError, json.JSONDecodeError) as err1:
            logger.warning("LLM output validation failed on Attempt 1: %s. Attempting 1 repair retry...", str(err1))
            
            # One Repair Retry
            repair_prompt = (
                f"Your previous JSON output failed validation with error: {str(err1)}.\n"
                f"Original Prompt: {prompt}\n"
                f"Previous Output: {raw_output}\n"
                f"Please fix the output to strictly conform to valid JSON."
            )
            record_prompt(full_system, repair_prompt)
            try:
                repaired_output = self._call_raw_llm(prompt=repair_prompt, system_prompt=full_system)
                cleaned_repaired = self._extract_json_substring(repaired_output)
                return response_schema.model_validate_json(cleaned_repaired)
            except Exception as err2:
                logger.exception("LLM output repair retry failed")
                if isinstance(err2, LLMError):
                    raise
                raise LLMError(
                    message=f"LLM failed to output valid JSON matching schema after repair attempt. Validation error: {str(err2)}",
                    model=self.model,
                ) from err2

    def _extract_json_substring(self, text: str) -> str:
        """Extract valid JSON from markdown code blocks or surrounding text."""
        text = text.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()

        # If wrapped in markdown json block without leading ```
        if "```json" in text:
            start_idx = text.find("```json") + len("```json")
            end_idx = text.find("```", start_idx)
            if end_idx != -1:
                return text[start_idx:end_idx].strip()
            return text[start_idx:].strip()

        # Look for outermost matching JSON object or array braces
        obj_start = text.find("{")
        arr_start = text.find("[")
        if obj_start != -1 and (arr_start == -1 or obj_start < arr_start):
            obj_end = text.rfind("}")
            if obj_end != -1 and obj_end > obj_start:
                return text[obj_start : obj_end + 1].strip()
        elif arr_start != -1:
            arr_end = text.rfind("]")
            if arr_end != -1 and arr_end > arr_start:
                return text[arr_start : arr_end + 1].strip()

        return text

llm_service = LLMService()
