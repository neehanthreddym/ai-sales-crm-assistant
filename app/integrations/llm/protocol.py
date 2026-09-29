from typing import Protocol

from app.models.ai import LeadAnalysis
from app.models.lead import LeadInput


class LeadLLMClient(Protocol):
    async def analyze(self, lead: LeadInput) -> LeadAnalysis: ...

    async def draft_follow_up(self, lead: LeadInput, analysis: LeadAnalysis) -> str: ...

    async def aclose(self) -> None: ...
