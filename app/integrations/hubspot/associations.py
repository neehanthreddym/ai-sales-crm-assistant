from app.core.exceptions import CRMValidationError
from app.integrations.hubspot.client import HubSpotClient


class AssociationsRepository:
    def __init__(self, client: HubSpotClient) -> None:
        self.client = client

    async def default_type(self, from_type: str, to_type: str) -> dict[str, object]:
        data = await self.client.request(
            "GET",
            f"/crm/associations/{self.client.api_version}/{from_type}/{to_type}/labels",
        )
        candidates = [
            item
            for item in data.get("results", [])
            if item.get("category") == "HUBSPOT_DEFINED" and item.get("label") in {None, ""}
        ]
        if not candidates:
            candidates = [
                item
                for item in data.get("results", [])
                if item.get("category") == "HUBSPOT_DEFINED"
            ]
        if not candidates:
            raise CRMValidationError(
                f"No HubSpot-defined {from_type}-to-{to_type} association exists"
            )
        selected = candidates[0]
        return {
            "associationCategory": selected["category"],
            "associationTypeId": selected["typeId"],
        }

    async def associate(self, from_type: str, from_id: str, to_type: str, to_id: str) -> None:
        association_type = await self.default_type(from_type, to_type)
        await self.client.request(
            "POST",
            f"/crm/associations/{self.client.api_version}/{from_type}/{to_type}/batch/create",
            json={
                "inputs": [
                    {
                        "from": {"id": from_id},
                        "to": {"id": to_id},
                        "types": [association_type],
                    }
                ]
            },
        )
