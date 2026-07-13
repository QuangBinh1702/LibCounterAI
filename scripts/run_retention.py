import argparse
import os
import sys
import json

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_DIR = os.path.join(ROOT_DIR, "app")
sys.path.insert(0, APP_DIR)

from database import SessionLocal, DATABASE_URL  # noqa: E402
from retention import run_retention, count_pending  # noqa: E402


def display_url(url: str) -> str:
    if "://" not in url:
        return url
    scheme, rest = url.split("://", 1)
    if "@" in rest and ":" in rest.split("@", 1)[0]:
        credentials, host = rest.split("@", 1)
        user = credentials.split(":", 1)[0]
        return f"{scheme}://{user}:***@{host}"
    return url


def main() -> None:
    parser = argparse.ArgumentParser(description="Run retention cleanup on LibCounterAI database.")
    parser.add_argument("--dry-run", action="store_true", help="Log planned actions without deleting data.")
    parser.add_argument("--status", action="store_true", help="Print retention status and exit.")
    args = parser.parse_args()

    print(f"Database: {display_url(DATABASE_URL)}")
    db = SessionLocal()
    try:
        if args.status:
            cfg = {}
            for key in [
                "RETENTION_EVENT_DAYS", "RETENTION_SESSION_DAYS",
                "UNKNOWN_IDENTITY_EXPIRE_HOURS", "RETENTION_UNKNOWN_PURGE_DAYS",
                "RETENTION_TEMPLATE_GRACE_DAYS", "RETENTION_AUDIT_LOG_DAYS",
            ]:
                cfg[key.lower()] = int(os.getenv(key, "0"))
            pending = count_pending(db)
            print("Retention config:")
            for k, v in cfg.items():
                print(f"  {k}={v}")
            print("Pending counts:")
            for k, v in pending.items():
                print(f"  {k}: {v}")
            return

        label = "DRY RUN" if args.dry_run else "RUN"
        print(f"Retention {label}...")
        results = run_retention(db, dry_run=args.dry_run)
        print(f"\n{'Phase':35s} {'Rows':>6s}  Duration  Error")
        print("-" * 65)
        for r in results:
            err = r["error"] or ""
            print(f"{r['phase']:35s} {r['rows_affected']:>6d}  {r['duration_ms']:>4d}ms  {err}")
        print(f"\nRetention {label.lower()} complete.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
