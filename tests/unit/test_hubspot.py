import json

import httpx
import pytest

from app.core.exceptions import AuthenticationError, CRMValidationError
from app.integrations.hubspot.activities import ActivitiesRepository
from app.integrations.hubspot.associations import AssociationsRepository
from app.integrations.hubspot.client import HubSpotClient
from app.integrations.hubspot.contacts import ContactsRepository
from app.integrations.hubspot.deals import DealsRepository
from app.models.ai import LeadAnalysis
from app.models.lead import LeadInput


def lead() -> LeadInput:
    return LeadInput.model_validate(
        {
            "first_name": "Alex",
            "last_name": "Synthetic",
            "email": "alex.synthetic@example.com",
            "vehicle_interest": "2025 Honda CR-V",
            "budget": 35000,
        }
    )


def client(
    handler: object, *, retries: int = 0, sleeps: list[float] | None = None
) -> HubSpotClient:
    transport = httpx.MockTransport(handler)  # type: ignore[arg-type]
    http = httpx.AsyncClient(base_url="https://api.hubapi.com", transport=transport)

    async def sleep(delay: float) -> None:
        if sleeps is not None:
            sleeps.append(delay)

    return HubSpotClient("secret", http_client=http, max_retries=retries, sleep=sleep)


@pytest.mark.asyncio
async def test_contact_create_when_lookup_is_empty() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith("/search"):
            return httpx.Response(200, json={"results": []})
        return httpx.Response(201, json={"id": "contact-1", "properties": {}})

    record, created = await ContactsRepository(client(handler)).upsert(lead())
    assert created is True
    assert record.id == "contact-1"
    assert json.loads(requests[1].content)["properties"]["email"] == "alex.synthetic@example.com"


@pytest.mark.asyncio
async def test_contact_update_when_lookup_finds_email() -> None:
    methods: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        methods.append(request.method)
        if request.url.path.endswith("/search"):
            return httpx.Response(200, json={"results": [{"id": "contact-1"}]})
        return httpx.Response(200, json={"id": "contact-1", "properties": {}})

    record, created = await ContactsRepository(client(handler)).upsert(lead())
    assert record.id == "contact-1"
    assert created is False
    assert methods == ["POST", "PATCH"]


@pytest.mark.asyncio
async def test_retry_on_rate_limit_then_success() -> None:
    attempts = 0
    sleeps: list[float] = []

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(429, headers={"Retry-After": "1"}, json={})
        return httpx.Response(200, json={"ok": True})

    result = await client(handler, retries=1, sleeps=sleeps).request("GET", "/test")
    assert result == {"ok": True}
    assert sleeps == [1.0]


@pytest.mark.asyncio
async def test_auth_error_is_safely_mapped() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"message": "token abc-super-secret is invalid"})

    with pytest.raises(AuthenticationError) as exc:
        await client(handler).request("GET", "/test")
    assert "super-secret" not in str(exc.value)


@pytest.mark.asyncio
async def test_deal_create_uses_discovered_pipeline_and_stage() -> None:
    bodies: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if "/pipelines/" in request.url.path:
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "id": "pipeline-a",
                            "label": "Sales",
                            "stages": [{"id": "stage-a", "label": "New", "displayOrder": 0}],
                        }
                    ]
                },
            )
        bodies.append(json.loads(request.content))
        return httpx.Response(201, json={"id": "deal-1", "properties": {}})

    repo = DealsRepository(client(handler))
    pipeline, stage = await repo.resolve_pipeline_stage(None, None)
    deal = await repo.create(lead(), pipeline_id=pipeline.id, stage_id=stage.id)
    assert deal.id == "deal-1"
    assert bodies[0]["properties"]["pipeline"] == "pipeline-a"  # type: ignore[index]
    assert bodies[0]["properties"]["dealstage"] == "stage-a"  # type: ignore[index]


@pytest.mark.asyncio
async def test_deal_stage_rejects_unknown_stage() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"results": [{"id": "p", "label": "P", "stages": []}]},
        )

    with pytest.raises(CRMValidationError):
        await DealsRepository(client(handler)).update_stage("deal-1", "missing")


@pytest.mark.asyncio
async def test_existing_open_matching_deal_is_reused() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/contacts/contact-1"):
            return httpx.Response(
                200,
                json={
                    "id": "contact-1",
                    "associations": {"deals": {"results": [{"toObjectId": "deal-1"}]}},
                },
            )
        return httpx.Response(
            200,
            json={
                "id": "deal-1",
                "properties": {
                    "dealname": "Alex Synthetic - 2025 Honda CR-V",
                    "pipeline": "pipeline-a",
                    "dealstage": "stage-a",
                    "hs_is_closed": "false",
                },
            },
        )

    found = await DealsRepository(client(handler)).find_active_for_contact(
        "contact-1", pipeline_id="pipeline-a", vehicle_interest="2025 Honda CR-V"
    )
    assert found is not None
    assert found.id == "deal-1"


@pytest.mark.asyncio
async def test_deal_stage_update_validates_pipeline_and_patches() -> None:
    methods: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        methods.append(request.method)
        if "/pipelines/" in request.url.path:
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "id": "pipeline-a",
                            "label": "Sales",
                            "stages": [{"id": "qualified", "label": "Qualified"}],
                        }
                    ]
                },
            )
        if request.method == "GET":
            return httpx.Response(
                200, json={"id": "deal-1", "properties": {"pipeline": "pipeline-a"}}
            )
        body = json.loads(request.content)
        assert body == {"properties": {"dealstage": "qualified"}}
        return httpx.Response(
            200,
            json={
                "id": "deal-1",
                "properties": {"pipeline": "pipeline-a", "dealstage": "qualified"},
            },
        )

    updated = await DealsRepository(client(handler)).update_stage("deal-1", "qualified")
    assert updated.properties["dealstage"] == "qualified"
    assert methods == ["GET", "GET", "PATCH"]


@pytest.mark.asyncio
async def test_association_uses_discovered_type_and_date_versioned_batch_shape() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            return httpx.Response(
                200,
                json={"results": [{"category": "HUBSPOT_DEFINED", "typeId": 4, "label": None}]},
            )
        captured["path"] = request.url.path
        captured["body"] = json.loads(request.content)
        return httpx.Response(201, json={})

    await AssociationsRepository(client(handler)).associate("contacts", "1", "deals", "2")
    assert captured["path"] == "/crm/associations/2026-09/contacts/deals/batch/create"
    assert captured["body"] == {
        "inputs": [
            {
                "from": {"id": "1"},
                "to": {"id": "2"},
                "types": [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 4}],
            }
        ]
    }


@pytest.mark.asyncio
async def test_note_creation_associates_contact_and_deal() -> None:
    posted: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            return httpx.Response(
                200,
                json={"results": [{"category": "HUBSPOT_DEFINED", "typeId": 1, "label": None}]},
            )
        posted.append(request.url.path)
        if request.url.path.endswith("/notes"):
            body = json.loads(request.content)
            assert "human review required" in body["properties"]["hs_note_body"]
            return httpx.Response(201, json={"id": "note-1", "properties": {}})
        return httpx.Response(201, json={})

    api = client(handler)
    analysis = LeadAnalysis(
        intent="Purchase inquiry",
        urgency="high",
        financing_interest=True,
        trade_in_interest=True,
        lead_summary="Synthetic lead requests an SUV.",
        recommended_next_action="Review and contact the lead.",
    )
    note = await ActivitiesRepository(api, AssociationsRepository(api)).create_ai_note(
        contact_id="contact-1",
        deal_id="deal-1",
        analysis=analysis,
        follow_up_draft="Draft only.",
    )
    assert note.id == "note-1"
    assert len(posted) == 3
