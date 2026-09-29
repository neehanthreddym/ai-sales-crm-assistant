import pytest

from app.models.ai import LeadAnalysis
from app.models.lead import LeadInput
from app.services.ai_service import AIService
from app.services.urgency import classify_urgency


@pytest.mark.parametrize(
    ("notes", "expected"),
    [
        ("I need a vehicle today.", "high"),
        ("Please contact me ASAP.", "high"),
        ("I want to purchase within 48 hours.", "high"),
        ("I am looking for an SUV this week.", "medium"),
        ("I am ready to buy soon.", "medium"),
        ("I am researching options with no timeline.", "low"),
        (None, "low"),
    ],
)
def test_classify_urgency_uses_stable_timing_rules(
    notes: str | None, expected: str
) -> None:
    lead = LeadInput(
        first_name="Taylor",
        last_name="Synthetic",
        email="taylor.synthetic@example.com",
        notes=notes,
    )
    assert classify_urgency(lead) == expected


class VariableUrgencyClient:
    def __init__(self, urgency: str) -> None:
        self.urgency = urgency

    async def analyze(self, _: LeadInput) -> LeadAnalysis:
        return LeadAnalysis(
            intent="Purchase research",
            urgency=self.urgency,  # type: ignore[arg-type]
            financing_interest=False,
            trade_in_interest=False,
            lead_summary="Synthetic lead.",
            recommended_next_action="Review the inquiry.",
        )

    async def draft_follow_up(self, _: LeadInput, __: LeadAnalysis) -> str:
        return "Synthetic draft."


@pytest.mark.asyncio
async def test_ai_service_normalizes_variable_llm_urgency() -> None:
    lead = LeadInput(
        first_name="Taylor",
        last_name="Synthetic",
        email="taylor.synthetic@example.com",
        notes="Looking for an SUV this week.",
    )

    medium_result = await AIService(VariableUrgencyClient("medium")).analyze(lead)  # type: ignore[arg-type]
    high_result = await AIService(VariableUrgencyClient("high")).analyze(lead)  # type: ignore[arg-type]

    assert medium_result.urgency == "medium"
    assert high_result.urgency == "medium"
