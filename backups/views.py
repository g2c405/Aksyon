
import logging

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from users.permissions import IsPrivilegedAdmin
from backups.services.database_backup import (
    BackupError,
    create_database_backup,
)


logger = logging.getLogger(__name__)


class DatabaseBackupView(APIView):
    permission_classes = [IsPrivilegedAdmin]

    def post(self, request):
        try:
            backup = create_database_backup()

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
