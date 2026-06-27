"""Shared fixtures and a synthetic schema for LLM provider tests."""

from __future__ import annotations

from pydantic import BaseModel

from app.llm.base import ImageInput

#: Marker bytes used to prove the raw image never reaches logs. The value is not
#: a real image; the providers and the fake never decode it, only base64-encode.
SENSITIVE_IMAGE_BYTES = b"SENSITIVE_IMAGE_BYTES_marker"


class Candidate(BaseModel):
    """A small synthetic structured-output schema used across provider tests."""

    name: str
    calories: int


def sample_image() -> ImageInput:
    """A synthetic JPEG image input for vision tests (no real photo data)."""

    return ImageInput(data=SENSITIVE_IMAGE_BYTES, media_type="image/jpeg")


def openai_completion(content: str) -> dict[str, object]:
    """Build a minimal OpenAI chat-completion response carrying ``content``."""

    return {"choices": [{"message": {"role": "assistant", "content": content}}]}


def anthropic_tool_response(tool_input: dict[str, object]) -> dict[str, object]:
    """Build a minimal Anthropic messages response carrying a ``tool_use`` block."""

    return {
        "content": [{"type": "tool_use", "name": "emit_structured_output", "input": tool_input}]
    }
