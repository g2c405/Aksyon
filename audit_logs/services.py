
from .models import AuditLog


def record_activity(
    actor,
    action,
    target_type,
    target_id=None,
    description="",
    changes=None,
):
    return AuditLog.objects.create(
        actor=actor,
        actor_username=actor.username,
        actor_role=actor.role,
        barangay=getattr(actor, "assigned_barangay", None),
        action=action,
        target_type=target_type,
        target_id=str(target_id) if target_id is not None else None,
        description=description,
        changes=changes or {},
    )
