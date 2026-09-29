import json
from types import SimpleNamespace

import pytest

from app.integrations.llm.groq_client import GroqLeadClient
from app.models.ai import LeadAnalysis
from app.models.lead import LeadInput


class FakeCompletions:
    def __init__(self) -> None:
        self.requests: list[dict[str, object]] = []

    async def create(self, **kwargs: object) -> object:
        self.requests.append(kwargs)
        schema = kwargs["response_format"]["json_schema"]["schema"]  # type: ignore[index]
        if "lead_summary" in schema["properties"]:
            content = json.dumps(
                {
                    "intent": "Purchase inquiry",
                    "urgency": "high",
                    "vehicle_interest": "Synthetic Demo SUV",
                    "budget_range": "$25,000-$30,000",
                    "financing_interest": True,
                    "trade_in_interest": False,
                    "lead_summary": "Synthetic lead wants to talk this week.",
                    "recommended_next_action": "A salesperson should review and respond.",
                }
            )
        else:
            content = json.dumps(
                {"draft": "Thanks for your interest. Would you like to schedule a call?"}
            )
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


class FakeGroqOpenAI:
    def __init__(self) -> None:
        self.chat = SimpleNamespace(completions=FakeCompletions())

    async def close(self) -> None:
        pass


def lead() -> LeadInput:
    return LeadInput(
        first_name="Groq",
        last_name="Synthetic",
        email="groq.synthetic@example.com",
        vehicle_interest="Synthetic Demo SUV",
    )


@pytest.mark.asyncio
async def test_groq_uses_strict_structured_output_and_validates_with_pydantic() -> None:
    fake = FakeGroqOpenAI()
    client = GroqLeadClient("unused", client=fake)  # type: ignore[arg-type]
    analysis = await client.analyze(lead())
    draft = await client.draft_follow_up(lead(), analysis)

    assert isinstance(analysis, LeadAnalysis)
    assert "schedule" in draft
    request = fake.chat.completions.requests[0]
    response_format = request["response_format"]
    assert response_format["type"] == "json_schema"  # type: ignore[index]
    json_schema = response_format["json_schema"]  # type: ignore[index]
    assert json_schema["strict"] is True
    schema = json_schema["schema"]
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(schema["properties"])
