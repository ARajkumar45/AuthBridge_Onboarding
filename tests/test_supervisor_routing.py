"""
test_supervisor_routing.py — Verify rule-based router accuracy.
"""
import pytest
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


class TestRuleBasedRouter:
    """_rule_based_route() must return correct agent for common queries."""

    @pytest.fixture(autouse=True)
    def import_router(self):
        from agents.supervisor import _rule_based_route
        self.route = _rule_based_route

    @pytest.mark.parametrize("query,expected", [
        ("What is the leave policy?",           "policy_agent"),
        ("How many sick leaves do I get?",      "policy_agent"),
        ("What is the code of conduct?",        "policy_agent"),
        ("Tell me about IT provisioning",       "policy_agent"),
        ("My laptop setup instructions",        "policy_agent"),
        ("Upload my Aadhaar card",              "document_agent"),
        ("I need to submit my PAN card",        "document_agent"),
        ("Passport OCR failed",                 "document_agent"),
        ("Degree certificate upload",           "document_agent"),
        ("DPDP consent withdrawal",             "compliance_agent"),
        ("Data privacy rights",                 "compliance_agent"),
        ("Can I see my audit trail?",           "compliance_agent"),
        ("BGV status update",                   "bgv_agent"),
        ("Background verification check",       "bgv_agent"),
        ("Criminal record check status",        "bgv_agent"),
        ("iBRIDGE API verification",            "bgv_agent"),
    ])
    def test_routing(self, query, expected):
        result = self.route(query)
        assert result == expected, \
            f"Query '{query}' routed to '{result}', expected '{expected}'"

    def test_ambiguous_returns_none(self):
        result = self.route("Hello how are you?")
        assert result is None, \
            f"Ambiguous query should return None for LLM fallback, got '{result}'"

    def test_case_insensitive(self):
        from agents.supervisor import _rule_based_route
        assert _rule_based_route("LEAVE POLICY") == "policy_agent"
        assert _rule_based_route("bgv STATUS") == "bgv_agent"
