import argparse
import datetime
import os
import sys

from sqlalchemy import text


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_DIR = os.path.join(ROOT_DIR, "app")
sys.path.insert(0, APP_DIR)

from database import DATABASE_URL, Base, SessionLocal, engine  # noqa: E402
import models  # noqa: E402,F401

DEMO_CAMERA_NAME = "Demo Gate"
DEMO_UNKNOWN_CODE = "UNKNOWN_DEMO_0001"
DEMO_MEMBER_CODES = ["DEMO-STUDENT-001", "DEMO-FACULTY-001"]
DEMO_TRACK_BASE = 9000

DEMO_PEOPLE = [
    {
        "full_name": "Nguyen Minh Demo",
        "member_code": "DEMO-STUDENT-001",
        "role": "STUDENT",
        "vector_seed": 0.12,
    },
    {
        "full_name": "Tran Thu Demo",
        "member_code": "DEMO-FACULTY-001",
        "role": "FACULTY",
        "vector_seed": 0.42,
    },
]


def display_url(url: str) -> str:
    if "://" not in url:
        return url
    scheme, rest = url.split("://", 1)
    if "@" in rest and ":" in rest.split("@", 1)[0]:
        credentials, host = rest.split("@", 1)
        user = credentials.split(":", 1)[0]
        return f"{scheme}://{user}:***@{host}"
    return url


def demo_vector(seed: float) -> list[float]:
    return [round(seed + (index * 0.001), 6) for index in range(128)]


def noon_today_utc() -> datetime.datetime:
    vn_tz = datetime.timezone(datetime.timedelta(hours=7))
    vn_noon = datetime.datetime.now(vn_tz).replace(
        hour=12, minute=0, second=0, microsecond=0,
    )
    return vn_noon.astimezone(datetime.timezone.utc)


def ensure_demo_camera(db):
    camera = db.query(models.Camera).filter_by(name=DEMO_CAMERA_NAME).first()
    if camera is None:
        camera = models.Camera(
            name=DEMO_CAMERA_NAME,
            source_type="RTSP",
            source_url="rtsp://demo.local/library",
            status="OFFLINE",
        )
        db.add(camera)
        db.flush()
        print(f"Seeded demo camera: {DEMO_CAMERA_NAME}.")
    else:
        camera.source_type = "RTSP"
        camera.source_url = "rtsp://demo.local/library"
        camera.status = "OFFLINE"
        print(f"Demo camera refreshed: {DEMO_CAMERA_NAME}.")

    if camera.config is None:
        camera.config = models.CameraConfig(
            entry_line_config=[[80, 320], [560, 320]],
            exit_line_config=[[80, 320], [560, 320]],
            inside_zone_config=[[80, 0], [560, 0], [560, 320], [80, 320]],
            outside_zone_config=[[80, 320], [560, 320], [560, 480], [80, 480]],
            roi_config=[[0, 0], [640, 0], [640, 480], [0, 480]],
            debounce_seconds=5,
            person_detection_confidence=0.5,
            face_detection_confidence=0.6,
            recognition_threshold=0.6,
            unknown_threshold=0.55,
        )
    else:
        camera.config.entry_line_config = [[80, 320], [560, 320]]
        camera.config.exit_line_config = [[80, 320], [560, 320]]
        camera.config.inside_zone_config = [[80, 0], [560, 0], [560, 320], [80, 320]]
        camera.config.outside_zone_config = [[80, 320], [560, 320], [560, 480], [80, 480]]
        camera.config.roi_config = [[0, 0], [640, 0], [640, 480], [0, 480]]

    db.flush()
    return camera


def ensure_demo_people(db):
    people = []
    for spec in DEMO_PEOPLE:
        person = db.query(models.Person).filter_by(member_code=spec["member_code"]).first()
        if person is None:
            person = models.Person(
                full_name=spec["full_name"],
                member_code=spec["member_code"],
                role=spec["role"],
                status="ACTIVE",
            )
            db.add(person)
            db.flush()
            print(f"Seeded demo person: {spec['member_code']}.")
        else:
            person.full_name = spec["full_name"]
            person.role = spec["role"]
            person.status = "ACTIVE"
            print(f"Demo person refreshed: {spec['member_code']}.")

        template = (
            db.query(models.FaceTemplate)
            .filter_by(person_id=person.id, model_name="sface", model_version="demo")
            .first()
        )
        if template is None:
            template = models.FaceTemplate(
                person_id=person.id,
                embedding_vector=demo_vector(spec["vector_seed"]),
                model_name="sface",
                model_version="demo",
                quality_score=0.95,
                source_type="UPLOAD",
                is_active=True,
            )
            db.add(template)
        else:
            template.embedding_vector = demo_vector(spec["vector_seed"])
            template.quality_score = 0.95
            template.source_type = "UPLOAD"
            template.is_active = True
        people.append(person)

    db.flush()
    return people


def ensure_demo_unknown(db, now: datetime.datetime):
    unknown = db.query(models.UnknownIdentity).filter_by(anonymous_code=DEMO_UNKNOWN_CODE).first()
    if unknown is None:
        unknown = models.UnknownIdentity(
            anonymous_code=DEMO_UNKNOWN_CODE,
            embedding_vector=demo_vector(0.72),
            first_seen_at=now - datetime.timedelta(hours=3),
            last_seen_at=now - datetime.timedelta(minutes=25),
            visit_count=2,
            expire_at=now + datetime.timedelta(hours=24),
            status="ACTIVE",
            created_at=now - datetime.timedelta(hours=3),
        )
        db.add(unknown)
        print(f"Seeded demo unknown identity: {DEMO_UNKNOWN_CODE}.")
    else:
        unknown.embedding_vector = demo_vector(0.72)
        unknown.first_seen_at = now - datetime.timedelta(hours=3)
        unknown.last_seen_at = now - datetime.timedelta(minutes=25)
        unknown.visit_count = 2
        unknown.expire_at = now + datetime.timedelta(hours=24)
        unknown.status = "ACTIVE"
        print(f"Demo unknown identity refreshed: {DEMO_UNKNOWN_CODE}.")

    db.flush()
    return unknown


def clear_demo_activity(db, camera, people, unknown) -> None:
    person_ids = [person.id for person in people]
    db.query(models.VisitSession).filter(
        models.VisitSession.entry_camera_id == camera.id,
        models.VisitSession.person_id.in_(person_ids),
    ).delete(synchronize_session=False)
    db.query(models.VisitSession).filter(
        models.VisitSession.entry_camera_id == camera.id,
        models.VisitSession.unknown_id == unknown.id,
    ).delete(synchronize_session=False)
    db.query(models.Event).filter(
        models.Event.camera_id == camera.id,
        models.Event.person_id.in_(person_ids),
    ).delete(synchronize_session=False)
    db.query(models.Event).filter(
        models.Event.camera_id == camera.id,
        models.Event.unknown_id == unknown.id,
    ).delete(synchronize_session=False)
    db.flush()


def add_demo_event(db, *, camera, event_type, identity_type, timestamp, track_id, person=None, unknown=None, confidence=0.9):
    event = models.Event(
        event_type=event_type,
        identity_type=identity_type,
        person_id=person.id if person else None,
        unknown_id=unknown.id if unknown else None,
        track_id=track_id,
        camera_id=camera.id,
        timestamp=timestamp,
        confidence=confidence,
        metadata_json={"demo_seed": True},
    )
    db.add(event)
    db.flush()
    return event


def add_demo_session(
    db,
    *,
    camera,
    identity_type,
    entry_event,
    entry_at,
    exit_event=None,
    exit_at=None,
    person=None,
    unknown=None,
    confidence_avg=0.9,
):
    session = models.VisitSession(
        identity_type=identity_type,
        person_id=person.id if person else None,
        unknown_id=unknown.id if unknown else None,
        entry_camera_id=camera.id,
        entry_event_id=entry_event.id,
        exit_camera_id=camera.id if exit_event else None,
        exit_event_id=exit_event.id if exit_event else None,
        entry_at=entry_at,
        exit_at=exit_at,
        duration_seconds=int((exit_at - entry_at).total_seconds()) if exit_at else None,
        status="CLOSED" if exit_event else "ACTIVE",
        confidence_avg=confidence_avg,
    )
    db.add(session)


def seed_demo_data() -> None:
    db = SessionLocal()
    now = noon_today_utc()
    try:
        camera = ensure_demo_camera(db)
        people = ensure_demo_people(db)
        unknown = ensure_demo_unknown(db, now)
        clear_demo_activity(db, camera, people, unknown)

        student_entry = add_demo_event(
            db,
            camera=camera,
            event_type="ENTRY",
            identity_type="KNOWN",
            person=people[0],
            track_id=DEMO_TRACK_BASE + 1,
            timestamp=now - datetime.timedelta(hours=3),
            confidence=0.97,
        )
        student_exit = add_demo_event(
            db,
            camera=camera,
            event_type="EXIT",
            identity_type="KNOWN",
            person=people[0],
            track_id=DEMO_TRACK_BASE + 1,
            timestamp=now - datetime.timedelta(hours=2, minutes=5),
            confidence=0.96,
        )
        add_demo_session(
            db,
            camera=camera,
            identity_type="KNOWN",
            person=people[0],
            entry_event=student_entry,
            exit_event=student_exit,
            entry_at=student_entry.timestamp,
            exit_at=student_exit.timestamp,
            confidence_avg=0.965,
        )

        faculty_entry = add_demo_event(
            db,
            camera=camera,
            event_type="ENTRY",
            identity_type="KNOWN",
            person=people[1],
            track_id=DEMO_TRACK_BASE + 2,
            timestamp=now - datetime.timedelta(minutes=55),
            confidence=0.94,
        )
        add_demo_session(
            db,
            camera=camera,
            identity_type="KNOWN",
            person=people[1],
            entry_event=faculty_entry,
            entry_at=faculty_entry.timestamp,
            confidence_avg=0.94,
        )

        unknown_entry = add_demo_event(
            db,
            camera=camera,
            event_type="ENTRY",
            identity_type="UNKNOWN",
            unknown=unknown,
            track_id=DEMO_TRACK_BASE + 3,
            timestamp=now - datetime.timedelta(hours=1, minutes=35),
            confidence=0.88,
        )
        unknown_exit = add_demo_event(
            db,
            camera=camera,
            event_type="EXIT",
            identity_type="UNKNOWN",
            unknown=unknown,
            track_id=DEMO_TRACK_BASE + 3,
            timestamp=now - datetime.timedelta(minutes=50),
            confidence=0.86,
        )
        add_demo_session(
            db,
            camera=camera,
            identity_type="UNKNOWN",
            unknown=unknown,
            entry_event=unknown_entry,
            exit_event=unknown_exit,
            entry_at=unknown_entry.timestamp,
            exit_at=unknown_exit.timestamp,
            confidence_avg=0.87,
        )

        unknown_reentry = add_demo_event(
            db,
            camera=camera,
            event_type="ENTRY",
            identity_type="UNKNOWN",
            unknown=unknown,
            track_id=DEMO_TRACK_BASE + 4,
            timestamp=now - datetime.timedelta(minutes=25),
            confidence=0.9,
        )
        add_demo_session(
            db,
            camera=camera,
            identity_type="UNKNOWN",
            unknown=unknown,
            entry_event=unknown_reentry,
            entry_at=unknown_reentry.timestamp,
            confidence_avg=0.9,
        )

        for idx, (action, entity_type, detail) in enumerate([
            ("retention_purge", "expire_unknowns", {"rows_affected": 3, "dry_run": False}),
            ("retention_purge", "purge_events", {"rows_affected": 42, "dry_run": False}),
            ("staff_enroll", "persons", {"person_name": "Nguyen Minh Demo"}),
        ]):
            db.add(models.AuditLog(
                action=action,
                entity_type=entity_type,
                actor="SYSTEM",
                details=detail,
                created_at=now - datetime.timedelta(hours=1, minutes=idx * 15),
            ))
        db.commit()
        print("Demo seed data is ready: 1 camera, 2 persons, 1 unknown identity, 6 events, 4 sessions, 3 audit log entries.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def ensure_postgres_vector_support() -> None:
    if engine.dialect.name != "postgresql":
        return

    try:
        import pgvector.sqlalchemy  # noqa: F401
    except ImportError as exc:
        raise SystemExit(
            "PostgreSQL setup requires the Python package 'pgvector'. "
            "Run the script with the project venv or install app/requirements.txt first."
        ) from exc

    with engine.begin() as connection:
        print("Ensuring PostgreSQL pgvector extension...")
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))


def ensure_postgres_vector_indexes() -> None:
    if engine.dialect.name != "postgresql":
        return

    with engine.begin() as connection:
        print("Ensuring pgvector HNSW indexes...")
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_face_templates_embedding_hnsw "
                "ON face_templates USING hnsw (embedding_vector vector_cosine_ops)"
            )
        )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_unknown_identities_embedding_hnsw "
                "ON unknown_identities USING hnsw (embedding_vector vector_cosine_ops)"
            )
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Create LibCounterAI database tables.")
    parser.add_argument("--seed-demo", action="store_true", help="Insert or refresh demo camera, persons, sessions, and analytics data.")
    parser.add_argument("--require-postgres", action="store_true", help="Fail if DATABASE_URL/POSTGRES_* did not select PostgreSQL.")
    args = parser.parse_args()

    print(f"Database URL: {display_url(DATABASE_URL)}")
    print(f"Database dialect: {engine.dialect.name}")
    if args.require_postgres and engine.dialect.name != "postgresql":
        raise SystemExit("PostgreSQL is required, but the configured database is not PostgreSQL.")

    ensure_postgres_vector_support()
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables are ready.")
    ensure_postgres_vector_indexes()

    if args.seed_demo:
        seed_demo_data()


if __name__ == "__main__":
    main()
