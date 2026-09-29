import asyncio
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import get_settings
from app.integrations.hubspot.activities import ActivitiesRepository
from app.integrations.hubspot.associations import AssociationsRepository
from app.integrations.hubspot.client import HubSpotClient
from app.integrations.hubspot.contacts import ContactsRepository
from app.integrations.hubspot.deals import DealsRepository
from app.models.ai import LeadAnalysis
from app.models.lead import LeadInput


async def run() -> int:
    settings = get_settings()
    if settings.hubspot_access_token is None:
        print("FAIL: HUBSPOT_ACCESS_TOKEN is not configured; no live checks were run.")
        return 2
    suffix = uuid4().hex[:10]
    lead = LeadInput(
        first_name="HubSpot",
        last_name="ValidationSynthetic",
        email=f"hubspot.validation.{suffix}@example.com",
        phone="9015550199",
        vehicle_interest="Synthetic Demo Vehicle",
        budget=30000,
    )
    api = HubSpotClient(
        settings.hubspot_access_token.get_secret_value(),
        base_url=settings.hubspot_base_url,
        api_version=settings.hubspot_api_version,
    )
    contacts = ContactsRepository(api)
    deals = DealsRepository(api)
    associations = AssociationsRepository(api)
    activities = ActivitiesRepository(api, associations)
    checks: list[tuple[str, bool]] = []
    try:
        pipelines = await deals.list_pipelines()
        checks.append(("Authentication", bool(pipelines)))
        contact = await contacts.create(lead)
        checks.append(("Contact Create", bool(contact.id)))
        retrieved = await contacts.get(contact.id)
        checks.append(("Contact Retrieve", retrieved.id == contact.id))
        updated_lead = lead.model_copy(update={"phone": "9015550188"})
        updated = await contacts.update(contact.id, updated_lead)
        checks.append(("Contact Update", updated.id == contact.id))
        found = await contacts.search_by_email(str(lead.email))
        checks.append(("Duplicate Detection", found is not None and found.id == contact.id))
        pipeline, initial_stage = await deals.resolve_pipeline_stage(
            settings.hubspot_pipeline_id, settings.hubspot_initial_stage_id
        )
        deal = await deals.create(lead, pipeline_id=pipeline.id, stage_id=initial_stage.id)
        checks.append(("Deal Create", bool(deal.id)))
        await associations.associate("contacts", contact.id, "deals", deal.id)
        associated = await contacts.get(contact.id, include_deals=True)
        association_results = associated.associations.get("deals", {}).get("results", [])
        checks.append(
            (
                "Contact-Deal Association",
                any(
                    str(x.get("toObjectId") or x.get("id")) == deal.id for x in association_results
                ),
            )
        )
        target_stage = next(
            (stage for stage in pipeline.stages if not stage.archived), initial_stage
        )
        staged = await deals.update_stage(deal.id, target_stage.id)
        checks.append(("Deal Stage Update", staged.properties.get("dealstage") == target_stage.id))
        analysis = LeadAnalysis(
            intent="Synthetic integration validation",
            urgency="low",
            vehicle_interest=lead.vehicle_interest,
            financing_interest=False,
            trade_in_interest=False,
            lead_summary="Synthetic record created by the HubSpot validation script.",
            recommended_next_action="Verify the synthetic objects, then archive them manually.",
        )
        note = await activities.create_ai_note(
            contact_id=contact.id,
            deal_id=deal.id,
            analysis=analysis,
            follow_up_draft="Synthetic validation draft; do not send.",
        )
        note_data = await api.request(
            "GET", f"{api.objects_path}/notes/{note.id}", params={"associations": "contacts,deals"}
        )
        checks.append(("CRM Note Creation", note_data.get("id") == note.id))
    except Exception as exc:
        checks.append(("Unexpected Failure", False))
        print(f"Safe error: {type(exc).__name__}: {exc}")
    finally:
        await api.aclose()

    print("\nHubSpot Integration Validation\n")
    for name, passed in checks:
        print(f"{name:.<32} {'PASS' if passed else 'FAIL'}")
    passed_count = sum(passed for _, passed in checks)
    timestamp = datetime.now(UTC).isoformat()
    print(f"\n{passed_count}/{len(checks)} integration checks passed at {timestamp}")
    return 0 if checks and all(passed for _, passed in checks) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(run()))
