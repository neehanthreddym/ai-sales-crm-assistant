from types import SimpleNamespace

import pytest

from app.integrations.llm.openai_client import OpenAILeadClient
from app.models.ai import FollowUpDraft, LeadAnalysis
from app.models.lead import LeadInput


class FakeResponses:
    def __init__(self) -> None:
        self.schemas: list[type] = []

    async def parse(self, **kwargs: object) -> object:
        schema = kwargs["text_format"]
        self.schemas.append(schema)  # type: ignore[arg-type]
        if schema is LeadAnalysis:
            parsed = LeadAnalysis(
                intent="Purchase inquiry",
                urgency="high",
                vehicle_interest="2025 Honda CR-V",
                budget_range="$30,000-$35,000",
                financing_interest=True,
                trade_in_interest=True,
                lead_summary="Synthetic buyer is shopping this week.",
                recommended_next_action=(
                    "A salesperson should confirm needs and arrange a conversation."
                ),
            )
        else:
            parsed = FollowUpDraft(
                draft="Thanks for your interest. Would you like to schedule a call?"
            )
        return SimpleNamespace(output_parsed=parsed)


class FakeOpenAI:
    def __init__(self) -> None:
        self.responses = FakeResponses()

    async def close(self) -> None:
        pass


def lead() -> LeadInput:
    return LeadInput.model_validate(
        {
            "first_name": "Alex",
            "last_name": "Synthetic",
            "email": "alex.synthetic@example.com",
            "financing_interest": True,
            "trade_in_interest": True,
        }
    )


@pytest.mark.asyncio
async def test_sdk_structured_parsing_is_used_for_both_outputs() -> None:
    fake = FakeOpenAI()
    client = OpenAILeadClient("unused", model="test-model", client=fake)  # type: ignore[arg-type]
    analysis = await client.analyze(lead())
    draft = await client.draft_follow_up(lead(), analysis)
    assert analysis.urgency == "high"
    assert "schedule" in draft
    assert fake.responses.schemas == [LeadAnalysis, FollowUpDraft]
