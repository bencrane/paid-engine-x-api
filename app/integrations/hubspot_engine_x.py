"""hubspot-engine-x API client for PaidEdge backend (BJC-188).

Service-to-service client consuming hubspot-engine-x's CRM proxy API.
PaidEdge never calls HubSpot directly — all CRM reads/writes flow through
hubspot-engine-x, which manages OAuth tokens via Nango.

Pattern: mirrors DataEngineXClient (async httpx, Bearer auth, exponential
backoff retry on timeout/429/5xx).
"""

import asyncio
import logging
from typing import Any

import httpx

from app.config import settings
from app.integrations.crm_base import (
    CRMEngineAuthError,
    CRMEngineError,
    CRMEngineRateLimitError,
)

logger = logging.getLogger(__name__)


class HubSpotEngineClient:
    """Authenticated HTTP client for hubspot-engine-x API.

    All endpoints use POST with JSON bodies (hubspot-engine-x convention).
    Auth via Bearer token provisioned in hubspot-engine-x and stored in Doppler.
    """

    MAX_RETRIES = 5
    BACKOFF_BASE = 1  # seconds
    BACKOFF_CAP = 16  # seconds
    TIMEOUT = 30.0  # seconds

    def __init__(
        self,
        base_url: str | None = None,
        api_token: str | None = None,
    ):
        self.base_url = (base_url or settings.HUBSPOT_ENGINE_X_BASE_URL).rstrip("/")
        self.api_token = api_token or settings.HUBSPOT_ENGINE_X_API_TOKEN
        self._client = httpx.AsyncClient(timeout=self.TIMEOUT)

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

    async def _request(
        self,
        method: str,
        path: str,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Core request method with retry + exponential backoff."""
        url = f"{self.base_url}{path}"
        headers = self._headers()

        for attempt in range(self.MAX_RETRIES + 1):
            try:
                resp = await self._client.request(
                    method, url, headers=headers, json=json,
                )
            except httpx.TimeoutException:
                if attempt >= self.MAX_RETRIES:
                    raise CRMEngineError(0, "Request timed out after retries")
                delay = min(self.BACKOFF_BASE * (2 ** attempt), self.BACKOFF_CAP)
                logger.warning(
                    "hubspot-engine-x timeout on %s %s — retrying in %ds (attempt %d/%d)",
                    method, path, delay, attempt + 1, self.MAX_RETRIES,
                )
                await asyncio.sleep(delay)
                continue

            if resp.status_code == 429:
                if attempt >= self.MAX_RETRIES:
                    raise CRMEngineRateLimitError()
                delay = min(self.BACKOFF_BASE * (2 ** attempt), self.BACKOFF_CAP)
                logger.warning(
                    "hubspot-engine-x rate limited on %s %s — retrying in %ds (attempt %d/%d)",
                    method, path, delay, attempt + 1, self.MAX_RETRIES,
                )
                await asyncio.sleep(delay)
                continue

            if resp.status_code in (500, 502, 503):
                if attempt >= self.MAX_RETRIES:
                    self._raise_for_status(resp)
                delay = min(self.BACKOFF_BASE * (2 ** attempt), self.BACKOFF_CAP)
                logger.warning(
                    "hubspot-engine-x %d on %s %s — retrying in %ds (attempt %d/%d)",
                    resp.status_code, method, path, delay, attempt + 1, self.MAX_RETRIES,
                )
                await asyncio.sleep(delay)
                continue

            if resp.status_code >= 400:
                self._raise_for_status(resp)

            return resp.json()

        raise CRMEngineError(500, "Unexpected retry exhaustion")

    def _raise_for_status(self, resp: httpx.Response) -> None:
        """Parse error response and raise appropriate exception."""
        try:
            body = resp.json()
            message = body.get("error", resp.text)
        except Exception:
            message = resp.text

        if resp.status_code in (401, 403):
            raise CRMEngineAuthError(message)
        if resp.status_code == 429:
            raise CRMEngineRateLimitError()
        raise CRMEngineError(resp.status_code, message)

    # --- Connection ---

    async def get_connection(self, client_id: str) -> dict[str, Any]:
        """Check a client's HubSpot connection status."""
        return await self._request("POST", "/api/connections/get", json={
            "client_id": client_id,
        })

    # --- CRM reads ---

    async def search(
        self,
        client_id: str,
        object_type: str,
        filters: list[dict] | None = None,
        properties: list[str] | None = None,
        after: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        """Search CRM objects with filters. Returns {results, paging}."""
        payload: dict[str, Any] = {
            "client_id": client_id,
            "object_type": object_type,
            "limit": limit,
        }
        if filters:
            payload["filters"] = filters
        if properties:
            payload["properties"] = properties
        if after:
            payload["after"] = after
        return await self._request("POST", "/api/crm/search", json=payload)

    async def search_all(
        self,
        client_id: str,
        object_type: str,
        filters: list[dict] | None = None,
        properties: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Auto-paginate through all search results."""
        all_results: list[dict[str, Any]] = []
        after: str | None = None

        while True:
            data = await self.search(
                client_id=client_id,
                object_type=object_type,
                filters=filters,
                properties=properties,
                after=after,
            )
            results = data.get("results", [])
            all_results.extend(results)

            paging = data.get("paging", {})
            next_page = paging.get("next", {})
            after = next_page.get("after")
            if not after or not results:
                break

        return all_results

    async def list_records(
        self,
        client_id: str,
        object_type: str,
        properties: list[str] | None = None,
        after: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        """List CRM objects with optional property selection."""
        payload: dict[str, Any] = {
            "client_id": client_id,
            "object_type": object_type,
            "limit": limit,
        }
        if properties:
            payload["properties"] = properties
        if after:
            payload["after"] = after
        return await self._request("POST", "/api/crm/list", json=payload)

    async def get_record(
        self,
        client_id: str,
        object_type: str,
        record_id: str,
        properties: list[str] | None = None,
    ) -> dict[str, Any]:
        """Get a single CRM record by ID."""
        payload: dict[str, Any] = {
            "client_id": client_id,
            "object_type": object_type,
            "record_id": record_id,
        }
        if properties:
            payload["properties"] = properties
        return await self._request("POST", "/api/crm/get", json=payload)

    async def batch_read(
        self,
        client_id: str,
        object_type: str,
        record_ids: list[str],
        properties: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Batch-read multiple CRM records by ID."""
        data = await self._request("POST", "/api/crm/batch-read", json={
            "client_id": client_id,
            "object_type": object_type,
            "record_ids": record_ids,
            "properties": properties or [],
        })
        return data.get("results", [])

    # --- Associations ---

    async def get_associations(
        self,
        client_id: str,
        from_type: str,
        to_type: str,
        record_id: str,
    ) -> list[dict[str, Any]]:
        """Get associations for a single record."""
        data = await self._request("POST", "/api/crm/associations", json={
            "client_id": client_id,
            "from_type": from_type,
            "to_type": to_type,
            "record_id": record_id,
        })
        return data.get("results", [])

    async def batch_associations(
        self,
        client_id: str,
        from_type: str,
        to_type: str,
        record_ids: list[str],
    ) -> dict[str, list[dict[str, Any]]]:
        """Batch-read associations for multiple records.

        Returns {record_id: [associated_records]}.
        """
        data = await self._request("POST", "/api/crm/batch-associations", json={
            "client_id": client_id,
            "from_type": from_type,
            "to_type": to_type,
            "record_ids": record_ids,
        })
        return data.get("results", {})

    # --- Pipelines ---

    async def get_pipelines(
        self,
        client_id: str,
        object_type: str = "deals",
    ) -> list[dict[str, Any]]:
        """Get pipeline definitions with stages."""
        data = await self._request("POST", "/api/crm/pipelines", json={
            "client_id": client_id,
            "object_type": object_type,
        })
        return data.get("results", [])

    # --- Push / Update ---

    async def push_records(
        self,
        client_id: str,
        object_type: str,
        records: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Create records in HubSpot CRM."""
        data = await self._request("POST", "/api/crm/push", json={
            "client_id": client_id,
            "object_type": object_type,
            "records": records,
        })
        return data.get("results", [])

    async def update_records(
        self,
        client_id: str,
        object_type: str,
        records: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Update existing records in HubSpot CRM."""
        data = await self._request("POST", "/api/crm/update", json={
            "client_id": client_id,
            "object_type": object_type,
            "records": records,
        })
        return data.get("results", [])

    async def link_records(
        self,
        client_id: str,
        from_type: str,
        to_type: str,
        from_id: str,
        to_id: str,
    ) -> dict[str, Any]:
        """Create an association between two records."""
        return await self._request("POST", "/api/crm/link", json={
            "client_id": client_id,
            "from_type": from_type,
            "to_type": to_type,
            "from_id": from_id,
            "to_id": to_id,
        })

    # --- Field mappings ---

    async def set_mapping(
        self,
        client_id: str,
        object_type: str,
        mapping: dict[str, str],
    ) -> dict[str, Any]:
        """Set field mapping for a CRM object type."""
        return await self._request("POST", "/api/mappings/set", json={
            "client_id": client_id,
            "object_type": object_type,
            "mapping": mapping,
        })

    async def get_mappings(
        self,
        client_id: str,
        object_type: str,
    ) -> dict[str, str]:
        """Get field mapping for a CRM object type."""
        data = await self._request("POST", "/api/mappings/get", json={
            "client_id": client_id,
            "object_type": object_type,
        })
        return data.get("mapping", {})

    async def list_all_mappings(
        self,
        client_id: str,
    ) -> dict[str, dict[str, str]]:
        """List all field mappings for a client."""
        data = await self._request("POST", "/api/mappings/list", json={
            "client_id": client_id,
        })
        return data.get("mappings", {})
