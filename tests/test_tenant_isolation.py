"""
test_tenant_isolation.py — Verify no data leaks between tenants.
These tests must ALWAYS pass — a failure means a DPDP compliance breach.
"""
import pytest
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


class TestDatabaseTenantIsolation:
    """Verify SQLite queries never return cross-tenant data."""

    def test_employees_isolated(self):
        from database.db import get_connection
        conn = get_connection()
        try:
            auth_emps = conn.execute(
                "SELECT employee_id FROM employees WHERE tenant_id = 'authbridge'"
            ).fetchall()
            gb_emps = conn.execute(
                "SELECT employee_id FROM employees WHERE tenant_id = 'globalbank'"
            ).fetchall()
            auth_ids = {r["employee_id"] for r in auth_emps}
            gb_ids   = {r["employee_id"] for r in gb_emps}
            assert auth_ids.isdisjoint(gb_ids), \
                f"Employee ID overlap between tenants: {auth_ids & gb_ids}"
        finally:
            conn.close()

    def test_audit_trail_isolated(self):
        from database.db import get_connection
        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT DISTINCT tenant_id FROM audit_trail WHERE tenant_id NOT IN ('authbridge','globalbank','system')"
            ).fetchall()
            assert not rows, f"Unknown tenant_ids in audit_trail: {[r[0] for r in rows]}"
        finally:
            conn.close()

    def test_consents_not_shared(self):
        from database.db import get_connection
        conn = get_connection()
        try:
            # EMP001 belongs to authbridge — should NOT appear in globalbank consents
            globalbank_emp001 = conn.execute(
                "SELECT * FROM consents WHERE employee_id='EMP001' AND tenant_id='globalbank'"
            ).fetchall()
            assert not globalbank_emp001, \
                "EMP001 (authbridge) found in globalbank consents — data leak!"
        finally:
            conn.close()


class TestConversationHistoryIsolation:
    def test_conversation_history_isolated(self):
        from database.db import save_conversation_turn, load_conversation_history
        save_conversation_turn("EMP001", "authbridge", "human", "leave policy question")
        save_conversation_turn("EMP004", "globalbank", "human", "globalbank question")

        auth_history = load_conversation_history("EMP001", "authbridge")
        gb_history   = load_conversation_history("EMP004", "globalbank")

        auth_contents = [t["content"] for t in auth_history]
        gb_contents   = [t["content"] for t in gb_history]

        assert "globalbank question" not in auth_contents, \
            "GlobalBank conversation leaked into authbridge history!"
        assert "leave policy question" not in gb_contents, \
            "AuthBridge conversation leaked into globalbank history!"
