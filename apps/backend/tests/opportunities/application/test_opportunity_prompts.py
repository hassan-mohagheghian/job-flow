"""Opportunity prompt framing tests — generic professional, no visa positioning."""

from __future__ import annotations

from opportunities.application.services.opportunity_evaluate_prompt import (
    build_opportunity_evaluate_prompt,
)
from opportunities.application.services.opportunity_extract_prompt import (
    build_opportunity_extract_prompt,
)


class TestOpportunityPrompts:
    def test_extract_prompt_is_work_arrangement_agnostic(self):
        prompt = build_opportunity_extract_prompt("manual", None, None, "raw message")
        assert "professional evaluating an opportunity" in prompt
        assert "visa-sponsored" not in prompt

    def test_evaluate_prompt_is_work_arrangement_agnostic(self):
        prompt = build_opportunity_evaluate_prompt("extracted", "candidate", "rules")
        assert "professional evaluating an inbound opportunity" in prompt
        assert "visa-sponsored" not in prompt
        assert "authorization outlook" not in prompt
