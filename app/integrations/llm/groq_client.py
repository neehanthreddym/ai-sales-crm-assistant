import json
from time import perf_counter
from typing import Any

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncOpenAI,
    RateLimitError,
)
from pydantic import BaseModel, ValidationError

from app.core.exceptions import AuthenticationError, ExternalServiceError, LLMOutputError
from app.core.logging import get_logger
from app.models.ai import FollowUpDraft, LeadAnalysis
from app.models.lead import LeadInput
from app.prompts.follow_up import FOLLOW_UP_SYSTEM_PROMPT
from app.prompts.lead_analysis import LEAD_ANALYSIS_SYSTEM_PROMPT


def _strict_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Adapt Pydantic JSON Schema to Groq strict-mode requirements."""
    schema.pop("default", None)
    if schema.get("type") == "object" or "properties" in schema:
        properties = schema.get("properties", {})
        schema["additionalProperties"] = False
        schema["required"] = list(properties)
    for value in schema.values():
        if isinstance(value, dict):
            _strict_schema(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    _strict_schema(item)
    return schema


class GroqLeadClient:
    """Groq adapter using its OpenAI-compatible API and strict JSON Schema output."""

    def __init__(
        self,
        api_key: str,
        *,
        model: str = "openai/gpt-oss-20b",
        base_url: str = "https://api.groq.com/openai/v1",
        timeout_seconds: float = 30,
        client: AsyncOpenAI | None = None,
    ) -> None:
        self.model = model
        self._client = client or AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout_seconds,
            max_retries=2,
        )

    async def _parse(
        self,
        *,
        instructions: str,
        input_text: str,
        schema: type[BaseModel],
    ) -> BaseModel:
        started = perf_counter()
        try:
            response = await self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": instructions},
                    {"role": "user", "content": input_text},
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": schema.__name__,
                        "strict": True,
                        "schema": _strict_schema(schema.model_json_schema()),
                    },
                },
            )
        except (APITimeoutError, APIConnectionError, RateLimitError) as exc:
            raise ExternalServiceError("Groq is temporarily unavailable") from exc
        except APIStatusError as exc:
            if exc.status_code in {401, 403}:
                raise AuthenticationError("Groq authentication or permissions failed") from exc
            if exc.status_code == 400:
                raise LLMOutputError("Groq rejected the structured output request") from exc
            raise ExternalServiceError("Groq returned an API error") from exc
        content = response.choices[0].message.content
        if not content:
            raise LLMOutputError("Groq did not return a usable structured result")
        try:
            parsed = schema.model_validate(json.loads(content))
        except (json.JSONDecodeError, ValidationError) as exc:
            raise LLMOutputError(
                "Groq returned output that did not match the required schema"
            ) from exc
        get_logger().info(
            "llm_operation",
            provider="groq",
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
