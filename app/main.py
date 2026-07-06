import os
import time
import datetime
from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
import cv2
import numpy as np

from detector import YOLOv8Detector
from tracker import IoUTracker
from face_pipeline import FacePipeline
from database import get_db
import models

app = FastAPI(
    title="LibCounterAI Backend API",
    description="Backend API for Visitor Recognition and Counting System",
    version="0.1.0"
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize detector globally
detector = None
face_pipeline = None
session_trackers = {}

@app.on_event("startup")
def load_models():
    global detector, face_pipeline
    # Initialize YOLOv8 Detector
    detector = YOLOv8Detector()
    print("YOLOv8 ONNX Detector loaded successfully.")
    
    # Initialize Face Pipeline
    face_pipeline = FacePipeline()
    print("FacePipeline ONNX Models loaded successfully.")

@app.get("/api/health")
async def health_check():
    # Simple check for database/redis environment configuration
    db_host = os.getenv("POSTGRES_HOST", "localhost")
    redis_host = os.getenv("REDIS_HOST", "localhost")
    
    # In a full implementation, we would ping the services here.
    # For initial skeleton, we return configuration presence.
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "services": {
            "database": f"configured at {db_host}",
            "cache": f"configured at {redis_host}"
        }
    }

@app.post("/api/process-frame")
async def process_frame(
    file: UploadFile = File(...),
    session_id: str = Form("default"),
    line_config: str = Form(None),
    mock_detections: str = Form(None),
    db: Session = Depends(get_db)
):
    if detector is None:
        return {"error": "Detector not loaded yet"}
        
    # Read image from file
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if img is None:
        return {"error": "Invalid image file"}
        
    # Get or create tracker for session
    if session_id not in session_trackers:
        session_trackers[session_id] = IoUTracker()
    tracker = session_trackers[session_id]
    
    # Parse line config if provided
    parsed_line_config = None
    if line_config:
        try:
            import json
            parsed_line_config = json.loads(line_config)
        except Exception as e:
            print(f"Error parsing line_config: {e}")
            
    # Parse mock detections if provided (for testing and validation)
    detections = None
    if mock_detections:
        try:
            import json
            detections = json.loads(mock_detections)
        except Exception as e:
            print(f"Error parsing mock_detections: {e}")
            
    if detections is None:
        # Run YOLO detection
        detections = detector.detect(img)
    
    print(f"[API] Processing frame: detections={detections}, line_config={parsed_line_config}")
    
    # Run tracking update with line crossing detection
    tracks, crossing_events = tracker.update(detections, parsed_line_config)
    
    # Run face recognition on tracks that do not have a KNOWN identity
    if tracks:
        templates = db.query(models.FaceTemplate).filter_by(is_active=True).all()
        # Pre-cache template vectors as numpy arrays for speed
        parsed_templates = []
        for t in templates:
            if t.embedding_vector:
                parsed_templates.append({
                    "person_id": t.person_id,
                    "person_name": t.person.full_name,
                    "vector": np.array(t.embedding_vector, dtype=np.float32)
                })
                
        for track in tracks:
            track_id = track["track_id"]
            
            # If already identified as KNOWN, skip face detection/matching
            if track_id in tracker.identities and tracker.identities[track_id]["identity_type"] == "KNOWN":
                # Update track dictionary with identity
                track.update(tracker.identities[track_id])
                continue
                
            # Otherwise, try to detect and match
            x1, y1, x2, y2 = [int(coord) for coord in track["bbox"]]
            
            # Bound coordinates to image dimensions
            h_img, w_img = img.shape[:2]
            x1 = max(0, min(x1, w_img - 1))
            y1 = max(0, min(y1, h_img - 1))
            x2 = max(0, min(x2, w_img - 1))
            y2 = max(0, min(y2, h_img - 1))
            
            if x2 > x1 and y2 > y1:
                person_crop = img[y1:y2, x1:x2]
                try:
                    # Detect faces in crop (lower threshold slightly for smaller crops)
                    faces = face_pipeline.detect_faces(person_crop, score_threshold=0.5)
                    if faces:
                        # Use the face with the highest score
                        faces.sort(key=lambda x: x["score"], reverse=True)
                        face = faces[0]
                        
                        # Extract embedding
                        embedding = face_pipeline.extract_embedding(person_crop, face["raw_face"])
                        emb_arr = np.array(embedding, dtype=np.float32)
                        
                        # Find best match using cosine similarity
                        best_sim = -1.0
                        best_match = None
                        
                        for pt in parsed_templates:
                            dot = np.dot(emb_arr, pt["vector"])
                            norm_a = np.linalg.norm(emb_arr)
                            norm_b = np.linalg.norm(pt["vector"])
                            if norm_a > 1e-6 and norm_b > 1e-6:
                                sim = dot / (norm_a * norm_b)
                                if sim > best_sim:
                                    best_sim = sim
                                    best_match = pt
                                    
                        # Threshold is 0.6
                        if best_sim >= 0.6 and best_match is not None:
                            identity = {
                                "person_id": best_match["person_id"],
                                "person_name": best_match["person_name"],
                                "identity_type": "KNOWN",
                                "similarity_score": float(best_sim)
                            }
                            tracker.identities[track_id] = identity
                            track.update(identity)
                        else:
                            # Not matched, check against unknown_identities (E03 Re-ID)
                            now = datetime.datetime.utcnow()
                            active_unknowns = db.query(models.UnknownIdentity).filter(
                                models.UnknownIdentity.status == "ACTIVE",
                                models.UnknownIdentity.expire_at > now
                            ).all()
                            
                            best_unk_sim = -1.0
                            best_unk_match = None
                            for unk in active_unknowns:
                                # unk.embedding_vector is a list/vector
                                unk_vec = np.array(unk.embedding_vector, dtype=np.float32)
                                dot = np.dot(emb_arr, unk_vec)
                                norm_a = np.linalg.norm(emb_arr)
                                norm_b = np.linalg.norm(unk_vec)
                                if norm_a > 1e-6 and norm_b > 1e-6:
                                    sim = dot / (norm_a * norm_b)
                                    if sim > best_unk_sim:
                                        best_unk_sim = sim
                                        best_unk_match = unk
                            
                            # Unknown similarity threshold is 0.55
                            if best_unk_sim >= 0.55 and best_unk_match is not None:
                                best_unk_match.last_seen_at = now
                                best_unk_match.visit_count += 1
                                db.commit()
                                
                                identity = {
                                    "person_id": None,
                                    "unknown_id": best_unk_match.id,
                                    "person_name": best_unk_match.anonymous_code,
                                    "identity_type": "UNKNOWN",
                                    "similarity_score": float(best_unk_sim)
                                }
                                tracker.identities[track_id] = identity
                                track.update(identity)
                            else:
                                # Create a new UnknownIdentity with code UNKNOWN_YYYYMMDD_XXXX
                                today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
                                today_end = today_start + datetime.timedelta(days=1)
                                count_today = db.query(models.UnknownIdentity).filter(
                                    models.UnknownIdentity.created_at >= today_start,
                                    models.UnknownIdentity.created_at < today_end
                                ).count()
                                seq = count_today + 1
                                date_str = now.strftime("%Y%m%d")
                                anonymous_code = f"UNKNOWN_{date_str}_{seq:04d}"
                                
                                new_unk = models.UnknownIdentity(
                                    anonymous_code=anonymous_code,
                                    embedding_vector=embedding,
                                    expire_at=now + datetime.timedelta(hours=24),
                                    status="ACTIVE",
                                    visit_count=1,
                                    created_at=now,
                                    last_seen_at=now
                                )
                                db.add(new_unk)
                                db.flush()
                                db.commit()
                                
                                identity = {
                                    "person_id": None,
                                    "unknown_id": new_unk.id,
                                    "person_name": anonymous_code,
                                    "identity_type": "UNKNOWN",
                                    "similarity_score": float(best_sim) if best_sim > -1.0 else 0.0
                                }
                                tracker.identities[track_id] = identity
                                track.update(identity)
                except Exception as ex:
                    print(f"Error during face matching for track {track_id}: {ex}")

    # For each crossing event, link it with identified details and write to DB
    for event in crossing_events:
        track_id = event["track_id"]
        direction = event["direction"] # ENTRY or EXIT
        
        # Look up identity
        identity_type = "UNKNOWN"
        person_id = None
        unknown_id = None
        confidence = 0.9
        
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
                
        # Write Event and VisitSession to DB
        try:
            camera = db.query(models.Camera).first()
            if not camera:
                camera = models.Camera(
                    name="Default Camera",
                    source_type="WEBCAM",
                    source_url="0",
                    status="ONLINE"
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
                timestamp=datetime.datetime.utcnow()
            )
            db.add(db_event)
            db.flush()
            
            if identity_type == "KNOWN" and person_id is not None:
                if direction == "ENTRY":
                    # Check if active session exists for this person
                    active_sess = db.query(models.VisitSession).filter_by(
                        person_id=person_id,
                        status="ACTIVE"
                    ).first()
                    if not active_sess:
                        new_sess = models.VisitSession(
                            identity_type="KNOWN",
                            person_id=person_id,
                            entry_camera_id=camera.id,
                            entry_event_id=db_event.id,
                            entry_at=datetime.datetime.utcnow(),
                            status="ACTIVE"
                        )
                        db.add(new_sess)
                elif direction == "EXIT":
                    # Find active session
                    active_sess = db.query(models.VisitSession).filter_by(
                        person_id=person_id,
                        status="ACTIVE"
                    ).first()
                    if active_sess:
                        active_sess.exit_camera_id = camera.id
                        active_sess.exit_event_id = db_event.id
                        active_sess.exit_at = datetime.datetime.utcnow()
                        active_sess.status = "CLOSED"
                        delta = (active_sess.exit_at - active_sess.entry_at).total_seconds()
                        active_sess.duration_seconds = int(delta)
            elif identity_type == "UNKNOWN" and unknown_id is not None:
                if direction == "ENTRY":
                    # Check if active session exists for this unknown visitor
                    active_sess = db.query(models.VisitSession).filter_by(
                        unknown_id=unknown_id,
                        status="ACTIVE"
                    ).first()
                    if not active_sess:
                        new_sess = models.VisitSession(
                            identity_type="UNKNOWN",
                            unknown_id=unknown_id,
                            entry_camera_id=camera.id,
                            entry_event_id=db_event.id,
                            entry_at=datetime.datetime.utcnow(),
                            status="ACTIVE"
                        )
                        db.add(new_sess)
                elif direction == "EXIT":
                    # Find active session
                    active_sess = db.query(models.VisitSession).filter_by(
                        unknown_id=unknown_id,
                        status="ACTIVE"
                    ).first()
                    if active_sess:
                        active_sess.exit_camera_id = camera.id
                        active_sess.exit_event_id = db_event.id
                        active_sess.exit_at = datetime.datetime.utcnow()
                        active_sess.status = "CLOSED"
                        delta = (active_sess.exit_at - active_sess.entry_at).total_seconds()
                        active_sess.duration_seconds = int(delta)
            
            db.commit()
            print(f"[DB Log] Event logged: {direction} for track {track_id} ({identity_type})")
        except Exception as ex:
            db.rollback()
            print(f"Error logging crossing event: {ex}")
            
    print(f"[API] Frame processed: tracks={tracks}, crossing_events={crossing_events}")
    
    return {
        "session_id": session_id,
        "tracks": tracks,
        "crossing_events": crossing_events
    }

@app.post("/api/persons/register", status_code=status.HTTP_201_CREATED)
async def register_person(
    full_name: str = Form(...),
    member_code: str = Form(...),
    role: str = Form(...),
    status_str: str = Form("ACTIVE", alias="status"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # 1. Check duplicate member_code
    db_person = db.query(models.Person).filter_by(member_code=member_code).first()
    if db_person:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Member code {member_code} is already registered."
        )
        
    # 2. Read and decode uploaded image
    try:
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Decoded image is None")
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database transaction failed: {str(e)}"
        )

@app.get("/api/persons")
async def get_persons(db: Session = Depends(get_db)):
    persons = db.query(models.Person).all()
    return [
        {
            "id": p.id,
            "full_name": p.full_name,
            "member_code": p.member_code,
            "role": p.role,
            "status": p.status
        }
        for p in persons
    ]

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
        return {"message": "Person deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/events")
async def get_events(db: Session = Depends(get_db)):
    events = db.query(models.Event).order_by(models.Event.timestamp.desc()).all()
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
            
        result.append({
            "id": e.id,
            "event_type": e.event_type,
            "identity_type": e.identity_type,
            "person_name": name,
            "member_code": code,
            "timestamp": e.timestamp.isoformat(),
            "confidence": e.confidence
        })
    return result

@app.get("/api/sessions")
async def get_sessions(db: Session = Depends(get_db), date: str = None):
    query = db.query(models.VisitSession)
    
    # E04: Optional date filter (format: YYYY-MM-DD)
    if date:
        try:
            filter_date = datetime.datetime.strptime(date, "%Y-%m-%d")
            day_start = filter_date.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + datetime.timedelta(days=1)
            query = query.filter(
                models.VisitSession.entry_at >= day_start,
                models.VisitSession.entry_at < day_end
            )
        except ValueError:
            pass  # If date format is invalid, return all sessions
    
    sessions = query.order_by(models.VisitSession.entry_at.desc()).all()
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
    return result

@app.get("/api/stats/occupancy")
async def get_occupancy(db: Session = Depends(get_db)):
    today_start = datetime.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    entries = db.query(models.Event).filter(
        models.Event.event_type == "ENTRY",
        models.Event.timestamp >= today_start
    ).count()
    
    exits = db.query(models.Event).filter(
        models.Event.event_type == "EXIT",
        models.Event.timestamp >= today_start
    ).count()
    
    active_sessions = db.query(models.VisitSession).filter_by(status="ACTIVE").count()
    
    # E04: Known vs Unknown breakdown
    known_entries = db.query(models.Event).filter(
        models.Event.event_type == "ENTRY",
        models.Event.identity_type == "KNOWN",
        models.Event.timestamp >= today_start
    ).count()
    
    unknown_entries = db.query(models.Event).filter(
        models.Event.event_type == "ENTRY",
        models.Event.identity_type == "UNKNOWN",
        models.Event.timestamp >= today_start
    ).count()
    
    total_sessions = db.query(models.VisitSession).filter(
        models.VisitSession.entry_at >= today_start
    ).count()
    
    return {
        "current_occupancy": active_sessions,
        "total_entries_today": entries,
        "total_exits_today": exits,
        "known_visitors_today": known_entries,
        "unknown_visitors_today": unknown_entries,
        "total_sessions_today": total_sessions
    }

@app.get("/api/stats/hourly")
async def get_hourly_stats(db: Session = Depends(get_db)):
    today_start = datetime.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    events = db.query(models.Event).filter(models.Event.timestamp >= today_start).all()
    
    hourly_data = {hour: {"entry": 0, "exit": 0} for hour in range(24)}
    for e in events:
        hour = e.timestamp.hour
        if e.event_type == "ENTRY":
            hourly_data[hour]["entry"] += 1
        elif e.event_type == "EXIT":
            hourly_data[hour]["exit"] += 1
            
    return [{"hour": h, "entry": d["entry"], "exit": d["exit"]} for h, d in hourly_data.items()]

class CameraCreate(BaseModel):
    name: str
    source_type: str # 'WEBCAM', 'FILE', 'RTSP'
    source_url: str

@app.get("/api/cameras")
async def get_cameras(db: Session = Depends(get_db)):
    cameras = db.query(models.Camera).all()
    return [
        {
            "id": c.id,
            "name": c.name,
            "source_type": c.source_type,
            "source_url": c.source_url,
            "status": c.status,
            "last_online_at": c.last_online_at.isoformat() if c.last_online_at else None
        }
        for c in cameras
    ]

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
        cap = cv2.VideoCapture(data.source_url)
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
        cap = cv2.VideoCapture(camera.source_url)
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

@app.get("/")
async def root():
    return {"message": "Welcome to LibCounterAI API. Visit /api/health for system status."}

if __name__ == "__main__":
    import uvicorn
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    reload_mode = os.environ.get("RELOAD", "false").lower() == "true"
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=reload_mode)
