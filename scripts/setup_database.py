import argparse
import os
import sys

from sqlalchemy import text


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_DIR = os.path.join(ROOT_DIR, "app")
sys.path.insert(0, APP_DIR)

from database import DATABASE_URL, Base, SessionLocal, engine  # noqa: E402
import models  # noqa: E402,F401


def display_url(url: str) -> str:
    if "://" not in url:
        return url
    scheme, rest = url.split("://", 1)
    if "@" in rest and ":" in rest.split("@", 1)[0]:
        credentials, host = rest.split("@", 1)
        user = credentials.split(":", 1)[0]
        return f"{scheme}://{user}:***@{host}"
    return url


def seed_demo_camera() -> None:
    db = SessionLocal()
    try:
        existing = db.query(models.Camera).filter_by(name="Demo Gate").first()
        if existing:
            print("Demo camera already exists.")
            return

        camera = models.Camera(
            name="Demo Gate",
            source_type="RTSP",
            source_url="rtsp://demo.local/library",
            status="OFFLINE",
        )
        db.add(camera)
        db.commit()
        print("Seeded demo camera: Demo Gate.")
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
    parser.add_argument("--seed-demo", action="store_true", help="Insert a small demo camera row if it is missing.")
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
        seed_demo_camera()


if __name__ == "__main__":
    main()
