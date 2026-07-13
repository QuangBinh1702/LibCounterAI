import argparse
import datetime
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "app"))

from database import DATABASE_URL


def parse_db_url(url: str) -> dict:
    parts = url.split("://", 1)
    if len(parts) != 2:
        return {}

    scheme_rest = parts[0]
    rest = parts[1]

    if "@" in rest:
        creds, host_part = rest.split("@", 1)
        user_pass = creds.split(":", 1)
        user = user_pass[0]
        pwd = user_pass[1] if len(user_pass) > 1 else ""
    else:
        user = pwd = ""
        host_part = rest

    if "/" in host_part:
        host_port, db = host_part.rsplit("/", 1)
    else:
        host_port = host_part
        db = ""

    if ":" in host_port:
        host, port = host_port.split(":", 1)
    else:
        host = host_port
        port = "5432"

    return {"user": user, "password": pwd, "host": host, "port": port, "db": db}


def main():
    parser = argparse.ArgumentParser(description="Backup LibCounterAI database")
    parser.add_argument("--output-dir", default=str(ROOT_DIR / "backups"), help="Backup output directory")
    parser.add_argument("--keep-days", type=int, default=30, help="Delete backups older than N days")
    args = parser.parse_args()

    if not DATABASE_URL.startswith("postgresql"):
        print("Backup script only supports PostgreSQL. Current DB:", DATABASE_URL)
        sys.exit(1)

    info = parse_db_url(DATABASE_URL)
    if not info.get("db"):
        print("Cannot parse DATABASE_URL:", DATABASE_URL)
        sys.exit(1)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"libcounterai_{timestamp}.sql"
    filepath = output_dir / filename

    env = os.environ.copy()
    env["PGPASSWORD"] = info["password"]

    cmd = [
        "pg_dump",
        "-h", info["host"],
        "-p", info["port"],
        "-U", info["user"],
        "-d", info["db"],
        "-F", "c",
        "-f", str(filepath),
    ]

    pg_dump_bin = shutil.which("pg_dump")
    if not pg_dump_bin:
        print("ERROR: pg_dump not found. Install PostgreSQL client tools or add pg_dump to PATH.")
        sys.exit(1)

    print(f"Backing up {info['db']}@{info['host']}:{info['port']} -> {filepath}")
    result = subprocess.run([pg_dump_bin] + cmd[1:], env=env, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"Backup failed: {result.stderr}")
        sys.exit(1)

    size_mb = filepath.stat().st_size / (1024 * 1024)
    print(f"Backup complete: {filename} ({size_mb:.2f} MB)")

    # Cleanup old backups
    cutoff = datetime.datetime.now() - datetime.timedelta(days=args.keep_days)
    removed = 0
    for f in sorted(output_dir.glob("libcounterai_*.sql")):
        mtime = datetime.datetime.fromtimestamp(f.stat().st_mtime)
        if mtime < cutoff:
            f.unlink()
            removed += 1

    if removed:
        print(f"Cleaned up {removed} old backup(s) (>{args.keep_days} days)")


if __name__ == "__main__":
    main()
