"""
database/db.py — SQLite Schema for AuthBridge AI-Native Onboarding

Design rationale (maps to playbook Section 6 + Section 8):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. employees      → Core hire record; tenant_id enables multi-tenant isolation
2. tasks          → Onboarding task tracker (document upload, BGV, IT, etc.)
3. audit_trail    → DPDP immutable log: prompt + context + consent + model + purpose
4. consents       → Per-purpose withdrawable consent (DPDP Section 6/7)
5. hitl_queue     → Human-in-the-loop approval queue for enterprise trust
6. conversation_history → Multi-turn agent memory (persistent across sessions)
7. query_metrics  → Per-query latency + quality tracking for HR dashboard

The audit_trail table is the SINGLE most impressive artifact in the demo.
Every AI action logs: who accessed what, with which consent, for what purpose,
which model version, and the retrieved RAG context. This is what no competitor shows.
"""

import sqlite3
import os
import logging
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)

DB_PATH = os.getenv("SQLITE_DB_PATH", "./authbridge.db")


# ── Enums — enforce valid values in Python before they reach the DB ──────────

class EmployeeStatus(str, Enum):
    OFFER_ACCEPTED    = "offer_accepted"
    DOCUMENTS_PENDING = "documents_pending"
    BGV_INITIATED     = "bgv_initiated"
    BGV_IN_PROGRESS   = "bgv_in_progress"
    BGV_COMPLETED     = "bgv_completed"
    ONBOARDING_COMPLETE = "onboarding_complete"
    FLAGGED           = "flagged"


class TaskStatus(str, Enum):
    PENDING      = "pending"
    IN_PROGRESS  = "in_progress"
    COMPLETED    = "completed"
    FAILED       = "failed"
    NEEDS_REVIEW = "needs_review"


class ConsentStatus(str, Enum):
    PENDING   = "pending"
    GRANTED   = "granted"
    WITHDRAWN = "withdrawn"
    EXPIRED   = "expired"


def get_connection() -> sqlite3.Connection:
    """Get a SQLite connection with row factory enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")  # Better concurrent reads
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_database():
    """Create all tables. Idempotent — safe to call on every startup."""
    conn = get_connection()
    cursor = conn.cursor()

    # ── 1. EMPLOYEES ──
    # tenant_id is critical: proves multi-tenant data isolation to the panel
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id       TEXT NOT NULL DEFAULT 'authbridge',
            employee_id     TEXT UNIQUE NOT NULL,
            full_name       TEXT NOT NULL,
            email           TEXT NOT NULL,
            department      TEXT DEFAULT '',
            designation     TEXT DEFAULT '',
            date_of_joining TEXT DEFAULT '',
            phone           TEXT DEFAULT '',
            status          TEXT DEFAULT 'offer_accepted'
                CHECK(status IN (
                    'offer_accepted','documents_pending','bgv_initiated',
                    'bgv_in_progress','bgv_completed','onboarding_complete',
                    'flagged'
                )),
            risk_score      REAL DEFAULT 0.0,
            created_at      TEXT DEFAULT (datetime('now')),
            updated_at      TEXT DEFAULT (datetime('now'))
        )
    """)

    # ── 2. TASKS ──
    # Tracks every onboarding task per employee
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id     TEXT NOT NULL,
            tenant_id       TEXT NOT NULL DEFAULT 'authbridge',
            task_type       TEXT NOT NULL
                CHECK(task_type IN (
                    'document_upload','identity_verification','address_verification',
                    'education_verification','employment_verification',
                    'criminal_check','drug_test','reference_check',
                    'it_provisioning','policy_acknowledgement','training_assignment'
                )),
            task_name       TEXT NOT NULL,
            status          TEXT DEFAULT 'pending'
                CHECK(status IN ('pending','in_progress','completed','failed','needs_review')),
            assigned_agent  TEXT DEFAULT '',
            result_summary  TEXT DEFAULT '',
            created_at      TEXT DEFAULT (datetime('now')),
            completed_at    TEXT,
            FOREIGN KEY (employee_id) REFERENCES employees(employee_id)
        )
    """)

    # ── 3. AUDIT TRAIL (DPDP — the demo's crown jewel) ──
    # Immutable log: prompt + retrieved_context + consent_ref + model_version + purpose
    # This is what makes the panel say "nobody else shows this"
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_trail (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp           TEXT NOT NULL DEFAULT (datetime('now')),
            tenant_id           TEXT NOT NULL DEFAULT 'authbridge',
            employee_id         TEXT DEFAULT '',
            user_role           TEXT NOT NULL DEFAULT 'system'
                CHECK(user_role IN ('new_hire','hr_admin','system','agent')),
            action              TEXT NOT NULL,
            agent_name          TEXT DEFAULT '',
            prompt_sent         TEXT DEFAULT '',
            retrieved_context   TEXT DEFAULT '',
            model_version       TEXT DEFAULT '',
            consent_reference   TEXT DEFAULT '',
            purpose             TEXT DEFAULT '',
            legal_basis         TEXT DEFAULT 'legitimate_use_s7_1_i',
            data_category       TEXT DEFAULT '',
            pii_detected        INTEGER DEFAULT 0,
            ip_address          TEXT DEFAULT '',
            result_summary      TEXT DEFAULT ''
        )
    """)

    # ── 4. CONSENTS (DPDP Section 6 — per-purpose, withdrawable) ──
    # BGV consent must be specific, revocable, unbundled from offer acceptance
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS consents (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id     TEXT NOT NULL,
            tenant_id       TEXT NOT NULL DEFAULT 'authbridge',
            consent_type    TEXT NOT NULL
                CHECK(consent_type IN (
                    'bgv_identity','bgv_address','bgv_education',
                    'bgv_employment','bgv_criminal','bgv_drug_test',
                    'data_processing','data_storage','data_sharing_third_party',
                    'biometric_collection'
                )),
            status          TEXT DEFAULT 'pending'
                CHECK(status IN ('pending','granted','withdrawn','expired')),
            granted_at      TEXT,
            withdrawn_at    TEXT,
            purpose_description TEXT DEFAULT '',
            retention_period_days INTEGER DEFAULT 365,
            legal_notice_language TEXT DEFAULT 'en',
            created_at      TEXT DEFAULT (datetime('now'))
        )
    """)

    # ── 5. HITL QUEUE (Human-in-the-Loop) ──
    # Enterprise trust feature: agents pause here for HR approval
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS hitl_queue (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id     TEXT NOT NULL,
            tenant_id       TEXT NOT NULL DEFAULT 'authbridge',
            agent_name      TEXT NOT NULL,
            action_type     TEXT NOT NULL,
            description     TEXT NOT NULL,
            risk_level      TEXT DEFAULT 'medium'
                CHECK(risk_level IN ('low','medium','high','critical')),
            status          TEXT DEFAULT 'pending'
                CHECK(status IN ('pending','approved','rejected','escalated')),
            payload         TEXT DEFAULT '{}',
            reviewer        TEXT DEFAULT '',
            review_notes    TEXT DEFAULT '',
            created_at      TEXT DEFAULT (datetime('now')),
            reviewed_at     TEXT
        )
    """)

    # ── 6. CONVERSATION HISTORY (multi-turn agent memory) ──
    # Persists every conversation turn so agents can recall prior context
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversation_history (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT NOT NULL,
            tenant_id   TEXT NOT NULL DEFAULT 'authbridge',
            role        TEXT NOT NULL CHECK(role IN ('human', 'ai')),
            content     TEXT NOT NULL,
            agent_name  TEXT DEFAULT '',
            created_at  TEXT DEFAULT (datetime('now'))
        )
    """)

    # ── 7. QUERY METRICS (latency + quality tracking) ──
    # Every agent query logs timing, retrieval quality, and HITL signals
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS query_metrics (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id          TEXT NOT NULL,
            tenant_id            TEXT NOT NULL,
            query                TEXT NOT NULL,
            agent_name           TEXT NOT NULL,
            routing_method       TEXT DEFAULT 'rule_based',
            llm_latency_ms       REAL DEFAULT 0,
            rag_latency_ms       REAL DEFAULT 0,
            total_latency_ms     REAL DEFAULT 0,
            confidence_score     REAL DEFAULT 0,
            chunks_retrieved     INTEGER DEFAULT 0,
            cache_hit            INTEGER DEFAULT 0,
            needs_hitl           INTEGER DEFAULT 0,
            created_at           TEXT DEFAULT (datetime('now'))
        )
    """)

    # ── DB INDEXES — fast lookups for the most common query patterns ──
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_tenant_ts    ON audit_trail(tenant_id, timestamp DESC)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_employee      ON audit_trail(employee_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_employee      ON tasks(employee_id, tenant_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_hitl_status         ON hitl_queue(tenant_id, status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_conversation_emp    ON conversation_history(employee_id, tenant_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_metrics_emp         ON query_metrics(employee_id, tenant_id)")

    conn.commit()
    conn.close()
    logger.info("database_initialized", extra={"tables": [
        "employees", "tasks", "audit_trail", "consents", "hitl_queue",
        "conversation_history", "query_metrics",
    ]})


def log_audit(
    action: str,
    tenant_id: str = "authbridge",
    employee_id: str = "",
    user_role: str = "system",
    agent_name: str = "",
    prompt_sent: str = "",
    retrieved_context: str = "",
    model_version: str = "meta/llama-3.3-70b-instruct",
    consent_reference: str = "",
    purpose: str = "",
    legal_basis: str = "legitimate_use_s7_1_i",
    data_category: str = "",
    pii_detected: int = 0,
    result_summary: str = ""
):
    """
    Insert an immutable audit trail entry. Called by every agent action.
    Uses try/finally to guarantee the connection is always closed.
    """
    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO audit_trail (
                tenant_id, employee_id, user_role, action, agent_name,
                prompt_sent, retrieved_context, model_version, consent_reference,
                purpose, legal_basis, data_category, pii_detected, result_summary
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            tenant_id, employee_id, user_role, action, agent_name,
            prompt_sent[:2000], retrieved_context[:2000], model_version,
            consent_reference, purpose, legal_basis, data_category,
            pii_detected, result_summary[:2000],
        ))
        conn.commit()
    except Exception:
        logger.exception("audit_log_write_failed", extra={"action": action, "employee_id": employee_id})
        # Never raise — audit failures must not interrupt the main workflow
    finally:
        conn.close()


def seed_demo_data():
    """Seed realistic demo data for the panel presentation."""
    conn = get_connection()
    cursor = conn.cursor()

    # Check if already seeded
    existing = cursor.execute("SELECT COUNT(*) FROM employees").fetchone()[0]
    if existing > 0:
        conn.close()
        return

    # ── Demo Employees (two tenants to prove multi-tenant isolation) ──
    employees = [
        ("authbridge", "EMP001", "Priya Sharma", "priya.sharma@acmecorp.in",
         "Engineering", "Senior Software Engineer", "2026-05-01", "+91-98765-43210", "documents_pending"),
        ("authbridge", "EMP002", "Rahul Verma", "rahul.verma@acmecorp.in",
         "Finance", "Financial Analyst", "2026-05-15", "+91-87654-32109", "offer_accepted"),
        ("authbridge", "EMP003", "Ananya Iyer", "ananya.iyer@acmecorp.in",
         "Product", "Product Manager", "2026-05-01", "+91-76543-21098", "bgv_initiated"),
        # Second tenant — proves data isolation
        ("globalbank", "EMP004", "Vikram Patel", "vikram.patel@globalbank.in",
         "Risk", "Risk Analyst", "2026-06-01", "+91-65432-10987", "offer_accepted"),
        ("globalbank", "EMP005", "Meera Reddy", "meera.reddy@globalbank.in",
         "Compliance", "Compliance Officer", "2026-06-15", "+91-54321-09876", "documents_pending"),
    ]

    for emp in employees:
        cursor.execute("""
            INSERT OR IGNORE INTO employees
            (tenant_id, employee_id, full_name, email, department, designation,
             date_of_joining, phone, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, emp)

    # ── Demo Tasks ──
    tasks = [
        ("EMP001", "authbridge", "document_upload", "Upload Aadhaar Card", "completed", "document_agent"),
        ("EMP001", "authbridge", "document_upload", "Upload PAN Card", "completed", "document_agent"),
        ("EMP001", "authbridge", "identity_verification", "Aadhaar Verification via iBRIDGE", "in_progress", "bgv_agent"),
        ("EMP001", "authbridge", "education_verification", "B.Tech Degree Verification", "pending", "bgv_agent"),
        ("EMP001", "authbridge", "employment_verification", "Previous Employer Check", "pending", "bgv_agent"),
        ("EMP001", "authbridge", "policy_acknowledgement", "Code of Conduct", "pending", "policy_agent"),
        ("EMP002", "authbridge", "document_upload", "Upload Identity Documents", "pending", "document_agent"),
        ("EMP003", "authbridge", "identity_verification", "PAN Verification", "completed", "bgv_agent"),
        ("EMP003", "authbridge", "criminal_check", "Criminal Record Check", "in_progress", "bgv_agent"),
        ("EMP004", "globalbank", "document_upload", "Upload KYC Documents", "pending", "document_agent"),
        ("EMP005", "globalbank", "identity_verification", "Aadhaar Verification", "pending", "bgv_agent"),
    ]

    for t in tasks:
        cursor.execute("""
            INSERT INTO tasks (employee_id, tenant_id, task_type, task_name, status, assigned_agent)
            VALUES (?, ?, ?, ?, ?, ?)
        """, t)

    # ── Demo Consents (DPDP-compliant: specific, per-purpose) ──
    consents = [
        ("EMP001", "authbridge", "bgv_identity", "granted", "Identity verification for employment onboarding"),
        ("EMP001", "authbridge", "bgv_education", "granted", "Education credential verification"),
        ("EMP001", "authbridge", "bgv_employment", "pending", "Previous employment history verification"),
        ("EMP001", "authbridge", "data_processing", "granted", "Processing personal data for onboarding"),
        ("EMP002", "authbridge", "bgv_identity", "pending", "Identity verification for employment onboarding"),
        ("EMP003", "authbridge", "bgv_identity", "granted", "Identity verification for employment onboarding"),
        ("EMP003", "authbridge", "bgv_criminal", "granted", "Criminal background check"),
        ("EMP004", "globalbank", "bgv_identity", "pending", "Identity verification — BFSI regulatory requirement"),
        ("EMP005", "globalbank", "data_processing", "granted", "Processing personal data under RBI guidelines"),
    ]

    for c in consents:
        cursor.execute("""
            INSERT INTO consents (employee_id, tenant_id, consent_type, status, purpose_description,
                                  granted_at)
            VALUES (?, ?, ?, ?, ?, CASE WHEN ? = 'granted' THEN datetime('now') ELSE NULL END)
        """, (*c, c[3]))

    # ── Demo HITL Queue ──
    hitl_items = [
        ("EMP001", "authbridge", "bgv_agent", "initiate_criminal_check",
         "Criminal background check requires HR approval before API call to iBRIDGE",
         "high", "pending"),
        ("EMP003", "authbridge", "compliance_agent", "flag_address_mismatch",
         "Address on Aadhaar does not match current residence declared in Form 2. Risk flag raised.",
         "critical", "pending"),
        ("EMP001", "authbridge", "document_agent", "low_confidence_extraction",
         "PAN card OCR confidence 67% — below 80% threshold. Manual review needed.",
         "medium", "pending"),
    ]

    for h in hitl_items:
        cursor.execute("""
            INSERT INTO hitl_queue (employee_id, tenant_id, agent_name, action_type,
                                     description, risk_level, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, h)

    # ── Demo Audit Trail entries ──
    audit_entries = [
        ("authbridge", "EMP001", "new_hire", "document_uploaded", "document_agent",
         "User uploaded Aadhaar card image", "", "meta/llama-3.3-70b-instruct",
         "consent_bgv_identity_001", "identity_verification", "consent_s6", "identity_document", 1,
         "Aadhaar card extracted — Name: Priya Sharma, DOB: 1995-03-15"),
        ("authbridge", "EMP001", "system", "bgv_api_called", "bgv_agent",
         "Initiate iBRIDGE identity verification for EMP001", "", "meta/llama-3.3-70b-instruct",
         "consent_bgv_identity_001", "background_verification", "consent_s6", "identity_document", 1,
         "iBRIDGE API called — verification pending"),
        ("authbridge", "EMP001", "hr_admin", "policy_query", "policy_agent",
         "What is the leave policy for new joiners?",
         "Retrieved: Leave policy doc chunk 1, chunk 2", "meta/llama-3.3-70b-instruct",
         "", "policy_information", "legitimate_use_s7_1_i", "policy_document", 0,
         "Answered leave policy query with 2 source citations"),
        ("authbridge", "EMP003", "system", "compliance_flag_raised", "compliance_agent",
         "Check DPDP consent status for criminal BGV", "", "meta/llama-3.3-70b-instruct",
         "consent_bgv_criminal_003", "compliance_check", "legitimate_use_s7_1_i", "compliance", 0,
         "Consent verified — criminal check may proceed"),
        ("globalbank", "EMP004", "system", "tenant_policy_query", "policy_agent",
         "What are the KYC requirements for new banking employees?",
         "Retrieved: GlobalBank KYC policy v2.1", "meta/llama-3.3-70b-instruct",
         "", "policy_information", "legitimate_use_s7_1_i", "policy_document", 0,
         "Answered with tenant-specific GlobalBank KYC policy"),
    ]

    for a in audit_entries:
        cursor.execute("""
            INSERT INTO audit_trail (
                tenant_id, employee_id, user_role, action, agent_name,
                prompt_sent, retrieved_context, model_version, consent_reference,
                purpose, legal_basis, data_category, pii_detected, result_summary
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, a)

    conn.commit()
    conn.close()
    logger.info("demo_data_seeded", extra={"employees": 5, "tasks": 11, "consents": 9, "hitl_items": 3, "audit_entries": 5})


# ── CONVERSATION HISTORY HELPERS ─────────────────────────────────────────────

def save_conversation_turn(
    employee_id: str,
    tenant_id: str,
    role: str,            # "human" or "ai"
    content: str,
    agent_name: str = "",
) -> None:
    """Persist one conversation turn for multi-turn agent memory."""
    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO conversation_history
               (employee_id, tenant_id, role, content, agent_name)
               VALUES (?, ?, ?, ?, ?)""",
            (employee_id, tenant_id, role, content[:4000], agent_name),
        )
        conn.commit()
    except Exception:
        logger.exception("save_conversation_turn_failed",
                         extra={"employee_id": employee_id})
    finally:
        conn.close()


def load_conversation_history(
    employee_id: str,
    tenant_id: str,
    limit: int = 6,
) -> list:
    """
    Return the last `limit` conversation turns as a list of dicts.
    Each dict: {"role": "human"|"ai", "content": str}
    Used to populate agent memory for multi-turn context.
    """
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT role, content FROM conversation_history
               WHERE employee_id = ? AND tenant_id = ?
               ORDER BY created_at DESC LIMIT ?""",
            (employee_id, tenant_id, limit),
        ).fetchall()
        # Return in chronological order (oldest first)
        return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]
    except Exception:
        logger.exception("load_conversation_history_failed")
        return []
    finally:
        conn.close()


# ── QUERY METRICS HELPERS ────────────────────────────────────────────────────

def save_query_metrics(
    employee_id: str,
    tenant_id: str,
    query: str,
    agent_name: str,
    routing_method: str = "rule_based",
    llm_latency_ms: float = 0,
    rag_latency_ms: float = 0,
    total_latency_ms: float = 0,
    confidence_score: float = 0,
    chunks_retrieved: int = 0,
    cache_hit: bool = False,
    needs_hitl: bool = False,
) -> None:
    """Store per-query performance and quality metrics."""
    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO query_metrics
               (employee_id, tenant_id, query, agent_name, routing_method,
                llm_latency_ms, rag_latency_ms, total_latency_ms,
                confidence_score, chunks_retrieved, cache_hit, needs_hitl)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                employee_id, tenant_id, query[:500], agent_name, routing_method,
                llm_latency_ms, rag_latency_ms, total_latency_ms,
                confidence_score, chunks_retrieved,
                int(cache_hit), int(needs_hitl),
            ),
        )
        conn.commit()
    except Exception:
        logger.exception("save_query_metrics_failed")
    finally:
        conn.close()


def get_performance_summary(tenant_id: str, days: int = 7) -> dict:
    """
    Return aggregated performance stats for the HR dashboard.
    Covers the last `days` days for the given tenant.
    """
    conn = get_connection()
    try:
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        row = conn.execute(
            """SELECT
                 COUNT(*)                        AS total_queries,
                 AVG(total_latency_ms)           AS avg_latency_ms,
                 MAX(total_latency_ms)           AS p100_latency_ms,
                 AVG(confidence_score)           AS avg_confidence,
                 SUM(cache_hit)                  AS cache_hits,
                 SUM(needs_hitl)                 AS hitl_escalations
               FROM query_metrics
               WHERE tenant_id = ? AND created_at > ?""",
            (tenant_id, cutoff),
        ).fetchone()
        return {
            "total_queries":    row["total_queries"] or 0,
            "avg_latency_ms":   round(row["avg_latency_ms"] or 0, 1),
            "p100_latency_ms":  round(row["p100_latency_ms"] or 0, 1),
            "avg_confidence":   round(row["avg_confidence"] or 0, 3),
            "cache_hits":       row["cache_hits"] or 0,
            "hitl_escalations": row["hitl_escalations"] or 0,
        }
    except Exception:
        logger.exception("get_performance_summary_failed")
        return {}
    finally:
        conn.close()


if __name__ == "__main__":
    init_database()
    seed_demo_data()
