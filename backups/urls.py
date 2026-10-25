from django.urls import path

from backups.views import DatabaseBackupView


urlpatterns = [
    path("database/", DatabaseBackupView.as_view(), name="database-backup"),
]