"""Tests for CRM ClickHouse writer (BJC-190)."""

from datetime import date, datetime
from unittest.mock import MagicMock

from app.integrations.crm_models import CRMContact, CRMOpportunity
from app.services.crm_clickhouse import (
    CONTACT_COLUMNS,
    OPPORTUNITY_COLUMNS,
    get_last_sync_date,
    insert_crm_contacts,
    insert_crm_opportunities,
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
        "is_closed": False,
        "is_won": False,
        "account_id": "acc-1",
        "lead_source": "Outbound",
        "contact_ids": ["hs-101", "hs-102"],
        "created_at": datetime(2026, 2, 1),
        "updated_at": datetime(2026, 3, 20),
    }
    defaults.update(overrides)
    return CRMOpportunity(**defaults)


# --- insert_crm_contacts ---


class TestInsertCrmContacts:
    def test_inserts_correct_columns(self):
        """Should call clickhouse.insert with correct column_names."""
        mock_ch = MagicMock()
        contacts = [_sample_contact()]

        insert_crm_contacts("org-1", "hubspot", contacts, clickhouse=mock_ch)

        mock_ch.insert.assert_called_once()
        args = mock_ch.insert.call_args
        assert args[0][0] == "crm_contacts"
        assert args[1]["column_names"] == CONTACT_COLUMNS

    def test_row_data_mapping(self):
        """Should map CRMContact fields to correct column positions."""
        mock_ch = MagicMock()
        contact = _sample_contact()

        insert_crm_contacts("org-1", "hubspot", [contact], clickhouse=mock_ch)

        data = mock_ch.insert.call_args[0][1]
        row = data[0]
        assert row[0] == "org-1"       # tenant_id
        assert row[1] == "hubspot"     # crm_source
        assert row[2] == "hs-101"      # crm_contact_id
        assert row[3] == "jane@acme.com"  # email
        assert row[4] == "Jane"        # first_name
        assert row[5] == "Doe"         # last_name

    def test_returns_count(self):
        """Should return number of rows inserted."""
        mock_ch = MagicMock()
        contacts = [_sample_contact(crm_contact_id=f"c-{i}") for i in range(5)]

        result = insert_crm_contacts("org-1", "hubspot", contacts, clickhouse=mock_ch)

        assert result == 5

    def test_empty_list_skips_insert(self):
        """Should not call insert when contacts list is empty."""
        mock_ch = MagicMock()
        result = insert_crm_contacts("org-1", "hubspot", [], clickhouse=mock_ch)
        assert result == 0
        mock_ch.insert.assert_not_called()

    def test_none_datetime_uses_epoch(self):
        """Should use epoch sentinel for None datetime fields."""
        mock_ch = MagicMock()
        contact = _sample_contact(created_at=None, updated_at=None)

        insert_crm_contacts("org-1", "hubspot", [contact], clickhouse=mock_ch)

        data = mock_ch.insert.call_args[0][1]
        row = data[0]
        # created_at and updated_at are last two columns
        assert row[-2] == datetime(1970, 1, 1)  # created_at
        assert row[-1] == datetime(1970, 1, 1)  # updated_at


# --- insert_crm_opportunities ---


class TestInsertCrmOpportunities:
    def test_inserts_correct_columns(self):
        """Should call clickhouse.insert with correct column_names."""
        mock_ch = MagicMock()
        opps = [_sample_opportunity()]

        insert_crm_opportunities("org-1", "hubspot", opps, clickhouse=mock_ch)

        mock_ch.insert.assert_called_once()
        args = mock_ch.insert.call_args
        assert args[0][0] == "crm_opportunities"
        assert args[1]["column_names"] == OPPORTUNITY_COLUMNS

    def test_row_data_mapping(self):
        """Should map CRMOpportunity fields to correct column positions."""
        mock_ch = MagicMock()
        opp = _sample_opportunity()

        insert_crm_opportunities("org-1", "hubspot", [opp], clickhouse=mock_ch)

        data = mock_ch.insert.call_args[0][1]
        row = data[0]
        assert row[0] == "org-1"
        assert row[1] == "hubspot"
        assert row[2] == "hs-d-1"        # crm_opportunity_id
        assert row[3] == "Acme Deal"     # name
        assert row[4] == 50000.0         # amount
        assert row[5] == date(2026, 6, 30)  # close_date
        assert row[6] == "proposal"      # stage
        assert row[7] == 0              # is_closed (int)
        assert row[8] == 0              # is_won (int)
        assert row[11] == ["hs-101", "hs-102"]  # contact_ids

    def test_closed_won_as_int(self):
        """Should convert booleans to UInt8 (0/1)."""
        mock_ch = MagicMock()
        opp = _sample_opportunity(is_closed=True, is_won=True)

        insert_crm_opportunities("org-1", "hubspot", [opp], clickhouse=mock_ch)

        data = mock_ch.insert.call_args[0][1]
        row = data[0]
        assert row[7] == 1  # is_closed
        assert row[8] == 1  # is_won

    def test_returns_count(self):
        mock_ch = MagicMock()
        opps = [_sample_opportunity(crm_opportunity_id=f"d-{i}") for i in range(3)]
        result = insert_crm_opportunities("org-1", "hubspot", opps, clickhouse=mock_ch)
        assert result == 3

    def test_empty_list_skips_insert(self):
        mock_ch = MagicMock()
        result = insert_crm_opportunities("org-1", "hubspot", [], clickhouse=mock_ch)
        assert result == 0
        mock_ch.insert.assert_not_called()


# --- get_last_sync_date ---


class TestGetLastSyncDate:
    def test_returns_datetime_when_exists(self):
        """Should return most recent synced_at."""
        mock_ch = MagicMock()
        mock_result = MagicMock()
        mock_result.result_rows = [[datetime(2026, 3, 25, 10, 0)]]
        mock_ch.query.return_value = mock_result

        result = get_last_sync_date("org-1", "hubspot", clickhouse=mock_ch)

        assert result == datetime(2026, 3, 25, 10, 0)
        mock_ch.query.assert_called_once()

    def test_returns_none_when_no_records(self):
        """Should return None for initial sync (no records)."""
        mock_ch = MagicMock()
        mock_result = MagicMock()
        mock_result.result_rows = [[None]]
        mock_ch.query.return_value = mock_result

        result = get_last_sync_date("org-1", "hubspot", clickhouse=mock_ch)

        assert result is None

    def test_returns_none_for_epoch(self):
        """Should treat epoch as no-sync sentinel."""
        mock_ch = MagicMock()
        mock_result = MagicMock()
        mock_result.result_rows = [[datetime(1970, 1, 1)]]
        mock_ch.query.return_value = mock_result

        result = get_last_sync_date("org-1", "hubspot", clickhouse=mock_ch)

        assert result is None

    def test_passes_tenant_and_source(self):
        """Should filter by tenant_id and crm_source."""
        mock_ch = MagicMock()
        mock_result = MagicMock()
        mock_result.result_rows = [[None]]
        mock_ch.query.return_value = mock_result

        get_last_sync_date("org-42", "salesforce", clickhouse=mock_ch)

        call_args = mock_ch.query.call_args
        params = call_args[1]["parameters"]
        assert params["tid"] == "org-42"
        assert params["src"] == "salesforce"
