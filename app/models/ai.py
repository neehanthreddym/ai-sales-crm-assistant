from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class LeadAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent: str = Field(min_length=1, max_length=200)
    urgency: Literal["low", "medium", "high"]
    vehicle_interest: str | None = Field(default=None, max_length=160)
    budget_range: str | None = Field(default=None, max_length=100)
    financing_interest: bool
    trade_in_interest: bool
    lead_summary: str = Field(min_length=1, max_length=1000)
    recommended_next_action: str = Field(min_length=1, max_length=500)


class FollowUpDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    draft: str = Field(min_length=1, max_length=2000)
