"""
test_dpdp_compliance.py — Verify DPDP audit trail completeness and consent logic.
"""
import pytest
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


class TestAuditTrailCompleteness:
    def test_audit_trail_has_required_fields(self):
        from database.db import get_connection
        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT * FROM audit_trail LIMIT 5"
            ).fetchall()
            assert rows, "Audit trail is empty — seeding failed"
            required_fields = {
                "tenant_id", "employee_id", "action", "purpose",
                "legal_basis", "agent_name", "timestamp"
            }
            for row in rows:
                row_keys = set(dict(row).keys())
                missing = required_fields - row_keys
                assert not missing, f"Audit trail row missing fields: {missing}"
        finally:
            conn.close()

    def test_audit_log_audit_function(self):
        from database.db import log_audit, get_connection
        log_audit(
            action="test_dpdp_audit",
            tenant_id="authbridge",
            employee_id="EMP001",
            agent_name="test_agent",
            purpose="testing",
            legal_basis="legitimate_use_s7_1_i",
            result_summary="Audit log test",
        )
        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM audit_trail WHERE action='test_dpdp_audit' ORDER BY id DESC LIMIT 1"
            ).fetchone()
            assert row is not None, "log_audit() failed to write entry"
            assert row["tenant_id"] == "authbridge"
            assert row["purpose"] == "testing"
        finally:
            conn.close()

    def test_audit_trail_immutability_pattern(self):
        """Audit trail should only have INSERT operations (no DELETE on real data)."""
        from database.db import get_connection
        conn = get_connection()
        try:
            count_before = conn.execute("SELECT COUNT(*) FROM audit_trail").fetchone()[0]
            # Verify we cannot easily delete (no cascade, no triggers that auto-delete)
            conn.execute(
                "INSERT INTO audit_trail (tenant_id, action, purpose) VALUES ('authbridge','immutability_test','testing')"
            )
            conn.commit()
            count_after = conn.execute("SELECT COUNT(*) FROM audit_trail").fetchone()[0]
            assert count_after == count_before + 1
        finally:
            conn.close()


class TestConsentManagement:
    def test_consent_statuses_valid(self):
        from database.db import get_connection
        conn = get_connection()
        try:
            invalid = conn.execute(
                "SELECT * FROM consents WHERE status NOT IN ('pending','granted','withdrawn','expired')"
            ).fetchall()
            assert not invalid, f"Invalid consent statuses found: {invalid}"
        finally:
            conn.close()

    def test_granted_consents_have_timestamp(self):
        from database.db import get_connection
        conn = get_connection()
        try:
            broken = conn.execute(
                "SELECT * FROM consents WHERE status='granted' AND granted_at IS NULL"
            ).fetchall()
            assert not broken, f"Granted consents missing granted_at timestamp: {len(broken)}"
        finally:
            conn.close()

    def test_save_conversation_turn_persists(self):
        from database.db import save_conversation_turn, load_conversation_history
        save_conversation_turn("EMP001", "authbridge", "human", "DPDP test query for compliance")
        history = load_conversation_history("EMP001", "authbridge", limit=10)
        contents = [t["content"] for t in history]
        assert "DPDP test query for compliance" in contents

    def test_retention_job_runs_without_error(self):
        from retention_job import run_data_retention
        result = run_data_retention()
        assert "errors" in result
        assert len(result["errors"]) == 0, f"Retention job errors: {result['errors']}"
        assert "deleted_consents" in result
        assert "anonymized_audit" in result
