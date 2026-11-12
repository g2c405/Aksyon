
from django.urls import path

from backups.views import (
    DatabaseBackupView,
    DatabaseRestoreView,
    DatabaseBackupListView,
    AuditLogCSVDownloadView,
)


urlpatterns = [
    path(
        "database/",
        DatabaseBackupView.as_view(),
        name="database-backup",
    ),
    path(
        "database/list/",
        DatabaseBackupListView.as_view(),
        name="database-backup-list",
    ),
    path(
        "database/restore/",
        DatabaseRestoreView.as_view(),
        name="database-restore",
    ),
    path(
        "database/audit-logs/<str:filename>/",
        AuditLogCSVDownloadView.as_view(),
        name="database-audit-log-download",
    ),
]
