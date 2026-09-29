from types import SimpleNamespace

import pytest

from app.core.exceptions import ExternalServiceError
from app.models.ai import LeadAnalysis
from app.models.lead import LeadInput
from app.services.lead_service import LeadService


class FakeAI:
    async def analyze(self, _: LeadInput) -> LeadAnalysis:
        return LeadAnalysis(
            intent="Purchase",
            urgency="medium",
            financing_interest=False,
            trade_in_interest=False,
            lead_summary="Synthetic lead.",
            recommended_next_action="Human review and follow-up.",
        )

    async def draft(self, _: LeadInput, __: LeadAnalysis) -> str:
        return "Thanks for your inquiry. Would you like to schedule a conversation?"


class FakeCRM:
    def __init__(self) -> None:
        self.logged = False

    async def upsert_records(self, _: LeadInput) -> tuple[object, object, str, bool, bool]:
        return (
            SimpleNamespace(id="contact-1"),
            SimpleNamespace(id="deal-1"),
            "stage-1",
            True,
            True,
        )

    async def log_ai_output(self, **_: object) -> object:
        self.logged = True
        return SimpleNamespace(id="note-1")


class FakeSheets:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.upserts = 0

    def build_row(self, *_: object, **__: object) -> list[str]:
        return ["row"]

    async def upsert(self, _: list[str]) -> str:
        self.upserts += 1
        if self.fail:
            raise ExternalServiceError("synthetic sheets outage")
        return "created"


def lead() -> LeadInput:
    return LeadInput(
        first_name="Workflow",
        last_name="Synthetic",
        email="workflow.synthetic@example.com",
    )


@pytest.mark.asyncio
async def test_end_to_end_orchestration_returns_structured_response() -> None:
    crm = FakeCRM()
    sheets = FakeSheets()
    service = LeadService(FakeAI(), crm, object(), object(), sheets)  # type: ignore[arg-type]
    result = await service.process(lead())
    assert result.status == "success"
    assert result.contact_id == "contact-1"
    assert result.deal_id == "deal-1"
    assert result.sheet_synced is True
    assert result.processing_time_ms >= 0
    assert crm.logged is True
    assert sheets.upserts == 1


@pytest.mark.asyncio
async def test_sheet_failure_returns_partial_success_after_crm_completion() -> None:
    service = LeadService(FakeAI(), FakeCRM(), object(), object(), FakeSheets(fail=True))  # type: ignore[arg-type]
    result = await service.process(lead())
    assert result.status == "partial_success"
    assert result.sheet_synced is False
    assert result.warnings
