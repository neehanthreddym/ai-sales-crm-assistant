from time import perf_counter

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncOpenAI,
    RateLimitError,
)
from pydantic import ValidationError

from app.core.exceptions import AuthenticationError, ExternalServiceError, LLMOutputError
from app.core.logging import get_logger
from app.models.ai import FollowUpDraft, LeadAnalysis
from app.models.lead import LeadInput
from app.prompts.follow_up import FOLLOW_UP_SYSTEM_PROMPT
from app.prompts.lead_analysis import LEAD_ANALYSIS_SYSTEM_PROMPT


class OpenAILeadClient:
    """Responses API adapter using SDK-native Pydantic structured outputs."""

    def __init__(
        self,
        api_key: str,
        *,
        model: str,
        timeout_seconds: float = 30,
        client: AsyncOpenAI | None = None,
    ) -> None:
        self.model = model
        self._client = client or AsyncOpenAI(
            api_key=api_key, timeout=timeout_seconds, max_retries=2
        )

    async def _parse(self, *, instructions: str, input_text: str, schema: type) -> object:
        started = perf_counter()
        try:
            response = await self._client.responses.parse(
                model=self.model,
                instructions=instructions,
                input=input_text,
                text_format=schema,
            )
        except (APITimeoutError, APIConnectionError, RateLimitError) as exc:
            raise ExternalServiceError("OpenAI is temporarily unavailable") from exc
        except APIStatusError as exc:
            if exc.status_code in {401, 403}:
                raise AuthenticationError("OpenAI authentication or permissions failed") from exc
            raise ExternalServiceError("OpenAI returned an API error") from exc
        except ValidationError as exc:
            raise LLMOutputError(
                "OpenAI returned output that did not match the required schema"
            ) from exc
        parsed = response.output_parsed
        if parsed is None:
            raise LLMOutputError("OpenAI did not return a usable structured result")
        get_logger().info(
            "llm_operation",
            execution_stage="structured_generation",
            latency_ms=round((perf_counter() - started) * 1000),
            model=self.model,
        )
        return parsed

    async def analyze(self, lead: LeadInput) -> LeadAnalysis:
        result = await self._parse(
            instructions=LEAD_ANALYSIS_SYSTEM_PROMPT,
            input_text=lead.model_dump_json(exclude_none=True),
            schema=LeadAnalysis,
        )
        return result  # type: ignore[return-value]

    async def draft_follow_up(self, lead: LeadInput, analysis: LeadAnalysis) -> str:
        result = await self._parse(
            instructions=FOLLOW_UP_SYSTEM_PROMPT,
            input_text=(
                f"Validated lead:\n{lead.model_dump_json(exclude_none=True)}\n"
                f"Validated analysis:\n{analysis.model_dump_json()}"
            ),
            schema=FollowUpDraft,
        )
        return result.draft  # type: ignore[union-attr]

    async def aclose(self) -> None:
        await self._client.close()
