"""Tests for HubSpot engine-x client and syncer (BJC-188)."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.integrations.crm_base import (
    CRMEngineAuthError,
    CRMEngineError,
    CRMEngineRateLimitError,
)
from app.integrations.crm_models import CRMContact, CRMOpportunity, PipelineStage
from app.integrations.hubspot_engine_x import HubSpotEngineClient
from app.integrations.hubspot_syncer import HubSpotSyncer


# --- Fixtures ---


@pytest.fixture
def client():
    return HubSpotEngineClient(
        base_url="https://hubspot-engine-x.test",
        api_token="test-hs-token",
    )


@pytest.fixture
def syncer(client):
    return HubSpotSyncer(engine_client=client)


def _mock_response(status_code: int, json_data: dict) -> httpx.Response:
    return httpx.Response(status_code, json=json_data)


# --- HubSpotEngineClient: Auth headers ---


class TestHeaders:
    def test_bearer_token(self, client):
        headers = client._headers()
        assert headers["Authorization"] == "Bearer test-hs-token"
        assert headers["Content-Type"] == "application/json"


# --- HubSpotEngineClient: get_connection ---


class TestGetConnection:
    async def test_returns_connection_data(self, client):
        mock_resp = _mock_response(200, {
            "id": "conn-1",
            "status": "connected",
            "client_id": "cl-1",
        })
        client._client = AsyncMock()
        client._client.request = AsyncMock(return_value=mock_resp)

        result = await client.get_connection("cl-1")

        assert result["status"] == "connected"


# --- HubSpotEngineClient: search ---


class TestSearch:
    async def test_search_with_filters(self, client):
        mock_resp = _mock_response(200, {
            "results": [{"id": "101", "properties": {"email": "a@b.com"}}],
            "paging": {},
        })
        client._client = AsyncMock()
        client._client.request = AsyncMock(return_value=mock_resp)

        result = await client.search(
            client_id="cl-1",
            object_type="contacts",
            filters=[{"propertyName": "email", "operator": "EQ", "value": "a@b.com"}],
        )

        assert len(result["results"]) == 1

    async def test_search_passes_after_param(self, client):
        mock_resp = _mock_response(200, {"results": [], "paging": {}})
        client._client = AsyncMock()
        client._client.request = AsyncMock(return_value=mock_resp)

        await client.search(
            client_id="cl-1", object_type="contacts", after="cursor-123",
        )

        call_args = client._client.request.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        assert payload["after"] == "cursor-123"


# --- HubSpotEngineClient: search_all (auto-pagination) ---


class TestSearchAll:
    async def test_paginates_until_no_after(self, client):
        page1 = _mock_response(200, {
            "results": [{"id": "1"}],
            "paging": {"next": {"after": "cursor-2"}},
        })
        page2 = _mock_response(200, {
            "results": [{"id": "2"}],
            "paging": {},
        })
        client._client = AsyncMock()
        client._client.request = AsyncMock(side_effect=[page1, page2])

        results = await client.search_all(client_id="cl-1", object_type="contacts")

        assert len(results) == 2
        assert client._client.request.call_count == 2

    async def test_empty_results(self, client):
        mock_resp = _mock_response(200, {"results": [], "paging": {}})
        client._client = AsyncMock()
        client._client.request = AsyncMock(return_value=mock_resp)

        results = await client.search_all(client_id="cl-1", object_type="contacts")
        assert results == []


# --- HubSpotEngineClient: batch_associations ---


class TestBatchAssociations:
    async def test_returns_mapping(self, client):
        mock_resp = _mock_response(200, {
            "results": {
                "deal-1": [{"id": "c-1"}, {"id": "c-2"}],
                "deal-2": [{"id": "c-3"}],
            },
        })
        client._client = AsyncMock()
        client._client.request = AsyncMock(return_value=mock_resp)

        result = await client.batch_associations(
            client_id="cl-1",
            from_type="deals",
            to_type="contacts",
            record_ids=["deal-1", "deal-2"],
        )

        assert len(result["deal-1"]) == 2
        assert len(result["deal-2"]) == 1


# --- HubSpotEngineClient: get_pipelines ---


class TestGetPipelines:
    async def test_returns_pipelines(self, client):
        mock_resp = _mock_response(200, {
            "results": [{
                "id": "p-1",
                "label": "Sales",
                "stages": [
                    {"stageId": "s-1", "label": "Discovery", "isClosed": "false", "isWon": "false"},
                    {"stageId": "s-2", "label": "Closed Won", "isClosed": "true", "isWon": "true"},
                ],
            }],
        })
        client._client = AsyncMock()
        client._client.request = AsyncMock(return_value=mock_resp)

        result = await client.get_pipelines(client_id="cl-1")

        assert len(result) == 1
        assert len(result[0]["stages"]) == 2


# --- HubSpotEngineClient: Error handling ---


class TestErrorHandling:
    async def test_401_raises_auth_error(self, client):
        mock_resp = _mock_response(401, {"error": "Invalid token"})
        client._client = AsyncMock()
        client._client.request = AsyncMock(return_value=mock_resp)

        with pytest.raises(CRMEngineAuthError):
            await client.get_connection("cl-1")

    async def test_429_retries_then_raises(self, client):
        client.MAX_RETRIES = 1
        mock_resp = _mock_response(429, {"error": "Rate limited"})
        client._client = AsyncMock()
        client._client.request = AsyncMock(return_value=mock_resp)

        with (
            patch("asyncio.sleep", new_callable=AsyncMock),
            pytest.raises(CRMEngineRateLimitError),
        ):
            await client.get_connection("cl-1")

    async def test_500_retries_then_raises(self, client):
        client.MAX_RETRIES = 1
        mock_resp = _mock_response(500, {"error": "Internal error"})
        client._client = AsyncMock()
        client._client.request = AsyncMock(return_value=mock_resp)

        with (
            patch("asyncio.sleep", new_callable=AsyncMock),
            pytest.raises(CRMEngineError),
        ):
            await client.get_connection("cl-1")

    async def test_timeout_retries_then_raises(self, client):
        client.MAX_RETRIES = 1
        client._client = AsyncMock()
        client._client.request = AsyncMock(side_effect=httpx.TimeoutException("timed out"))

        with (
            patch("asyncio.sleep", new_callable=AsyncMock),
            pytest.raises(CRMEngineError, match="timed out"),
        ):
            await client.get_connection("cl-1")

    async def test_retry_success_after_failure(self, client):
        success_resp = _mock_response(200, {"status": "connected"})
        fail_resp = _mock_response(500, {"error": "temporary"})
        client._client = AsyncMock()
        client._client.request = AsyncMock(side_effect=[fail_resp, success_resp])

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await client.get_connection("cl-1")

        assert result["status"] == "connected"
        assert client._client.request.call_count == 2


# --- HubSpotSyncer: pull_contacts ---


class TestSyncerPullContacts:
    async def test_normalizes_contacts(self, client, syncer):
        page_resp = _mock_response(200, {
            "results": [{
                "id": "hs-101",
                "properties": {
                    "email": "jane@acme.com",
                    "firstname": "Jane",
                    "lastname": "Doe",
                    "company": "Acme",
                    "lifecyclestage": "lead",
                    "createdate": "2026-01-15T12:00:00.000Z",
                    "lastmodifieddate": "2026-03-20T08:30:00.000Z",
                },
            }],
            "paging": {},
        })
        client._client = AsyncMock()
        client._client.request = AsyncMock(return_value=page_resp)

        contacts = await syncer.pull_contacts("cl-1")

        assert len(contacts) == 1
        assert isinstance(contacts[0], CRMContact)
        assert contacts[0].crm_contact_id == "hs-101"
        assert contacts[0].email == "jane@acme.com"
        assert contacts[0].first_name == "Jane"
        assert contacts[0].lifecycle_stage == "lead"

    async def test_incremental_with_since(self, client, syncer):
        mock_resp = _mock_response(200, {"results": [], "paging": {}})
        client._client = AsyncMock()
        client._client.request = AsyncMock(return_value=mock_resp)

        await syncer.pull_contacts("cl-1", since="2026-03-20T00:00:00Z")

        call_args = client._client.request.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        assert payload["filters"][0]["propertyName"] == "lastmodifieddate"
        assert payload["filters"][0]["operator"] == "GTE"


# --- HubSpotSyncer: pull_opportunities ---


class TestSyncerPullOpportunities:
    async def test_normalizes_deals_with_associations(self, client, syncer):
        search_resp = _mock_response(200, {
            "results": [{
                "id": "deal-1",
                "properties": {
                    "dealname": "Big Deal",
                    "amount": "50000",
                    "closedate": "2026-06-30",
                    "dealstage": "proposal",
                    "hs_is_closed": "false",
                    "hs_is_closed_won": "false",
                    "createdate": "2026-02-01T00:00:00.000Z",
                    "hs_lastmodifieddate": "2026-03-20T00:00:00.000Z",
                },
            }],
            "paging": {},
        })
        assoc_resp = _mock_response(200, {
            "results": {
                "deal-1": [{"id": "c-1"}, {"id": "c-2"}],
            },
        })
        client._client = AsyncMock()
        client._client.request = AsyncMock(side_effect=[search_resp, assoc_resp])

        opps = await syncer.pull_opportunities("cl-1")

        assert len(opps) == 1
        assert isinstance(opps[0], CRMOpportunity)
        assert opps[0].crm_opportunity_id == "deal-1"
        assert opps[0].name == "Big Deal"
        assert opps[0].amount == 50000.0
        assert opps[0].contact_ids == ["c-1", "c-2"]
        assert opps[0].is_closed is False

    async def test_empty_deals(self, client, syncer):
        mock_resp = _mock_response(200, {"results": [], "paging": {}})
        client._client = AsyncMock()
        client._client.request = AsyncMock(return_value=mock_resp)

        opps = await syncer.pull_opportunities("cl-1")

        assert opps == []
        # Should not call batch_associations if no deals
        assert client._client.request.call_count == 1


# --- HubSpotSyncer: pull_pipeline_stages ---


class TestSyncerPullPipelineStages:
    async def test_normalizes_stages(self, client, syncer):
        mock_resp = _mock_response(200, {
            "results": [{
                "id": "p-1",
                "stages": [
                    {"stageId": "s-1", "label": "Discovery", "isClosed": "false", "isWon": "false", "probability": "0.2"},
                    {"stageId": "s-2", "label": "Closed Won", "isClosed": "true", "isWon": "true", "probability": "1.0"},
                ],
            }],
        })
        client._client = AsyncMock()
        client._client.request = AsyncMock(return_value=mock_resp)

        stages = await syncer.pull_pipeline_stages("cl-1")

        assert len(stages) == 2
        assert isinstance(stages[0], PipelineStage)
        assert stages[0].stage_id == "s-1"
        assert stages[0].label == "Discovery"
        assert stages[0].is_closed is False
        assert stages[1].is_won is True
        assert stages[1].probability == 1.0


# --- HubSpotSyncer: check_connection ---


class TestSyncerCheckConnection:
    async def test_returns_true_when_connected(self, client, syncer):
        mock_resp = _mock_response(200, {"status": "connected"})
        client._client = AsyncMock()
        client._client.request = AsyncMock(return_value=mock_resp)

        assert await syncer.check_connection("cl-1") is True

    async def test_returns_false_when_expired(self, client, syncer):
        mock_resp = _mock_response(200, {"status": "expired"})
        client._client = AsyncMock()
        client._client.request = AsyncMock(return_value=mock_resp)

        assert await syncer.check_connection("cl-1") is False

    async def test_returns_false_on_error(self, client, syncer):
        client._client = AsyncMock()
        client._client.request = AsyncMock(side_effect=Exception("connection error"))

        assert await syncer.check_connection("cl-1") is False


# --- HubSpotSyncer: push_lead ---


class TestSyncerPushLead:
    async def test_pushes_contact(self, client, syncer):
        mock_resp = _mock_response(200, {
            "results": [{"id": "new-c-1"}],
        })
        client._client = AsyncMock()
        client._client.request = AsyncMock(return_value=mock_resp)

        result = await syncer.push_lead(
            "cl-1",
            {"email": "new@acme.com", "first_name": "New", "last_name": "Lead"},
            attribution={"source": "PaidEdge"},
        )

        assert result == "new-c-1"

    async def test_returns_empty_on_no_results(self, client, syncer):
        mock_resp = _mock_response(200, {"results": []})
        client._client = AsyncMock()
        client._client.request = AsyncMock(return_value=mock_resp)

        result = await syncer.push_lead("cl-1", {"email": "a@b.com"})

        assert result == ""
