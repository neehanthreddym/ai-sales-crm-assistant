from app.integrations.hubspot.activities import ActivitiesRepository
from app.integrations.hubspot.associations import AssociationsRepository
from app.integrations.hubspot.contacts import ContactsRepository
from app.integrations.hubspot.deals import DealsRepository
from app.integrations.hubspot.models import HubSpotObject
from app.models.ai import LeadAnalysis
from app.models.lead import LeadInput


class CRMWorkflow:
    def __init__(
        self,
        contacts: ContactsRepository,
        deals: DealsRepository,
        associations: AssociationsRepository,
        activities: ActivitiesRepository,
        *,
        pipeline_id: str | None = None,
        initial_stage_id: str | None = None,
    ) -> None:
        self.contacts = contacts
        self.deals = deals
        self.associations = associations
        self.activities = activities
        self.pipeline_id = pipeline_id
        self.initial_stage_id = initial_stage_id

    async def upsert_records(
        self, lead: LeadInput
    ) -> tuple[HubSpotObject, HubSpotObject, str, bool, bool]:
        contact, contact_created = await self.contacts.upsert(lead)
        pipeline, stage = await self.deals.resolve_pipeline_stage(
            self.pipeline_id, self.initial_stage_id
        )
        deal = await self.deals.find_active_for_contact(
            contact.id,
            pipeline_id=pipeline.id,
            vehicle_interest=lead.vehicle_interest,
        )
        deal_created = deal is None
        if deal is None:
            deal = await self.deals.create(lead, pipeline_id=pipeline.id, stage_id=stage.id)
            await self.associations.associate("contacts", contact.id, "deals", deal.id)
        return (
            contact,
            deal,
            str(deal.properties.get("dealstage") or stage.id),
            contact_created,
            deal_created,
        )

    async def log_ai_output(
        self,
        *,
        contact_id: str,
        deal_id: str,
        analysis: LeadAnalysis,
        follow_up_draft: str,
    ) -> HubSpotObject:
        return await self.activities.create_ai_note(
            contact_id=contact_id,
            deal_id=deal_id,
            analysis=analysis,
            follow_up_draft=follow_up_draft,
        )
