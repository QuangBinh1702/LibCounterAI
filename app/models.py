import json
import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, JSON, Text, TypeDecorator
from sqlalchemy.orm import relationship
from database import Base

# --- Custom Vector Type for SQLite / Postgres Compatibility ---
class VectorType(TypeDecorator):
    impl = Text
    cache_ok = True
    
    def __init__(self, dim=512):
        super().__init__()
        self.dim = dim
        try:
            from pgvector.sqlalchemy import Vector
            self.pg_vector = Vector(dim)
        except ImportError:
            self.pg_vector = None

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql" and self.pg_vector is not None:
            return dialect.type_descriptor(self.pg_vector)
        return dialect.type_descriptor(Text())

    def process_bind_param(self, value, dialect):
        if value is not None:
            if dialect.name == "postgresql":
                return value
            else:
                if not isinstance(value, str):
                    import numpy as np
                    if isinstance(value, np.ndarray):
                        value = value.tolist()
                    value = json.dumps(value)
                return value
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            if dialect.name == "postgresql" and not isinstance(value, str):
                # pgvector may return a native list/array when the driver is registered.
                return value
            try:
                return json.loads(value)
            except Exception:
                return [float(x) for x in value.strip("[]").split(",") if x]
        return value


# --- Models Definitions ---

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="LIBRARIAN") # 'ADMIN', 'LIBRARIAN'
    status = Column(String(20), nullable=False, default="ACTIVE") # 'ACTIVE', 'INACTIVE'
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class Person(Base):
    __tablename__ = "persons"
    
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(100), nullable=False)
    member_code = Column(String(50), unique=True, nullable=False, index=True)
    role = Column(String(20), nullable=False) # 'STUDENT', 'FACULTY', 'STAFF', 'GUEST'
    status = Column(String(20), nullable=False, default="PENDING") # 'PENDING', 'ACTIVE', 'INACTIVE'
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relationships
    face_templates = relationship("FaceTemplate", back_populates="person", cascade="all, delete-orphan")
    events = relationship("Event", back_populates="person")
    visit_sessions = relationship("VisitSession", back_populates="person")


class FaceTemplate(Base):
    __tablename__ = "face_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    person_id = Column(Integer, ForeignKey("persons.id", ondelete="CASCADE"), nullable=False)
    embedding_vector = Column(VectorType(128), nullable=False)
    model_name = Column(String(50), nullable=False, default="sface")
    model_version = Column(String(20), nullable=False, default="2021dec")
    quality_score = Column(Float, nullable=False, default=1.0)
    source_type = Column(String(20), nullable=False, default="UPLOAD") # 'UPLOAD', 'CAMERA'
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)
    
    # Relationships
    person = relationship("Person", back_populates="face_templates")


class UnknownIdentity(Base):
    __tablename__ = "unknown_identities"
    
    id = Column(Integer, primary_key=True, index=True)
    anonymous_code = Column(String(50), unique=True, nullable=False, index=True)
    embedding_vector = Column(VectorType(128), nullable=False)
    first_seen_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)
    last_seen_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    visit_count = Column(Integer, default=1)
    expire_at = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(20), nullable=False, default="ACTIVE") # 'ACTIVE', 'EXPIRED'
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)
    
    # Relationships
    events = relationship("Event", back_populates="unknown_identity")
    visit_sessions = relationship("VisitSession", back_populates="unknown_identity")


class Camera(Base):
    __tablename__ = "cameras"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    source_type = Column(String(20), nullable=False) # 'WEBCAM', 'FILE', 'RTSP'
    source_url = Column(String(500), nullable=False)
    status = Column(String(20), nullable=False, default="OFFLINE") # 'ONLINE', 'OFFLINE', 'ERROR'
    last_online_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relationships
    config = relationship("CameraConfig", back_populates="camera", uselist=False, cascade="all, delete-orphan")
    events = relationship("Event", back_populates="camera")


class CameraConfig(Base):
    __tablename__ = "camera_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id", ondelete="CASCADE"), unique=True, nullable=False)
    entry_line_config = Column(JSON, nullable=False) # e.g. [[x1, y1], [x2, y2]]
    exit_line_config = Column(JSON, nullable=False)
    inside_zone_config = Column(JSON, nullable=True)
    outside_zone_config = Column(JSON, nullable=True)
    roi_config = Column(JSON, nullable=True)
    debounce_seconds = Column(Integer, default=5)
    person_detection_confidence = Column(Float, default=0.5)
    face_detection_confidence = Column(Float, default=0.6)
    recognition_threshold = Column(Float, default=0.6)
    unknown_threshold = Column(Float, default=0.55)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relationships
    camera = relationship("Camera", back_populates="config")


class Event(Base):
    __tablename__ = "events"
    
    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(20), nullable=False) # 'ENTRY', 'EXIT', 'SEEN', 'UNMATCHED_EXIT'
    identity_type = Column(String(20), nullable=False) # 'KNOWN', 'UNKNOWN', 'UNRESOLVED'
    person_id = Column(Integer, ForeignKey("persons.id", ondelete="SET NULL"), nullable=True)
    unknown_id = Column(Integer, ForeignKey("unknown_identities.id", ondelete="SET NULL"), nullable=True)
    track_id = Column(Integer, nullable=False)
    camera_id = Column(Integer, ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=datetime.datetime.utcnow)
    confidence = Column(Float, nullable=False)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)
    
    # Relationships
    person = relationship("Person", back_populates="events")
    unknown_identity = relationship("UnknownIdentity", back_populates="events")
    camera = relationship("Camera", back_populates="events")


class VisitSession(Base):
    __tablename__ = "visit_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    identity_type = Column(String(20), nullable=False) # 'KNOWN', 'UNKNOWN'
    person_id = Column(Integer, ForeignKey("persons.id", ondelete="SET NULL"), nullable=True)
    unknown_id = Column(Integer, ForeignKey("unknown_identities.id", ondelete="SET NULL"), nullable=True)
    entry_camera_id = Column(Integer, ForeignKey("cameras.id", ondelete="SET NULL"), nullable=True)
    entry_event_id = Column(Integer, ForeignKey("events.id", ondelete="SET NULL"), nullable=True)
    exit_camera_id = Column(Integer, ForeignKey("cameras.id", ondelete="SET NULL"), nullable=True)
    exit_event_id = Column(Integer, ForeignKey("events.id", ondelete="SET NULL"), nullable=True)
    entry_at = Column(DateTime(timezone=True), nullable=False)
    exit_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    status = Column(String(20), nullable=False, default="ACTIVE") # 'ACTIVE', 'CLOSED', 'UNMATCHED', 'TIMEOUT'
    confidence_avg = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relationships
    person = relationship("Person", back_populates="visit_sessions")
    unknown_identity = relationship("UnknownIdentity", back_populates="visit_sessions")
