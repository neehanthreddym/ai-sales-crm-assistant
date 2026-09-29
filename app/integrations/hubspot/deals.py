from app.core.exceptions import CRMValidationError, RecordNotFoundError
from app.integrations.hubspot.client import HubSpotClient
from app.integrations.hubspot.models import DealPipeline, DealStage, HubSpotObject
from app.models.lead import LeadInput


class DealsRepository:
    def __init__(self, client: HubSpotClient) -> None:
        self.client = client

    async def list_pipelines(self) -> list[DealPipeline]:
        data = await self.client.request("GET", f"/crm/pipelines/{self.client.api_version}/deals")
        return [DealPipeline.model_validate(item) for item in data.get("results", [])]

    async def resolve_pipeline_stage(
        self, pipeline_id: str | None, stage_id: str | None
    ) -> tuple[DealPipeline, DealStage]:
        pipelines = [item for item in await self.list_pipelines() if not item.archived]
        if not pipelines:
            raise CRMValidationError("No active HubSpot deal pipeline is available")
        pipeline = next((item for item in pipelines if item.id == pipeline_id), None)
        if pipeline_id and pipeline is None:
            raise CRMValidationError("Configured HubSpot pipeline does not exist")
        pipeline = pipeline or sorted(pipelines, key=lambda item: item.id)[0]
        stages = [item for item in pipeline.stages if not item.archived]
        stage = next((item for item in stages if item.id == stage_id), None)
        if stage_id and stage is None:
            raise CRMValidationError(
                "Configured HubSpot deal stage is not in the selected pipeline"
            )
        stage = stage or min(stages, key=lambda item: item.display_order, default=None)
        if stage is None:
            raise CRMValidationError("Selected HubSpot pipeline has no active stage")
        return pipeline, stage

    async def get(self, deal_id: str) -> HubSpotObject:
        data = await self.client.request(
            "GET",
            f"{self.client.objects_path}/deals/{deal_id}",
            params={"properties": "dealname,dealstage,pipeline,amount,hs_is_closed"},
        )
        return HubSpotObject.model_validate(data)

    async def find_active_for_contact(
        self, contact_id: str, *, pipeline_id: str, vehicle_interest: str | None
    ) -> HubSpotObject | None:
        contact = await self.client.request(
            "GET",
            f"{self.client.objects_path}/contacts/{contact_id}",
            params={"associations": "deals"},
        )
        ids = [
            item.get("toObjectId") or item.get("id")
            for item in contact.get("associations", {}).get("deals", {}).get("results", [])
            if item.get("toObjectId") or item.get("id")
        ]
        for deal_id in ids:
            deal = await self.get(str(deal_id))
            props = deal.properties
            same_vehicle = (
                not vehicle_interest
                or vehicle_interest.casefold() in str(props.get("dealname", "")).casefold()
            )
            if (
                props.get("pipeline") == pipeline_id
                and str(props.get("hs_is_closed", "false")).lower() != "true"
                and same_vehicle
            ):
                return deal
        return None

    async def create(self, lead: LeadInput, *, pipeline_id: str, stage_id: str) -> HubSpotObject:
        subject = lead.vehicle_interest or "Vehicle inquiry"
        properties = {
            "dealname": f"{lead.first_name} {lead.last_name} - {subject}",
            "pipeline": pipeline_id,
            "dealstage": stage_id,
        }
        if lead.budget is not None:
            properties["amount"] = str(lead.budget)
        data = await self.client.request(
            "POST", f"{self.client.objects_path}/deals", json={"properties": properties}
        )
        return HubSpotObject.model_validate(data)

    async def update_stage(self, deal_id: str, stage_id: str) -> HubSpotObject:
        pipelines = await self.list_pipelines()
        target_pipelines = [
            pipeline
            for pipeline in pipelines
            if any(stage.id == stage_id and not stage.archived for stage in pipeline.stages)
        ]
        if not target_pipelines:
            raise CRMValidationError("Requested deal stage is not active in this HubSpot account")
        deal = await self.get(deal_id)
        if not any(pipeline.id == deal.properties.get("pipeline") for pipeline in target_pipelines):
            raise CRMValidationError("Requested deal stage does not belong to the deal's pipeline")
        data = await self.client.request(
            "PATCH",
            f"{self.client.objects_path}/deals/{deal_id}",
            json={"properties": {"dealstage": stage_id}},
        )
        return HubSpotObject.model_validate(data)

    async def require_for_contact(self, contact_id: str) -> HubSpotObject:
        contact = await self.client.request(
            "GET",
            f"{self.client.objects_path}/contacts/{contact_id}",
            params={"associations": "deals"},
        )
        results = contact.get("associations", {}).get("deals", {}).get("results", [])
        if not results:
            raise RecordNotFoundError("No deal is associated with this contact")
        deal_id = results[0].get("toObjectId") or results[0].get("id")
        if not deal_id:
            raise RecordNotFoundError("HubSpot returned an associated deal without an identifier")
        return await self.get(str(deal_id))
