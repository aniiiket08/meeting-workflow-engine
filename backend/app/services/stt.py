import hashlib
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

from app.core.errors import ToolError, ValidationFailed
from app.observability.tracer import record_tool_call, trace_agent

logger = logging.getLogger("meeting_organizer")

_SUPPORTED_EXTENSIONS = {".wav", ".mp3", ".m4a", ".ogg", ".flac", ".webm", ".mp4", ".wma"}

# Module-level cache so the model is loaded only once across requests.
_cached_model = None


def _get_whisper_model():
    """Load faster-whisper model once and cache it for reuse."""
    global _cached_model
    if _cached_model is not None:
        return _cached_model
    try:
        from faster_whisper import WhisperModel
        _cached_model = WhisperModel("tiny", device="cpu", compute_type="int8")
        return _cached_model
    except Exception as exc:
        logger.exception("Could not load Whisper model")
        raise ToolError(
            "Speech transcription model failed to load. "
            "Ensure faster-whisper and its dependencies are installed.",
            tool_name="faster-whisper",
        ) from exc


class STTService:
    @trace_agent(agent_name="transcription_agent", sensitive=True)
    def transcribe(self, audio_bytes: bytes, filename: str = "meeting_audio.wav") -> dict[str, Any]:
        """Transcribe audio bytes with faster-whisper and retain segment timestamps."""
        if not audio_bytes:
            raise ValidationFailed("Uploaded audio file is empty.")

        suffix = Path(filename).suffix.lower() or ".wav"
        if suffix not in _SUPPORTED_EXTENSIONS:
            raise ValidationFailed(
                f"Unsupported audio format '{suffix}'. "
                f"Supported formats: {', '.join(sorted(_SUPPORTED_EXTENSIONS))}."
            )

        temp_path: str | None = None
        try:
            model = _get_whisper_model()

            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as audio_file:
                audio_file.write(audio_bytes)
                temp_path = audio_file.name

            segments, info = model.transcribe(temp_path, beam_size=5)
            timestamped_lines = []
            for segment in segments:
                text_segment = segment.text.strip()
                if text_segment:
                    total_seconds = max(0, int(segment.start))
                    timestamp = (
                        f"{total_seconds // 3600:02d}:"
                        f"{(total_seconds % 3600) // 60:02d}:"
                        f"{total_seconds % 60:02d}"
                    )
                    timestamped_lines.append(f"[{timestamp}] {text_segment}")

            if not timestamped_lines:
                raise ValidationFailed("Speech recognition returned no transcript text.")
            text = "\n".join(timestamped_lines)
            record_tool_call(
                "faster_whisper.transcribe",
                {"filename": Path(filename).name, "audio_bytes": len(audio_bytes)},
                {"segment_count": len(timestamped_lines), "language": info.language},
            )
        except (ToolError, ValidationFailed):
            raise
        except Exception as exc:
            logger.exception("Speech transcription failed")
            raise ToolError(
                "Speech transcription is unavailable or failed.",
                tool_name="faster-whisper",
            ) from exc
        finally:
            if temp_path:
                try:
                    os.unlink(temp_path)
                except OSError:
                    logger.exception("Could not remove temporary audio file")

        content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return {
            "text": text,
            "language": info.language or "unknown",
            "hash": content_hash,
        }

    @trace_agent(agent_name="pasted_transcript_agent", sensitive=True)
    def process_pasted_transcript(self, raw_text: str) -> dict[str, Any]:
        """Process manually pasted transcript text."""
        cleaned = raw_text.strip()
        if not cleaned:
            raise ValidationFailed("Transcript text cannot be empty.")
        content_hash = hashlib.sha256(cleaned.encode("utf-8")).hexdigest()
        return {
            "text": cleaned,
            "language": "en",
            "hash": content_hash,
        }

stt_service = STTService()
