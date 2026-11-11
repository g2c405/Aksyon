
import logging

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from users.permissions import IsPrivilegedAdmin
from backups.services.database_backup import (
    BackupError,
    create_database_backup, list_database_backups
)

from backups.services.database_restore import (
    RestoreError,
    RestoreRejected,
    restore_database_backup,
)

from audit_logs.services import record_activity
logger = logging.getLogger(__name__)


class DatabaseBackupView(APIView):
    permission_classes = [IsPrivilegedAdmin]

    def post(self, request):
        try:
            backup = create_database_backup()

            record_activity(
                actor=request.user,
                action="DATABASE_BACKUP_CREATED",
                target_type="DatabaseBackup",
                target_id=backup["filename"],
                description="Created a database backup.",
                changes={
                    "filename": backup["filename"],
                    "size_bytes": backup["size_bytes"],
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

class DatabaseRestoreView(APIView):
    permission_classes = [IsAuthenticated, IsPrivilegedAdmin]

    def post(self, request):
        filename = request.data.get("filename")

        if not isinstance(filename, str) or not filename:
            return Response(
                {"detail": "A backup filename is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = restore_database_backup(filename)

            record_activity(
                actor=request.user,
                action="DATABASE_BACKUP_RESTORED",
                target_type="DatabaseBackup",
                target_id=filename,
                description=f"Restored database using backup {filename}.",
                changes={
                    "filename": filename,
                },
            )

            return Response(
                result,
                status=status.HTTP_200_OK,
            )

        except RestoreRejected as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_409_CONFLICT,
            )

        except RestoreError as exc:
            logger.error("Database restore failed: %s", exc)
            return Response(
                {"detail": str(exc)},
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