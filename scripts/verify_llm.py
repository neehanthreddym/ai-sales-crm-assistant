import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import get_settings
from app.models.lead import LeadInput
from app.services.factory import build_llm_client


async def run() -> int:
    settings = get_settings()
    try:
        client = build_llm_client(settings)
    except Exception as exc:
        print(f"FAIL: {exc}")
        return 2

    checks: list[tuple[str, bool]] = []
    try:
        lead = LeadInput(
            first_name="LLM",
            last_name="ValidationSynthetic",
            email="llm.validation.synthetic@example.com",
            vehicle_interest="Synthetic Demo SUV",
            budget=30000,
            financing_interest=True,
            trade_in_interest=False,
            notes="Synthetic validation lead requesting a conversation this week.",
        )
        analysis = await client.analyze(lead)
        checks.append(("Structured Lead Analysis", bool(analysis.lead_summary)))
        checks.append(("Validated Urgency", analysis.urgency in {"low", "medium", "high"}))
        draft = await client.draft_follow_up(lead, analysis)
        checks.append(("Structured Follow-Up Draft", bool(draft.strip())))
    except Exception as exc:
        checks.append(("Unexpected Failure", False))
        print(f"Safe error: {type(exc).__name__}: {exc}")
    finally:
        await client.aclose()

    print(f"\n{settings.llm_provider.title()} Integration Validation\n")
    for name, passed in checks:
        print(f"{name:.<32} {'PASS' if passed else 'FAIL'}")
    passed_count = sum(passed for _, passed in checks)
    print(f"\n{passed_count}/{len(checks)} integration checks passed")
    return 0 if checks and all(passed for _, passed in checks) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(run()))
