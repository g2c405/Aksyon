
import logging
import os
import subprocess
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from django.conf import settings
from supabase import create_client


logger = logging.getLogger(__name__)

BUCKET_NAME = "aksyon-backups"

# Stay below the bucket's 50 MB upload limit.
MAX_BACKUP_SIZE = 49_000_000


class BackupError(Exception):
    """Raised when database backup creation or upload fails."""


def create_database_backup():
    database_url = os.environ.get("DATABASE_URL")

    if not database_url:
        raise BackupError("DATABASE_URL is not configured.")

    parsed_url = urlparse(database_url)

    if parsed_url.scheme not in ("postgres", "postgresql"):
        raise BackupError("DATABASE_URL is not a PostgreSQL URL.")

    if not all(
        [parsed_url.hostname, parsed_url.username, parsed_url.path.strip("/")]
    ):
        raise BackupError("DATABASE_URL is missing required connection details.")

    # Decode URL-encoded credentials and database name.
    username = unquote(parsed_url.username)
    password = unquote(parsed_url.password or "")
    database_name = unquote(parsed_url.path.lstrip("/"))

    # Supabase database connections should use SSL.
    query_options = parse_qs(parsed_url.query)
    ssl_mode = query_options.get("sslmode", ["require"])[0]

    if ssl_mode not in ("require", "verify-ca", "verify-full"):
        raise BackupError("Database connections must use SSL.")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    filename = f"aksyon-db-{timestamp}-{uuid.uuid4().hex[:8]}.dump"

    with tempfile.TemporaryDirectory(prefix="aksyon-backup-") as temp_dir:
        dump_path = Path(temp_dir) / filename

        # Supply credentials through the subprocess environment.
        env = os.environ.copy()
        env["PGPASSWORD"] = password
        env["PGSSLMODE"] = ssl_mode
        env["PGCONNECT_TIMEOUT"] = "15"

        command = [
            "pg_dump",
            "--host", parsed_url.hostname,
            "--port", str(parsed_url.port or 5432),
            "--username", username,
            "--dbname", database_name,
            "--format=custom",
            "--no-password",
            "--file", str(dump_path),
        ]

        try:
            result = subprocess.run(
                command,
                env=env,
                capture_output=True,
                text=True,
                timeout=300,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise BackupError("Database backup timed out.") from exc
        except OSError as exc:
            raise BackupError("Could not run pg_dump.") from exc

        if result.returncode != 0:
            # Log a limited diagnostic, never the connection URL or password.
            logger.error(
                "pg_dump failed with exit code %s: %s",
                result.returncode,
                (result.stderr or "No diagnostic output")[-2000:],
            )
            raise BackupError(
                "Database backup failed. Check the server logs."
            )

        if not dump_path.is_file() or dump_path.stat().st_size == 0:
            raise BackupError("pg_dump did not produce a backup file.")

        file_size = dump_path.stat().st_size

        if file_size > MAX_BACKUP_SIZE:
            raise BackupError(
                "Backup exceeds the configured upload size limit. "
                "No file was uploaded."
            )

        # Confirm that PostgreSQL can read the dump's archive structure.
        try:
            validation = subprocess.run(
                ["pg_restore", "--list", str(dump_path)],
                env=env,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
        except (subprocess.TimeoutExpired, OSError) as exc:
            raise BackupError(
                "Could not validate the database backup."
            ) from exc

        if validation.returncode != 0:
            logger.error(
                "pg_restore validation failed: %s",
                (validation.stderr or "No diagnostic output")[-2000:],
            )
            raise BackupError(
                "The database backup failed its integrity check."
            )

        try:
            supabase = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_SECRET_KEY,
            )

            with dump_path.open("rb") as backup_file:
                supabase.storage.from_(BUCKET_NAME).upload(
                    path=filename,
                    file=backup_file,
                    file_options={
                        "content-type": "application/octet-stream",
                        "upsert": "false",
                    },
                )
        except Exception as exc:
            logger.exception("Database backup upload failed.")
            raise BackupError(
                "Backup was created but could not be uploaded."
            ) from exc

        return {
            "filename": filename,
            "storage_path": filename,
            "size_bytes": file_size,
            "created_at": timestamp,
        }
