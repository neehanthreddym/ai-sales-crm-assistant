import os

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_live_synthetic_workflow() -> None:
    if os.getenv("RUN_INTEGRATION_TESTS", "false").lower() != "true":
        pytest.skip("Set RUN_INTEGRATION_TESTS=true with test-account credentials")
    payload = {
        "first_name": "Integration",
        "last_name": "Synthetic",
        "email": "integration.synthetic@example.com",
        "vehicle_interest": "Synthetic Demo Vehicle",
        "notes": "Credential-gated integration test using no real customer data.",
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/leads/process", json=payload)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["contact_id"]
    assert body["deal_id"]
    assert body["lead_analysis"]["lead_summary"]
    assert body["recommended_action"]
    assert body["follow_up_draft"]
    assert body["sheet_synced"] is True
    assert body["processing_time_ms"] > 0
    print(f"\nLive workflow processing time: {body['processing_time_ms']} ms")
