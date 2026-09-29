import asyncio
import sys
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import get_settings
from app.integrations.google_sheets.client import GoogleSheetsClient
from app.integrations.google_sheets.repository import SheetsRepository
from app.models.ai import LeadAnalysis
from app.models.lead import LeadInput


async def run() -> int:
    settings = get_settings()
    if not settings.google_sheets_spreadsheet_id:
        print("FAIL: GOOGLE_SHEETS_SPREADSHEET_ID is not configured; no live checks were run.")
        return 2
    suffix = uuid4().hex[:10]
    client = GoogleSheetsClient(
        settings.google_sheets_spreadsheet_id,
        credentials_file=settings.google_application_credentials,
    )
    repo = SheetsRepository(client, settings.google_sheets_worksheet)
    checks: list[tuple[str, bool]] = []
    try:
        rows = await repo.read_rows()
        checks.append(("Authentication and Read", isinstance(rows, list)))
        lead = LeadInput(
            first_name="Sheets",
            last_name="ValidationSynthetic",
            email=f"sheets.validation.{suffix}@example.com",
        )
        analysis = LeadAnalysis(
            intent="Synthetic validation",
            urgency="low",
            financing_interest=False,
            trade_in_interest=False,
            lead_summary="Synthetic Sheets integration check.",
            recommended_next_action="No customer action; validation only.",
        )
        row = repo.build_row(
            lead,
            analysis,
            workflow_id=f"validation-{suffix}",
            contact_id=f"synthetic-contact-{suffix}",
            deal_id=f"synthetic-deal-{suffix}",
            deal_stage="synthetic-validation",
            status="validation",
        )
        first = await repo.upsert(row)
        checks.append(("Insert", first == "created"))
        reread = await repo.read_rows()
        checks.append(("Lookup", any(len(item) > 7 and item[7] == row[7] for item in reread)))
        row[12] = "validation-updated"
        second = await repo.upsert(row)
        checks.append(("Update", second == "updated"))
        final_rows = await repo.read_rows()
        matches = [item for item in final_rows if len(item) > 7 and item[7] == row[7]]
        checks.append(("Duplicate Prevention", len(matches) == 1))
    except Exception as exc:
        checks.append(("Unexpected Failure", False))
        print(f"Safe error: {type(exc).__name__}: {exc}")
    finally:
        await client.aclose()
    print("\nGoogle Sheets Integration Validation\n")
    for name, passed in checks:
        print(f"{name:.<32} {'PASS' if passed else 'FAIL'}")
    passed_count = sum(passed for _, passed in checks)
    print(f"\n{passed_count}/{len(checks)} integration checks passed")
    return 0 if checks and all(passed for _, passed in checks) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(run()))
