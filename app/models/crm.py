from typing import Any

from pydantic import BaseModel, Field


class CRMRecord(BaseModel):
    id: str
    properties: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = None
    updated_at: str | None = None


class PipelineStage(BaseModel):
    id: str
    label: str
    display_order: int = 0
    archived: bool = False


class Pipeline(BaseModel):
    id: str
    label: str
    stages: list[PipelineStage]


class StageUpdateRequest(BaseModel):
    stage_id: str = Field(min_length=1)


class LeadProcessResponse(BaseModel):
    status: str
    workflow_id: str
    contact_id: str
    deal_id: str
    lead_analysis: "LeadAnalysis"
    recommended_action: str
    follow_up_draft: str
    sheet_synced: bool
    processing_time_ms: int
    warnings: list[str] = Field(default_factory=list)


from app.models.ai import LeadAnalysis  # noqa: E402
