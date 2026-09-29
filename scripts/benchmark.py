import argparse
import asyncio
import json
import math
import statistics
import sys
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from types import SimpleNamespace
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.models.ai import LeadAnalysis
from app.models.lead import LeadInput
from app.services.lead_service import LeadService

FIXTURES = ROOT / "tests" / "fixtures" / "synthetic_leads.json"
OUTPUT = ROOT / "artifacts" / "benchmark_results.json"


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    return ordered[max(0, math.ceil(fraction * len(ordered)) - 1)]


class BenchmarkAI:
    def __init__(self) -> None:
        self.latencies: list[float] = []

    async def analyze(self, lead: LeadInput) -> LeadAnalysis:
        started = perf_counter()
        await asyncio.sleep(0)
        result = LeadAnalysis(
            intent="Synthetic benchmark inquiry",
            urgency="high" if "week" in (lead.notes or "").lower() else "medium",
            vehicle_interest=lead.vehicle_interest,
            budget_range=str(lead.budget) if lead.budget else None,
            financing_interest=lead.financing_interest,
            trade_in_interest=lead.trade_in_interest,
            lead_summary="Deterministic synthetic analysis used only by the offline benchmark.",
            recommended_next_action="A salesperson should review the synthetic lead.",
        )
        self.latencies.append((perf_counter() - started) * 1000)
        return result

    async def draft(self, _: LeadInput, __: LeadAnalysis) -> str:
        started = perf_counter()
        await asyncio.sleep(0)
        self.latencies.append((perf_counter() - started) * 1000)
        return "Synthetic draft for benchmark validation; human review required."


class BenchmarkCRM:
    def __init__(self) -> None:
        self.contacts: dict[str, str] = {}
        self.deals: dict[str, str] = {}
        self.created_contacts = 0
        self.created_deals = 0

    async def upsert_records(self, lead: LeadInput) -> tuple[object, object, str, bool, bool]:
        email = str(lead.email).casefold()
        contact_created = email not in self.contacts
        if contact_created:
            self.created_contacts += 1
            self.contacts[email] = f"contact-{self.created_contacts}"
        deal_created = email not in self.deals
        if deal_created:
            self.created_deals += 1
            self.deals[email] = f"deal-{self.created_deals}"
        return (
            SimpleNamespace(id=self.contacts[email]),
            SimpleNamespace(id=self.deals[email]),
            "benchmark-stage",
            contact_created,
            deal_created,
        )

    async def log_ai_output(self, **_: object) -> object:
        return SimpleNamespace(id="benchmark-note")


class BenchmarkSheets:
    def __init__(self) -> None:
        self.rows: dict[str, list[str]] = {}

    def build_row(self, lead: LeadInput, *_: object, **__: object) -> list[str]:
        return [str(lead.email)]

    async def upsert(self, row: list[str]) -> str:
        result = "updated" if row[0] in self.rows else "created"
        self.rows[row[0]] = row
        return result


async def offline_benchmark(count: int) -> dict[str, Any]:
    source = json.loads(FIXTURES.read_text())
    payloads = []
    for index in range(count):
        item = dict(source[index % len(source)])
        if index >= len(source):
            base = index % max(1, count - 5)
            item["email"] = f"benchmark.synthetic.{base}@example.com"
            item["first_name"] = f"Benchmark{base}"
        payloads.append(item)
    # Force the final five requests to repeat earlier identities.
    for index in range(max(0, count - 5), count):
        payloads[index] = dict(payloads[index - (count - 5)])

    ai = BenchmarkAI()
    crm = BenchmarkCRM()
    sheets = BenchmarkSheets()
    service = LeadService(ai, crm, object(), object(), sheets)  # type: ignore[arg-type]
    latencies: list[float] = []
    successes = 0
    sheet_successes = 0
    for payload in payloads:
        started = perf_counter()
        result = await service.process(LeadInput.model_validate(payload))
        latencies.append((perf_counter() - started) * 1000)
        successes += result.status == "success"
        sheet_successes += result.sheet_synced
    unique_emails = len({item["email"].casefold() for item in payloads})
    duplicate_checks = count - unique_emails
    duplicates_prevented = count - crm.created_contacts
    return {
        "mode": "offline_mocked_integrations",
        "disclaimer": (
            "Measures local orchestration with deterministic mocked external services; "
            "not external API performance."
        ),
        "requests": count,
        "successful_workflows": successes,
        "workflow_completion_rate": successes / count,
        "median_end_to_end_latency_ms": round(statistics.median(latencies), 3),
        "p95_end_to_end_latency_ms": round(percentile(latencies, 0.95), 3),
        "hubspot_api_failure_count": 0,
        "median_mock_llm_latency_ms": round(statistics.median(ai.latencies), 3),
        "sheets_sync_success_rate": sheet_successes / count,
        "duplicate_requests": duplicate_checks,
        "duplicate_prevention_success_rate": (
            duplicates_prevented / duplicate_checks if duplicate_checks else None
        ),
        "unique_contacts_created": crm.created_contacts,
        "unique_sheet_rows": len(sheets.rows),
    }


async def live_benchmark(count: int, base_url: str) -> dict[str, Any]:
    source = json.loads(FIXTURES.read_text())
    latencies: list[float] = []
    successful = 0
    sheet_successes = 0
    async with httpx.AsyncClient(base_url=base_url, timeout=90) as client:
        for index in range(count):
            payload = dict(source[index % len(source)])
            payload["email"] = f"live.benchmark.synthetic.{index % max(1, count - 5)}@example.com"
            started = perf_counter()
            response = await client.post("/api/v1/leads/process", json=payload)
            latencies.append((perf_counter() - started) * 1000)
            if response.is_success:
                successful += 1
                sheet_successes += bool(response.json().get("sheet_synced"))
    return {
        "mode": "live_http_external_integrations",
        "requests": count,
        "successful_workflows": successful,
        "workflow_completion_rate": successful / count,
        "median_end_to_end_latency_ms": round(statistics.median(latencies), 3),
        "p95_end_to_end_latency_ms": round(percentile(latencies, 0.95), 3),
        "hubspot_api_failure_count": count - successful,
        "llm_processing_latency_ms": "Not separately measured.",
        "sheets_sync_success_rate": sheet_successes / count,
        "duplicate_prevention_success_rate": (
            "Run verification scripts and inspect CRM before claiming."
        ),
    }


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=25, choices=range(20, 51))
    parser.add_argument("--base-url", help="Use a running API and real configured integrations")
    args = parser.parse_args()
    results = (
        await live_benchmark(args.count, args.base_url)
        if args.base_url
        else await offline_benchmark(args.count)
    )
    results["measured_at"] = datetime.now(UTC).isoformat()
    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps(results, indent=2))
    print(f"\nSaved {OUTPUT}")


if __name__ == "__main__":
    asyncio.run(main())
