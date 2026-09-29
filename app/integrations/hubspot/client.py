import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

import httpx

from app.core.exceptions import (
    AuthenticationError,
    CRMValidationError,
    ExternalServiceError,
    RateLimitError,
)
from app.core.logging import get_logger

Sleep = Callable[[float], Awaitable[None]]


class HubSpotClient:
    """Small async REST client pinned to one documented HubSpot date version."""

    def __init__(
        self,
        access_token: str,
        *,
        base_url: str = "https://api.hubapi.com",
        api_version: str = "2026-09",
        http_client: httpx.AsyncClient | None = None,
        max_retries: int = 3,
        sleep: Sleep = asyncio.sleep,
    ) -> None:
        self.api_version = api_version
        self._owns_client = http_client is None
        self._client = http_client or httpx.AsyncClient(
            base_url=base_url,
            headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
            timeout=httpx.Timeout(20.0),
        )
        self._max_retries = max_retries
        self._sleep = sleep

    @property
    def objects_path(self) -> str:
        return f"/crm/objects/{self.api_version}"

    async def request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        logger = get_logger()
        last_response: httpx.Response | None = None
        for attempt in range(self._max_retries + 1):
            try:
                response = await self._client.request(method, path, json=json, params=params)
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                if attempt >= self._max_retries:
                    raise ExternalServiceError("HubSpot is temporarily unreachable") from exc
                await self._sleep(0.25 * (2**attempt))
                continue
            last_response = response
            logger.info(
                "hubspot_operation",
                crm_operation=f"{method.upper()} {path}",
                http_status=response.status_code,
                attempt=attempt + 1,
            )
            if response.status_code < 400:
                return response.json() if response.content else {}
            if response.status_code in {429, 500, 502, 503, 504} and attempt < self._max_retries:
                retry_after = response.headers.get("Retry-After")
                delay = (
                    float(retry_after)
                    if retry_after and retry_after.isdigit()
                    else 0.25 * (2**attempt)
                )
                await self._sleep(min(delay, 4.0))
                continue
            break

        assert last_response is not None
        status = last_response.status_code
        correlation_id = last_response.headers.get("x-hubspot-correlation-id")
        details = {"http_status": status, "correlation_id": correlation_id}
        if status in {401, 403}:
            raise AuthenticationError(
                "HubSpot authentication or permissions failed", details=details
            )
        if status == 429:
            raise RateLimitError("HubSpot rate limit exceeded", details=details)
        if status in {400, 404, 409, 422}:
            raise CRMValidationError("HubSpot rejected the CRM operation", details=details)
        raise ExternalServiceError("HubSpot returned a server error", details=details)

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()
