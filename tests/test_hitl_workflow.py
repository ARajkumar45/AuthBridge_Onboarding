"""
test_hitl_workflow.py — Test full HITL state machine transitions.
"""
import pytest
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


class TestHITLWorkflow:
    def setup_method(self):
        from database.db import get_connection
        self.conn = get_connection()

    def teardown_method(self):
        self.conn.close()

    def _create_hitl_item(self, emp_id="EMP001", tenant_id="authbridge", risk="high"):
        self.conn.execute("""
            INSERT INTO hitl_queue (employee_id, tenant_id, agent_name,
                                     action_type, description, risk_level, status)
            VALUES (?, ?, 'bgv_agent', 'test_action', 'Test HITL item', ?, 'pending')
        """, (emp_id, tenant_id, risk))
        self.conn.commit()
        return self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    def test_hitl_item_created_as_pending(self):
        hitl_id = self._create_hitl_item()
        row = self.conn.execute(
            "SELECT status FROM hitl_queue WHERE id = ?", (hitl_id,)
        ).fetchone()
        assert row["status"] == "pending"

    def test_hitl_approval_transition(self):
        hitl_id = self._create_hitl_item()
        self.conn.execute("""
            UPDATE hitl_queue SET status='approved', reviewer='HR Admin',
                                   review_notes='Approved for testing',
                                   reviewed_at=datetime('now')
            WHERE id=?
        """, (hitl_id,))
        self.conn.commit()
        row = self.conn.execute(
            "SELECT status, reviewer FROM hitl_queue WHERE id=?", (hitl_id,)
        ).fetchone()
        assert row["status"] == "approved"
        assert row["reviewer"] == "HR Admin"

    def test_hitl_rejection_transition(self):
        hitl_id = self._create_hitl_item()
        self.conn.execute("""
            UPDATE hitl_queue SET status='rejected', reviewer='HR Admin',
                                   review_notes='Rejected: missing consent'
            WHERE id=?
        """, (hitl_id,))
        self.conn.commit()
        row = self.conn.execute(
            "SELECT status FROM hitl_queue WHERE id=?", (hitl_id,)
        ).fetchone()
        assert row["status"] == "rejected"

    def test_invalid_status_rejected_by_db(self):
        with pytest.raises(Exception):
            self.conn.execute("""
                INSERT INTO hitl_queue (employee_id, tenant_id, agent_name,
                                         action_type, description, risk_level, status)
                VALUES ('EMP001','authbridge','test','test','test','high','INVALID_STATUS')
            """)
            self.conn.commit()

    def test_high_risk_items_queryable(self):
        self._create_hitl_item(risk="critical")
        rows = self.conn.execute(
            "SELECT * FROM hitl_queue WHERE risk_level='critical'"
        ).fetchall()
        assert len(rows) >= 1
