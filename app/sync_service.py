import threading
import time
import datetime
import logging
from sqlalchemy.orm import Session
from database import SessionLocal
import models
from offline_queue import get_pending, remove, mark_error, is_postgres_alive, count_pending

logger = logging.getLogger("libcounterai.sync")

SYNC_INTERVAL_SECONDS = 15
MAX_RETRIES = 10
_running = False
_last_sync_at = None


def _replay_op(op: dict, db: Session) -> bool:
    table = op["table_name"]
    op_type = op["operation"]
    data = op["data"]

    try:
        if table == "events":
            if op_type == "INSERT":
                event = models.Event(
                    event_type=data["event_type"],
                    identity_type=data.get("identity_type", "UNKNOWN"),
                    person_id=data.get("person_id"),
                    unknown_id=data.get("unknown_id"),
                    track_id=data["track_id"],
                    camera_id=data["camera_id"],
                    confidence=data.get("confidence", 0.9),
                    timestamp=datetime.datetime.fromisoformat(data["timestamp"]) if isinstance(data.get("timestamp"), str) else datetime.datetime.now(datetime.timezone.utc),
                    metadata_json=data.get("metadata_json"),
                )
                db.add(event)
                db.flush()
                if data.get("visit_session_data"):
                    vsd = data["visit_session_data"]
                    existing = db.query(models.VisitSession).filter_by(id=vsd.get("existing_session_id")).first() if vsd.get("existing_session_id") else None
                    if existing:
                        for k, v in vsd.items():
                            if k != "existing_session_id":
                                setattr(existing, k, v)
                    elif vsd.get("identity_type"):
                        sess = models.VisitSession(
                            identity_type=vsd["identity_type"],
                            person_id=vsd.get("person_id"),
                            unknown_id=vsd.get("unknown_id"),
                            entry_camera_id=vsd.get("entry_camera_id"),
                            entry_event_id=vsd.get("entry_event_id"),
                            entry_at=datetime.datetime.fromisoformat(vsd["entry_at"]) if isinstance(vsd.get("entry_at"), str) else datetime.datetime.now(datetime.timezone.utc),
                            status=vsd.get("status", "ACTIVE"),
                        )
                        db.add(sess)
                db.commit()

        elif table == "visit_sessions":
            if op_type == "UPDATE":
                sess = db.query(models.VisitSession).filter_by(id=data["id"]).first()
                if sess:
                    for k, v in data.items():
                        if k != "id" and v is not None:
                            setattr(sess, k, v)
                    db.commit()

        elif table == "unknown_identities":
            if op_type == "INSERT":
                unk = models.UnknownIdentity(
                    anonymous_code=data["anonymous_code"],
                    embedding_vector=data["embedding_vector"],
                    expire_at=datetime.datetime.fromisoformat(data["expire_at"]) if isinstance(data.get("expire_at"), str) else datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=24),
                    status=data.get("status", "ACTIVE"),
                    visit_count=data.get("visit_count", 1),
                    created_at=datetime.datetime.fromisoformat(data["created_at"]) if isinstance(data.get("created_at"), str) else datetime.datetime.now(datetime.timezone.utc),
                    last_seen_at=datetime.datetime.fromisoformat(data["last_seen_at"]) if isinstance(data.get("last_seen_at"), str) else datetime.datetime.now(datetime.timezone.utc),
                )
                db.add(unk)
                db.commit()

        elif table == "persons":
            if op_type == "INSERT":
                person = models.Person(
                    full_name=data["full_name"],
                    member_code=data["member_code"],
                    role=data["role"],
                    status=data.get("status", "ACTIVE"),
                )
                db.add(person)
                db.flush()
                if data.get("face_template"):
                    ft = data["face_template"]
                    face = models.FaceTemplate(
                        person_id=person.id,
                        embedding_vector=ft["embedding_vector"],
                        model_name=ft.get("model_name", "sface"),
                        model_version=ft.get("model_version", "2021dec"),
                        quality_score=ft.get("quality_score", 1.0),
                        source_type=ft.get("source_type", "UPLOAD"),
                        is_active=True,
                    )
                    db.add(face)
                db.commit()

        logger.info(f"Replayed {op_type} on {table} (op #{op['id']})")
        return True

    except Exception as e:
        logger.warning(f"Failed to replay op #{op['id']} ({op_type} {table}): {e}")
        return False


def sync_loop():
    global _last_sync_at, _running
    _running = True
    logger.info("Sync worker started")
    while _running:
        try:
            if is_postgres_alive():
                ops = get_pending()
                if ops:
                    db = SessionLocal()
                    try:
                        for op in ops:
                            ok = _replay_op(op, db)
                            if ok:
                                remove(op["id"])
                                _last_sync_at = datetime.datetime.now(datetime.timezone.utc)
                            else:
                                mark_error(op["id"], "replay_failed")
                                if op["retries"] >= MAX_RETRIES:
                                    logger.warning(f"Op #{op['id']} exceeded max retries, removing")
                                    remove(op["id"])
                    finally:
                        db.close()
        except Exception as e:
            logger.error(f"Sync loop error: {e}")
        time.sleep(SYNC_INTERVAL_SECONDS)
    _running = False


def start():
    thread = threading.Thread(target=sync_loop, daemon=True)
    thread.start()
    return thread


def stop():
    global _running
    _running = False


def get_status():
    return {
        "pending_count": count_pending(),
        "postgres_alive": is_postgres_alive(),
        "running": _running,
        "last_sync_at": _last_sync_at.isoformat() if _last_sync_at else None,
    }
