"""Tests for CRM canonical models and parsing helpers (BJC-187)."""

from datetime import date, datetime

from app.integrations.crm_models import (
    CRMContact,
    CRMOpportunity,
    CRMSyncResult,
    PipelineStage,
    parse_hs_bool,
    parse_hs_date,
    parse_hs_datetime,
    parse_hs_float,
)


# --- CRMContact ---


class TestCRMContact:
    def test_minimal_contact(self):
        """Should create contact with only required fields."""
        c = CRMContact(crm_contact_id="123", email="jane@acme.com")
        assert c.crm_contact_id == "123"
        assert c.email == "jane@acme.com"
        assert c.first_name is None
        assert c.company_name is None

    def test_full_contact(self):
        """Should serialize all fields."""
        c = CRMContact(
            crm_contact_id="456",
            email="john@beta.io",
            first_name="John",
            last_name="Doe",
            company_name="Beta Inc",
            account_id="acc-1",
            lead_source="Web",
            lifecycle_stage="lead",
            created_at=datetime(2026, 1, 15, 12, 0),
            updated_at=datetime(2026, 3, 20, 8, 30),
        )
        data = c.model_dump()
        assert data["first_name"] == "John"
        assert data["lead_source"] == "Web"
        assert data["created_at"] == datetime(2026, 1, 15, 12, 0)


# --- CRMOpportunity ---


class TestCRMOpportunity:
    def test_minimal_opportunity(self):
        """Should create opportunity with required fields."""
        o = CRMOpportunity(crm_opportunity_id="d-1", name="Acme Deal", stage="proposal")
        assert o.crm_opportunity_id == "d-1"
        assert o.is_closed is False
        assert o.is_won is False
        assert o.contact_ids == []

    def test_full_opportunity(self):
        """Should handle all fields including contact_ids."""
        o = CRMOpportunity(
            crm_opportunity_id="d-2",
            name="Big Deal",
            amount=50000.0,
            close_date=date(2026, 6, 30),
            stage="closed_won",
            is_closed=True,
            is_won=True,
            account_id="acc-1",
            lead_source="Outbound",
            contact_ids=["c-1", "c-2"],
        )
        assert o.amount == 50000.0
        assert o.close_date == date(2026, 6, 30)
        assert len(o.contact_ids) == 2


# --- PipelineStage ---


class TestPipelineStage:
    def test_stage_defaults(self):
        stage = PipelineStage(stage_id="s-1", label="Discovery")
        assert stage.display_order == 0
        assert stage.is_closed is False
        assert stage.probability is None


# --- CRMSyncResult ---


class TestCRMSyncResult:
    def test_empty_result(self):
        r = CRMSyncResult(tenant_id="org-1", crm_source="hubspot")
        assert r.contacts == []
        assert r.opportunities == []
        assert r.pipeline_stages == []

    def test_with_data(self):
        r = CRMSyncResult(
            tenant_id="org-1",
            crm_source="hubspot",
            contacts=[CRMContact(crm_contact_id="c-1", email="a@b.com")],
            opportunities=[CRMOpportunity(crm_opportunity_id="d-1", name="D", stage="s")],
            pipeline_stages=[PipelineStage(stage_id="s-1", label="L")],
        )
        assert len(r.contacts) == 1
        assert len(r.opportunities) == 1
        assert len(r.pipeline_stages) == 1


# --- parse_hs_float ---


class TestParseHsFloat:
    def test_string_number(self):
        assert parse_hs_float("50000.00") == 50000.0

    def test_none(self):
        assert parse_hs_float(None) is None

    def test_empty_string(self):
        assert parse_hs_float("") is None

    def test_invalid_string(self):
        assert parse_hs_float("not_a_number") is None

    def test_actual_float(self):
        assert parse_hs_float(123.45) == 123.45

    def test_int(self):
        assert parse_hs_float(100) == 100.0


# --- parse_hs_date ---


class TestParseHsDate:
    def test_iso_date(self):
        assert parse_hs_date("2026-06-30") == date(2026, 6, 30)

    def test_iso_datetime(self):
        assert parse_hs_date("2026-06-30T00:00:00.000Z") == date(2026, 6, 30)

    def test_epoch_ms(self):
        # 2026-03-15 12:00:00 UTC = 1773835200000 ms
        result = parse_hs_date("1773835200000")
        assert result is not None
        assert result.year == 2026

    def test_none(self):
        assert parse_hs_date(None) is None

    def test_empty(self):
        assert parse_hs_date("") is None

    def test_invalid(self):
        assert parse_hs_date("garbage") is None

    def test_date_passthrough(self):
        d = date(2026, 3, 25)
        assert parse_hs_date(d) == d


# --- parse_hs_datetime ---


class TestParseHsDatetime:
    def test_iso_datetime(self):
        result = parse_hs_datetime("2026-03-25T14:30:00.000Z")
        assert result is not None
        assert result.year == 2026
        assert result.hour == 14

    def test_epoch_ms(self):
        result = parse_hs_datetime("1773835200000")
        assert result is not None
        assert result.year == 2026

    def test_none(self):
        assert parse_hs_datetime(None) is None

    def test_empty(self):
        assert parse_hs_datetime("") is None

    def test_datetime_passthrough(self):
        dt = datetime(2026, 3, 25, 10, 0)
        assert parse_hs_datetime(dt) == dt


# --- parse_hs_bool ---


class TestParseHsBool:
    def test_string_true(self):
        assert parse_hs_bool("true") is True

    def test_string_false(self):
        assert parse_hs_bool("false") is False

    def test_string_True(self):
        assert parse_hs_bool("True") is True

    def test_bool_true(self):
        assert parse_hs_bool(True) is True

    def test_bool_false(self):
        assert parse_hs_bool(False) is False

    def test_none(self):
        assert parse_hs_bool(None) is False
