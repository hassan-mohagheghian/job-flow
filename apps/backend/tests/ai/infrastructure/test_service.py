"""Tests for LLMService — unified entry point for AI calls.

TDD: Tests define the service contract.
Facade Pattern: Tests verify the simple interface over complex internals.
"""

import pytest
from unittest.mock import MagicMock, patch

from ai.infrastructure.service import LLMService, get_llm_service, reset_llm_service
from ai.infrastructure.providers.base import LLMProvider, ProviderConfig, ProviderResponse
from ai.infrastructure.providers.mock import MockProvider


class TestLLMService:
    """LLMService — Facade Pattern over provider complexity."""

    def test_create_with_provider(self):
        provider = MockProvider()
        service = LLMService(provider)
        assert service.provider is provider

    def test_generate_delegates_to_provider(self):
        provider = MockProvider(ProviderConfig(
            name="mock", extra={"mock_response": "response"},
        ))
        service = LLMService(provider)

        resp = service.generate("test prompt")
        assert resp.content == "response"
        assert len(provider.generate_calls) == 1
        assert provider.generate_calls[0].prompt == "test prompt"
        assert provider.generate_calls[0].context is None
        assert provider.generate_calls[0].timeout is None

    def test_generate_structured_delegates_to_provider(self):
        provider = MockProvider(ProviderConfig(
            name="mock", extra={"mock_structured_response": '{"key": "value"}'},
        ))
        service = LLMService(provider)

        resp = service.generate_structured("test prompt")
        assert resp.content == '{"key": "value"}'
        assert len(provider.structured_calls) == 1
        assert provider.structured_calls[0].prompt == "test prompt"

    def test_generate_streaming_fallback_without_streaming(self):
        """When provider doesn't have generate_streaming, falls back to generate."""
        provider = MockProvider(ProviderConfig(
            name="mock", extra={"mock_response": "fallback"},
        ))
        service = LLMService(provider)

        resp = service.generate_streaming("test prompt")
        assert resp.content == "fallback"

    def test_generate_logs_duration(self):
        provider = MockProvider()
        service = LLMService(provider)

        # Should not raise
        service.generate("prompt")

    def test_generate_raises_on_error(self):
        provider = MockProvider(ProviderConfig(
            name="mock", extra={"mock_error": RuntimeError("LLM failed")},
        ))
        service = LLMService(provider)

        with pytest.raises(RuntimeError, match="LLM failed"):
            service.generate("prompt")

    def test_close_delegates_to_provider(self):
        provider = MockProvider()
        service = LLMService(provider)
        service.close()
        # MockProvider.close() is a no-op; just verify no error

    def test_generate_streaming_delegates_to_provider(self):
        """When provider has generate_streaming, it's called directly."""
        provider = MockProvider()
        # Add generate_streaming method to mock provider
        provider.generate_streaming = lambda prompt, context=None, timeout=None, \
            on_event=None, on_session_id=None: ProviderResponse(
                content="streamed response",
                metadata={"mock": True, "streaming": True},
                provider="mock",
                model="mock-model",
            )
        service = LLMService(provider)

        resp = service.generate_streaming(
            "test prompt",
            context={"key": "value"},
            timeout=30,
            on_event=lambda evt: None,
            on_session_id=lambda sid: None,
        )

        assert resp.content == "streamed response"
        assert resp.metadata["streaming"] is True
        # Verify the method was called (we can't easily track calls to lambda,
        # but we can verify it didn't fall back to generate by checking
        # that generate wasn't called)
        assert len(provider.generate_calls) == 0

    def test_generate_streaming_passes_through_callbacks(self):
        """on_event and on_session_id callbacks are passed to provider."""
        callbacks_received = {"event": None, "session_id": None}
        
        def capture_event(evt):
            callbacks_received["event"] = evt
            
        def capture_session_id(sid):
            callbacks_received["session_id"] = sid

        provider = MockProvider()
        # Add generate_streaming method that captures the callbacks
        def mock_generate_streaming(prompt, context=None, timeout=None,
                                  on_event=None, on_session_id=None):
            # Call the callbacks to verify they're passed through
            if on_event:
                on_event({"type": "test_event"})
            if on_session_id:
                on_session_id("test-session-123")
            return ProviderResponse(
                content="streamed response",
                metadata={"mock": True},
                provider="mock",
                model="mock-model",
            )
        
        provider.generate_streaming = mock_generate_streaming
        service = LLMService(provider)

        service.generate_streaming(
            "test prompt",
            context={},
            timeout=None,
            on_event=capture_event,
            on_session_id=capture_session_id,
        )

        # Verify callbacks were invoked
        assert callbacks_received["event"] == {"type": "test_event"}
        assert callbacks_received["session_id"] == "test-session-123"

    def test_generate_streaming_handles_provider_error(self):
        """When provider's generate_streaming throws, it's propagated."""
        provider = MockProvider()
        # Add generate_streaming method that throws
        def mock_generate_streaming(prompt, context=None, timeout=None,
                                  on_event=None, on_session_id=None):
            raise RuntimeError("Streaming failed")
        
        provider.generate_streaming = mock_generate_streaming
        service = LLMService(provider)

        with pytest.raises(RuntimeError, match="Streaming failed"):
            service.generate_streaming("test prompt")

    def test_generate_streaming_logs_duration(self):
        """generate_streaming logs duration and provider info."""
        provider = MockProvider()
        # Add generate_streaming method
        def mock_generate_streaming(prompt, context=None, timeout=None,
                                  on_event=None, on_session_id=None):
            return ProviderResponse(
                content="streamed response",
                metadata={"mock": True},
                provider="mock",
                model="mock-model",
            )
        
        provider.generate_streaming = mock_generate_streaming
        service = LLMService(provider)

        # Should not raise
        service.generate_streaming("test prompt")


class TestGetLLMService:
    """Test the singleton factory function."""

    def test_get_returns_service(self):
        reset_llm_service()
        provider = MockProvider()
        service = get_llm_service(provider)
        assert isinstance(service, LLMService)
        reset_llm_service()

    def test_get_caches_instance(self):
        reset_llm_service()
        provider = MockProvider()
        s1 = get_llm_service(provider)
        s2 = get_llm_service()
        assert s1 is s2
        reset_llm_service()

    def test_get_with_provider_replaces(self):
        reset_llm_service()
        p1 = MockProvider(ProviderConfig(name="mock", extra={"mock_response": "p1"}))
        s1 = get_llm_service(p1)
        p2 = MockProvider(ProviderConfig(name="mock", extra={"mock_response": "p2"}))
        s2 = get_llm_service(p2)
        assert s1 is not s2
        reset_llm_service()
