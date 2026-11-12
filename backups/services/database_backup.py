
import json
import logging
import os
import subprocess
import tempfile
import uuid

from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from django.conf import settings
from django.db import connection, transaction
from supabase import create_client

from .audit_log_export import export_audit_logs_csv


logger = logging.getLogger(__name__)

BUCKET_NAME = "aksyon-backups"

# Stay below the bucket's 50 MB upload limit.
MAX_BACKUP_SIZE = 49_000_000

MAX_DESCRIPTION_LENGTH = 150

BACKUP_FILENAME_PATTERN = (
    r"^aksyon-db-\d{8}T\d{6}Z-[a-f0-9]{8}\.dump$"
)


class BackupError(Exception):
    """Raised when database backup creation or upload fails."""


def get_storage():
    if not settings.SUPABASE_URL or not settings.SUPABASE_SECRET_KEY:
        raise BackupError(
            "Supabase storage credentials are not configured."
        )

    supabase = create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_SECRET_KEY,
    )

    return supabase.storage.from_(BUCKET_NAME)


def get_database_connection_config():
    database_url = os.environ.get("DATABASE_URL")

    if not database_url:
        raise BackupError("DATABASE_URL is not configured.")

    parsed_url = urlparse(database_url)

    if parsed_url.scheme not in ("postgres", "postgresql"):
        raise BackupError("DATABASE_URL is not a PostgreSQL URL.")

    if not all([
        parsed_url.hostname,
        parsed_url.username,
        parsed_url.path.strip("/"),
    ]):
        raise BackupError(
            "DATABASE_URL is missing required connection details."
        )

    ssl_mode = parse_qs(parsed_url.query).get(
        "sslmode",
        ["require"],
    )[0]

    if ssl_mode not in ("require", "verify-ca", "verify-full"):
        raise BackupError("Database connections must use SSL.")

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


def upload_file(storage, filename, file_path, content_type):
    with open(file_path, "rb") as file:
        storage.upload(
            path=filename,
            file=file,
            file_options={
                "content-type": content_type,
                "upsert": "false",
            },
        )


def remove_uploaded_files(storage, filenames):
    try:
        storage.remove(filenames)
    except Exception:
        logger.exception(
            "Could not clean up an incomplete backup package."
        )


def create_database_backup(description):
    if not isinstance(description, str):
        raise BackupError("Backup description must be a string.")

    description = description.strip()

    if not description:
        raise BackupError("Backup description is required.")

    if len(description) > MAX_DESCRIPTION_LENGTH:
        raise BackupError(
            f"Description cannot exceed {MAX_DESCRIPTION_LENGTH} characters."
        )

    config = get_database_connection_config()
    env = get_postgres_environment(config)

    timestamp = datetime.now(timezone.utc).strftime(
        "%Y%m%dT%H%M%SZ"
    )

    created_at = datetime.now(timezone.utc).isoformat()

    filename = (
        f"aksyon-db-{timestamp}-{uuid.uuid4().hex[:8]}.dump"
    )

    csv_filename = (
        filename.removesuffix(".dump") + "-audit-logs.csv"
    )

    manifest_filename = f"{filename}.json"

    storage = get_storage()

    uploaded_files = []

    try:
        with tempfile.TemporaryDirectory(
            prefix="aksyon-backup-"
        ) as temp_dir:
            dump_path = Path(temp_dir) / filename
            csv_path = Path(temp_dir) / csv_filename
            manifest_path = Path(temp_dir) / manifest_filename

            # A snapshot must be exported from the same database
            # that pg_dump connects to.
            if connection.in_atomic_block:
                raise BackupError(
                    "Backup cannot run inside an existing database transaction."
                )

            with transaction.atomic():
                with connection.cursor() as cursor:
                    # This must be the first SQL statement in this transaction.
                    cursor.execute(
                        "SET TRANSACTION "
                        "ISOLATION LEVEL REPEATABLE READ, READ ONLY"
                    )

                    cursor.execute("SELECT pg_export_snapshot()")
                    snapshot_id = cursor.fetchone()[0]

                command = [
                    "pg_dump",
                    "--host", config["host"],
                    "--port", config["port"],
                    "--username", config["username"],
                    "--dbname", config["database"],
                    "--format=custom",
                    "--schema=public",
                    "--no-password",
                    "--snapshot", snapshot_id,
                    "--file", str(dump_path),
                ]

                try:
                    result = subprocess.run(
                        command,
                        env=env,
                        capture_output=True,
                        text=True,
                        timeout=600,
                        check=False,
                    )
                except subprocess.TimeoutExpired as exc:
                    raise BackupError(
                        "Database backup timed out."
                    ) from exc
                except OSError as exc:
                    raise BackupError(
                        "Could not run pg_dump."
                    ) from exc

                if result.returncode != 0:
                    logger.error(
                        "pg_dump failed with exit code %s: %s",
                        result.returncode,
                        (result.stderr or "No diagnostic output")[-2000:],
                    )

                    raise BackupError(
                        "Database backup failed. Check the server logs."
                    )

                if not dump_path.is_file() or dump_path.stat().st_size == 0:
                    raise BackupError(
                        "pg_dump did not produce a backup file."
                    )

                # This query uses the same exported transaction snapshot.
                export_audit_logs_csv(csv_path)

            # The snapshot transaction has now ended.
            dump_size = dump_path.stat().st_size
            csv_size = csv_path.stat().st_size

            if dump_size > MAX_BACKUP_SIZE:
                raise BackupError(
                    "Database dump exceeds the configured upload size limit."
                )

            if csv_size > MAX_BACKUP_SIZE:
                raise BackupError(
                    "Audit log CSV exceeds the configured upload size limit."
                )

            # Validate the PostgreSQL archive before uploading.
            validation = subprocess.run(
                ["pg_restore", "--list", str(dump_path)],
                env=env,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )

            if validation.returncode != 0:
                logger.error(
                    "pg_restore validation failed: %s",
                    (validation.stderr or "No diagnostic output")[-2000:],
                )

                raise BackupError(
                    "The database backup failed its integrity check."
                )

            manifest = {
                "version": 1,
                "filename": filename,
                "audit_csv_filename": csv_filename,
                "description": description,
                "backup_type": "full",
                "created_at": created_at,
                "dump_size_bytes": dump_size,
                "audit_csv_size_bytes": csv_size,
                "format": "postgresql_custom",
            }

            manifest_path.write_text(
                json.dumps(manifest, indent=2),
                encoding="utf-8",
            )

            # Upload the dump first, then the CSV, then the manifest.
            # The manifest is the package's completion indicator.
            upload_file(
                storage,
                filename,
                dump_path,
                "application/octet-stream",
            )
            uploaded_files.append(filename)

            upload_file(
                storage,
                csv_filename,
                csv_path,
                "text/csv",
            )
            uploaded_files.append(csv_filename)

            upload_file(
                storage,
                manifest_filename,
                manifest_path,
                "application/json",
            )
            uploaded_files.append(manifest_filename)

            return {
                **manifest,
                "storage_path": filename,
            }

    except BackupError:
        if uploaded_files:
            remove_uploaded_files(storage, uploaded_files)
        raise

    except Exception as exc:
        if uploaded_files:
            remove_uploaded_files(storage, uploaded_files)

        logger.exception("Database backup creation failed.")

        raise BackupError(
            "Database backup failed. Check the server logs."
        ) from exc


def get_backup_manifest(filename):
    import re

    if not isinstance(filename, str) or not re.fullmatch(
        BACKUP_FILENAME_PATTERN,
        filename,
    ):
        raise BackupError("Invalid backup filename.")

    storage = get_storage()

    try:
        content = storage.download(f"{filename}.json")
        manifest = json.loads(content.decode("utf-8"))

        if manifest.get("filename") != filename:
            raise BackupError(
                "Backup manifest does not match the requested file."
            )

        if manifest.get("backup_type") != "full":
            raise BackupError("Unsupported backup type.")

        if manifest.get("version") != 1:
            raise BackupError("Unsupported backup manifest version.")

        if manifest.get("audit_csv_filename") != (
            filename.removesuffix(".dump") + "-audit-logs.csv"
        ):
            raise BackupError(
                "Invalid audit CSV filename in backup manifest."
            )

        return manifest

    except BackupError:
        raise

    except Exception:
        return None


def list_database_backups():
    try:
        storage = get_storage()
        files = storage.list()

    except Exception as exc:
        logger.exception("Failed to list database backups.")

        raise BackupError(
            "Could not retrieve database backups."
        ) from exc

    backups = []

    for file in files:
        filename = file.get("name", "")

        if not filename.endswith(".dump"):
            continue

        manifest = get_backup_manifest(filename)

        if manifest:
            backups.append({
                **manifest,
                "legacy": False,
            })
        else:
            metadata = file.get("metadata") or {}

            backups.append({
                "filename": filename,
                "description": "Legacy backup",
                "backup_type": "full",
                "audit_csv_filename": None,
                "size_bytes": metadata.get("size"),
                "created_at": file.get("created_at"),
                "updated_at": file.get("updated_at"),
                "legacy": True,
            })

    backups.sort(
        key=lambda item: item.get("created_at") or "",
        reverse=True,
    )

    return backups


def download_audit_log_csv(filename):
    manifest = get_backup_manifest(filename)

    if not manifest:
        raise BackupError(
            "Audit log export is unavailable for this legacy backup."
        )

    storage = get_storage()

    try:
        return (
            manifest["audit_csv_filename"],
            storage.download(manifest["audit_csv_filename"]),
        )

    except Exception as exc:
        logger.exception("Audit log CSV download failed.")

        raise BackupError(
            "Could not retrieve the audit log export."
        ) from exc
