"""LLM Provider abstraction layer.

Providers are registered via get_provider() factory. The active provider
is selected by the AI_PROVIDER environment variable (default: "mimo" for the Mimo CLI provider).
"""

from __future__ import annotations

import os
from typing import Optional

from .base import LLMProvider, ProviderConfig, ProviderResponse

_providers: dict[str, LLMProvider] = {}


def get_provider(name: Optional[str] = None, config: Optional[ProviderConfig] = None) -> LLMProvider:
    """Get or create an LLM provider by name.

    Args:
        name: Provider name (e.g. mimo, openai, local). Defaults to AI_PROVIDER env var.
        config: Optional provider configuration override.

    Returns:
        Cached LLMProvider instance for the given name.
    """
    if name is None:
        name = os.environ.get("AI_PROVIDER", "mimo")
    name = name.lower()

    if name not in _providers:
        _providers[name] = _create_provider(name, config)

    return _providers[name]


def _create_provider(name: str, config: Optional[ProviderConfig] = None) -> LLMProvider:
    """Create a provider instance by name."""
    if name == "mimo":
        from .mimo.adapter import MimoProvider
        return MimoProvider(config)
    elif name == "openai":
        from .openai.adapter import OpenAIProvider
        return OpenAIProvider(config)
    elif name == "local":
        from .local.adapter import LocalLLMProvider
        return LocalLLMProvider(config)
    elif name == "gemini":
        from .gemini.adapter import GeminiProvider
        return GeminiProvider(config)
    elif name == "agy":
        from .agy.adapter import AGYProvider
        return AGYProvider(config)
    elif name == "opencode" or name == "fcc-opencode":
        from .opencode.adapter import OpencodeProvider
        return OpencodeProvider(config)
    elif name == "mock":
        from .mock.adapter import MockProvider
        return MockProvider(config)
    else:
        raise ValueError(f"Unknown provider: {name!r}. Available: mimo, openai, local, gemini, agy, opencode, mock")


def reset_providers():
    """Clear cached provider instances (useful for testing)."""
    _providers.clear()
