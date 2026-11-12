
import logging
import os
import re
import subprocess
import tempfile

from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from django.core.management import call_command
from django.conf import settings

from supabase import create_client

from .database_backup import (
    BUCKET_NAME,
    MAX_BACKUP_SIZE,
    get_backup_manifest,
)


logger = logging.getLogger(__name__)

RESTORE_TIMEOUT = 600

BACKUP_FILENAME_PATTERN = re.compile(
    r"^aksyon-db-\d{8}T\d{6}Z-[a-f0-9]{8}\.dump$"
)


class RestoreError(Exception):
    """Raised when a database restore cannot be completed."""


class RestoreRejected(Exception):
    """Raised when a restore request fails a safety check."""


def get_database_connection():
    database_url = os.environ.get("DATABASE_URL")

    if not database_url:
        raise RestoreError("DATABASE_URL is not configured.")

    parsed_url = urlparse(database_url)

    if parsed_url.scheme not in ("postgres", "postgresql"):
        raise RestoreError("DATABASE_URL is not a PostgreSQL URL.")

    if not all([
        parsed_url.hostname,
        parsed_url.username,
        parsed_url.path.strip("/"),
    ]):
        raise RestoreError(
            "DATABASE_URL is missing required connection details."
        )

    ssl_mode = parse_qs(parsed_url.query).get(
        "sslmode",
        ["require"],
    )[0]

    if ssl_mode not in ("require", "verify-ca", "verify-full"):
        raise RestoreError(
            "Database connections must use SSL."
        )

    return {
        "host": parsed_url.hostname,
        "port": str(parsed_url.port or 5432),
        "username": unquote(parsed_url.username),
        "password": unquote(parsed_url.password or ""),
        "database": unquote(parsed_url.path.lstrip("/")),
        "ssl_mode": ssl_mode,
    }


def get_postgres_environment(config):
    env = os.environ.copy()

    env["PGPASSWORD"] = config["password"]
    env["PGSSLMODE"] = config["ssl_mode"]
    env["PGCONNECT_TIMEOUT"] = "15"

    return env


def restore_database_backup(filename):
    if not isinstance(filename, str) or not (
        BACKUP_FILENAME_PATTERN.fullmatch(filename)
    ):
        raise RestoreRejected("Invalid backup filename.")

    if not settings.SUPABASE_URL or not settings.SUPABASE_SECRET_KEY:
        raise RestoreError(
            "Supabase storage credentials are not configured."
        )

    config = get_database_connection()
    env = get_postgres_environment(config)

    try:
        supabase = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SECRET_KEY,
        )

        backup_data = supabase.storage.from_(
            BUCKET_NAME
        ).download(filename)

    except Exception as exc:
        logger.exception("Could not download the selected backup.")

        raise RestoreError(
            "Could not download the selected backup."
        ) from exc

    if not backup_data:
        raise RestoreError("The selected backup is empty.")

    if len(backup_data) > MAX_BACKUP_SIZE:
        raise RestoreError(
            "The selected backup exceeds the permitted size."
        )

    with tempfile.TemporaryDirectory(
        prefix="aksyon-restore-"
    ) as temp_dir:
        dump_path = Path(temp_dir) / filename
        dump_path.write_bytes(backup_data)

        # Validate the archive before touching the database.
        try:
            validation = subprocess.run(
                [
                    "pg_restore",
                    "--list",
                    str(dump_path),
                ],
                env=env,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )

        except subprocess.TimeoutExpired as exc:
            raise RestoreError(
                "Backup archive validation timed out."
            ) from exc

        except OSError as exc:
            raise RestoreError(
                "Could not validate the backup archive."
            ) from exc

        if validation.returncode != 0:
            logger.error(
                "Backup validation failed: %s",
                (validation.stderr or "No diagnostic output")[-2000:],
            )

            raise RestoreError(
                "The selected backup failed archive validation."
            )

        command = [
            "pg_restore",
            "--host", config["host"],
            "--port", config["port"],
            "--username", config["username"],
            "--dbname", config["database"],
            "--no-password",
            "--schema=public",
            "--clean",
            "--if-exists",
            "--no-owner",
            "--no-privileges",
            "--single-transaction",
            "--exit-on-error",
            str(dump_path),
        ]

        try:
            result = subprocess.run(
                command,
                env=env,
                capture_output=True,
                text=True,
                timeout=RESTORE_TIMEOUT,
                check=False,
            )

        except subprocess.TimeoutExpired as exc:
            raise RestoreError(
                "Database restoration timed out. "
                "PostgreSQL rolled back the restore transaction."
            ) from exc

        except OSError as exc:
            raise RestoreError(
                "Could not run pg_restore."
            ) from exc

        if result.returncode != 0:
            logger.error(
                "Database restore failed with exit code %s: %s",
                result.returncode,
                (result.stderr or "No diagnostic output")[-4000:],
            )

            raise RestoreError(
                "Database restoration failed. "
                "PostgreSQL rolled back the restore transaction."
            )

    # This command is deliberately outside the pg_restore transaction.
    # It resets the built-in privileged admin password from environment
    # variables after the database has been successfully restored.
    try:
        call_command(
            "create_privileged_admin",
            verbosity=0,
        )

    except Exception:
        logger.exception(
            "Database restore succeeded, but privileged admin "
            "bootstrap verification failed."
        )

        # Do not report the database restore as failed here.
        # The pg_restore transaction has already committed.
        return {
            "filename": filename,
            "message": "Database restored successfully.",
            "admin_bootstrap_warning": (
                "The database was restored, but privileged admin "
                "verification failed. Check the server logs."
            ),
        }

    return {
        "filename": filename,
        "message": "Database restored successfully.",
    }
