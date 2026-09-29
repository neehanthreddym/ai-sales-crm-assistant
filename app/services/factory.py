from app.config import Settings
from app.core.exceptions import ConfigurationError
from app.integrations.google_sheets.client import GoogleSheetsClient
from app.integrations.google_sheets.repository import SheetsRepository
from app.integrations.hubspot.activities import ActivitiesRepository
from app.integrations.hubspot.associations import AssociationsRepository
from app.integrations.hubspot.client import HubSpotClient
from app.integrations.hubspot.contacts import ContactsRepository
from app.integrations.hubspot.deals import DealsRepository
from app.integrations.llm.groq_client import GroqLeadClient
from app.integrations.llm.openai_client import OpenAILeadClient
from app.integrations.llm.protocol import LeadLLMClient
from app.services.ai_service import AIService
from app.services.crm_workflow import CRMWorkflow
from app.services.lead_service import LeadService


def build_llm_client(settings: Settings) -> LeadLLMClient:
    if settings.llm_provider == "groq":
        if settings.groq_api_key is None:
            raise ConfigurationError("GROQ_API_KEY is required when LLM_PROVIDER=groq")
        return GroqLeadClient(
            settings.groq_api_key.get_secret_value(),
            model=settings.groq_model,
            base_url=settings.groq_base_url,
            timeout_seconds=settings.llm_timeout_seconds,
        )
    if settings.openai_api_key is None:
        raise ConfigurationError("OPENAI_API_KEY is required when LLM_PROVIDER=openai")
    return OpenAILeadClient(
        settings.openai_api_key.get_secret_value(),
        model=settings.openai_model,
        timeout_seconds=settings.llm_timeout_seconds,
    )


def build_lead_service(settings: Settings) -> LeadService:
    if settings.hubspot_access_token is None:
        raise ConfigurationError("HUBSPOT_ACCESS_TOKEN is required for lead processing")

    hubspot = HubSpotClient(
        settings.hubspot_access_token.get_secret_value(),
        base_url=settings.hubspot_base_url,
        api_version=settings.hubspot_api_version,
    )
    contacts = ContactsRepository(hubspot)
    deals = DealsRepository(hubspot)
    associations = AssociationsRepository(hubspot)
    activities = ActivitiesRepository(hubspot, associations)
    crm = CRMWorkflow(
        contacts,
        deals,
        associations,
        activities,
        pipeline_id=settings.hubspot_pipeline_id,
        initial_stage_id=settings.hubspot_initial_stage_id,
    )
    llm = build_llm_client(settings)
    sheets_client = None
    sheets = None
    if settings.google_sheets_spreadsheet_id:
        sheets_client = GoogleSheetsClient(
            settings.google_sheets_spreadsheet_id,
            credentials_file=settings.google_application_credentials,
        )
        sheets = SheetsRepository(sheets_client, settings.google_sheets_worksheet)
    closeables: list[object] = [hubspot, llm]
    if sheets_client:
        closeables.append(sheets_client)
    return LeadService(AIService(llm), crm, contacts, deals, sheets, closeables=closeables)
