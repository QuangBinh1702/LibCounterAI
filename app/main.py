import os
import threading
import time
import datetime
import json
import logging
import traceback
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Generic, TypeVar

T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int

def paginate(query, skip: int = 0, limit: int = 100):
    total = query.count()
    items = query.offset(skip).limit(limit).all()
    return items, total
from sqlalchemy.orm import Session, joinedload
import cv2
import numpy as np

from detector import YOLOv8Detector
from tracker import IoUTracker
from face_pipeline import FacePipeline
from database import get_db
import models
from offline_queue import enqueue as offline_enqueue, count_pending as offline_count
import sync_service

app = FastAPI(
    title="LibCounterAI Backend API",
    description="Backend API for Visitor Recognition and Counting System",
    version="0.1.0"
)

# Enable CORS for frontend.
# CORS_ORIGINS: comma-separated list of allowed origins, or "*" for all.
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")
origins = [o.strip() for o in CORS_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=origins != ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize detector globally
detector = None
face_pipeline = None
session_trackers = {}
face_template_cache = {"loaded_at": 0.0, "items": []}
FACE_TEMPLATE_CACHE_TTL_SECONDS = 10.0

# Retention & privacy config
UNKNOWN_IDENTITY_EXPIRE_HOURS = int(os.getenv("UNKNOWN_IDENTITY_EXPIRE_HOURS", "24"))
UNKNOWN_EXPIRED_GRACE_HOURS = int(os.getenv("UNKNOWN_EXPIRED_GRACE_HOURS", "72"))
RETENTION_CLEANUP_INTERVAL_SECONDS = int(os.getenv("RETENTION_CLEANUP_INTERVAL_SECONDS", "3600"))
AUDIT_LOG_ENABLED = os.getenv("AUDIT_LOG_ENABLED", "true").lower() == "true"
MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "10"))
RETENTION_EVENT_DAYS = int(os.getenv("RETENTION_EVENT_DAYS", "365"))
RETENTION_SESSION_DAYS = int(os.getenv("RETENTION_SESSION_DAYS", "365"))
RETENTION_UNKNOWN_PURGE_DAYS = int(os.getenv("RETENTION_UNKNOWN_PURGE_DAYS", "30"))
RETENTION_TEMPLATE_GRACE_DAYS = int(os.getenv("RETENTION_TEMPLATE_GRACE_DAYS", "90"))
RETENTION_AUDIT_LOG_DAYS = int(os.getenv("RETENTION_AUDIT_LOG_DAYS", "730"))

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/bmp"}
ALLOWED_PERSON_ROLES = {"STUDENT", "FACULTY", "STAFF", "GUEST"}
ALLOWED_USER_ROLES = {"ADMIN", "LIBRARIAN"}


logger = logging.getLogger("libcounterai")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def utc_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


VIETNAM_TZ = datetime.timezone(datetime.timedelta(hours=7), name="Asia/Ho_Chi_Minh")


def as_vietnam_time(value: datetime.datetime) -> datetime.datetime:
    """Normalize a stored UTC timestamp to the local timezone used by reports."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=datetime.timezone.utc)
    return value.astimezone(VIETNAM_TZ)


def local_day_start_as_utc(value: datetime.datetime) -> datetime.datetime:
    """Convert a Vietnam-local midnight to a UTC-naive DB query boundary."""
    local_value = value.replace(tzinfo=VIETNAM_TZ)
    return local_value.astimezone(datetime.timezone.utc).replace(tzinfo=None)


def log_info(message: str) -> None:
    """Log without crashing on Windows consoles that cannot encode Vietnamese."""
    try:
        logger.info(message)
    except UnicodeEncodeError:
        logger.info(message.encode("ascii", errors="replace").decode("ascii"))

def audit_log(
    db: Session | None,
    action: str,
    entity_type: str,
    entity_id: int | None = None,
    actor: str | None = None,
    details: dict | None = None,
    ip_address: str | None = None,
) -> None:
    if not AUDIT_LOG_ENABLED:
        return
    try:
        if db is None:
            from database import SessionLocal as _SL
            _db = _SL()
            close = True
        else:
            _db = db
            close = False
        _db.add(models.AuditLog(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            actor=actor,
            details=details,
            ip_address=ip_address,
        ))
        _db.commit()
        if close:
            _db.close()
    except Exception as e:
        log_info(f"Audit log failed: {e}")


def cors_headers(request: Request) -> dict:
    origin = request.headers.get("origin") or "*"
    return {
        "Access-Control-Allow-Origin": origin,
        "Access-Control-Allow-Methods": "*",
        "Access-Control-Allow-Headers": "*",
        "Vary": "Origin",
    }


def elapsed_seconds(start: datetime.datetime, end: datetime.datetime) -> int:
    if start.tzinfo is None:
        start = start.replace(tzinfo=datetime.timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=datetime.timezone.utc)
    return int((end - start).total_seconds())


def parse_bool(value, default=False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def parse_float(value, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default

async def validate_image_file(file: UploadFile) -> bytes:
    if file.content_type:
        if not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail=f"Invalid content type: {file.content_type}. Only image files are allowed.")
        if file.content_type not in ALLOWED_IMAGE_TYPES:
            allowed = ", ".join(sorted(ALLOWED_IMAGE_TYPES))
            raise HTTPException(status_code=400, detail=f"Unsupported image type: {file.content_type}. Allowed: {allowed}.")
    contents = await file.read()
    size_mb = len(contents) / (1024 * 1024)
    if size_mb > MAX_UPLOAD_SIZE_MB:
        raise HTTPException(status_code=400, detail=f"File too large ({size_mb:.1f} MB). Maximum is {MAX_UPLOAD_SIZE_MB} MB.")
    if len(contents) < 32:
        raise HTTPException(status_code=400, detail="File is empty or too small.")
    magic = contents[:8]
    if not any((
        magic[:2] == b'\xff\xd8',
        magic[:4] == b'\x89PNG',
        magic[:4] == b'RIFF',
        magic[:2] == b'BM',
    )):
        raise HTTPException(status_code=400, detail=f"Invalid image signature. Expected JPEG, PNG, WEBP, or BMP.")
    return contents


def invalidate_face_template_cache() -> None:
    face_template_cache["loaded_at"] = 0.0
    face_template_cache["items"] = []


def _queue_event(direction, identity_type, person_id, unknown_id, track_id, camera_id, confidence, metadata, session_event=None, session_data=None):
    data = {
        "event_type": direction,
        "identity_type": identity_type,
        "person_id": person_id,
        "unknown_id": unknown_id,
        "track_id": track_id,
        "camera_id": camera_id,
        "confidence": float(confidence),
        "timestamp": utc_now().isoformat(),
        "metadata_json": metadata,
        "session_event": session_event,
        "visit_session_data": session_data,
    }
    offline_enqueue("events", "INSERT", data)


def _queue_unknown_identity(now, anonymous_code, embedding, count_today, expire_hours=24):
    data = {
        "anonymous_code": anonymous_code,
        "embedding_vector": embedding,
        "expire_at": (now + datetime.timedelta(hours=expire_hours)).isoformat(),
        "status": "ACTIVE",
        "visit_count": 1,
        "created_at": now.isoformat(),
        "last_seen_at": now.isoformat(),
    }
    offline_enqueue("unknown_identities", "INSERT", data)


def _queue_person(full_name, member_code, role, status_str, embedding, face_score):
    data = {
        "full_name": full_name,
        "member_code": member_code,
        "role": role,
        "status": status_str,
        "face_template": {
            "embedding_vector": embedding,
            "quality_score": face_score,
        },
    }
    offline_enqueue("persons", "INSERT", data)




def load_active_face_templates(db: Session, *, force_refresh: bool = False):
    now = time.monotonic()
    cache_age = now - float(face_template_cache["loaded_at"])
    if (
        not force_refresh
        and float(face_template_cache["loaded_at"]) > 0
        and cache_age < FACE_TEMPLATE_CACHE_TTL_SECONDS
    ):
        return face_template_cache["items"]

    templates = (
        db.query(models.FaceTemplate)
        .options(joinedload(models.FaceTemplate.person))
        .filter_by(is_active=True)
        .all()
    )
    parsed_templates = []
    for template in templates:
        if not template.embedding_vector:
            continue
        person_name = (
            template.person.full_name
            if template.person is not None
            else f"person_{template.person_id}"
        )
        parsed_templates.append({
            "person_id": template.person_id,
            "person_name": person_name,
            "vector": np.array(template.embedding_vector, dtype=np.float32),
        })

    face_template_cache["loaded_at"] = now
    face_template_cache["items"] = parsed_templates
    return parsed_templates


def identity_from_visit_session(session: models.VisitSession):
    if session.identity_type == "KNOWN" and session.person_id is not None:
        return {
            "identity_type": "KNOWN",
            "person_id": session.person_id,
            "unknown_id": None,
            "person_name": session.person.full_name if session.person else f"person_{session.person_id}",
        }
    if session.identity_type == "UNKNOWN" and session.unknown_id is not None:
        return {
            "identity_type": "UNKNOWN",
            "person_id": None,
            "unknown_id": session.unknown_id,
            "person_name": (
                session.unknown_identity.anonymous_code
                if session.unknown_identity
                else f"UNKNOWN_{session.unknown_id}"
            ),
        }
    return None


def infer_exit_identity_from_active_sessions(db: Session):
    active_sessions = (
        db.query(models.VisitSession)
        .filter_by(status="ACTIVE")
        .order_by(models.VisitSession.entry_at.desc())
        .all()
    )
    if len(active_sessions) != 1:
        return None, len(active_sessions)

    identity = identity_from_visit_session(active_sessions[0])
    if identity is None:
        return None, len(active_sessions)
    identity["visit_session_id"] = active_sessions[0].id
    return identity, len(active_sessions)


# ── Retention cleanup ──────────────────────────────────────────────

_retention_running = False


def _close_expired_sessions(db: Session, now: datetime.datetime) -> int:
    expired = (
        db.query(models.VisitSession)
        .filter(
            models.VisitSession.status == "ACTIVE",
            models.VisitSession.entry_at < now - datetime.timedelta(hours=UNKNOWN_IDENTITY_EXPIRE_HOURS + 24),
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
        log_info(f"Retention: closed {count} stale session(s)")
    return count


def _expire_unknown_identities(db: Session, now: datetime.datetime) -> int:
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
        log_info(f"Retention: expired {count} unknown identit(ies)")
        for unk in expired:
            audit_log(None, "expire", "unknown_identity", unk.id, details={"anonymous_code": unk.anonymous_code})
    return count


def _purge_expired_embeddings(db: Session, now: datetime.datetime) -> int:
    cutoff = now - datetime.timedelta(hours=UNKNOWN_EXPIRED_GRACE_HOURS)
    expired = (
        db.query(models.UnknownIdentity)
        .filter(
            models.UnknownIdentity.status == "EXPIRED",
            models.UnknownIdentity.expire_at < cutoff,
        )
        .all()
    )
    count = 0
    for unk in expired:
        unk.embedding_vector = None
        count += 1
    if count:
        db.commit()
        log_info(f"Retention: purged embeddings of {count} expired unknown identit(ies)")
    return count


def _retention_cleanup():
    from retention import run_retention as _run_retention
    from database import SessionLocal
    global _retention_running
    _retention_running = True
    log_info("Retention cleanup worker started (app.retention)")
    while _retention_running:
        try:
            db = SessionLocal()
            try:
                _run_retention(db, now=utc_now())
            finally:
                db.close()
        except Exception as e:
            log_info(f"Retention cleanup error: {e}")
        time.sleep(RETENTION_CLEANUP_INTERVAL_SECONDS)
    _retention_running = False


def start_retention_cleanup():
    thread = threading.Thread(target=_retention_cleanup, daemon=True)
    thread.start()
    return thread


def stop_retention_cleanup():
    global _retention_running
    _retention_running = False

@app.on_event("startup")
def load_models():
    global detector, face_pipeline
    # Initialize YOLOv8 Detector
    detector = YOLOv8Detector()
    print("YOLOv8 ONNX Detector loaded successfully.")
    
    # Initialize Face Pipeline
    face_pipeline = FacePipeline()
    print("FacePipeline ONNX Models loaded successfully.")
    sync_service.start()
    print("Offline sync service started.")
    start_retention_cleanup()
    print("Retention cleanup started.")
    _seed_admin_user()

def _seed_admin_user():
    from database import SessionLocal
    from auth import hash_password
    db = SessionLocal()
    try:
        existing = db.query(models.User).filter_by(username="admin").first()
        if existing is None:
            db.add(models.User(
                username="admin",
                password_hash=hash_password("admin"),
                role="ADMIN",
                status="ACTIVE",
            ))
            db.commit()
            print("Created default admin user (admin/admin).")
    except Exception as e:
        print(f"Seed admin user skipped: {e}")
    finally:
        db.close()

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # Ensure browsers always see CORS headers, even on unexpected 500s.
    log_info(f"Unhandled error on {request.url.path}: {exc}")
    log_info(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"error": "internal_server_error", "detail": str(exc)},
        headers=cors_headers(request),
    )


@app.get("/api/health")
async def health_check(db: Session = Depends(get_db)):
    db_host = os.getenv("POSTGRES_HOST", "localhost")
    redis_host = os.getenv("REDIS_HOST", "localhost")

    database_status = "configured"
    try:
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        database_status = "up"
    except Exception as exc:
        database_status = f"down: {exc.__class__.__name__}"
        return JSONResponse(
            status_code=503,
            content={
                "status": "degraded",
                "timestamp": time.time(),
                "services": {
                    "database": f"{database_status} at {db_host}",
                    "cache": f"configured at {redis_host}",
                },
                "hint": "PostgreSQL is not reachable. Start it with: npm run db:up",
            },
        )

    return {
        "status": "healthy",
        "timestamp": time.time(),
        "services": {
            "database": f"{database_status} at {db_host}",
            "cache": f"configured at {redis_host}",
        },
    }

@app.post("/api/process-frame")
async def process_frame(
    request: Request,
    file: UploadFile = File(...),
    session_id: str = Form("default"),
    line_config: str = Form(None),
    mock_detections: str = Form(None),
    fast_mode: str = Form("false"),
    identity_probe: str = Form("false"),
    detect_frame: str = Form("true"),
    identity_ttl_seconds: str = Form("5"),
    db: Session = Depends(get_db)
):
    request_start = time.perf_counter()
    try:
        if detector is None or face_pipeline is None:
            return JSONResponse(
                status_code=503,
                content={"error": "Detector not loaded yet"},
                headers=cors_headers(request),
            )

        contents = await validate_image_file(file)
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid image file"},
                headers=cors_headers(request),
            )

        if session_id not in session_trackers:
            session_trackers[session_id] = IoUTracker()
        tracker = session_trackers[session_id]

        parsed_line_config = None
        if line_config:
            try:
                parsed_line_config = json.loads(line_config)
            except Exception as e:
                log_info(f"Error parsing line_config: {e}")

        fast_mode_enabled = parse_bool(fast_mode)
        identity_probe_enabled = parse_bool(identity_probe)
        detect_frame_enabled = parse_bool(detect_frame, True)
        identity_ttl = max(1.0, parse_float(identity_ttl_seconds, 5.0))

        detections = None
        detector_ran = False
        if mock_detections:
            try:
                detections = json.loads(mock_detections)
                detector_ran = True
            except Exception as e:
                log_info(f"Error parsing mock_detections: {e}")

        if detections is None:
            if detect_frame_enabled:
                detections = detector.detect(img)
                detector_ran = True
            else:
                detections = []

        tracks, crossing_events = tracker.update(detections, parsed_line_config)
        crossing_track_ids = {event["track_id"] for event in crossing_events}
        now_monotonic = time.monotonic()
        for track in tracks:
            track_id = track["track_id"]
            identity = tracker.identities.get(track_id)
            if identity and now_monotonic - float(identity.get("identified_at", 0.0)) > identity_ttl:
                del tracker.identities[track_id]

        tracks_to_identify = [
            track
            for track in tracks
            if track["track_id"] not in tracker.identities
            and not track.get("predicted", False)
            and (
                not fast_mode_enabled
                or identity_probe_enabled
                or track["track_id"] in crossing_track_ids
            )
        ]

        if tracks_to_identify:
            parsed_templates = load_active_face_templates(db)

            for track in tracks_to_identify:
                track_id = track["track_id"]

                x1, y1, x2, y2 = [int(coord) for coord in track["bbox"]]
                h_img, w_img = img.shape[:2]
                x1 = max(0, min(x1, w_img - 1))
                y1 = max(0, min(y1, h_img - 1))
                x2 = max(0, min(x2, w_img - 1))
                y2 = max(0, min(y2, h_img - 1))

                if x2 <= x1 or y2 <= y1:
                    continue

                person_crop = img[y1:y2, x1:x2]
                try:
                    faces = face_pipeline.detect_faces(person_crop, score_threshold=0.5)
                    if not faces:
                        continue

                    faces.sort(key=lambda item: item["score"], reverse=True)
                    face = faces[0]
                    embedding = face_pipeline.extract_embedding(person_crop, face["raw_face"])
                    emb_arr = np.array(embedding, dtype=np.float32)

                    best_sim = -1.0
                    best_match = None
                    for pt in parsed_templates:
                        norm_a = np.linalg.norm(emb_arr)
                        norm_b = np.linalg.norm(pt["vector"])
                        if norm_a <= 1e-6 or norm_b <= 1e-6:
                            continue
                        sim = float(np.dot(emb_arr, pt["vector"]) / (norm_a * norm_b))
                        if sim > best_sim:
                            best_sim = sim
                            best_match = pt

                    if best_sim >= 0.6 and best_match is not None:
                        identity = {
                            "person_id": best_match["person_id"],
                            "person_name": best_match["person_name"],
                            "identity_type": "KNOWN",
                            "similarity_score": float(best_sim),
                            "identified_at": now_monotonic,
                        }
                        tracker.identities[track_id] = identity
                        track.update(identity)
                        continue

                    now = utc_now()
                    active_unknowns = db.query(models.UnknownIdentity).filter(
                        models.UnknownIdentity.status == "ACTIVE",
                        models.UnknownIdentity.expire_at > now,
                    ).all()

                    best_unk_sim = -1.0
                    best_unk_match = None
                    for unk in active_unknowns:
                        unk_vec = np.array(unk.embedding_vector, dtype=np.float32)
                        norm_a = np.linalg.norm(emb_arr)
                        norm_b = np.linalg.norm(unk_vec)
                        if norm_a <= 1e-6 or norm_b <= 1e-6:
                            continue
                        sim = float(np.dot(emb_arr, unk_vec) / (norm_a * norm_b))
                        if sim > best_unk_sim:
                            best_unk_sim = sim
                            best_unk_match = unk

                    if best_unk_sim >= 0.55 and best_unk_match is not None:
                        best_unk_match.last_seen_at = now
                        best_unk_match.visit_count += 1
                        db.commit()
                        identity = {
                            "person_id": None,
                            "unknown_id": best_unk_match.id,
                            "person_name": best_unk_match.anonymous_code,
                            "identity_type": "UNKNOWN",
                            "similarity_score": float(best_unk_sim),
                            "identified_at": now_monotonic,
                        }
                        tracker.identities[track_id] = identity
                        track.update(identity)
                        continue

                    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
                    today_end = today_start + datetime.timedelta(days=1)
                    count_today = db.query(models.UnknownIdentity).filter(
                        models.UnknownIdentity.created_at >= today_start,
                        models.UnknownIdentity.created_at < today_end,
                    ).count()
                    anonymous_code = f"UNKNOWN_{now.strftime('%Y%m%d')}_{count_today + 1:04d}"

                    new_unk = models.UnknownIdentity(
                        anonymous_code=anonymous_code,
                        embedding_vector=embedding,
                        expire_at=now + datetime.timedelta(hours=24),
                        status="ACTIVE",
                        visit_count=1,
                        created_at=now,
                        last_seen_at=now,
                    )
                    try:
                        db.add(new_unk)
                        db.flush()
                        db.commit()
                    except Exception as unk_db_ex:
                        log_info(f"DB error saving unknown identity (queued offline): {unk_db_ex}")
                        _queue_unknown_identity(now, anonymous_code, embedding, count_today, expire_hours=24)

                    identity = {
                        "person_id": None,
                        "unknown_id": new_unk.id,
                        "person_name": anonymous_code,
                        "identity_type": "UNKNOWN",
                        "similarity_score": float(best_sim) if best_sim > -1.0 else 0.0,
                        "identified_at": now_monotonic,
                    }
                    tracker.identities[track_id] = identity
                    track.update(identity)
                except Exception as ex:
                    log_info(f"Error during face matching for track {track_id}: {ex}")

        for track in tracks:
            identity = tracker.identities.get(track["track_id"])
            if identity:
                track.update(identity)

        for event in crossing_events:
            track_id = event["track_id"]
            direction = event["direction"]

            identity_type = "UNKNOWN"
            person_id = None
            unknown_id = None
            confidence = 0.9
            person_name = "Khách"
            metadata = {"resolution": "face_or_track_identity"}

            if track_id in tracker.identities:
                id_data = tracker.identities[track_id]
                if id_data["identity_type"] == "KNOWN":
                    identity_type = "KNOWN"
                    person_id = id_data["person_id"]
                    confidence = id_data.get("similarity_score", 0.9)
                elif id_data["identity_type"] == "UNKNOWN":
                    identity_type = "UNKNOWN"
                    unknown_id = id_data.get("unknown_id")
                    confidence = id_data.get("similarity_score", 0.9)
                person_name = id_data.get("person_name") or person_name
            else:
                event["identity_type"] = identity_type
                event["person_name"] = "Khách"
                event["similarity_score"] = float(confidence)

            if track_id not in tracker.identities and direction == "EXIT":
                inferred_identity, active_count = infer_exit_identity_from_active_sessions(db)
                metadata = {
                    "resolution": "session_continuity" if inferred_identity else "unresolved_exit",
                    "active_session_candidates": active_count,
                }
                if inferred_identity:
                    identity_type = inferred_identity["identity_type"]
                    person_id = inferred_identity["person_id"]
                    unknown_id = inferred_identity["unknown_id"]
                    person_name = inferred_identity["person_name"]
                    confidence = 0.45
                    metadata["visit_session_id"] = inferred_identity["visit_session_id"]
                else:
                    identity_type = "UNRESOLVED"
                    person_name = "Chưa xác định"
                    confidence = 0.0

            event["identity_type"] = identity_type
            event["person_name"] = person_name
            event["similarity_score"] = float(confidence)
            event["identity_resolution"] = metadata["resolution"]

            try:
                camera = db.query(models.Camera).first()
                if not camera:
                    camera = models.Camera(
                        name="Default Camera",
                        source_type="WEBCAM",
                        source_url="0",
                        status="ONLINE",
                    )
                    db.add(camera)
                    db.flush()

                db_event = models.Event(
                    event_type=direction,
                    identity_type=identity_type,
                    person_id=person_id,
                    unknown_id=unknown_id,
                    track_id=track_id,
                    camera_id=camera.id,
                    confidence=float(confidence),
                    timestamp=utc_now(),
                    metadata_json=metadata,
                )
                db.add(db_event)
                db.flush()

                if identity_type == "KNOWN" and person_id is not None:
                    if direction == "ENTRY":
                        active_sess = db.query(models.VisitSession).filter_by(
                            person_id=person_id,
                            status="ACTIVE",
                        ).first()
                        if not active_sess:
                            db.add(models.VisitSession(
                                identity_type="KNOWN",
                                person_id=person_id,
                                entry_camera_id=camera.id,
                                entry_event_id=db_event.id,
                                entry_at=utc_now(),
                                status="ACTIVE",
                            ))
                    elif direction == "EXIT":
                        active_sess = db.query(models.VisitSession).filter_by(
                            person_id=person_id,
                            status="ACTIVE",
                        ).first()
                        if active_sess:
                            active_sess.exit_camera_id = camera.id
                            active_sess.exit_event_id = db_event.id
                            active_sess.exit_at = utc_now()
                            active_sess.status = "CLOSED"
                            active_sess.duration_seconds = elapsed_seconds(active_sess.entry_at, active_sess.exit_at)
                elif identity_type == "UNKNOWN" and unknown_id is not None:
                    if direction == "ENTRY":
                        active_sess = db.query(models.VisitSession).filter_by(
                            unknown_id=unknown_id,
                            status="ACTIVE",
                        ).first()
                        if not active_sess:
                            db.add(models.VisitSession(
                                identity_type="UNKNOWN",
                                unknown_id=unknown_id,
                                entry_camera_id=camera.id,
                                entry_event_id=db_event.id,
                                entry_at=utc_now(),
                                status="ACTIVE",
                            ))
                    elif direction == "EXIT":
                        active_sess = db.query(models.VisitSession).filter_by(
                            unknown_id=unknown_id,
                            status="ACTIVE",
                        ).first()
                        if active_sess:
                            active_sess.exit_camera_id = camera.id
                            active_sess.exit_event_id = db_event.id
                            active_sess.exit_at = utc_now()
                            active_sess.status = "CLOSED"
                            active_sess.duration_seconds = elapsed_seconds(active_sess.entry_at, active_sess.exit_at)

                db.commit()
                log_info(f"[DB Log] Event logged: {direction} for track {track_id} ({identity_type})")
            except Exception as ex:
                db.rollback()
                log_info(f"Error logging crossing event: {ex}")
                _camera = locals().get("camera")
                _cam_id = _camera.id if _camera is not None else None
                _queue_event(
                    direction, identity_type, person_id, unknown_id,
                    track_id, _cam_id, confidence, metadata
                )

        processing_ms = round((time.perf_counter() - request_start) * 1000, 1)
        return {
            "session_id": session_id,
            "tracks": tracks,
            "crossing_events": crossing_events,
            "processing_ms": processing_ms,
            "fast_mode": fast_mode_enabled,
            "identity_probe": identity_probe_enabled,
            "detect_frame": detect_frame_enabled,
            "detector_ran": detector_ran,
        }
    except Exception as ex:
        db.rollback()
        log_info(f"process-frame failed: {ex}")
        log_info(traceback.format_exc())
        detail = str(ex)
        hint = None
        if "connection" in detail.lower() and ("5432" in detail or "postgres" in detail.lower() or "OperationalError" in detail):
            hint = "PostgreSQL is not reachable. Run: npm run db:up"
        payload = {"error": "process_frame_failed", "detail": detail}
        if hint:
            payload["hint"] = hint
        return JSONResponse(
            status_code=503 if hint else 500,
            content=payload,
            headers=cors_headers(request),
        )


@app.post("/api/persons/register", status_code=status.HTTP_201_CREATED)
async def register_person(
    full_name: str = Form(...),
    member_code: str = Form(...),
    role: str = Form(...),
    status_str: str = Form("ACTIVE", alias="status"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # 1. Validate role
    if role.upper() not in ALLOWED_PERSON_ROLES:
        allowed = ", ".join(sorted(ALLOWED_PERSON_ROLES))
        raise HTTPException(status_code=400, detail=f"Invalid role '{role}'. Allowed: {allowed}.")

    # 2. Check duplicate member_code
    db_person = db.query(models.Person).filter_by(member_code=member_code).first()
    if db_person:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Member code {member_code} is already registered."
        )
        
    # 3. Read and decode uploaded image
    try:
        contents = await validate_image_file(file)
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Decoded image is None")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid image file: {str(e)}"
        )
        
    # 3. Detect face
    try:
        faces = face_pipeline.detect_faces(img)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error executing face detection: {str(e)}"
        )
        
    if len(faces) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No face detected in the uploaded photo."
        )
    if len(faces) > 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Multiple faces detected in the uploaded photo. Please upload a portrait with exactly one face."
        )
        
    # 4. Extract face embedding
    try:
        embedding = face_pipeline.extract_embedding(img, faces[0]["raw_face"])
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error extracting face embedding: {str(e)}"
        )
        
    # 5. Persist to Database
    try:
        new_person = models.Person(
            full_name=full_name,
            member_code=member_code,
            role=role,
            status=status_str
        )
        db.add(new_person)
        db.flush()
        
        new_face = models.FaceTemplate(
            person_id=new_person.id,
            embedding_vector=embedding,
            model_name="sface",
            model_version="2021dec",
            quality_score=float(faces[0]["score"]),
            source_type="UPLOAD",
            is_active=True
        )
        db.add(new_face)
        db.commit()
        invalidate_face_template_cache()
        db.refresh(new_person)
        
        return {
            "id": new_person.id,
            "full_name": new_person.full_name,
            "member_code": new_person.member_code,
            "role": new_person.role,
            "status": new_person.status,
            "face_template": {
                "id": new_face.id,
                "model_name": new_face.model_name,
                "quality_score": new_face.quality_score
            }
        }
    except Exception as e:
        db.rollback()
        log_info(f"Database transaction failed (queued offline): {e}")
        _queue_person(full_name, member_code, role, status_str, embedding, float(faces[0]["score"]))
        return {"message": "Person queued for registration (database unavailable)", "queued": True}

@app.get("/api/persons")
async def get_persons(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
):
    query = db.query(models.Person).order_by(models.Person.created_at.desc())
    persons, total = paginate(query, skip, limit)
    return PaginatedResponse(
        items=[
            {
                "id": p.id,
                "full_name": p.full_name,
                "member_code": p.member_code,
                "role": p.role,
                "status": p.status
            }
            for p in persons
        ],
        total=total,
    )

@app.delete("/api/persons/{person_id}")
async def delete_person(person_id: int, db: Session = Depends(get_db)):
    person = db.query(models.Person).filter_by(id=person_id).first()
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")
    
    try:
        # Delete templates first due to foreign key
        db.query(models.FaceTemplate).filter_by(person_id=person_id).delete()
        # Delete sessions/events or set person_id to NULL
        db.query(models.VisitSession).filter_by(person_id=person_id).update({"person_id": None})
        db.query(models.Event).filter_by(person_id=person_id).update({"person_id": None})
        
        db.delete(person)
        db.commit()
        invalidate_face_template_cache()
        return {"message": "Person deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/persons/{person_id}")
async def update_person(
    person_id: int,
    full_name: str = Form(...),
    member_code: str = Form(...),
    role: str = Form(...),
    status_str: str = Form("ACTIVE", alias="status"),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    person = db.query(models.Person).filter_by(id=person_id).first()
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")

    if role.upper() not in ALLOWED_PERSON_ROLES:
        allowed = ", ".join(sorted(ALLOWED_PERSON_ROLES))
        raise HTTPException(status_code=400, detail=f"Invalid role '{role}'. Allowed: {allowed}.")

    # Check duplicate member_code (excluding self)
    db_person = db.query(models.Person).filter(
        models.Person.member_code == member_code,
        models.Person.id != person_id
    ).first()
    if db_person:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Member code {member_code} is already registered."
        )

    # Update basic details
    person.full_name = full_name
    person.member_code = member_code
    person.role = role
    person.status = status_str

    # Optional image upload for updating template
    if file is not None and file.filename:
        try:
            contents = await validate_image_file(file)
            nparr = np.frombuffer(contents, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                raise ValueError("Decoded image is None")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid image file: {str(e)}"
            )
            
        try:
            faces = face_pipeline.detect_faces(img)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error executing face detection: {str(e)}"
            )
            
        if len(faces) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No face detected in the uploaded photo."
            )
        if len(faces) > 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Multiple faces detected in the uploaded photo. Please upload a portrait with exactly one face."
            )
            
        try:
            embedding = face_pipeline.extract_embedding(img, faces[0]["raw_face"])
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error extracting face embedding: {str(e)}"
            )
            
        try:
            # Delete old templates first, or update the existing active template
            db.query(models.FaceTemplate).filter_by(person_id=person_id).delete()
            
            new_face = models.FaceTemplate(
                person_id=person.id,
                embedding_vector=embedding,
                model_name="sface",
                model_version="2021dec",
                quality_score=float(faces[0]["score"]),
                source_type="UPLOAD",
                is_active=True
            )
            db.add(new_face)
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Database error saving face template: {str(e)}")

    try:
        db.commit()
        invalidate_face_template_cache()
        db.refresh(person)
        return {
            "id": person.id,
            "full_name": person.full_name,
            "member_code": person.member_code,
            "role": person.role,
            "status": person.status
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/events")
async def get_events(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
):
    query = db.query(models.Event).order_by(models.Event.timestamp.desc())
    events, total = paginate(query, skip, limit)
    result = []
    for e in events:
        name = "Unknown"
        code = None
        if e.identity_type == "KNOWN" and e.person:
            name = e.person.full_name
            code = e.person.member_code
        elif e.identity_type == "UNKNOWN" and e.unknown_identity:
            name = e.unknown_identity.anonymous_code
            code = None
        elif e.identity_type == "UNRESOLVED":
            name = "Chưa xác định"
            
        result.append({
            "id": e.id,
            "event_type": e.event_type,
            "identity_type": e.identity_type,
            "person_name": name,
            "member_code": code,
            "timestamp": e.timestamp.isoformat(),
            "confidence": e.confidence
        })
    return PaginatedResponse(items=result, total=total)

def parse_day_start(value: str | None) -> datetime.datetime | None:
    if not value:
        return None
    try:
        return datetime.datetime.strptime(value, "%Y-%m-%d").replace(
            hour=0, minute=0, second=0, microsecond=0
        )
    except ValueError:
        return None


def resolve_report_window(
    date: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
) -> tuple[datetime.datetime, datetime.datetime]:
    """Resolve local Vietnam dates into UTC-naive [start, end) DB boundaries."""
    today_local = datetime.datetime.now(VIETNAM_TZ).replace(
        hour=0, minute=0, second=0, microsecond=0, tzinfo=None
    )
    start_local = parse_day_start(from_date) or parse_day_start(date) or today_local
    end_local = parse_day_start(to_date) or parse_day_start(date) or start_local
    if end_local < start_local:
        start_local, end_local = end_local, start_local
    end_local += datetime.timedelta(days=1)
    return local_day_start_as_utc(start_local), local_day_start_as_utc(end_local)


@app.get("/api/sessions")
async def get_sessions(
    db: Session = Depends(get_db),
    date: str = None,
    from_date: str = None,
    to_date: str = None,
    skip: int = 0,
    limit: int = 100,
):
    query = db.query(models.VisitSession)

    # Prefer explicit range; keep legacy `date=` for single-day filters.
    if from_date or to_date or date:
        day_start, day_end = resolve_report_window(date=date, from_date=from_date, to_date=to_date)
        query = query.filter(
            models.VisitSession.entry_at >= day_start,
            models.VisitSession.entry_at < day_end,
        )

    query = query.order_by(models.VisitSession.entry_at.desc())
    sessions, total = paginate(query, skip, limit)
    result = []
    for s in sessions:
        name = "Unknown"
        code = None
        if s.identity_type == "KNOWN" and s.person:
            name = s.person.full_name
            code = s.person.member_code
        elif s.identity_type == "UNKNOWN" and s.unknown_identity:
            name = s.unknown_identity.anonymous_code
            code = None

        result.append({
            "id": s.id,
            "person_name": name,
            "member_code": code,
            "identity_type": s.identity_type,
            "entry_at": s.entry_at.isoformat() if s.entry_at else None,
            "exit_at": s.exit_at.isoformat() if s.exit_at else None,
            "duration_seconds": s.duration_seconds,
            "status": s.status
        })
    return PaginatedResponse(items=result, total=total)

@app.get("/api/stats/occupancy")
async def get_occupancy(
    db: Session = Depends(get_db),
    date: str = None,
    from_date: str = None,
    to_date: str = None,
):
    range_start, range_end = resolve_report_window(date=date, from_date=from_date, to_date=to_date)

    entries = db.query(models.Event).filter(
        models.Event.event_type == "ENTRY",
        models.Event.timestamp >= range_start,
        models.Event.timestamp < range_end,
    ).count()

    exits = db.query(models.Event).filter(
        models.Event.event_type == "EXIT",
        models.Event.timestamp >= range_start,
        models.Event.timestamp < range_end,
    ).count()

    # Auto-close stale sessions from before the selected period.
    # Sessions still ACTIVE whose entry_at is before range_start are likely
    # leftover from previous days where the person never properly exited.
    stale_sessions = db.query(models.VisitSession).filter(
        models.VisitSession.status == "ACTIVE",
        models.VisitSession.entry_at < range_start,
    ).all()
    for stale in stale_sessions:
        stale.status = "CLOSED"
        stale.exit_at = stale.entry_at  # no real exit observed
        stale.duration_seconds = 0
    if stale_sessions:
        db.commit()

    active_sessions = db.query(models.VisitSession).filter(
        models.VisitSession.status == "ACTIVE",
        models.VisitSession.entry_at >= range_start,
        models.VisitSession.entry_at < range_end,
    ).count()

    known_entries = db.query(models.Event).filter(
        models.Event.event_type == "ENTRY",
        models.Event.identity_type == "KNOWN",
        models.Event.timestamp >= range_start,
        models.Event.timestamp < range_end,
    ).count()

    unknown_entries = db.query(models.Event).filter(
        models.Event.event_type == "ENTRY",
        models.Event.identity_type == "UNKNOWN",
        models.Event.timestamp >= range_start,
        models.Event.timestamp < range_end,
    ).count()

    total_sessions = db.query(models.VisitSession).filter(
        models.VisitSession.entry_at >= range_start,
        models.VisitSession.entry_at < range_end,
    ).count()

    return {
        "current_occupancy": active_sessions,
        "total_entries_today": entries,
        "total_exits_today": exits,
        "known_visitors_today": known_entries,
        "unknown_visitors_today": unknown_entries,
        "total_sessions_today": total_sessions,
        "from_date": range_start.date().isoformat(),
        "to_date": (range_end - datetime.timedelta(days=1)).date().isoformat(),
    }

@app.get("/api/stats/hourly")
async def get_hourly_stats(
    db: Session = Depends(get_db),
    date: str = None,
    from_date: str = None,
    to_date: str = None,
):
    range_start, range_end = resolve_report_window(date=date, from_date=from_date, to_date=to_date)
    events = db.query(models.Event).filter(
        models.Event.timestamp >= range_start,
        models.Event.timestamp < range_end,
    ).all()

    hourly_data = {hour: {"entry": 0, "exit": 0} for hour in range(24)}
    for e in events:
        hour = as_vietnam_time(e.timestamp).hour
        if e.event_type == "ENTRY":
            hourly_data[hour]["entry"] += 1
        elif e.event_type == "EXIT":
            hourly_data[hour]["exit"] += 1

    return [{"hour": h, "entry": d["entry"], "exit": d["exit"]} for h, d in hourly_data.items()]


# ── Auth endpoints ────────────────────────────────────────────────


from auth import (
    hash_password, verify_password, create_access_token,
    get_current_user, require_user, require_admin,
)


@app.post("/api/auth/login")
async def login(
    body: dict,
    db: Session = Depends(get_db),
):
    username = body.get("username", "").strip()
    password = body.get("password", "")
    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password required")
    user = db.query(models.User).filter_by(username=username, status="ACTIVE").first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = create_access_token({"sub": str(user.id), "role": user.role})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {"id": user.id, "username": user.username, "role": user.role},
    }


@app.post("/api/auth/register", status_code=status.HTTP_201_CREATED)
async def register(
    body: dict,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(require_admin),
):
    username = body.get("username", "").strip()
    password = body.get("password", "")
    role = body.get("role", "LIBRARIAN").strip().upper()
    if not username or len(username) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters")
    if not password or len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    if role not in ALLOWED_USER_ROLES:
        allowed = ", ".join(sorted(ALLOWED_USER_ROLES))
        raise HTTPException(status_code=400, detail=f"Invalid role '{role}'. Allowed: {allowed}.")
    existing = db.query(models.User).filter_by(username=username).first()
    if existing:
        raise HTTPException(status_code=409, detail="Username already exists")
    user = models.User(
        username=username,
        password_hash=hash_password(password),
        role=role,
        status="ACTIVE",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    audit_log(db, "register", "user", user.id, details={"username": username, "role": role})
    return {"id": user.id, "username": user.username, "role": user.role}


@app.get("/api/auth/me")
async def auth_me(user: models.User = Depends(require_user)):
    return {"id": user.id, "username": user.username, "role": user.role, "status": user.status}


@app.get("/api/auth/users")
async def list_users(
    db: Session = Depends(get_db),
    _admin: models.User = Depends(require_admin),
    skip: int = 0,
    limit: int = 100,
):
    query = db.query(models.User).order_by(models.User.created_at.desc())
    users, total = paginate(query, skip, limit)
    return PaginatedResponse(
        items=[{"id": u.id, "username": u.username, "role": u.role, "status": u.status} for u in users],
        total=total,
    )


# ── Retention & audit endpoints ────────────────────────────────────


@app.get("/api/admin/expired-unknowns")
async def get_expired_unknowns(
    db: Session = Depends(get_db),
    _admin: models.User = Depends(require_admin),
    skip: int = 0,
    limit: int = 100,
):
    query = (
        db.query(models.UnknownIdentity)
        .filter(models.UnknownIdentity.status == "EXPIRED")
        .order_by(models.UnknownIdentity.expire_at.desc())
    )
    expired, total = paginate(query, skip, limit)
    return PaginatedResponse(
        items=[
            {
                "id": u.id,
                "anonymous_code": u.anonymous_code,
                "expire_at": u.expire_at.isoformat() if u.expire_at else None,
                "visit_count": u.visit_count,
                "has_embedding": u.embedding_vector is not None,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in expired
        ],
        total=total,
    )


@app.post("/api/admin/retention/run")
async def trigger_retention_run(
    db: Session = Depends(get_db),
    _admin: models.User = Depends(require_admin),
):
    from retention import run_retention as _run_retention
    now = utc_now()
    results = _run_retention(db, now=now)
    return {
        "phases": results,
        "duration_ms": sum(r["duration_ms"] for r in results),
        "timestamp": now.isoformat(),
    }


@app.get("/api/admin/retention/config")
async def get_retention_config(
    _admin: models.User = Depends(require_admin),
):
    return {
        "unknown_identity_expire_hours": UNKNOWN_IDENTITY_EXPIRE_HOURS,
        "unknown_expired_grace_hours": UNKNOWN_EXPIRED_GRACE_HOURS,
        "retention_cleanup_interval_seconds": RETENTION_CLEANUP_INTERVAL_SECONDS,
        "audit_log_enabled": AUDIT_LOG_ENABLED,
        "event_days": RETENTION_EVENT_DAYS,
        "session_days": RETENTION_SESSION_DAYS,
        "unknown_purge_days": RETENTION_UNKNOWN_PURGE_DAYS,
        "template_grace_days": RETENTION_TEMPLATE_GRACE_DAYS,
        "audit_log_days": RETENTION_AUDIT_LOG_DAYS,
    }


@app.get("/api/admin/retention/status")
async def get_retention_status(
    db: Session = Depends(get_db),
    _admin: models.User = Depends(require_admin),
):
    from retention import count_pending, read_config
    cfg = read_config()
    counts = count_pending(db)
    return {
        "config": cfg,
        "counts": counts,
    }


@app.get("/api/admin/audit-log")
async def get_audit_log(
    db: Session = Depends(get_db),
    action: str | None = None,
    entity_type: str | None = None,
    skip: int = 0,
    limit: int = 100,
    _admin: models.User = Depends(require_admin),
):
    query = db.query(models.AuditLog)
    if action:
        query = query.filter(models.AuditLog.action == action)
    if entity_type:
        query = query.filter(models.AuditLog.entity_type == entity_type)
    query = query.order_by(models.AuditLog.created_at.desc())
    entries, total = paginate(query, skip, limit)
    return PaginatedResponse(
        items=[
            {
                "id": e.id,
                "action": e.action,
                "entity_type": e.entity_type,
                "entity_id": e.entity_id,
                "actor": e.actor,
                "details": e.details,
                "ip_address": e.ip_address,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in entries
        ],
        total=total,
    )


@app.get("/api/persons/{person_id}/templates")
async def get_person_templates(
    person_id: int,
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
):
    person = db.query(models.Person).filter_by(id=person_id).first()
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")
    query = (
        db.query(models.FaceTemplate)
        .filter_by(person_id=person_id)
        .order_by(models.FaceTemplate.created_at.desc())
    )
    templates, total = paginate(query, skip, limit)
    return PaginatedResponse(
        items=[
            {
                "id": t.id,
                "model_name": t.model_name,
                "model_version": t.model_version,
                "quality_score": t.quality_score,
                "source_type": t.source_type,
                "is_active": t.is_active,
                "has_embedding": t.embedding_vector is not None,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in templates
        ],
        total=total,
    )


@app.delete("/api/persons/{person_id}/templates/{template_id}")
async def delete_person_template(
    person_id: int,
    template_id: int,
    request: Request,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(require_admin),
):
    person = db.query(models.Person).filter_by(id=person_id).first()
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")
    template = db.query(models.FaceTemplate).filter_by(id=template_id, person_id=person_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Face template not found")
    db.delete(template)
    db.commit()
    invalidate_face_template_cache()
    audit_log(
        db, "delete", "face_template", template_id,
        details={"person_id": person_id, "person_name": person.full_name},
        ip_address=request.client.host if request.client else None,
    )
    return {"message": "Face template deleted", "template_id": template_id}


@app.get("/api/admin/retention/config")
async def get_retention_config(
    _admin: models.User = Depends(require_admin),
):
    return {
        "unknown_identity_expire_hours": UNKNOWN_IDENTITY_EXPIRE_HOURS,
        "unknown_expired_grace_hours": UNKNOWN_EXPIRED_GRACE_HOURS,
        "retention_cleanup_interval_seconds": RETENTION_CLEANUP_INTERVAL_SECONDS,
        "audit_log_enabled": AUDIT_LOG_ENABLED,
    }

class CameraCreate(BaseModel):
    name: str
    source_type: str # 'WEBCAM', 'FILE', 'RTSP'
    source_url: str

@app.get("/api/cameras")
async def get_cameras(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
):
    query = db.query(models.Camera).order_by(models.Camera.created_at.desc())
    cameras, total = paginate(query, skip, limit)
    return PaginatedResponse(
        items=[
            {
                "id": c.id,
                "name": c.name,
                "source_type": c.source_type,
                "source_url": c.source_url,
                "status": c.status,
                "last_online_at": c.last_online_at.isoformat() if c.last_online_at else None
            }
            for c in cameras
        ],
        total=total,
    )

@app.post("/api/cameras")
async def create_camera(data: CameraCreate, db: Session = Depends(get_db)):
    # Validate connection based on type
    status_str = "ONLINE"
    if data.source_type == "FILE":
        if not os.path.exists(data.source_url):
            raise HTTPException(
                status_code=400,
                detail=f"Video file does not exist at path: {data.source_url}"
            )
    elif data.source_type == "RTSP":
        # Attempt to open RTSP stream
        cap = cv2.VideoCapture(data.source_url, cv2.CAP_FFMPEG)
        cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 3000)
        cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 3000)
        if not cap.isOpened():
            raise HTTPException(
                status_code=400,
                detail=f"Failed to connect to RTSP stream: {data.source_url}"
            )
        cap.release()
    elif data.source_type == "WEBCAM":
        try:
            cam_idx = int(data.source_url)
            cap = cv2.VideoCapture(cam_idx)
            if not cap.isOpened():
                status_str = "OFFLINE"
            else:
                cap.release()
        except ValueError:
            status_str = "OFFLINE"

    new_cam = models.Camera(
        name=data.name,
        source_type=data.source_type,
        source_url=data.source_url,
        status=status_str,
        last_online_at=datetime.datetime.utcnow() if status_str == "ONLINE" else None
    )
    try:
        db.add(new_cam)
        db.commit()
        db.refresh(new_cam)
        return {
            "id": new_cam.id,
            "name": new_cam.name,
            "source_type": new_cam.source_type,
            "source_url": new_cam.source_url,
            "status": new_cam.status
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/cameras/{camera_id}")
async def update_camera(camera_id: int, data: CameraCreate, db: Session = Depends(get_db)):
    camera = db.query(models.Camera).filter_by(id=camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    try:
        camera.name = data.name
        camera.source_url = data.source_url
        db.commit()
        return {
            "id": camera.id,
            "name": camera.name,
            "source_type": camera.source_type,
            "source_url": camera.source_url,
            "status": camera.status
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/cameras/{camera_id}/test")
async def test_camera_connection(camera_id: int, db: Session = Depends(get_db)):
    camera = db.query(models.Camera).filter_by(id=camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
        
    status_str = "OFFLINE"
    if camera.source_type == "FILE":
        if os.path.exists(camera.source_url):
            status_str = "ONLINE"
    elif camera.source_type == "RTSP":
        cap = cv2.VideoCapture(camera.source_url, cv2.CAP_FFMPEG)
        cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 3000)
        cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 3000)
        if cap.isOpened():
            status_str = "ONLINE"
            cap.release()
    elif camera.source_type == "WEBCAM":
        try:
            cam_idx = int(camera.source_url)
            cap = cv2.VideoCapture(cam_idx)
            if cap.isOpened():
                status_str = "ONLINE"
                cap.release()
        except ValueError:
            pass

    try:
        camera.status = status_str
        if status_str == "ONLINE":
            camera.last_online_at = datetime.datetime.utcnow()
        db.commit()
        return {"status": status_str}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/cameras/{camera_id}")
async def delete_camera(camera_id: int, db: Session = Depends(get_db)):
    camera = db.query(models.Camera).filter_by(id=camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    try:
        db.delete(camera)
        db.commit()
        return {"message": "Camera deleted"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {"message": "Welcome to LibCounterAI API. Visit /api/health for system status."}


@app.get("/api/sync/status")
async def sync_status():
    return sync_service.get_status()


@app.post("/api/sync/trigger")
async def sync_trigger():
    from offline_queue import get_pending, remove, mark_error, is_postgres_alive
    from database import SessionLocal
    import models
    if not is_postgres_alive():
        return {"message": "PostgreSQL still not reachable", "synced": False}
    import sync_service
    ops = get_pending()
    synced = 0
    if ops:
        db = SessionLocal()
        try:
            from sync_service import _replay_op
            for op in ops:
                ok = _replay_op(op, db)
                if ok:
                    remove(op["id"])
                    synced += 1
                else:
                    mark_error(op["id"], "manual_sync_failed")
                    remove(op["id"])
        finally:
            db.close()
    return {"message": f"Synced {synced} pending operations", "synced": synced}


@app.get("/api/sync/pending")
async def sync_pending():
    from offline_queue import get_pending
    return {"pending": get_pending()}

if __name__ == "__main__":
    import uvicorn
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    reload_mode = os.environ.get("RELOAD", "false").lower() == "true"
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=reload_mode)
