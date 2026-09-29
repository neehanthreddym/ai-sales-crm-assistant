from typing import Any

from pydantic import BaseModel, Field


class AssociationType(BaseModel):
    category: str = Field(alias="category")
    type_id: int = Field(alias="typeId")
    label: str | None = None


class HubSpotObject(BaseModel):
    id: str
    properties: dict[str, Any] = Field(default_factory=dict)
    associations: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = Field(default=None, alias="createdAt")
    updated_at: str | None = Field(default=None, alias="updatedAt")


class DealStage(BaseModel):
    id: str
    label: str
    display_order: int = Field(default=0, alias="displayOrder")
    archived: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class DealPipeline(BaseModel):
    id: str
    label: str
    stages: list[DealStage]
    archived: bool = False
