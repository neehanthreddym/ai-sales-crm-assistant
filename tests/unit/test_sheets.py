from typing import Any

import httpx
import pytest

from app.core.exceptions import AuthenticationError
from app.integrations.google_sheets.client import GoogleSheetsClient
from app.integrations.google_sheets.repository import HEADERS, SheetsRepository
from app.models.ai import LeadAnalysis
from app.models.lead import LeadInput


class FakeSheetsClient:
    def __init__(self, rows: list[list[Any]]) -> None:
        self.rows = rows
        self.calls: list[tuple[str, str, dict[str, Any] | None]] = []

    def values_path(self, range_name: str, suffix: str = "") -> str:
        return f"/{range_name}{suffix}"

    async def request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.calls.append((method, path, json))
        if method == "GET":
            return {"values": self.rows}
        return {}


def row(repo: SheetsRepository) -> list[str]:
    lead = LeadInput(
        first_name="Sheet",
        last_name="Synthetic",
        email="sheet.synthetic@example.com",
    )
    analysis = LeadAnalysis(
        intent="Research",
        urgency="low",
        financing_interest=False,
        trade_in_interest=False,
        lead_summary="Synthetic inquiry.",
        recommended_next_action="Review the inquiry.",
    )
    return repo.build_row(
        lead,
        analysis,
        workflow_id="workflow-1",
        contact_id="contact-1",
        deal_id="deal-1",
        deal_stage="stage-1",
        status="success",
    )


@pytest.mark.asyncio
async def test_sheets_inserts_new_row() -> None:
    client = FakeSheetsClient([HEADERS])
    repo = SheetsRepository(client)  # type: ignore[arg-type]
    assert await repo.upsert(row(repo)) == "created"
    assert client.calls[-1][0] == "POST"
    assert client.calls[-1][1].endswith(":append")


@pytest.mark.asyncio
async def test_sheets_updates_existing_contact_row() -> None:
    client = FakeSheetsClient(
        [HEADERS, ["old", "", "", "old@example.com", "", "", "", "contact-1"]]
    )
    repo = SheetsRepository(client)  # type: ignore[arg-type]
    assert await repo.upsert(row(repo)) == "updated"
    assert client.calls[-1][0] == "PUT"
    assert "A2:M2" in client.calls[-1][1]


@pytest.mark.asyncio
async def test_sheets_creates_headers_before_first_append() -> None:
    client = FakeSheetsClient([])
    repo = SheetsRepository(client)  # type: ignore[arg-type]
    await repo.upsert(row(repo))
    writes = [call for call in client.calls if call[0] in {"PUT", "POST"}]
    assert writes[0][2] == {"values": [HEADERS]}
    assert writes[1][0] == "POST"


@pytest.mark.asyncio
async def test_sheets_client_retries_transient_server_error() -> None:
    attempts = 0
    sleeps: list[float] = []

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(500 if attempts == 1 else 200, json={"values": []})

    async def sleep(delay: float) -> None:
        sleeps.append(delay)

    credentials = type("Credentials", (), {"valid": True, "token": "test-token"})()
    http = httpx.AsyncClient(
        base_url="https://sheets.googleapis.com", transport=httpx.MockTransport(handler)
    )
    client = GoogleSheetsClient(
        "sheet-1",
        credentials=credentials,  # type: ignore[arg-type]
        http_client=http,
        max_retries=1,
        sleep=sleep,
    )
    result = await client.request("GET", client.values_path("Leads!A:M"))
    assert result == {"values": []}
    assert sleeps == [0.25]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status_code", "expected_message"),
    [
        (401, "rejected the service-account credentials"),
        (403, "enable the Sheets API and share the spreadsheet"),
    ],
)
async def test_sheets_client_maps_auth_and_permission_errors_safely(
    status_code: int, expected_message: str
) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json={"error": {"message": "sensitive upstream body"}})

    credentials = type("Credentials", (), {"valid": True, "token": "test-token"})()
    http = httpx.AsyncClient(
        base_url="https://sheets.googleapis.com", transport=httpx.MockTransport(handler)
    )
    client = GoogleSheetsClient(
        "sheet-1",
        credentials=credentials,  # type: ignore[arg-type]
        http_client=http,
        max_retries=0,
    )

    with pytest.raises(AuthenticationError) as exc:
        await client.request("GET", client.values_path("Leads!A:M"))

    assert expected_message in str(exc.value)
    assert "sensitive upstream body" not in str(exc.value)
