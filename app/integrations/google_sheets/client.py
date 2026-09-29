import asyncio
from collections.abc import Awaitable, Callable
from typing import Any
from urllib.parse import quote

import google.auth
import httpx
from google.auth.credentials import Credentials
from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials as ServiceAccountCredentials

from app.core.exceptions import AuthenticationError, ExternalServiceError, RateLimitError

SHEETS_SCOPE = "https://www.googleapis.com/auth/spreadsheets"
Sleep = Callable[[float], Awaitable[None]]


class GoogleSheetsClient:
    """Async Sheets v4 REST client using Application Default Credentials."""

    def __init__(
        self,
        spreadsheet_id: str,
        *,
        credentials_file: str | None = None,
        credentials: Credentials | None = None,
        http_client: httpx.AsyncClient | None = None,
        max_retries: int = 3,
        sleep: Sleep = asyncio.sleep,
    ) -> None:
        self.spreadsheet_id = spreadsheet_id
        self.credentials_file = credentials_file
        self._credentials = credentials
        self._owns_client = http_client is None
        self._client = http_client or httpx.AsyncClient(
            base_url="https://sheets.googleapis.com", timeout=httpx.Timeout(20)
        )
        self.max_retries = max_retries
        self.sleep = sleep

    def _load_credentials(self) -> Credentials:
        if self._credentials:
            return self._credentials
        if self.credentials_file:
            self._credentials = ServiceAccountCredentials.from_service_account_file(
                self.credentials_file, scopes=[SHEETS_SCOPE]
            )
        else:
            self._credentials, _ = google.auth.default(scopes=[SHEETS_SCOPE])
        return self._credentials

    async def _token(self) -> str:
        try:
            credentials = self._load_credentials()
            if not credentials.valid or not credentials.token:
                await asyncio.to_thread(credentials.refresh, Request())
            if not credentials.token:
                raise ValueError("credential refresh produced no token")
            return credentials.token
        except Exception as exc:
            raise AuthenticationError("Google Sheets authentication failed") from exc

    async def request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        token = await self._token()
        response: httpx.Response | None = None
        for attempt in range(self.max_retries + 1):
            try:
                response = await self._client.request(
                    method,
                    path,
                    json=json,
                    params=params,
                    headers={"Authorization": f"Bearer {token}"},
                )
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                if attempt >= self.max_retries:
                    raise ExternalServiceError("Google Sheets is temporarily unreachable") from exc
                await self.sleep(0.25 * (2**attempt))
                continue
            if response.status_code < 400:
                return response.json() if response.content else {}
            if response.status_code in {429, 500, 502, 503, 504} and attempt < self.max_retries:
                await self.sleep(0.25 * (2**attempt))
                continue
            break
        assert response is not None
        if response.status_code == 401:
            raise AuthenticationError("Google Sheets rejected the service-account credentials")
        if response.status_code == 403:
            raise AuthenticationError(
                "Google Sheets denied access; enable the Sheets API and share the spreadsheet "
                "with the service-account email as Editor"
            )
        if response.status_code == 429:
            raise RateLimitError("Google Sheets rate limit exceeded")
        raise ExternalServiceError("Google Sheets write or read failed")

    def values_path(self, range_name: str, suffix: str = "") -> str:
        encoded = quote(range_name, safe="")
        return f"/v4/spreadsheets/{self.spreadsheet_id}/values/{encoded}{suffix}"

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()
