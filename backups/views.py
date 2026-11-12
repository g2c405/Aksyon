
import logging
import os

from django.contrib.auth import get_user_model
from django.http import HttpResponse

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from users.permissions import IsPrivilegedAdmin

from backups.services.database_backup import (
    BackupError,
    create_database_backup,
    list_database_backups,
    download_audit_log_csv,
    MAX_DESCRIPTION_LENGTH,
)

from backups.services.database_restore import (
    RestoreError,
    RestoreRejected,
    restore_database_backup,
)

from audit_logs.services import record_activity


logger = logging.getLogger(__name__)

User = get_user_model()

RESTORE_CONFIRMATION_PHRASE = "RESTORE DATABASE"


class DatabaseBackupView(APIView):
    permission_classes = [IsAuthenticated, IsPrivilegedAdmin]

    def post(self, request):
        description = request.data.get("description")

        if not isinstance(description, str) or not description.strip():
            return Response(
                {"detail": "A backup description is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(description.strip()) > MAX_DESCRIPTION_LENGTH:
            return Response(
                {
                    "detail": (
                        f"Description cannot exceed "
                        f"{MAX_DESCRIPTION_LENGTH} characters."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            backup = create_database_backup(description)

            record_activity(
                actor=request.user,
                action="DATABASE_BACKUP_CREATED",
                target_type="DatabaseBackup",
                target_id=backup["filename"],
                description=description.strip(),
                changes={
                    "filename": backup["filename"],
                    "description": description.strip(),
                    "dump_size_bytes": backup["dump_size_bytes"],
                    "audit_csv_size_bytes": backup["audit_csv_size_bytes"],
                    "created_at": backup["created_at"],
                },
            )

            return Response(
                {
                    "message": "Database backup created successfully.",
                    "backup": backup,
                },
                status=status.HTTP_201_CREATED,
            )

        except BackupError as exc:
            logger.error("Database backup failed: %s", exc)

            return Response(
                {"detail": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        except Exception:
            logger.exception(
                "Unexpected error while creating database backup."
            )

            return Response(
                {"detail": "Unable to create the database backup."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class DatabaseRestoreView(APIView):
    permission_classes = [IsAuthenticated, IsPrivilegedAdmin]

    def post(self, request):
        filename = request.data.get("filename")
        password = request.data.get("password")
        confirmation_phrase = request.data.get("confirmation_phrase")

        if not isinstance(filename, str) or not filename:
            return Response(
                {"detail": "A backup filename is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not isinstance(password, str) or not password:
            return Response(
                {"detail": "Your current password is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Verify the password before checking the confirmation phrase.
        if not request.user.check_password(password):
            return Response(
                {"detail": "The password is incorrect."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if confirmation_phrase != RESTORE_CONFIRMATION_PHRASE:
            return Response(
                {
                    "detail": (
                        f'Type "{RESTORE_CONFIRMATION_PHRASE}" '
                        "exactly to confirm restoration."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = restore_database_backup(filename)

            # Restoration may replace the current user row.
            # Resolve the built-in privileged admin after restoration.
            privileged_username = os.environ.get(
                "PRIVILEGED_ADMIN_USERNAME"
            )

            restored_actor = None

            if privileged_username:
                restored_actor = User.objects.filter(
                    username=privileged_username
                ).first()

            if restored_actor is None:
                restored_actor = User.objects.filter(
                    pk=request.user.pk
                ).first()

            if restored_actor is not None:
                try:
                    record_activity(
                        actor=restored_actor,
                        action="DATABASE_BACKUP_RESTORED",
                        target_type="DatabaseBackup",
                        target_id=filename,
                        description=(
                            f"Restored database using backup {filename}."
                        ),
                        changes={
                            "filename": filename,
                        },
                    )
                except Exception:
                    # Do not misrepresent a successful restore as failed
                    # just because the post-restore audit entry failed.
                    logger.exception(
                        "Database was restored, but the restoration "
                        "activity could not be recorded."
                    )

            else:
                logger.warning(
                    "Database was restored, but no privileged admin "
                    "could be resolved for the restoration audit entry."
                )

            return Response(
                result,
                status=status.HTTP_200_OK,
            )

        except RestoreRejected as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        except RestoreError as exc:
            logger.error("Database restore failed: %s", exc)

            return Response(
                {"detail": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        except Exception:
            logger.exception(
                "Unexpected error during database restoration."
            )

            return Response(
                {"detail": "Unable to restore the database."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class DatabaseBackupListView(APIView):
    permission_classes = [IsAuthenticated, IsPrivilegedAdmin]

    def get(self, request):
        try:
            backups = list_database_backups()

            return Response(
                {"backups": backups},
                status=status.HTTP_200_OK,
            )

        except BackupError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AuditLogCSVDownloadView(APIView):
    permission_classes = [IsAuthenticated, IsPrivilegedAdmin]

    def get(self, request, filename):
        try:
            csv_filename, csv_content = download_audit_log_csv(
                filename
            )

            response = HttpResponse(
                csv_content,
                content_type="text/csv; charset=utf-8",
            )

            response["Content-Disposition"] = (
                f'attachment; filename="{csv_filename}"'
            )

            return response

        except BackupError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_404_NOT_FOUND,
            )
