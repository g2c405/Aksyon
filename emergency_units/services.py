
from .models import EmergencyUnit


def get_available_responders():
    return list(
        EmergencyUnit.objects.filter(
            is_active=True
        ).values(
            "id",
            "name",
            "unit_type",
            "address",
            "latitude",
            "longitude",
            "contact_number",
        )
    )
