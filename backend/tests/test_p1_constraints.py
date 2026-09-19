"""Tests for P1 schema constraints, indexes, and model exports (T2.2 & T2.3)."""

import pytest

import models
from db.session import Base
from models.blocked_ip import BlockedIP
from models.correlated_event import CorrelatedEvent
from models.playbook_approval import PlaybookApprovalModel
from models.trigger import TriggerInvocationModel


@pytest.mark.unit
class TestModelExportsT22:
    """T2.2: Ensure vulnerability models are properly exported."""

    def test_models_exported_in_init(self):
        assert hasattr(models, "SecurityVulnerability")
        assert hasattr(models, "VulnerabilityNote")
        assert "SecurityVulnerability" in models.__all__
        assert "VulnerabilityNote" in models.__all__

    def test_tables_in_base_metadata(self):
        assert "security_vulnerabilities" in Base.metadata.tables
        assert "vulnerability_notes" in Base.metadata.tables


@pytest.mark.unit
class TestSchemaConstraintsT23:
    """T2.3: Ensure unique constraints and indexes are defined on models."""

    def test_blocked_ip_unique_constraint(self):
        table = BlockedIP.__table__
        unique_constraints = [c for c in table.constraints if hasattr(c, "columns")]
        # Find unique constraint spanning value and type
        found = False
        for c in unique_constraints:
            col_names = {col.name for col in c.columns}
            if col_names == {"value", "type"} and getattr(c, "unique", True):
                found = True
                break
        assert found, "BlockedIP missing UniqueConstraint on ('value', 'type')"

    def test_trigger_idempotency_key_unique(self):
        table = TriggerInvocationModel.__table__
        col = table.c.idempotency_key
        assert col.unique is True, "TriggerInvocationModel.idempotency_key must have unique=True"

    def test_correlated_event_timestamp_indexes(self):
        table = CorrelatedEvent.__table__
        assert table.c.created_at.index is True
        assert table.c.updated_at.index is True

    def test_playbook_approval_run_id_index(self):
        table = PlaybookApprovalModel.__table__
        assert table.c.run_id.index is True
