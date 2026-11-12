
import csv
import json

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

from django.apps import apps


AUDIT_LOG_FIELDS = [
    "id",
    "actor_username",
    "actor_role",
    "barangay",
    "action",
    "target_type",
    "target_id",
    "description",
    "changes",
    "created_at",
]


def serialize_csv_value(value):
    if value is None:
        return ""

    if isinstance(value, (dict, list)):
        return json.dumps(
            value,
            ensure_ascii=False,
            default=str,
        )

    if isinstance(value, datetime):
        if value.tzinfo is not None:
            value = value.astimezone(timezone.utc)

        return value.isoformat()

    if isinstance(value, (date, Decimal, UUID)):
        return str(value)

    return value


def export_audit_logs_csv(output_path):
    """
    Export audit logs using the current database transaction snapshot.

    The caller must establish a repeatable-read transaction before
    invoking this function.
    """
    AuditLog = apps.get_model("audit_logs", "AuditLog")

    available_fields = {
        field.name
        for field in AuditLog._meta.concrete_fields
    }

    missing_fields = set(AUDIT_LOG_FIELDS) - available_fields

    if missing_fields:
        raise ValueError(
            "AuditLog is missing expected fields: "
            + ", ".join(sorted(missing_fields))
        )

    queryset = (
        AuditLog.objects
        .order_by("id")
        .values_list(*AUDIT_LOG_FIELDS)
    )

    with open(
        output_path,
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(AUDIT_LOG_FIELDS)

        for record in queryset.iterator(chunk_size=2000):
            writer.writerow([
                serialize_csv_value(value)
                for value in record
            ])
