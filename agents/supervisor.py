"""
agents/supervisor.py — LangGraph Multi-Agent Supervisor  [production-refactored v2]

Key changes vs. v1
─────────────────────────────────────────────────────────────────────────────
1. Full async execution — all node functions are async def; graph uses ainvoke().
   Sync callers (Streamlit, CLI) are served by the run_onboarding_query() wrapper
   which calls asyncio.run(run_onboarding_query_async(...)).

2. _call_llm() helper — centralises LLM invocation with:
     • asyncio.wait_for() timeout (default 30 s, env: LLM_TIMEOUT_SEC)
     • tenacity retry (3 attempts, exponential 2-10 s back-off)
     • optional Langfuse callback tracing

3. DB calls in async nodes wrapped with asyncio.to_thread() so they never
   block the event loop.

4. policy_agent_node uses HyDE query expansion + query_policies_with_scores
   for confidence-scored RAG retrieval.

5. Multi-turn conversation memory — run_onboarding_query_async() loads the
   last 6 turns from conversation_history, prepends them to the initial
   message list, and persists new turns after each invocation.

6. Latency + quality metrics — save_query_metrics() is called after every
   successful invocation.

7. Langfuse integration — opt-in via LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY
   environment variables; silently disabled if not configured or import fails.

Architecture (unchanged):
  Supervisor (llama-3.3-70b) routes to 4 specialist agents:
    1. document_agent   → Document extraction & classification
    2. policy_agent     → RAG over multi-tenant ChromaDB policies
    3. compliance_agent → DPDP consent & compliance checks
    4. bgv_agent        → Mock AuthBridge iBRIDGE API integration
"""

import os
import re
import json
import time
import asyncio
import logging
from datetime import datetime
from typing import TypedDict, Annotated, Literal
from operator import add
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from database.db import (
    log_audit, get_connection,
    save_conversation_turn, load_conversation_history, save_query_metrics,
)
from rag.loader import query_policies, query_policies_with_scores, hyde_expand_query

# ── Module-level constants ────────────────────────────────────────────────────
LLM_TIMEOUT_SEC = int(os.getenv("LLM_TIMEOUT_SEC", "30"))
logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# STATE DEFINITION
# ══════════════════════════════════════════════════════════════════════════════

class OnboardingState(TypedDict):
    """State shared across all agents in the graph."""
    messages:       Annotated[list, add_messages]
    employee_id:    str
    tenant_id:      str
    current_agent:  str
    task_type:      str
    agent_trace:    Annotated[list, add]   # accumulates within one invocation
    needs_hitl:     bool
    hitl_reason:    str
    final_response: str


# ══════════════════════════════════════════════════════════════════════════════
# MODULE-LEVEL SINGLETONS
# ══════════════════════════════════════════════════════════════════════════════

_llm: "ChatNVIDIA | None" = None
_graph = None   # CompiledGraph — built once, reused forever


def get_llm() -> ChatNVIDIA:
    """Return the shared ChatNVIDIA instance — created once at first call."""
    global _llm
    if _llm is None:
        _llm = ChatNVIDIA(
            model=os.getenv("NVIDIA_LLM_MODEL", "meta/llama-3.3-70b-instruct"),
            api_key=os.getenv("NVIDIA_API_KEY", ""),
            temperature=0.1,
            max_tokens=1024,
        )
        logger.info(
            "llm_initialized",
            extra={"model": os.getenv("NVIDIA_LLM_MODEL", "meta/llama-3.3-70b-instruct")},
        )
    return _llm


def _get_langfuse_handler():
    """Return Langfuse callback handler if configured, else None."""
    try:
        pk = os.getenv("LANGFUSE_PUBLIC_KEY")
        sk = os.getenv("LANGFUSE_SECRET_KEY")
        if pk and sk:
            from langfuse.callback import CallbackHandler
            return CallbackHandler(public_key=pk, secret_key=sk)
    except Exception:
        pass
    return None


async def _call_llm(messages: list, timeout_sec: int = LLM_TIMEOUT_SEC):
    """
    Async LLM call with timeout + tenacity retry (3 attempts, exponential backoff).
    Retries on any exception (covers 429, 503, network errors).
    Optional Langfuse tracing is attached when credentials are configured.
    """
    llm = get_llm()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def _invoke():
        try:
            handler = _get_langfuse_handler()
            config = {"callbacks": [handler]} if handler else {}
            return await asyncio.wait_for(
                llm.ainvoke(messages, config=config), timeout=timeout_sec
            )
        except asyncio.TimeoutError:
            raise TimeoutError(f"LLM timed out after {timeout_sec}s")

    return await _invoke()


def get_onboarding_graph():
    """Return the compiled LangGraph — compiled once, reused forever."""
    global _graph
    if _graph is None:
        _graph = build_onboarding_graph()
        logger.info("onboarding_graph_compiled")
    return _graph


# ══════════════════════════════════════════════════════════════════════════════
# RULE-BASED PRE-ROUTER
# Handles ~70% of queries without an LLM call.
# ══════════════════════════════════════════════════════════════════════════════

_ROUTING_RULES: list = [
    (
        r"leave|holiday|vacation|annual.leave|sick.leave|casual.leave|pto|time.off"
        r"|benefit|code.of.conduct|it.provision|laptop|equipment|handbook"
        r"|policy|onboard|joining|induction|probation|notice.period|salary",
        "policy_agent",
    ),
    (
        r"document|upload|extract|id.card|pan.card|aadhaar|passport"
        r"|certificate|degree|diploma|ocr|scan|photo|marksheet|experience.letter",
        "document_agent",
    ),
    (
        r"dpdp|consent|privacy|data.right|erasure|portability"
        r"|withdraw.consent|audit.trail|data.protection|section.6|section.7|section.8",
        "compliance_agent",
    ),
    (
        r"bgv|background.verif|criminal|ibridge|address.verif"
        r"|education.verif|employment.verif|verification.status|vault|discrepancy",
        "bgv_agent",
    ),
]


def _rule_based_route(query: str) -> "str | None":
    """
    Fast keyword routing — no LLM call needed.
    Returns an agent name when confident, None when ambiguous.
    """
    q = query.lower()
    for pattern, agent in _ROUTING_RULES:
        if re.search(pattern, q):
            return agent
    return None   # fall through to LLM routing


# ══════════════════════════════════════════════════════════════════════════════
# SUPERVISOR NODE
# ══════════════════════════════════════════════════════════════════════════════

async def supervisor_node(state: OnboardingState) -> dict:
    """
    Route query to the correct specialist agent.

    Fast path: keyword rules handle ~70% of queries with zero LLM latency.
    Slow path: LLM routing for ambiguous queries (uses _call_llm with retry + timeout).
    """
    messages = state.get("messages", [])
    if not messages:
        return {"final_response": "No query provided.", "agent_trace": []}

    last_message = messages[-1].content if messages else ""
    employee_id  = state.get("employee_id", "")
    tenant_id    = state.get("tenant_id", "authbridge")

    # ── Fast path: rule-based routing ──
    selected = _rule_based_route(last_message)
    routing_method = "rule_based"

    # ── Slow path: LLM routing for ambiguous queries ──
    if selected is None:
        routing_method = "llm"
        routing_prompt = f"""You are the Supervisor Agent for AuthBridge's AI-Native Employee Onboarding System.
Route the user's query to the correct specialist agent.

Available agents:
1. document_agent   — Document uploads, extraction, OCR, document status
2. policy_agent     — HR policies (leave, benefits, code of conduct, IT provisioning)
3. compliance_agent — DPDP compliance, consent management, data rights, audit trail
4. bgv_agent        — Background verification, iBRIDGE API, criminal/address/education checks

Employee ID: {employee_id} | Tenant: {tenant_id}
User query: {last_message}

Respond with ONLY one of: document_agent, policy_agent, compliance_agent, bgv_agent"""

        try:
            response = await _call_llm([HumanMessage(content=routing_prompt)])
            route = response.content.strip().lower()
            valid_agents = ["document_agent", "policy_agent", "compliance_agent", "bgv_agent"]
            for agent in valid_agents:
                if agent in route:
                    selected = agent
                    break
        except Exception as exc:
            logger.warning("supervisor_llm_routing_failed", extra={"error": str(exc)})

        if selected is None:
            selected = "policy_agent"  # safe default

    logger.info(
        "supervisor_routed",
        extra={
            "agent":         selected,
            "method":        routing_method,
            "employee_id":   employee_id,
            "tenant_id":     tenant_id,
            "query_preview": last_message[:80],
        },
    )

    log_audit(
        action="supervisor_routing",
        tenant_id=tenant_id,
        employee_id=employee_id,
        agent_name="supervisor",
        prompt_sent=last_message[:500],
        purpose="query_routing",
        result_summary=f"Routed to {selected} via {routing_method}",
        model_version="meta/llama-3.3-70b-instruct" if routing_method == "llm" else "rule_engine",
    )

    trace_entry = {
        "timestamp":     datetime.now().isoformat(),
        "agent":         "supervisor",
        "action":        "route",
        "decision":      selected,
        "method":        routing_method,
        "query_preview": last_message[:100],
    }

    return {
        "current_agent": selected,
        "agent_trace":   [trace_entry],
    }


# ══════════════════════════════════════════════════════════════════════════════
# DOCUMENT AGENT
# ══════════════════════════════════════════════════════════════════════════════

async def document_agent_node(state: OnboardingState) -> dict:
    """Document extraction & classification agent."""
    messages     = state.get("messages", [])
    last_message = messages[-1].content if messages else ""
    emp_id       = state.get("employee_id", "unknown")
    tenant_id    = state.get("tenant_id", "authbridge")

    # ── Safe DB read (off event loop) ──
    def _fetch_tasks():
        c = get_connection()
        try:
            return c.execute(
                "SELECT * FROM tasks WHERE employee_id = ? AND tenant_id = ? AND task_type LIKE '%document%'",
                (emp_id, tenant_id),
            ).fetchall()
        finally:
            c.close()

    tasks = await asyncio.to_thread(_fetch_tasks)

    task_info = (
        "\n".join(f"- {t['task_name']}: {t['status']}" for t in tasks)
        if tasks else "No document tasks found."
    )

    prompt = f"""You are the Document Extraction Agent for AuthBridge's AI-Native Onboarding System.
You handle document uploads, extraction, classification, and OCR verification.

Employee: {emp_id} | Tenant: {tenant_id}

Current document tasks:
{task_info}

Capabilities you can describe:
- Aadhaar card extraction with PII masking (first 8 digits masked per UIDAI 2025 circular)
- PAN card verification via NSDL
- Degree certificate OCR with university cross-reference
- Passport extraction with MRZ reading
- Auto-classification of uploaded documents (Aadhaar, PAN, Passport, Degree, Experience Letter)
- Confidence scoring — documents below 80% confidence are flagged for HITL review

If OCR confidence is below 80%, flag for Human-in-the-Loop review.

User query: {last_message}

Respond helpfully about document status, extraction results, or upload instructions."""

    response = await _call_llm([HumanMessage(content=prompt)])

    needs_hitl  = any(
        word in last_message.lower()
        for word in ["low confidence", "unclear", "blurry", "can't read"]
    )
    hitl_reason = "Document extraction confidence below threshold — manual review required" if needs_hitl else ""

    log_audit(
        action="document_query_processed",
        tenant_id=tenant_id,
        employee_id=emp_id,
        agent_name="document_agent",
        prompt_sent=last_message[:500],
        purpose="document_extraction",
        result_summary=response.content[:500],
        model_version="meta/llama-3.3-70b-instruct",
    )

    trace_entry = {
        "timestamp":  datetime.now().isoformat(),
        "agent":      "document_agent",
        "action":     "process_query",
        "needs_hitl": needs_hitl,
    }

    return {
        "final_response": response.content,
        "needs_hitl":     needs_hitl,
        "hitl_reason":    hitl_reason,
        "agent_trace":    [trace_entry],
    }


# ══════════════════════════════════════════════════════════════════════════════
# POLICY RAG AGENT
# ══════════════════════════════════════════════════════════════════════════════

async def policy_agent_node(state: OnboardingState) -> dict:
    """
    Policy RAG agent — retrieves from multi-tenant ChromaDB (LRU-cached).
    Uses HyDE query expansion and confidence-scored retrieval.
    """
    messages     = state.get("messages", [])
    last_message = messages[-1].content if messages else ""
    tenant_id    = state.get("tenant_id", "authbridge")
    emp_id       = state.get("employee_id", "unknown")

    # ── HyDE query expansion (off event loop; fallback to original on failure) ──
    try:
        expanded_query = await asyncio.to_thread(hyde_expand_query, last_message, get_llm())
    except Exception as exc:
        logger.warning("policy_agent_hyde_failed", extra={"error": str(exc)})
        expanded_query = last_message

    # ── RAG retrieval with confidence scores ──
    sources: set = set()
    rag_results: list = []
    confidence_score: float = 0.0
    try:
        results_with_scores = await asyncio.to_thread(
            query_policies_with_scores, expanded_query, tenant_id, None, 4
        )
        rag_results = [doc for doc, score in results_with_scores]
        confidence_score = max((score for _, score in results_with_scores), default=0.0)

        context_chunks = []
        for doc in rag_results:
            context_chunks.append(doc.page_content)
            sources.add(doc.metadata.get("source", "unknown"))
        context     = "\n\n---\n\n".join(context_chunks)
        source_list = ", ".join(sources)
    except Exception as exc:
        logger.warning("policy_agent_rag_failed", extra={"error": str(exc)})
        context     = f"Policy retrieval temporarily unavailable: {exc}"
        source_list = "none"

    prompt = f"""You are the Policy RAG Agent for AuthBridge's AI-Native Onboarding System.
Answer employee questions about company policies using ONLY the retrieved context below.

RULES:
1. Only answer based on the retrieved context. If not found, say so.
2. Cite the policy document your answer comes from.
3. For DPDP-related questions, mention the legal basis (Section 6 consent or Section 7(1)(i)).

Tenant: {tenant_id} | Employee: {emp_id}

Retrieved Policy Context:
{context}

Sources: {source_list}

User Question: {last_message}

Provide a clear, helpful answer with policy citations."""

    response = await _call_llm([HumanMessage(content=prompt)])

    log_audit(
        action="policy_query_answered",
        tenant_id=tenant_id,
        employee_id=emp_id,
        agent_name="policy_agent",
        prompt_sent=last_message[:500],
        retrieved_context=context[:2000],
        purpose="policy_information",
        legal_basis="legitimate_use_s7_1_i",
        data_category="policy_document",
        result_summary=response.content[:500],
        model_version="meta/llama-3.3-70b-instruct",
    )

    trace_entry = {
        "timestamp":        datetime.now().isoformat(),
        "agent":            "policy_agent",
        "action":           "rag_retrieval",
        "sources":          list(sources),
        "chunks_retrieved": len(rag_results),
        "confidence_score": round(confidence_score, 3),
        "hyde_used":        expanded_query != last_message,
    }

    return {
        "final_response": response.content,
        "agent_trace":    [trace_entry],
    }


# ══════════════════════════════════════════════════════════════════════════════
# COMPLIANCE / DPDP AGENT
# ══════════════════════════════════════════════════════════════════════════════

async def compliance_agent_node(state: OnboardingState) -> dict:
    """DPDP compliance agent — consent checks, audit queries, data rights."""
    messages     = state.get("messages", [])
    last_message = messages[-1].content if messages else ""
    emp_id       = state.get("employee_id", "unknown")
    tenant_id    = state.get("tenant_id", "authbridge")

    # ── Safe DB reads (off event loop) ──
    def _fetch_compliance_data():
        c = get_connection()
        try:
            consents = c.execute(
                "SELECT * FROM consents WHERE employee_id = ? AND tenant_id = ?",
                (emp_id, tenant_id),
            ).fetchall()
            audit_count = c.execute(
                "SELECT COUNT(*) FROM audit_trail WHERE employee_id = ? AND tenant_id = ?",
                (emp_id, tenant_id),
            ).fetchone()[0]
            return consents, audit_count
        finally:
            c.close()

    consents, audit_count = await asyncio.to_thread(_fetch_compliance_data)

    consent_info = (
        "\n".join(
            f"- {c['consent_type']}: {c['status']} | Purpose: {c['purpose_description']}"
            for c in consents
        )
        if consents else "No consents recorded yet."
    )

    prompt = f"""You are the Compliance & DPDP Agent for AuthBridge's AI-Native Onboarding System.
Handle data privacy compliance, consent management, and data principal rights.

DPDP Act 2023 Key Provisions:
- Section 6: Consent must be specific, revocable, unbundled.
- Section 7(1)(i): Legitimate use covers recruitment, onboarding, payroll, PF/tax, security.
- Section 8: Data principal rights — access, correction, erasure, portability, nomination, grievance.
- Rules 2025: Notified Nov 13, 2025. Consent Manager: Nov 13, 2026. Full enforcement: May 13, 2027.
- Penalties: ₹250 crore (security failures), ₹200 crore (breach notification). 72-hour breach notification.

Employee: {emp_id} | Tenant: {tenant_id}
Consent Status:
{consent_info}
Audit Trail Entries: {audit_count}

User Query: {last_message}

Respond with specific DPDP references. Flag any action needing ungranted consent."""

    response = await _call_llm([HumanMessage(content=prompt)])

    needs_hitl       = False
    hitl_reason      = ""
    pending_consents = [c for c in consents if c["status"] == "pending"] if consents else []
    if any(word in last_message.lower() for word in ["verify", "check", "initiate", "bgv"]):
        if pending_consents:
            needs_hitl  = True
            hitl_reason = f"Consent pending for: {', '.join(c['consent_type'] for c in pending_consents)}"

    log_audit(
        action="compliance_check",
        tenant_id=tenant_id,
        employee_id=emp_id,
        agent_name="compliance_agent",
        prompt_sent=last_message[:500],
        purpose="compliance_verification",
        legal_basis="legitimate_use_s7_1_i",
        data_category="compliance",
        consent_reference=f"consents_checked_{len(consents) if consents else 0}",
        result_summary=response.content[:500],
        model_version="meta/llama-3.3-70b-instruct",
    )

    trace_entry = {
        "timestamp":        datetime.now().isoformat(),
        "agent":            "compliance_agent",
        "action":           "dpdp_check",
        "consents_checked": len(consents) if consents else 0,
        "needs_hitl":       needs_hitl,
    }

    return {
        "final_response": response.content,
        "needs_hitl":     needs_hitl,
        "hitl_reason":    hitl_reason,
        "agent_trace":    [trace_entry],
    }


# ══════════════════════════════════════════════════════════════════════════════
# BGV AGENT
# ══════════════════════════════════════════════════════════════════════════════

async def bgv_agent_node(state: OnboardingState) -> dict:
    """BGV agent — mock AuthBridge iBRIDGE 2.0 API integration."""
    messages     = state.get("messages", [])
    last_message = messages[-1].content if messages else ""
    emp_id       = state.get("employee_id", "unknown")
    tenant_id    = state.get("tenant_id", "authbridge")

    # ── Safe DB reads (off event loop) ──
    def _fetch_bgv_data():
        c = get_connection()
        try:
            tasks = c.execute(
                """SELECT * FROM tasks WHERE employee_id = ? AND tenant_id = ?
                   AND task_type IN ('identity_verification','address_verification',
                   'education_verification','employment_verification','criminal_check')""",
                (emp_id, tenant_id),
            ).fetchall()
            consents = c.execute(
                "SELECT * FROM consents WHERE employee_id = ? AND tenant_id = ? AND consent_type LIKE 'bgv_%'",
                (emp_id, tenant_id),
            ).fetchall()
            return tasks, consents
        finally:
            c.close()

    tasks, consents = await asyncio.to_thread(_fetch_bgv_data)

    task_info = (
        "\n".join(f"- {t['task_name']}: {t['status']} (agent: {t['assigned_agent']})" for t in tasks)
        if tasks else "No BGV tasks initiated."
    )
    consent_status = (
        "\n".join(f"- {c['consent_type']}: {c['status']}" for c in consents)
        if consents else "No BGV consents recorded."
    )

    ibridge_mock = {
        "api": "AuthBridge iBRIDGE 2.0",
        "endpoint": "/api/v2/verification/initiate",
        "status": "mock_response",
        "capabilities": [
            "Identity (Aadhaar/PAN/Passport) — 24-48hr SLA",
            "Address (physical + digital) — 3-5 day SLA",
            "Education (university direct) — 5-7 day SLA",
            "Employment (previous employer) — 5-10 day SLA",
            "Criminal (3,500+ courts via Vault) — 3-5 day SLA",
        ],
        "certifications": "ISO 27001, SOC 2 Type II",
        "data_residency": "India",
    }

    prompt = f"""You are the BGV (Background Verification) Agent for AuthBridge's AI-Native Onboarding System.
Interface with the AuthBridge iBRIDGE 2.0 API.

Employee: {emp_id} | Tenant: {tenant_id}

BGV Tasks:
{task_info}

Consent Status:
{consent_status}

Mock iBRIDGE API:
{json.dumps(ibridge_mock, indent=2)}

RULES:
1. NEVER initiate BGV without verified consent (DPDP Section 6).
2. Criminal checks ALWAYS require HITL approval from HR Admin.
3. Mention AuthBridge ISO 27001, SOC 2 Type II certifications and India data residency.

User Query: {last_message}

Respond with BGV status, next steps, or mock API results."""

    response = await _call_llm([HumanMessage(content=prompt)])

    needs_hitl  = any(
        word in last_message.lower()
        for word in ["criminal", "initiate", "start bgv", "run check"]
    )
    hitl_reason = "BGV action requires HR Admin approval before iBRIDGE API call" if needs_hitl else ""

    log_audit(
        action="bgv_query_processed",
        tenant_id=tenant_id,
        employee_id=emp_id,
        agent_name="bgv_agent",
        prompt_sent=last_message[:500],
        purpose="background_verification",
        legal_basis="consent_s6",
        data_category="verification_data",
        consent_reference=f"bgv_consents_{len(consents) if consents else 0}",
        result_summary=response.content[:500],
        model_version="meta/llama-3.3-70b-instruct",
        pii_detected=1,
    )

    trace_entry = {
        "timestamp":  datetime.now().isoformat(),
        "agent":      "bgv_agent",
        "action":     "ibridge_query",
        "needs_hitl": needs_hitl,
        "mock_api":   True,
    }

    return {
        "final_response": response.content,
        "needs_hitl":     needs_hitl,
        "hitl_reason":    hitl_reason,
        "agent_trace":    [trace_entry],
    }


# ══════════════════════════════════════════════════════════════════════════════
# HITL NODE
# ══════════════════════════════════════════════════════════════════════════════

async def hitl_check_node(state: OnboardingState) -> dict:
    """If any agent flagged needs_hitl, insert into queue and append notice."""
    if not state.get("needs_hitl", False):
        return {}

    emp_id    = state.get("employee_id", "unknown")
    tenant_id = state.get("tenant_id", "authbridge")
    agent     = state.get("current_agent", "unknown")
    reason    = state.get("hitl_reason", "Review required")

    # ── Safe DB write (off event loop) ──
    def _insert_hitl():
        c = get_connection()
        try:
            c.execute("""
                INSERT INTO hitl_queue (employee_id, tenant_id, agent_name, action_type,
                                         description, risk_level, status)
                VALUES (?, ?, ?, ?, ?, ?, 'pending')
            """, (emp_id, tenant_id, agent, "review_required", reason, "high"))
            c.commit()
        finally:
            c.close()

    await asyncio.to_thread(_insert_hitl)

    log_audit(
        action="hitl_queue_entry_created",
        tenant_id=tenant_id,
        employee_id=emp_id,
        agent_name="hitl_system",
        purpose="human_review",
        result_summary=reason,
    )

    hitl_notice = (
        f"\n\n⚠️ **Human-in-the-Loop Review Required**\n"
        f"Reason: {reason}\n"
        f"Status: Added to HR Admin approval queue."
    )

    trace_entry = {
        "timestamp": datetime.now().isoformat(),
        "agent":     "hitl_system",
        "action":    "queue_insert",
        "reason":    reason,
    }

    return {
        "final_response": state.get("final_response", "") + hitl_notice,
        "agent_trace":    [trace_entry],
    }


# ══════════════════════════════════════════════════════════════════════════════
# ROUTING FUNCTION
# ══════════════════════════════════════════════════════════════════════════════

def route_to_agent(state: OnboardingState) -> str:
    """Return the agent name chosen by supervisor_node."""
    return state.get("current_agent", "policy_agent")


# ══════════════════════════════════════════════════════════════════════════════
# GRAPH CONSTRUCTION
# ══════════════════════════════════════════════════════════════════════════════

def build_onboarding_graph():
    """
    Build and compile the LangGraph multi-agent onboarding workflow.

    Graph: START → supervisor → {document|policy|compliance|bgv}_agent → hitl_check → END

    This function is called exactly once (via get_onboarding_graph() singleton).
    All node functions are async; LangGraph handles async execution transparently.
    """
    graph = StateGraph(OnboardingState)

    graph.add_node("supervisor",       supervisor_node)
    graph.add_node("document_agent",   document_agent_node)
    graph.add_node("policy_agent",     policy_agent_node)
    graph.add_node("compliance_agent", compliance_agent_node)
    graph.add_node("bgv_agent",        bgv_agent_node)
    graph.add_node("hitl_check",       hitl_check_node)

    graph.add_edge(START, "supervisor")

    graph.add_conditional_edges(
        "supervisor",
        route_to_agent,
        {
            "document_agent":   "document_agent",
            "policy_agent":     "policy_agent",
            "compliance_agent": "compliance_agent",
            "bgv_agent":        "bgv_agent",
        },
    )

    graph.add_edge("document_agent",   "hitl_check")
    graph.add_edge("policy_agent",     "hitl_check")
    graph.add_edge("compliance_agent", "hitl_check")
    graph.add_edge("bgv_agent",        "hitl_check")
    graph.add_edge("hitl_check",       END)

    return graph.compile()


# ══════════════════════════════════════════════════════════════════════════════
# PUBLIC API — ASYNC ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

async def run_onboarding_query_async(
    query: str,
    employee_id: str = "EMP001",
    tenant_id: str = "authbridge",
) -> dict:
    """
    Async entry point — used by FastAPI endpoints.

    Loads multi-turn conversation history, invokes the graph, persists the new
    turn and query metrics, then returns a rich result dict including latency
    and confidence.
    """
    graph       = get_onboarding_graph()
    total_start = time.perf_counter()

    # ── Load conversation history for multi-turn context ──
    history = await asyncio.to_thread(load_conversation_history, employee_id, tenant_id, 6)
    history_messages = []
    for turn in history:
        if turn["role"] == "human":
            history_messages.append(HumanMessage(content=turn["content"]))
        else:
            history_messages.append(AIMessage(content=turn["content"]))

    initial_state = {
        "messages":       history_messages + [HumanMessage(content=query)],
        "employee_id":    employee_id,
        "tenant_id":      tenant_id,
        "current_agent":  "",
        "task_type":      "",
        "agent_trace":    [],   # fresh list every invocation
        "needs_hitl":     False,
        "hitl_reason":    "",
        "final_response": "",
    }

    try:
        result    = await graph.ainvoke(initial_state)
        total_ms  = (time.perf_counter() - total_start) * 1000

        # ── Persist conversation memory ──
        await asyncio.to_thread(
            save_conversation_turn, employee_id, tenant_id, "human", query
        )
        if result.get("final_response"):
            await asyncio.to_thread(
                save_conversation_turn,
                employee_id, tenant_id, "ai",
                result["final_response"],
                result.get("current_agent", ""),
            )

        # ── Extract metrics from agent trace ──
        trace      = result.get("agent_trace", [])
        confidence = next(
            (t.get("confidence_score", 0) for t in trace if "confidence_score" in t), 0.0
        )
        chunks     = next(
            (t.get("chunks_retrieved", 0) for t in trace if "chunks_retrieved" in t), 0
        )

        # ── Persist query metrics ──
        await asyncio.to_thread(
            save_query_metrics,
            employee_id=employee_id,
            tenant_id=tenant_id,
            query=query,
            agent_name=result.get("current_agent", "unknown"),
            total_latency_ms=total_ms,
            confidence_score=confidence,
            chunks_retrieved=chunks,
            needs_hitl=result.get("needs_hitl", False),
        )

        logger.info(
            "query_completed",
            extra={
                "employee_id": employee_id,
                "tenant_id":   tenant_id,
                "agent":       result.get("current_agent"),
                "latency_ms":  round(total_ms, 1),
                "confidence":  round(confidence, 3),
                "needs_hitl":  result.get("needs_hitl", False),
            },
        )

        return {
            "response":    result.get("final_response", "No response generated."),
            "agent_trace": result.get("agent_trace", []),
            "needs_hitl":  result.get("needs_hitl", False),
            "hitl_reason": result.get("hitl_reason", ""),
            "employee_id": employee_id,
            "tenant_id":   tenant_id,
            "latency_ms":  round(total_ms, 1),
            "confidence":  round(confidence, 3),
        }

    except Exception as exc:
        logger.error(
            "graph_invocation_failed",
            extra={
                "employee_id": employee_id,
                "tenant_id":   tenant_id,
                "error":       str(exc),
            },
            exc_info=True,
        )
        return {
            "response": (
                "I encountered an error processing your request. "
                "Please try again shortly."
            ),
            "agent_trace": [{
                "agent":     "error_handler",
                "error":     str(exc),
                "timestamp": datetime.now().isoformat(),
            }],
            "needs_hitl":  True,
            "hitl_reason": f"System error: {type(exc).__name__}: {str(exc)[:200]}",
            "employee_id": employee_id,
            "tenant_id":   tenant_id,
            "latency_ms":  0,
            "confidence":  0,
        }


# ══════════════════════════════════════════════════════════════════════════════
# PUBLIC API — SYNC WRAPPER (backward-compatible)
# ══════════════════════════════════════════════════════════════════════════════

def run_onboarding_query(
    query: str,
    employee_id: str = "EMP001",
    tenant_id: str = "authbridge",
) -> dict:
    """
    Sync wrapper — backward-compatible entry point for Streamlit and other sync callers.
    Runs the async implementation in a new event loop via asyncio.run().
    """
    return asyncio.run(run_onboarding_query_async(query, employee_id, tenant_id))


# ══════════════════════════════════════════════════════════════════════════════
# GRAPH DIAGRAM HELPER
# ══════════════════════════════════════════════════════════════════════════════

def get_graph_mermaid() -> str:
    """Get the Mermaid diagram of the agent graph (uses singleton)."""
    graph = get_onboarding_graph()
    try:
        return graph.get_graph().draw_mermaid()
    except Exception:
        return """graph LR
    __start__([Start]) --> supervisor
    supervisor -->|document_agent| document_agent
    supervisor -->|policy_agent| policy_agent
    supervisor -->|compliance_agent| compliance_agent
    supervisor -->|bgv_agent| bgv_agent
    document_agent --> hitl_check
    policy_agent --> hitl_check
    compliance_agent --> hitl_check
    bgv_agent --> hitl_check
    hitl_check --> __end__([End])

    style supervisor fill:#4CAF50,color:white
    style document_agent fill:#2196F3,color:white
    style policy_agent fill:#FF9800,color:white
    style compliance_agent fill:#9C27B0,color:white
    style bgv_agent fill:#F44336,color:white
    style hitl_check fill:#607D8B,color:white"""


# ══════════════════════════════════════════════════════════════════════════════
# STANDALONE TEST
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from dotenv import load_dotenv
    load_dotenv()

    from database.db import init_database, seed_demo_data
    init_database()
    seed_demo_data()

    print("Testing multi-agent graph (async)...")
    result = run_onboarding_query(
        query="What is the leave policy for new joiners during probation?",
        employee_id="EMP001",
        tenant_id="authbridge",
    )
    print(f"\nResponse: {result['response'][:500]}")
    print(f"Latency:  {result.get('latency_ms', 'n/a')} ms")
    print(f"Confidence: {result.get('confidence', 'n/a')}")
    print(f"\nAgent Trace: {json.dumps(result['agent_trace'], indent=2)}")
    print(f"\nMermaid Graph:\n{get_graph_mermaid()}")
