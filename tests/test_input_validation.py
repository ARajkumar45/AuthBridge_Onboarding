"""
test_input_validation.py — Verify API input constraints prevent abuse.
"""
import pytest
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from pydantic import ValidationError


class TestQueryRequestValidation:
    def _make_request(self, **kwargs):
        from api.main import QueryRequest
        return QueryRequest(**kwargs)

    def test_valid_request(self):
        req = self._make_request(query="What is the leave policy?", employee_id="EMP001", tenant_id="authbridge")
        assert req.query == "What is the leave policy?"

    def test_empty_query_rejected(self):
        with pytest.raises(ValidationError):
            self._make_request(query="", employee_id="EMP001", tenant_id="authbridge")

    def test_oversized_query_rejected(self):
        with pytest.raises(ValidationError):
            self._make_request(query="x" * 501, employee_id="EMP001", tenant_id="authbridge")

    def test_invalid_employee_id_rejected(self):
        with pytest.raises(ValidationError):
            self._make_request(query="test", employee_id="BADID", tenant_id="authbridge")

    def test_invalid_tenant_rejected(self):
        with pytest.raises(ValidationError):
            self._make_request(query="test", employee_id="EMP001", tenant_id="evil_tenant")

    def test_sql_injection_in_query_truncated(self):
        # Should NOT raise — just truncate at 500 chars
        long_injection = "'; DROP TABLE employees; --" * 20
        with pytest.raises(ValidationError):
            self._make_request(query=long_injection, employee_id="EMP001", tenant_id="authbridge")

    def test_max_length_boundary(self):
        req = self._make_request(query="a" * 500, employee_id="EMP001", tenant_id="authbridge")
        assert len(req.query) == 500


class TestOnboardRequestValidation:
    def test_valid_onboard(self):
        from api.main import OnboardRequest
        req = OnboardRequest(full_name="Test User", email="test@corp.com", tenant_id="authbridge")
        assert req.full_name == "Test User"

    def test_invalid_tenant_onboard(self):
        from api.main import OnboardRequest
        with pytest.raises(ValidationError):
            OnboardRequest(full_name="Test", email="t@t.com", tenant_id="hacker")
