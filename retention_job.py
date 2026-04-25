"""
retention_job.py — DPDP Data Retention & Anonymization

Runs nightly via APScheduler (set up in api/main.py startup).
Can also be called manually: python retention_job.py

DPDP Act compliance actions:
  1. Delete consents that were withdrawn > 30 days ago
  2. Anonymize audit_trail entries older than the consent's retention_period_days
  3. Log every retention action back to audit_trail (the meta-audit)

References:
  - DPDP Act 2023, Section 8(7): Data Fiduciary must erase personal data when
    purpose is served or consent withdrawn.
  - Rules 2025: Retention period to be specified at time of consent collection.
"""

import os
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Default retention: 365 days for general data, 7 years for BGV (post-termination)
DEFAULT_RETENTION_DAYS = int(os.getenv("DEFAULT_RETENTION_DAYS", "365"))
BGV_RETENTION_DAYS     = int(os.getenv("BGV_RETENTION_DAYS", "2555"))   # 7 years


def run_data_retention() -> dict:
    """
    Execute all DPDP data retention actions.

    Returns a summary dict: {"deleted_consents": N, "anonymized_audit": N, "errors": [...]}
    Safe to call repeatedly — uses idempotent WHERE clauses.
    """
    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    from database.db import get_connection, log_audit

    summary = {"deleted_consents": 0, "anonymized_audit": 0, "errors": []}

    conn = get_connection()
    try:
        # ── 1. Delete withdrawn consents older than 30 days ──────────────────
        cutoff_withdrawal = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
        cursor = conn.execute(
            """DELETE FROM consents
               WHERE status = 'withdrawn'
               AND withdrawn_at IS NOT NULL
               AND withdrawn_at < ?""",
            (cutoff_withdrawal,),
        )
        summary["deleted_consents"] = cursor.rowcount
        logger.info("retention_consents_deleted", extra={"count": cursor.rowcount})

        # ── 2. Anonymize expired audit entries ────────────────────────────────
        # Replace PII fields with [REDACTED] for entries older than retention period
        cutoff_audit = (datetime.now() - timedelta(days=DEFAULT_RETENTION_DAYS)).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        cursor = conn.execute(
            """UPDATE audit_trail
               SET prompt_sent       = '[REDACTED - retention expired]',
                   retrieved_context = '[REDACTED - retention expired]',
                   result_summary    = '[REDACTED - retention expired]'
               WHERE timestamp < ?
               AND prompt_sent != '[REDACTED - retention expired]'""",
            (cutoff_audit,),
        )
        summary["anonymized_audit"] = cursor.rowcount
        logger.info("retention_audit_anonymized", extra={"count": cursor.rowcount})

        # ── 3. Expire stale pending consents (older than 90 days) ────────────
        cutoff_pending = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d %H:%M:%S")
        conn.execute(
            """UPDATE consents
               SET status = 'expired'
               WHERE status = 'pending'
               AND created_at < ?""",
            (cutoff_pending,),
        )

        conn.commit()

        # ── 4. Log the retention run itself to audit trail ────────────────────
        log_audit(
            action="data_retention_executed",
            tenant_id="system",
            agent_name="retention_job",
            purpose="dpdp_compliance_s8_7",
            result_summary=(
                f"Retention run: deleted {summary['deleted_consents']} consents, "
                f"anonymized {summary['anonymized_audit']} audit entries"
            ),
        )

    except Exception as exc:
        logger.exception("retention_job_failed", extra={"error": str(exc)})
        summary["errors"].append(str(exc))
    finally:
        conn.close()

    return summary


def setup_retention_scheduler(app):
    """
    Attach an APScheduler to the FastAPI app that runs retention nightly at 02:00.
    Call this from FastAPI startup/lifespan initialization.
    """
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger

    scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")
    scheduler.add_job(
        run_data_retention,
        trigger=CronTrigger(hour=2, minute=0),   # 02:00 IST daily
        id="dpdp_retention",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    scheduler.start()
    app.state.retention_scheduler = scheduler
    logger.info("retention_scheduler_started", extra={"schedule": "daily 02:00 IST"})
    return scheduler


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    from dotenv import load_dotenv
    load_dotenv()
    logging.basicConfig(level=logging.INFO)

    print("Running DPDP data retention job...")
    result = run_data_retention()
    print(f"Done: {result}")
