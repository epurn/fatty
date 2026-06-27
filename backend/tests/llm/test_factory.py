"""Provider selection tests: env config picks the right adapter."""

from __future__ import annotations

from pydantic import SecretStr

from app.llm.config import LLMSettings
from app.llm.factory import build_provider
from app.llm.providers.anthropic import AnthropicProvider
from app.llm.providers.fake import FakeProvider
from app.llm.providers.openai import OpenAIProvider


def test_fake_is_the_default() -> None:
    provider = build_provider(LLMSettings())

    assert isinstance(provider, FakeProvider)


def test_openai_selected() -> None:
    settings = LLMSettings(provider="openai", api_key=SecretStr("k"), model="gpt-4o-mini")

    provider = build_provider(settings)

    assert isinstance(provider, OpenAIProvider)


def test_openai_compatible_selected() -> None:
    settings = LLMSettings(
        provider="openai_compatible",
        api_key=SecretStr("k"),
        model="m",
        base_url="https://llm.internal/v1",
    )

    provider = build_provider(settings)

    # OpenAI-compatible reuses the OpenAI Chat Completions adapter.
    assert isinstance(provider, OpenAIProvider)


def test_anthropic_selected() -> None:
    settings = LLMSettings(provider="anthropic", api_key=SecretStr("k"), model="claude")

    provider = build_provider(settings)

    assert isinstance(provider, AnthropicProvider)


def test_supports_vision_is_threaded_to_provider() -> None:
    # The config flag must reach the provider so the image-capability check is
    # enforced for the configured model, not just the fake.
    settings = LLMSettings(
        provider="openai",
        api_key=SecretStr("k"),
        model="gpt-4o",
        supports_vision=True,
    )

    provider = build_provider(settings)

    assert provider._supports_vision is True


def test_supports_vision_defaults_off_on_provider() -> None:
    settings = LLMSettings(provider="openai", api_key=SecretStr("k"), model="gpt-4o-mini")

    provider = build_provider(settings)

    assert provider._supports_vision is False
