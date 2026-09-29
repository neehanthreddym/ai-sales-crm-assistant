from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from app.core.exceptions import ExternalServiceError
from app.integrations.google_sheets.client import GoogleSheetsClient
from app.models.ai import LeadAnalysis
from app.models.lead import LeadInput

HEADERS = [
    "Lead ID",
    "First Name",
    "Last Name",
    "Email",
    "Vehicle Interest",
    "Budget",
    "Urgency",
    "CRM Contact ID",
    "CRM Deal ID",
    "Deal Stage",
    "Recommended Next Action",
    "Last Updated",
    "Workflow Status",
]


class SheetsRepository:
    def __init__(self, client: GoogleSheetsClient, worksheet: str = "Leads") -> None:
        self.client = client
        self.worksheet = worksheet

    async def read_rows(self) -> list[list[Any]]:
        data = await self.client.request("GET", self.client.values_path(f"{self.worksheet}!A:M"))
        return data.get("values", [])

    async def ensure_headers(self, rows: list[list[Any]] | None = None) -> list[list[Any]]:
        rows = await self.read_rows() if rows is None else rows
        if not rows:
            await self.client.request(
                "PUT",
                self.client.values_path(f"{self.worksheet}!A1:M1"),
                params={"valueInputOption": "RAW"},
                json={"values": [HEADERS]},
            )
            return [HEADERS]
        if rows[0] != HEADERS:
            raise ExternalServiceError(
                "Google Sheets header row does not match the documented schema"
            )
        return rows

    @staticmethod
    def _string(value: str | Decimal | None) -> str:
        return "" if value is None else str(value)

    def build_row(
        self,
        lead: LeadInput,
        analysis: LeadAnalysis,
        *,
        workflow_id: str,
        contact_id: str,
        deal_id: str,
        deal_stage: str,
        status: str,
    ) -> list[str]:
        return [
            workflow_id,
            lead.first_name,
            lead.last_name,
            str(lead.email),
            self._string(lead.vehicle_interest),
            self._string(lead.budget),
            analysis.urgency,
            contact_id,
            deal_id,
            deal_stage,
            analysis.recommended_next_action,
            datetime.now(UTC).isoformat(),
            status,
        ]

    async def upsert(self, row: list[str]) -> str:
        rows = await self.ensure_headers()
        email = row[3].casefold()
        contact_id = row[7]
        match = next(
            (
                index
                for index, existing in enumerate(rows[1:], start=2)
                if (len(existing) > 7 and str(existing[7]) == contact_id)
                or (len(existing) > 3 and str(existing[3]).casefold() == email)
            ),
            None,
        )
        if match is None:
            await self.client.request(
                "POST",
                self.client.values_path(f"{self.worksheet}!A:M", ":append"),
                params={"valueInputOption": "RAW", "insertDataOption": "INSERT_ROWS"},
                json={"values": [row]},
            )
            return "created"
        await self.client.request(
            "PUT",
            self.client.values_path(f"{self.worksheet}!A{match}:M{match}"),
            params={"valueInputOption": "RAW"},
            json={"values": [row]},
        )
        return "updated"
