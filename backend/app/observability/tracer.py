import functools
import time
from contextvars import ContextVar
from datetime import date, datetime
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Callable
from sqlalchemy import inspect as sqlalchemy_inspect
from sqlalchemy.exc import NoInspectionAvailable
from sqlalchemy.orm import Session
from app.db.models.trace import AgentRun
from app.db.session import SessionLocal
from app.core.logging import setup_logging

logger = setup_logging()


@dataclass
class TraceContext:
    prompts: list[dict[str, str]] = field(default_factory=list)
    tools: list[dict[str, Any]] = field(default_factory=list)
    tokens: int = 0
    reasoning_tokens: int = 0


_active_trace: ContextVar[TraceContext | None] = ContextVar("active_agent_trace", default=None)


def record_prompt(system_prompt: str, user_prompt: str) -> None:
    context = _active_trace.get()
    if context is not None:
        context.prompts.append({"system": system_prompt, "user": user_prompt})


def record_token_usage(tokens: int | None, reasoning_tokens: int | None = None) -> None:
    context = _active_trace.get()
    if context is not None and tokens is not None and tokens >= 0:
        context.tokens += tokens
    if context is not None and reasoning_tokens is not None and reasoning_tokens >= 0:
        context.reasoning_tokens += reasoning_tokens


def record_tool_call(
    name: str,
    arguments: Any = None,
    result: Any = None,
    status: str = "success",
) -> None:
    context = _active_trace.get()
    if context is not None:
        context.tools.append(
            {
                "name": name,
                "arguments": _json_safe(arguments),
                "result": _json_safe(result),
                "status": status,
            }
        )


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Session):
        return "<database session>"
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    if hasattr(value, "model_dump"):
        return _json_safe(value.model_dump())
    try:
        inspected = sqlalchemy_inspect(value)
        if inspected.mapper:
            return {
                attribute.key: _json_safe(getattr(value, attribute.key))
                for attribute in inspected.mapper.column_attrs
            }
    except NoInspectionAvailable:
        return str(value)
    return str(value)


def trace_agent(agent_name: str, *, sensitive: bool = False):
    """Persist inputs, prompts, outputs, tool calls, latency, and provider token use."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            start_time = time.perf_counter()
            status = "success"
            trace_context = TraceContext()
            context_token = _active_trace.set(trace_context)
            result: Any = None
            failure: Exception | None = None
            meeting_id = kwargs.get("meeting_id")

            # Try to extract meeting_id from first arg if dict/state
            if not meeting_id and args and isinstance(args[0], dict):
                meeting_id = args[0].get("meeting_id")

            try:
                result = func(*args, **kwargs)
            except Exception as exc:
                status = "failed"
                failure = exc
                logger.exception("Agent %s failed", agent_name)
            finally:
                elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                try:
                    if trace_context.prompts:
                        inputs = {"prompts": trace_context.prompts}
                    elif sensitive:
                        inputs = {
                            "argument_types": [type(argument).__name__ for argument in args],
                            "provided_fields": sorted(kwargs),
                            "audio_bytes": next(
                                (len(argument) for argument in args if isinstance(argument, bytes)),
                                None,
                            ),
                        }
                    else:
                        inputs = {"args": _json_safe(args), "kwargs": _json_safe(kwargs)}
                    if failure is not None:
                        outputs = {"error": {"type": type(failure).__name__, "message": str(failure)}}
                    elif sensitive and isinstance(result, dict):
                        outputs = {
                            "fields": sorted(result),
                            "text_characters": len(result.get("text", "")),
                            "language": result.get("language"),
                            "content_hash": result.get("hash"),
                        }
                    else:
                        outputs = _json_safe(result)
                    with SessionLocal() as db:
                        run_record = AgentRun(
                            meeting_id=meeting_id,
                            agent=agent_name,
                            input_data=inputs,
                            output_data=outputs,
                            tools_json=trace_context.tools,
                            latency_ms=round(elapsed_ms, 2),
                            tokens=trace_context.tokens,
                            status=status,
                        )
                        db.add(run_record)
                        db.commit()
                except Exception as exc:
                    logger.error(
                        "Failed to write trace for agent %s; execution result is preserved (error_type=%s)",
                        agent_name,
                        type(exc).__name__,
                    )
                finally:
                    _active_trace.reset(context_token)

            if failure is not None:
                raise failure
            return result

        return wrapper

    return decorator
