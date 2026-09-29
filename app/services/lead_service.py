from time import perf_counter
from uuid import uuid4

import structlog

from app.core.exceptions import ExternalServiceError, RecordNotFoundError
from app.integrations.google_sheets.repository import SheetsRepository
from app.integrations.hubspot.contacts import ContactsRepository
from app.integrations.hubspot.deals import DealsRepository
from app.models.crm import LeadProcessResponse
from app.models.lead import LeadInput
from app.services.ai_service import AIService
from app.services.crm_workflow import CRMWorkflow


class LeadService:
    def __init__(
        self,
        ai: AIService,
        crm: CRMWorkflow,
        contacts: ContactsRepository,
        deals: DealsRepository,
        sheets: SheetsRepository | None,
        *,
        closeables: list[object] | None = None,
    ) -> None:
        self.ai = ai
        self.crm = crm
        self.contacts = contacts
        self.deals = deals
        self.sheets = sheets
        self.closeables = closeables or []

    async def process(self, lead: LeadInput) -> LeadProcessResponse:
        workflow_id = str(uuid4())
        started = perf_counter()
        logger = structlog.get_logger().bind(workflow_id=workflow_id)
        logger.info("workflow_started", execution_stage="validation_complete")
        analysis = await self.ai.analyze(lead)
        contact, deal, deal_stage, contact_created, deal_created = await self.crm.upsert_records(
            lead
        )
        follow_up = await self.ai.draft(lead, analysis)
        await self.crm.log_ai_output(
            contact_id=contact.id,
            deal_id=deal.id,
            analysis=analysis,
            follow_up_draft=follow_up,
        )
        warnings: list[str] = []
        sheet_synced = False
        if self.sheets is None:
            warnings.append("Google Sheets integration is not configured")
        else:
            row = self.sheets.build_row(
                lead,
                analysis,
                workflow_id=workflow_id,
                contact_id=contact.id,
                deal_id=deal.id,
                deal_stage=deal_stage,
                status="success",
            )
            try:
                await self.sheets.upsert(row)
                sheet_synced = True
            except ExternalServiceError:
                logger.exception("sheet_sync_failed", execution_stage="sheets_sync")
                warnings.append("CRM workflow completed, but Google Sheets synchronization failed")
        elapsed = round((perf_counter() - started) * 1000)
        logger.info(
            "workflow_completed",
            execution_stage="complete",
            latency_ms=elapsed,
            contact_created=contact_created,
            deal_created=deal_created,
            sheet_synced=sheet_synced,
        )
        return LeadProcessResponse(
            status="success" if not warnings else "partial_success",
            workflow_id=workflow_id,
            contact_id=contact.id,
            deal_id=deal.id,
            lead_analysis=analysis,
            recommended_action=analysis.recommended_next_action,
            follow_up_draft=follow_up,
            sheet_synced=sheet_synced,
            processing_time_ms=elapsed,
            warnings=warnings,
        )

    async def get_by_email(self, email: str) -> dict[str, object]:
        contact = await self.contacts.search_by_email(email)
        if contact is None:
            raise RecordNotFoundError("No HubSpot contact was found for that email")
        deal = await self.deals.require_for_contact(contact.id)
        return {
            "contact_id": contact.id,
            "contact_properties": contact.properties,
            "deal_id": deal.id,
            "deal_properties": deal.properties,
        }

    async def update_stage(self, email: str, stage_id: str) -> dict[str, object]:
        contact = await self.contacts.search_by_email(email)
        if contact is None:
            raise RecordNotFoundError("No HubSpot contact was found for that email")
        deal = await self.deals.require_for_contact(contact.id)
        updated = await self.deals.update_stage(deal.id, stage_id)
        return {
            "status": "success",
            "contact_id": contact.id,
            "deal_id": updated.id,
            "stage_id": stage_id,
        }

    async def aclose(self) -> None:
        for item in self.closeables:
            closer = getattr(item, "aclose", None)
            if closer:
                await closer()
