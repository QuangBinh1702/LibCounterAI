import os
import sys
import datetime

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_DIR = os.path.join(ROOT_DIR, "app")
sys.path.insert(0, APP_DIR)

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from database import SessionLocal, engine
import database
from main import app
import models
from retention import run_retention, count_pending


REFERENCE_DATE = datetime.datetime(2024, 6, 1, tzinfo=datetime.timezone.utc)
NOW = datetime.datetime(2026, 7, 13, 12, 0, 0, tzinfo=datetime.timezone.utc)


def seed_test_data(db: Session) -> dict:
    camera = models.Camera(
        name="Retention Test Cam",
        source_type="FILE",
        source_url="/dev/null",
        status="OFFLINE",
    )
    db.add(camera)
    db.flush()

    old_camera_config = None
    camera.config = models.CameraConfig(
        entry_line_config=[[0, 0], [1, 1]],
        exit_line_config=[[0, 0], [1, 1]],
    )

    old_person = models.Person(
        full_name="Old Person",
        member_code="OLD-RETENTION-001",
        role="STUDENT",
        status="INACTIVE",
    )
    old_person2 = models.Person(
        full_name="Active Person",
        member_code="ACTIVE-RETENTION-002",
        role="STUDENT",
        status="ACTIVE",
    )
    db.add(old_person)
    db.add(old_person2)
    db.flush()

    old_template = models.FaceTemplate(
        person_id=old_person.id,
        embedding_vector=[0.1] * 128,
        model_name="sface",
        model_version="demo",
        quality_score=0.9,
        source_type="UPLOAD",
        is_active=False,
        created_at=REFERENCE_DATE,
    )
    db.add(old_template)

    active_template = models.FaceTemplate(
        person_id=old_person2.id,
        embedding_vector=[0.2] * 128,
        model_name="sface",
        model_version="demo",
        quality_score=0.9,
        source_type="UPLOAD",
        is_active=True,
        created_at=NOW,
    )
    db.add(active_template)

    old_unknown = models.UnknownIdentity(
        anonymous_code="OLD_UNKNOWN_001",
        embedding_vector=[0.3] * 128,
        first_seen_at=REFERENCE_DATE,
        last_seen_at=REFERENCE_DATE,
        visit_count=1,
        expire_at=REFERENCE_DATE,
        status="EXPIRED",
        created_at=REFERENCE_DATE,
    )
    db.add(old_unknown)

    active_unknown = models.UnknownIdentity(
        anonymous_code="ACTIVE_UNKNOWN_001",
        embedding_vector=[0.4] * 128,
        first_seen_at=NOW - datetime.timedelta(hours=1),
        last_seen_at=NOW,
        visit_count=1,
        expire_at=NOW + datetime.timedelta(hours=24),
        status="ACTIVE",
        created_at=NOW - datetime.timedelta(hours=1),
    )
    db.add(active_unknown)

    expired_unknown_recent = models.UnknownIdentity(
        anonymous_code="RECENT_EXPIRED_UNKNOWN",
        embedding_vector=[0.5] * 128,
        first_seen_at=NOW - datetime.timedelta(hours=2),
        last_seen_at=NOW - datetime.timedelta(hours=1),
        visit_count=1,
        expire_at=NOW - datetime.timedelta(hours=1),
        status="EXPIRED",
        created_at=NOW - datetime.timedelta(hours=2),
    )
    db.add(expired_unknown_recent)

    for i in range(10):
        db.add(models.Event(
            event_type="ENTRY",
            identity_type="KNOWN",
            track_id=8000 + i,
            camera_id=camera.id,
            timestamp=REFERENCE_DATE,
            confidence=0.9,
        ))

    for i in range(5):
        db.add(models.Event(
            event_type="ENTRY",
            identity_type="KNOWN",
            track_id=8100 + i,
            camera_id=camera.id,
            timestamp=NOW,
            confidence=0.9,
        ))

    stale_session = models.VisitSession(
        identity_type="UNKNOWN",
        unknown_id=old_unknown.id,
        entry_camera_id=camera.id,
        entry_at=REFERENCE_DATE,
        status="ACTIVE",
    )
    db.add(stale_session)

    old_closed_session = models.VisitSession(
        identity_type="KNOWN",
        person_id=old_person.id,
        entry_camera_id=camera.id,
        entry_at=REFERENCE_DATE,
        exit_at=REFERENCE_DATE + datetime.timedelta(hours=1),
        duration_seconds=3600,
        status="CLOSED",
    )
    db.add(old_closed_session)

    recent_closed_session = models.VisitSession(
        identity_type="KNOWN",
        person_id=old_person2.id,
        entry_camera_id=camera.id,
        entry_at=NOW - datetime.timedelta(hours=2),
        exit_at=NOW - datetime.timedelta(hours=1),
        duration_seconds=3600,
        status="CLOSED",
    )
    db.add(recent_closed_session)

    for i in range(40):
        db.add(models.AuditLog(
            action="retention_purge",
            entity_type="audit_log",
            actor="SYSTEM",
            details={"rows_purged": i},
            created_at=REFERENCE_DATE,
        ))

    for i in range(10):
        db.add(models.AuditLog(
            action="test_action",
            entity_type="test",
            actor="SYSTEM",
            details={"test": i},
            created_at=NOW,
        ))

    db.commit()

    return {
        "camera_id": camera.id,
        "old_person_id": old_person.id,
        "old_person2_id": old_person2.id,
        "old_template_id": old_template.id,
        "old_unknown_id": old_unknown.id,
    }


def run_tests() -> int:
    failures = 0

    def check(name: str, ok: bool):
        nonlocal failures
        if ok:
            print(f"  PASS  {name}")
        else:
            print(f"  FAIL  {name}")
            failures += 1

    database.Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    db_check = SessionLocal()
    try:
        ids = seed_test_data(db)
        db_check.close()
        db_check = SessionLocal()

        # Run dry-run BEFORE real run so data is still fresh
        print("\n  Dry run test...")
        db_dry = SessionLocal()
        try:
            counts_before = {
                "events": db_dry.query(models.Event).count(),
                "sessions": db_dry.query(models.VisitSession).count(),
                "unknowns": db_dry.query(models.UnknownIdentity).count(),
                "templates": db_dry.query(models.FaceTemplate).count(),
                "audit": db_dry.query(models.AuditLog).count(),
            }
            dry_results = run_retention(db_dry, dry_run=True, now=NOW)
            counts_after = {
                "events": db_dry.query(models.Event).count(),
                "sessions": db_dry.query(models.VisitSession).count(),
                "unknowns": db_dry.query(models.UnknownIdentity).count(),
                "templates": db_dry.query(models.FaceTemplate).count(),
                "audit": db_dry.query(models.AuditLog).count(),
            }
            dry_nonzero = sum(1 for r in dry_results if r["rows_affected"] > 0)
            check("Dry run reports rows to purge", dry_nonzero > 0)
            check("Dry run makes no changes",
                  counts_before == counts_after)
        finally:
            db_dry.close()

        results = run_retention(db, now=NOW)
        db_check.close()
        db_check = SessionLocal()

        results_by_phase = {r["phase"]: r for r in results}
        assert "timeout_stale_sessions" in results_by_phase
        assert "expire_unknowns" in results_by_phase
        assert "purge_events" in results_by_phase
        assert "purge_sessions" in results_by_phase
        assert "purge_templates" in results_by_phase
        assert "purge_expired_unknowns" in results_by_phase
        assert "purge_audit_log" in results_by_phase

        check("All 7 phases executed", len(results) == 7)

        audit_entries = db_check.query(models.AuditLog).filter(
            models.AuditLog.action == "retention_purge",
            models.AuditLog.entity_type != "audit_log",
        ).all()
        audit_phase_names = {e.entity_type for e in audit_entries}
        check("Audit written for purge phases",
              "purge_events" in audit_phase_names or
              any("purge" in (e.entity_type or "") for e in audit_entries))

        sessions = db_check.query(models.VisitSession).filter_by(status="ACTIVE").all()
        check("Stale session timed out",
              all(s.status != "ACTIVE" for s in sessions if hasattr(s, 'entry_at') and s.entry_at and s.entry_at < NOW - datetime.timedelta(hours=48)))

        events_old = db_check.query(models.Event).filter(models.Event.timestamp < REFERENCE_DATE + datetime.timedelta(days=1)).count()
        check("Old events purged", events_old == 0)

        events_new = db_check.query(models.Event).filter(models.Event.timestamp > NOW - datetime.timedelta(days=1)).count()
        check("Recent events kept", events_new == 5)

        templates_purged = db_check.query(models.FaceTemplate).filter_by(is_active=False).count()
        check("Inactive templates purged", templates_purged == 0)

        templates_active = db_check.query(models.FaceTemplate).filter_by(is_active=True).count()
        check("Active templates kept", templates_active == 1)

        old_expired_count = db_check.query(models.UnknownIdentity).filter(
            models.UnknownIdentity.status == "EXPIRED",
            models.UnknownIdentity.expire_at < NOW - datetime.timedelta(days=30),
        ).count()
        check("Old expired unknowns purged", old_expired_count == 0)

        active_unknowns = db_check.query(models.UnknownIdentity).filter_by(status="ACTIVE").count()
        check("Active unknowns kept", active_unknowns >= 1)

        recent_expired = db_check.query(models.UnknownIdentity).filter_by(anonymous_code="RECENT_EXPIRED_UNKNOWN").first()
        check("Recently expired unknown kept (grace)",
              recent_expired is not None and recent_expired.status == "EXPIRED")

        old_audit_remaining = db_check.query(models.AuditLog).filter(
            models.AuditLog.created_at < NOW - datetime.timedelta(days=700)
        ).count()
        check("Old audit log rows purged", old_audit_remaining == 0)

        print("\n  Idempotency test...")
        db3 = SessionLocal()
        try:
            db3_check = SessionLocal()
            results2 = run_retention(db3, now=NOW)
            second_affected = sum(r["rows_affected"] for r in results2)
            db3_check.close()
            db3_check.close()
            check("Second run reports 0 changes", second_affected == 0)
        finally:
            db3.close()

        print("\n  Empty database test...")
        from database import DATABASE_URL
        if DATABASE_URL.startswith("sqlite"):
            # Create a separate in-memory SQLite engine for empty db test
            from sqlalchemy import create_engine
            mem_engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
            database.Base.metadata.create_all(bind=mem_engine)
            from sqlalchemy.orm import sessionmaker
            MemSession = sessionmaker(bind=mem_engine)
            mem_db = MemSession()
            try:
                from retention import run_retention as rr
                empty_results = rr(mem_db, now=NOW)
                empty_total = sum(r["rows_affected"] for r in empty_results)
                check("Empty DB reports 0 changes", empty_total == 0)
                check("Empty DB no errors", all(r["error"] is None for r in empty_results))
            finally:
                mem_db.close()
                mem_engine.dispose()
        else:
            print("  SKIP  Empty DB test (not SQLite)")

        print("\n  API endpoint test...")
        with TestClient(app) as client:
            status_resp = client.get("/api/admin/retention/status",
                headers={"Authorization": "Bearer test"})
            if status_resp.status_code == 200:
                data = status_resp.json()
                check("Status endpoint returns config", "config" in data)
                check("Status endpoint returns counts", "counts" in data)
            else:
                check("Status endpoint returns 200 (or 401 expected without auth)",
                      status_resp.status_code in (200, 401))

        print(f"\n  Results: {len(results)} phases executed")

    finally:
        clean_db(db)
        db.close()

    return failures


def clean_db(db):
    db.query(models.AuditLog).delete()
    db.query(models.Event).delete()
    db.query(models.VisitSession).delete()
    db.query(models.FaceTemplate).delete()
    db.query(models.UnknownIdentity).delete()
    db.query(models.CameraConfig).delete()
    db.query(models.Camera).delete()
    db.query(models.Person).delete()
    db.commit()


def main():
    print("Retention validation...")

    from database import DATABASE_URL
    db_display = DATABASE_URL
    if "://" in db_display and "@" in db_display:
        scheme, rest = db_display.split("://", 1)
        user_pass, host = rest.split("@", 1)
        user = user_pass.split(":")[0]
        db_display = f"{scheme}://{user}:***@{host}"
    print(f"Database: {db_display}")

    failures = run_tests()

    if failures:
        print(f"\nRetention validation FAILED ({failures} failures).")
        sys.exit(1)
    else:
        print("\nRetention validation PASSED.")


if __name__ == "__main__":
    main()
