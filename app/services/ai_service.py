from app.integrations.llm.protocol import LeadLLMClient
from app.models.ai import LeadAnalysis
from app.models.lead import LeadInput
from app.services.urgency import classify_urgency


class AIService:
    def __init__(self, client: LeadLLMClient) -> None:
        self.client = client

    async def analyze(self, lead: LeadInput) -> LeadAnalysis:
        analysis = await self.client.analyze(lead)
        return analysis.model_copy(update={"urgency": classify_urgency(lead)})

    async def draft(self, lead: LeadInput, analysis: LeadAnalysis) -> str:
        return await self.client.draft_follow_up(lead, analysis)
