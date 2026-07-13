import datetime
import os
import time
from typing import Any

from sqlalchemy.orm import Session

import models


# ── Configuration from env ──────────────────────────────────────────

def read_config() -> dict[str, int]:
    return {
        "event_days": int(os.getenv("RETENTION_EVENT_DAYS", "365")),
        "session_days": int(os.getenv("RETENTION_SESSION_DAYS", "365")),
        "unknown_expire_hours": int(os.getenv("UNKNOWN_IDENTITY_EXPIRE_HOURS", "24")),
        "unknown_purge_days": int(os.getenv("RETENTION_UNKNOWN_PURGE_DAYS", "30")),
        "template_grace_days": int(os.getenv("RETENTION_TEMPLATE_GRACE_DAYS", "90")),
        "audit_log_days": int(os.getenv("RETENTION_AUDIT_LOG_DAYS", "730")),
        "session_timeout_hours": int(os.getenv("UNKNOWN_IDENTITY_EXPIRE_HOURS", "24")) + 24,
    }


def _write_audit(
    db: Session,
    action: str,
    entity_type: str,
    entity_id: int | None = None,
    details: dict | None = None,
) -> None:
    try:
        db.add(models.AuditLog(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            actor="SYSTEM",
            details=details,
        ))
        db.commit()
    except Exception as exc:
        db.rollback()
        print(f"Audit log write failed for {action}: {exc}")


# ── Phase implementations ───────────────────────────────────────────

def phase_timeout_sessions(db: Session, cfg: dict[str, int], now: datetime.datetime) -> int:
    cutoff = now - datetime.timedelta(hours=cfg["session_timeout_hours"])
    expired = (
        db.query(models.VisitSession)
        .filter(
            models.VisitSession.status == "ACTIVE",
            models.VisitSession.entry_at < cutoff,
        )
        .all()
    )
    count = 0
    for sess in expired:
        sess.status = "TIMEOUT"
        sess.exit_at = sess.entry_at
        sess.duration_seconds = 0
        count += 1
    if count:
        db.commit()
    return count


def phase_expire_unknowns(db: Session, cfg: dict[str, int], now: datetime.datetime) -> int:
    expired = (
        db.query(models.UnknownIdentity)
        .filter(
            models.UnknownIdentity.status == "ACTIVE",
            models.UnknownIdentity.expire_at <= now,
        )
        .all()
    )
    count = 0
    for unk in expired:
        unk.status = "EXPIRED"
        count += 1
    if count:
        db.commit()
    return count


def phase_purge_events(db: Session, cfg: dict[str, int], now: datetime.datetime) -> int:
    cutoff = now - datetime.timedelta(days=cfg["event_days"])
    count = (
        db.query(models.Event)
        .filter(models.Event.timestamp < cutoff)
        .delete(synchronize_session=False)
    )
    if count:
        db.commit()
    return count


def phase_purge_sessions(db: Session, cfg: dict[str, int], now: datetime.datetime) -> int:
    cutoff = now - datetime.timedelta(days=cfg["session_days"])
    count = (
        db.query(models.VisitSession)
        .filter(
            models.VisitSession.status.in_(["CLOSED", "TIMEOUT", "UNMATCHED"]),
            models.VisitSession.entry_at < cutoff,
        )
        .delete(synchronize_session=False)
    )
    if count:
        db.commit()
    return count


def phase_purge_templates(db: Session, cfg: dict[str, int], now: datetime.datetime) -> int:
    cutoff = now - datetime.timedelta(days=cfg["template_grace_days"])
    count = (
        db.query(models.FaceTemplate)
        .filter(
            models.FaceTemplate.is_active == False,
            models.FaceTemplate.created_at < cutoff,
        )
        .delete(synchronize_session=False)
    )
    if count:
        db.commit()
    return count


def phase_purge_expired_unknowns(db: Session, cfg: dict[str, int], now: datetime.datetime) -> int:
    cutoff = now - datetime.timedelta(days=cfg["unknown_purge_days"])
    count = (
        db.query(models.UnknownIdentity)
        .filter(
            models.UnknownIdentity.status == "EXPIRED",
            models.UnknownIdentity.expire_at < cutoff,
        )
        .delete(synchronize_session=False)
    )
    if count:
        db.commit()
    return count


def phase_purge_audit_log(db: Session, cfg: dict[str, int], now: datetime.datetime) -> int:
    cutoff = now - datetime.timedelta(days=cfg["audit_log_days"])
    count = (
        db.query(models.AuditLog)
        .filter(models.AuditLog.created_at < cutoff)
        .delete(synchronize_session=False)
    )
    if count:
        db.commit()
    return count


# ── Phase registry ──────────────────────────────────────────────────

PHASES = [
    ("timeout_stale_sessions", phase_timeout_sessions),
    ("expire_unknowns", phase_expire_unknowns),
    ("purge_events", phase_purge_events),
    ("purge_sessions", phase_purge_sessions),
    ("purge_templates", phase_purge_templates),
    ("purge_expired_unknowns", phase_purge_expired_unknowns),
    ("purge_audit_log", phase_purge_audit_log),
]


# ── Orchestrator ────────────────────────────────────────────────────

def _count_dry_run_phase(phase_name: str, db: Session, cfg: dict[str, int], now: datetime.datetime) -> int:
    if phase_name == "timeout_stale_sessions":
        cutoff = now - datetime.timedelta(hours=cfg["session_timeout_hours"])
        return db.query(models.VisitSession).filter(
            models.VisitSession.status == "ACTIVE",
            models.VisitSession.entry_at < cutoff,
        ).count()
    if phase_name == "expire_unknowns":
        return db.query(models.UnknownIdentity).filter(
            models.UnknownIdentity.status == "ACTIVE",
            models.UnknownIdentity.expire_at <= now,
        ).count()
    if phase_name == "purge_events":
        cutoff = now - datetime.timedelta(days=cfg["event_days"])
        return db.query(models.Event).filter(models.Event.timestamp < cutoff).count()
    if phase_name == "purge_sessions":
        cutoff = now - datetime.timedelta(days=cfg["session_days"])
        return db.query(models.VisitSession).filter(
            models.VisitSession.status.in_(["CLOSED", "TIMEOUT", "UNMATCHED"]),
            models.VisitSession.entry_at < cutoff,
        ).count()
    if phase_name == "purge_templates":
        cutoff = now - datetime.timedelta(days=cfg["template_grace_days"])
        return db.query(models.FaceTemplate).filter(
            models.FaceTemplate.is_active == False,
            models.FaceTemplate.created_at < cutoff,
        ).count()
    if phase_name == "purge_expired_unknowns":
        cutoff = now - datetime.timedelta(days=cfg["unknown_purge_days"])
        return db.query(models.UnknownIdentity).filter(
            models.UnknownIdentity.status == "EXPIRED",
            models.UnknownIdentity.expire_at < cutoff,
        ).count()
    if phase_name == "purge_audit_log":
        cutoff = now - datetime.timedelta(days=cfg["audit_log_days"])
        return db.query(models.AuditLog).filter(models.AuditLog.created_at < cutoff).count()
    return 0


def run_retention(
    db: Session,
    *,
    dry_run: bool = False,
    now: datetime.datetime | None = None,
) -> list[dict[str, Any]]:
    cfg = read_config()
    if now is None:
        now = datetime.datetime.now(datetime.timezone.utc)

    results: list[dict[str, Any]] = []

    for phase_name, phase_fn in PHASES:
        start = time.monotonic()
        rows_affected = 0
        error: str | None = None
        try:
            if dry_run:
                rows_affected = _count_dry_run_phase(phase_name, db, cfg, now)
            else:
                rows_affected = phase_fn(db, cfg, now)
                if rows_affected:
                    _write_audit(
                        db,
                        action="retention_purge",
                        entity_type=phase_name,
                        details={
                            "rows_affected": rows_affected,
                            "dry_run": dry_run,
                            "duration_ms": int((time.monotonic() - start) * 1000),
                        },
                    )
        except Exception as exc:
            error = str(exc)
            if not dry_run:
                _write_audit(
                    db,
                    action="retention_error",
                    entity_type=phase_name,
                    details={"error": error},
                )

        elapsed_ms = int((time.monotonic() - start) * 1000)
        results.append({
            "phase": phase_name,
            "rows_affected": rows_affected,
            "dry_run": dry_run,
            "duration_ms": elapsed_ms,
            "error": error,
        })

    return results


def count_pending(db: Session) -> dict[str, int]:
    cfg = read_config()
    now = datetime.datetime.now(datetime.timezone.utc)

    return {
        "active_unknowns": db.query(models.UnknownIdentity).filter_by(status="ACTIVE").count(),
        "expired_unknowns_pending_purge": (
            db.query(models.UnknownIdentity)
            .filter(
                models.UnknownIdentity.status == "EXPIRED",
                models.UnknownIdentity.expire_at < now - datetime.timedelta(days=cfg["unknown_purge_days"]),
            )
            .count()
        ),
        "events_older_than_retention": (
            db.query(models.Event)
            .filter(models.Event.timestamp < now - datetime.timedelta(days=cfg["event_days"]))
            .count()
        ),
        "sessions_older_than_retention": (
            db.query(models.VisitSession)
            .filter(
                models.VisitSession.status.in_(["CLOSED", "TIMEOUT", "UNMATCHED"]),
                models.VisitSession.entry_at < now - datetime.timedelta(days=cfg["session_days"]),
            )
            .count()
        ),
        "inactive_templates_pending_purge": (
            db.query(models.FaceTemplate)
            .filter(
                models.FaceTemplate.is_active == False,
                models.FaceTemplate.created_at < now - datetime.timedelta(days=cfg["template_grace_days"]),
            )
            .count()
        ),
        "audit_log_rows": db.query(models.AuditLog).count(),
    }
