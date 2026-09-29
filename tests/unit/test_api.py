from fastapi.testclient import TestClient

from app.main import app
from app.models.ai import LeadAnalysis
from app.models.crm import LeadProcessResponse


class FakeLeadService:
    async def process(self, _: object) -> LeadProcessResponse:
        analysis = LeadAnalysis(
            intent="Purchase",
            urgency="medium",
            financing_interest=False,
            trade_in_interest=False,
            lead_summary="Synthetic lead.",
            recommended_next_action="Review.",
        )
        return LeadProcessResponse(
            status="success",
            workflow_id="workflow-1",
            contact_id="contact-1",
            deal_id="deal-1",
            lead_analysis=analysis,
            recommended_action="Review.",
            follow_up_draft="Draft.",
            sheet_synced=True,
            processing_time_ms=12,
        )

    async def get_by_email(self, email: str) -> dict[str, object]:
        return {"contact_id": "contact-1", "email": email}

    async def update_stage(self, _: str, stage_id: str) -> dict[str, object]:
        return {"status": "success", "stage_id": stage_id}

    async def aclose(self) -> None:
        pass


def test_process_endpoint_and_validation() -> None:
    app.state.lead_service = FakeLeadService()
    with TestClient(app) as client:
        valid = client.post(
            "/api/v1/leads/process",
            json={
                "first_name": "API",
                "last_name": "Synthetic",
                "email": "api.synthetic@example.com",
            },
        )
        invalid = client.post(
            "/api/v1/leads/process",
            json={"first_name": "", "last_name": "Synthetic", "email": "bad"},
        )
    assert valid.status_code == 200
    assert valid.json()["deal_id"] == "deal-1"
    assert invalid.status_code == 422
    del app.state.lead_service


def test_get_and_patch_endpoints() -> None:
    app.state.lead_service = FakeLeadService()
    with TestClient(app) as client:
        read = client.get("/api/v1/leads/api.synthetic@example.com")
        update = client.patch(
            "/api/v1/leads/api.synthetic@example.com/stage", json={"stage_id": "qualified"}
        )
    assert read.status_code == 200
    assert update.json()["stage_id"] == "qualified"
    del app.state.lead_service
