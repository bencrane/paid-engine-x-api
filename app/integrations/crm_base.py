"""Abstract CRM syncer protocol and shared exception hierarchy (BJC-187).

BaseCRMSyncer defines the interface that all CRM integrations implement.
HubSpotSyncer and (future) SalesforceSyncer both conform to this protocol.
"""

from abc import ABC, abstractmethod

from app.integrations.crm_models import CRMContact, CRMOpportunity, PipelineStage


# --- Exception hierarchy (matches DataEngineXClient pattern) ---


class CRMEngineError(Exception):
    """Base exception for CRM engine API errors."""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"CRM engine API error {status_code}: {message}")


class CRMEngineAuthError(CRMEngineError):
    """401/403 authentication or permission error."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(401, message)


class CRMEngineRateLimitError(CRMEngineError):
    """429 rate limit exceeded."""

    def __init__(self, retry_after: int | None = None):
        self.retry_after = retry_after
        super().__init__(429, "Rate limit exceeded")


# --- Abstract syncer ---


class BaseCRMSyncer(ABC):
    """Abstract interface for CRM data synchronization.

    Each CRM provider (HubSpot, Salesforce) implements this interface.
    The sync task calls these methods generically — it doesn't know
    which CRM it's talking to.
    """

    @abstractmethod
    async def pull_contacts(
        self,
        client_id: str,
        since: str | None = None,
    ) -> list[CRMContact]:
        """Pull contacts modified since the given ISO timestamp.

        If since is None, pull all contacts (initial sync).
        """

    @abstractmethod
    async def pull_opportunities(
        self,
        client_id: str,
        since: str | None = None,
    ) -> list[CRMOpportunity]:
        """Pull opportunities/deals modified since the given ISO timestamp.

        Should include contact_ids via association lookups.
        """

    @abstractmethod
    async def pull_pipeline_stages(
        self,
        client_id: str,
    ) -> list[PipelineStage]:
        """Pull all pipeline stages for the connected CRM account."""

    @abstractmethod
    async def push_lead(
        self,
        client_id: str,
        lead: dict,
        attribution: dict | None = None,
    ) -> str:
        """Push a lead to the CRM. Returns the created record ID."""

    @abstractmethod
    async def check_connection(
        self,
        client_id: str,
    ) -> bool:
        """Check if the CRM connection is still active/valid."""
