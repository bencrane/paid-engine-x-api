"""Tests for Supabase CRM writer."""

from datetime import date, datetime
from unittest.mock import MagicMock

from app.integrations.crm_models import CRMContact, CRMOpportunity
from app.services.crm_supabase import (
    upsert_crm_contacts,
    upsert_crm_opportunities,
)


def _sample_contact(**overrides) -> CRMContact:
    defaults = {
        "crm_contact_id": "hs-101",
        "email": "jane@acme.com",
        "first_name": "Jane",
        "last_name": "Doe",
        "company_name": "Acme Corp",
        "account_id": "acc-1",
        "lead_source": "Web",
        "lifecycle_stage": "lead",
        "lead_status": "new",
        "job_title": "VP Engineering",
        "phone": "+15551234567",
        "company_size": 150,
        "industry": "Software",
        "linkedin_url": "https://linkedin.com/in/janedoe",
        "owner_id": "owner-1",
        "utm_source": "google",
        "utm_medium": "cpc",
        "utm_campaign": "spring-2026",
        "created_at": datetime(2026, 1, 15, 12, 0),
        "updated_at": datetime(2026, 3, 20, 8, 30),
    }
    defaults.update(overrides)
    return CRMContact(**defaults)


def _sample_opportunity(**overrides) -> CRMOpportunity:
    defaults = {
        "crm_opportunity_id": "hs-d-1",
        "name": "Acme Deal",
        "amount": 50000.0,
        "close_date": date(2026, 6, 30),
        "stage": "proposal",
        "pipeline": "default",
        "is_closed": False,
        "is_won": False,
        "account_id": "acc-1",
        "lead_source": "Outbound",
        "contact_ids": ["hs-101", "hs-102"],
        "owner_id": "owner-1",
        "created_at": datetime(2026, 2, 1),
        "updated_at": datetime(2026, 3, 20),
    }
    defaults.update(overrides)
    return CRMOpportunity(**defaults)


def _mock_supabase():
    mock = MagicMock()
    chain = MagicMock()
    chain.upsert.return_value = chain
    chain.execute.return_value = MagicMock()
    mock.table.return_value = chain
    return mock


# --- upsert_crm_contacts ---


class TestUpsertCrmContacts:
    def test_upserts_with_correct_conflict_key(self):
        mock_sb = _mock_supabase()
        contacts = [_sample_contact()]

        upsert_crm_contacts(contacts, "org-1", "hubspot", supabase=mock_sb)

        mock_sb.table.assert_called_with("crm_contacts")
        chain = mock_sb.table.return_value
        upsert_call = chain.upsert.call_args
        assert upsert_call[1]["on_conflict"] == "organization_id,crm_source,external_id"

    def test_row_mapping(self):
        mock_sb = _mock_supabase()
        contact = _sample_contact()

        upsert_crm_contacts([contact], "org-1", "hubspot", supabase=mock_sb)

        chain = mock_sb.table.return_value
        rows = chain.upsert.call_args[0][0]
        row = rows[0]
        assert row["organization_id"] == "org-1"
        assert row["crm_source"] == "hubspot"
        assert row["external_id"] == "hs-101"
        assert row["email"] == "jane@acme.com"
        assert row["first_name"] == "Jane"
        assert row["last_name"] == "Doe"
        assert row["company_name"] == "Acme Corp"
        assert row["job_title"] == "VP Engineering"
        assert row["lifecycle_stage"] == "lead"
        assert row["lead_status"] == "new"
        assert row["phone"] == "+15551234567"
        assert row["company_size"] == 150
        assert row["industry"] == "Software"
        assert row["linkedin_url"] == "https://linkedin.com/in/janedoe"
        assert row["owner_id"] == "owner-1"
        assert row["utm_source"] == "google"
        assert row["utm_medium"] == "cpc"
        assert row["utm_campaign"] == "spring-2026"
        assert row["crm_created_at"] is not None
        assert row["crm_updated_at"] is not None
        assert row["synced_at"] is not None

    def test_returns_count(self):
        mock_sb = _mock_supabase()
        contacts = [_sample_contact(crm_contact_id=f"c-{i}") for i in range(5)]

        result = upsert_crm_contacts(contacts, "org-1", "hubspot", supabase=mock_sb)

        assert result == 5

    def test_empty_list_skips(self):
        mock_sb = _mock_supabase()
        result = upsert_crm_contacts([], "org-1", "hubspot", supabase=mock_sb)
        assert result == 0
        mock_sb.table.assert_not_called()

    def test_none_datetimes_map_to_null(self):
        mock_sb = _mock_supabase()
        contact = _sample_contact(created_at=None, updated_at=None)

        upsert_crm_contacts([contact], "org-1", "hubspot", supabase=mock_sb)

        chain = mock_sb.table.return_value
        rows = chain.upsert.call_args[0][0]
        assert rows[0]["crm_created_at"] is None
        assert rows[0]["crm_updated_at"] is None


# --- upsert_crm_opportunities ---


class TestUpsertCrmOpportunities:
    def test_upserts_with_correct_conflict_key(self):
        mock_sb = _mock_supabase()
        opps = [_sample_opportunity()]

        upsert_crm_opportunities(opps, "org-1", "hubspot", supabase=mock_sb)

        mock_sb.table.assert_called_with("crm_opportunities")
        chain = mock_sb.table.return_value
        upsert_call = chain.upsert.call_args
        assert upsert_call[1]["on_conflict"] == "organization_id,crm_source,external_id"

    def test_row_mapping(self):
        mock_sb = _mock_supabase()
        opp = _sample_opportunity()

        upsert_crm_opportunities([opp], "org-1", "hubspot", supabase=mock_sb)

        chain = mock_sb.table.return_value
        rows = chain.upsert.call_args[0][0]
        row = rows[0]
        assert row["organization_id"] == "org-1"
        assert row["crm_source"] == "hubspot"
        assert row["external_id"] == "hs-d-1"
        assert row["name"] == "Acme Deal"
        assert row["amount"] == 50000.0
        assert row["close_date"] == "2026-06-30"
        assert row["stage"] == "proposal"
        assert row["pipeline"] == "default"
        assert row["is_closed"] is False
        assert row["is_won"] is False
        assert row["contact_ids"] == ["hs-101", "hs-102"]
        assert row["owner_id"] == "owner-1"

    def test_returns_count(self):
        mock_sb = _mock_supabase()
        opps = [_sample_opportunity(crm_opportunity_id=f"d-{i}") for i in range(3)]
        result = upsert_crm_opportunities(opps, "org-1", "hubspot", supabase=mock_sb)
        assert result == 3

    def test_empty_list_skips(self):
        mock_sb = _mock_supabase()
        result = upsert_crm_opportunities([], "org-1", "hubspot", supabase=mock_sb)
        assert result == 0
        mock_sb.table.assert_not_called()

    def test_null_amount_and_close_date(self):
        mock_sb = _mock_supabase()
        opp = _sample_opportunity(amount=None, close_date=None)

        upsert_crm_opportunities([opp], "org-1", "hubspot", supabase=mock_sb)

        chain = mock_sb.table.return_value
        rows = chain.upsert.call_args[0][0]
        assert rows[0]["amount"] is None
        assert rows[0]["close_date"] is None
