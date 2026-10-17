# Prompt 062 - AI LLMService Streaming Test

## Objective
Create a comprehensive test for LLMService.generate_streaming method that covers the case where the provider actually has a generate_streaming method (not just the fallback case). This test should verify:
1. Proper delegation to provider's generate_streaming method when available
2. Correct passing of on_event and on_session_id callback parameters
3. Error handling when provider's generate_streaming throws an exception
4. Proper logging of streaming calls

## Current State
Existing tests in apps/backend/tests/ai/infrastructure/test_service.py cover:
- Basic delegation for generate() and generate_structured()
- Fallback case for generate_streaming() when provider lacks the method
- Logging and error handling for generate()
- Singleton behavior of get_llm_service()

Missing coverage:
- Happy path for generate_streaming() when provider HAS generate_streaming method
- Testing of on_event and on_session_id parameter passing
- Error handling for generate_streaming() method calls
- Logging for generate_streaming() calls

## Implementation Steps
1. Create a mock provider that implements generate_streaming method to track calls and parameters
2. Write test for successful delegation to provider's generate_streaming method
3. Write test verifying on_event and on_session_id callbacks are properly passed through
4. Write test for error handling when provider's generate_streaming throws exception
5. Write test for logging of generate_streaming calls (duration, provider name, etc.)

## Testing Requirements
- Use pytest framework consistent with existing tests
- Use MockProvider pattern from existing tests or extend it
- Follow Arrange-Act-Assert pattern
- Test both success and error cases
- Verify logging occurs (can check that no exceptions are raised during logging)
- Ensure tests run in Docker using ./scripts/docker-test.sh backend

## Constraints
- Must follow existing test patterns and style in the codebase
- Must not change any production code
- Must use proper mocking techniques
- Test should be self-contained and not depend on external services
- Must follow TDD principles: write tests that define the expected behavior