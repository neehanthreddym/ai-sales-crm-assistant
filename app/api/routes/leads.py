from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import EmailStr

from app.config import get_settings
from app.models.crm import LeadProcessResponse, StageUpdateRequest
from app.models.lead import LeadInput
from app.services.factory import build_lead_service
from app.services.lead_service import LeadService

router = APIRouter(prefix="/api/v1/leads", tags=["leads"])


def get_lead_service(request: Request) -> LeadService:
    service = getattr(request.app.state, "lead_service", None)
    if service is None:
        service = build_lead_service(get_settings())
        request.app.state.lead_service = service
    return service


Service = Annotated[LeadService, Depends(get_lead_service)]


@router.post("/process", response_model=LeadProcessResponse)
async def process_lead(lead: LeadInput, service: Service) -> LeadProcessResponse:
    return await service.process(lead)


@router.get("/{email}")
async def get_lead(email: EmailStr, service: Service) -> dict[str, object]:
    return await service.get_by_email(str(email))


@router.patch("/{email}/stage")
async def update_lead_stage(
    email: EmailStr, payload: StageUpdateRequest, service: Service
) -> dict[str, object]:
    return await service.update_stage(str(email), payload.stage_id)
