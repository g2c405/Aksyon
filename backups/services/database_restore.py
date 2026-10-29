
import logging
import os
import re
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from supabase import create_client
from django.db import connection
logger = logging.getLogger(__name__)

BUCKET_NAME = "aksyon-backups"
MAX_BACKUP_SIZE = 49_000_000
RESTORE_TIMEOUT = 600

BACKUP_FILENAME_PATTERN = re.compile(
    r"^aksyon-db-\d{8}T\d{6}Z-[a-f0-9]{8}\.dump$"
)

APPLICATION_APP_LABELS = {
    "users",
    "reports",
    "notifications",
    "analytics",
    "announcements",
    "emergency_units",
}


class RestoreError(Exception):
    """Raised when a database restore cannot be completed safely."""

class RestoreRejected(Exception):
    """Raised when a restore request fails a safety check."""


def ensure_database_is_ready_for_restore():
    """
    Permit restoration into a genuinely empty database schema.
    Otherwise, require the expected application tables to exist
    and reject restoration if unexpected data is present.
    """
    User = get_user_model()

    # Inspect the schema before querying Django models.
    existing_tables = set(
        connection.introspection.table_names()
    )

    # The schema was dropped or the database has no visible tables.
    # Allow the restore service to proceed to archive validation.
    if not existing_tables:
        return

    # A partially missing schema is not safe to restore over blindly.
    if User._meta.db_table not in existing_tables:
        raise RestoreRejected(
            "Restore refused: the database schema is partially "
            "initialized. Restore only into an empty schema or "
            "a fully initialized, empty application database."
        )

    privileged_username = os.environ.get(
        "PRIVILEGED_ADMIN_USERNAME"
    )

    if not privileged_username:
        raise RestoreError(
            "PRIVILEGED_ADMIN_USERNAME is not configured."
        )

    allowed_usernames = {
        privileged_username,
        "devadmin",
    }

    if User.objects.exclude(
        username__in=allowed_usernames
    ).exists():
        raise RestoreRejected(
            "Restore refused: unexpected user accounts exist."
        )

    # Verify that the expected application tables exist before
    # querying their models.
    for model in apps.get_models():
        if (
            model._meta.app_label not in APPLICATION_APP_LABELS
            or model is User
            or model._meta.proxy
            or model._meta.abstract
            or model._meta.auto_created
            or not model._meta.managed
        ):
            continue

        if model._meta.db_table not in existing_tables:
            raise RestoreRejected(
                "Restore refused: an application table is missing. "
                "The database schema is incomplete."
            )

        if model.objects.exists():
            raise RestoreRejected(
                "Restore refused: application data already exists."
            )

def _get_database_connection():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RestoreError("DATABASE_URL is not configured.")

    parsed_url = urlparse(database_url)

    if parsed_url.scheme not in ("postgres", "postgresql"):
        raise RestoreError("DATABASE_URL is not a PostgreSQL URL.")

    if not all(
        [
            parsed_url.hostname,
            parsed_url.username,
            parsed_url.path.strip("/"),
        ]
    ):
        raise RestoreError(
            "DATABASE_URL is missing required connection details."
        )

    ssl_mode = parse_qs(parsed_url.query).get(
        "sslmode", ["require"]
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


def restore_database_backup(filename):
    if not isinstance(filename, str) or not (
        BACKUP_FILENAME_PATTERN.fullmatch(filename)
    ):
        raise RestoreRejected("Invalid backup filename.")

    ensure_database_is_ready_for_restore()

    if not settings.SUPABASE_URL or not settings.SUPABASE_SECRET_KEY:
        raise RestoreError(
            "Supabase storage credentials are not configured."
        )

    connection = _get_database_connection()

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

        env = os.environ.copy()
        env["PGPASSWORD"] = connection["password"]
        env["PGSSLMODE"] = connection["ssl_mode"]
        env["PGCONNECT_TIMEOUT"] = "15"

        base_command = [
            "--host", connection["host"],
            "--port", connection["port"],
            "--username", connection["username"],
            "--dbname", connection["database"],
            "--no-password",
        ]

        try:
            validation = subprocess.run(
                ["pg_restore", "--list", str(dump_path)],
                env=env,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise RestoreError(
                "Could not validate the backup archive."
            ) from exc

        if validation.returncode != 0:
            logger.error(
                "Backup validation failed: %s",
                (validation.stderr or "")[-2000:],
            )
            raise RestoreError(
                "The selected backup failed archive validation."
            )

        command = [
            "pg_restore",
            *base_command,
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
                "Database restoration timed out."
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
                "Check the server logs."
            )

    try:
        call_command("create_privileged_admin")
    except Exception as exc:
        logger.exception(
            "Restore succeeded, but default account verification failed."
        )
        raise RestoreError(
            "The database was restored, but default account "
            "verification failed. Check the server logs before retrying."
        ) from exc

    return {
        "filename": filename,
        "message": "Database restored successfully.",
    }
