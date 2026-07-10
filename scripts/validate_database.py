import os
import sys
import datetime

# Ensure app path is in sys.path
CWD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(CWD, "app"))

try:
    from database import engine, Base, SessionLocal
    import models
    print("Database connection & models imported successfully.")
except Exception as e:
    print(f"Error importing database/models: {e}")
    sys.exit(1)


def cleanup_test_records(db):
    test_person = db.query(models.Person).filter_by(member_code="SV123456").first()
    test_camera = db.query(models.Camera).filter_by(name="Main Entrance Gate").first()
    test_user = db.query(models.User).filter_by(username="librarian_test").first()

    if test_person:
        db.query(models.VisitSession).filter_by(person_id=test_person.id).delete()
        db.query(models.Event).filter_by(person_id=test_person.id).delete()
        db.delete(test_person)

    if test_camera:
        db.query(models.VisitSession).filter_by(entry_camera_id=test_camera.id).delete()
        db.query(models.Event).filter_by(camera_id=test_camera.id).delete()
        db.query(models.CameraConfig).filter_by(camera_id=test_camera.id).delete()
        db.delete(test_camera)

    if test_user:
        db.delete(test_user)

    db.commit()


# 1. Create tables
print("Creating database tables...")
try:
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")
except Exception as e:
    print(f"Error creating tables: {e}")
    sys.exit(1)

# 2. Test inserting dummy data and querying it
print("Testing database CRUD operations...")
db = SessionLocal()
try:
    cleanup_test_records(db)

    # 2.1 Add User
    user = models.User(
        username="librarian_test",
        password_hash="fake_hash",
        role="LIBRARIAN",
        status="ACTIVE"
    )
    db.add(user)
    
    # 2.2 Add Camera
    camera = models.Camera(
        name="Main Entrance Gate",
        source_type="WEBCAM",
        source_url="0",
        status="ONLINE"
    )
    db.add(camera)
    db.flush() # Populate camera.id
    
    # 2.3 Add Camera Config
    camera_config = models.CameraConfig(
        camera_id=camera.id,
        entry_line_config=[[100, 300], [500, 300]],
        exit_line_config=[[100, 300], [500, 300]]
    )
    db.add(camera_config)
    
    # 2.4 Add Person
    person = models.Person(
        full_name="Nguyen Van A",
        member_code="SV123456",
        role="STUDENT",
        status="ACTIVE"
    )
    db.add(person)
    db.flush() # Populate person.id
    
    # 2.5 Add Face Template
    face = models.FaceTemplate(
        person_id=person.id,
        embedding_vector=[0.1] * 128, # 128 dimensions dummy float vector
        model_name="sface",
        model_version="2021dec",
        quality_score=0.95,
        source_type="UPLOAD"
    )
    db.add(face)
    
    # 2.6 Add Event
    event = models.Event(
        event_type="ENTRY",
        identity_type="KNOWN",
        person_id=person.id,
        track_id=1,
        camera_id=camera.id,
        confidence=0.88
    )
    db.add(event)
    db.flush()
    
    # 2.7 Add Visit Session
    session = models.VisitSession(
        identity_type="KNOWN",
        person_id=person.id,
        entry_camera_id=camera.id,
        entry_event_id=event.id,
        entry_at=datetime.datetime.utcnow(),
        status="ACTIVE"
    )
    db.add(session)
    
    db.commit()
    print("Database insert transaction committed successfully.")
    
    # 3. Query and Assertions
    print("Performing assertions and querying data...")
    queried_user = db.query(models.User).filter_by(username="librarian_test").first()
    assert queried_user is not None, "User SV123456 not found"
    assert queried_user.role == "LIBRARIAN", f"Expected LIBRARIAN role, got {queried_user.role}"
    
    queried_person = db.query(models.Person).filter_by(member_code="SV123456").first()
    assert len(queried_person.face_templates) == 1, "Expected 1 face template"
    # Check that vector type returned list
    vector = queried_person.face_templates[0].embedding_vector
    assert isinstance(vector, list), f"Expected list vector, got {type(vector)}"
    assert len(vector) == 128, f"Expected 128 dimensions, got {len(vector)}"
    assert abs(vector[0] - 0.1) < 1e-5, "Vector value mismatch"
    
    print("All database assertions PASSED successfully!")
    
    # 4. Clean up test data
    print("Cleaning up test database records...")
    cleanup_test_records(db)
    print("Cleanup transaction committed successfully.")
    
    db.close()
    sys.exit(0)
    
except Exception as e:
    print(f"Database validation FAILED: {e}")
    db.rollback()
    db.close()
    sys.exit(1)
