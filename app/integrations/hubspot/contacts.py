from app.integrations.hubspot.client import HubSpotClient
from app.integrations.hubspot.models import HubSpotObject
from app.models.lead import LeadInput


class ContactsRepository:
    def __init__(self, client: HubSpotClient) -> None:
        self.client = client

    async def search_by_email(self, email: str) -> HubSpotObject | None:
        data = await self.client.request(
            "POST",
            f"{self.client.objects_path}/contacts/search",
            json={
                "filterGroups": [
                    {"filters": [{"propertyName": "email", "operator": "EQ", "value": email}]}
                ],
                "properties": ["email", "firstname", "lastname", "phone"],
                "limit": 1,
            },
        )
        results = data.get("results", [])
        return HubSpotObject.model_validate(results[0]) if results else None

    async def get(self, contact_id: str, *, include_deals: bool = False) -> HubSpotObject:
        params: dict[str, str] = {"properties": "email,firstname,lastname,phone"}
        if include_deals:
            params["associations"] = "deals"
        data = await self.client.request(
            "GET", f"{self.client.objects_path}/contacts/{contact_id}", params=params
        )
        return HubSpotObject.model_validate(data)

    @staticmethod
    def properties(lead: LeadInput) -> dict[str, str]:
        values = {
            "firstname": lead.first_name,
            "lastname": lead.last_name,
            "email": str(lead.email),
        }
        if lead.phone:
            values["phone"] = lead.phone
        return values

    async def create(self, lead: LeadInput) -> HubSpotObject:
        data = await self.client.request(
            "POST",
            f"{self.client.objects_path}/contacts",
            json={"properties": self.properties(lead)},
        )
        return HubSpotObject.model_validate(data)

    async def update(self, contact_id: str, lead: LeadInput) -> HubSpotObject:
        data = await self.client.request(
            "PATCH",
            f"{self.client.objects_path}/contacts/{contact_id}",
            json={"properties": self.properties(lead)},
        )
        return HubSpotObject.model_validate(data)

    async def upsert(self, lead: LeadInput) -> tuple[HubSpotObject, bool]:
        existing = await self.search_by_email(str(lead.email))
        if existing:
            return await self.update(existing.id, lead), False
        return await self.create(lead), True
