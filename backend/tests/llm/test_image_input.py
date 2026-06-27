"""Contract v2 image-input tests (FTY-076).

These cover the acceptance criteria for optional image input without any live
model: the text-only call is unchanged, a stubbed vision provider returns
schema-validated output from an image, image input on a non-vision model fails
fast before any provider call, and no image bytes are ever written to logs.
"""

from __future__ import annotations

import base64
import logging

import pytest

from app.llm.base import ALLOWED_IMAGE_MEDIA_TYPES, ImageInput
from app.llm.errors import LLMConfigurationError
from app.llm.providers.fake import FakeProvider
from tests.llm.conftest import SENSITIVE_IMAGE_BYTES, Candidate, sample_image


def test_text_only_call_is_unchanged() -> None:
    # Backward compatibility: the v1 signature still works with no image argument
    # and the provider receives zero images.
    provider = FakeProvider(responses=[{"name": "apple", "calories": 95}])

    result = provider.structured_completion("an apple", Candidate)

    assert result == Candidate(name="apple", calories=95)
    assert provider.image_counts == [0]


def test_stubbed_vision_provider_returns_validated_output() -> None:
    # A vision-capable stub accepts an image and returns schema-validated output.
    provider = FakeProvider(
        responses=[{"name": "granola bar", "calories": 190}],
        supports_vision=True,
    )

    result = provider.structured_completion(
        "extract the nutrition facts", Candidate, images=[sample_image()]
    )

    assert isinstance(result, Candidate)
    assert result == Candidate(name="granola bar", calories=190)
    assert provider.image_counts == [1]


def test_image_with_non_vision_model_fails_fast_before_provider_call() -> None:
    # The default model is not vision-capable; supplying an image must raise a
    # clear configuration error *before* any provider round-trip happens.
    provider = FakeProvider(responses=[{"name": "apple", "calories": 95}])

    with pytest.raises(LLMConfigurationError):
        provider.structured_completion("read this", Candidate, images=[sample_image()])

    # Fail-fast: the provider was never invoked, so the scripted response is
    # untouched and no image reached the call path.
    assert provider.prompts == []
    assert provider.image_counts == []


def test_empty_images_list_is_treated_as_text_only() -> None:
    # An empty sequence is "no image": it must not trip the vision requirement.
    provider = FakeProvider(responses=[{"name": "apple", "calories": 95}])

    result = provider.structured_completion("an apple", Candidate, images=[])

    assert result == Candidate(name="apple", calories=95)
    assert provider.image_counts == [0]


def test_image_bytes_are_never_logged(caplog: pytest.LogCaptureFixture) -> None:
    # Privacy: neither the raw image bytes nor their base64 encoding may appear
    # in logs, just as the prompt never does.
    provider = FakeProvider(
        responses=[{"name": "granola bar", "calories": 190}],
        supports_vision=True,
    )
    encoded = base64.b64encode(SENSITIVE_IMAGE_BYTES).decode("ascii")

    with caplog.at_level(logging.INFO, logger="app.llm"):
        provider.structured_completion(
            "extract the nutrition facts", Candidate, images=[sample_image()]
        )

    assert "SENSITIVE_IMAGE_BYTES" not in caplog.text
    assert encoded not in caplog.text
    # The sanitized success log is still emitted, proving logging ran.
    assert "llm call succeeded" in caplog.text


def test_image_input_rejects_empty_data() -> None:
    with pytest.raises(LLMConfigurationError):
        ImageInput(data=b"", media_type="image/png")


def test_image_input_rejects_unsupported_media_type() -> None:
    with pytest.raises(LLMConfigurationError):
        ImageInput(data=b"bytes", media_type="application/pdf")


def test_allowed_media_types_are_accepted() -> None:
    for media_type in ALLOWED_IMAGE_MEDIA_TYPES:
        image = ImageInput(data=b"bytes", media_type=media_type)
        assert image.media_type == media_type
