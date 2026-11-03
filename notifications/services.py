import json
import logging
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from django.db import transaction

from .models import Notification, DevicePushToken

logger = logging.getLogger(__name__)

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"


def create_notification(
    *,
    user,
    notification_type,
    title,
    message,
    report=None,
    announcement=None,
):
    notification = Notification.objects.create(
        user=user,
        notification_type=notification_type,
        title=title,
        message=message,
        report=report,
        announcement=announcement,
    )

    transaction.on_commit(
        lambda notification_id=notification.id:
            send_push_notification(notification_id)
    )

    return notification


def send_push_notification(notification_id):
    try:
        notification = Notification.objects.get(
            id=notification_id
        )

        devices = list(
            DevicePushToken.objects.filter(
                user=notification.user,
                is_active=True,
            ).values_list("id", "expo_push_token")
        )

        if not devices:
            return

        messages = []

        for device_id, token in devices:
            messages.append({
                "to": token,
                "title": notification.title,
                "body": notification.message,
                "sound": "default",
                "priority": "high",
                "data": {
                    "notificationId": notification.id,
                    "notificationType": notification.notification_type,
                    "reportId": notification.report_id,
                    "announcementId": notification.announcement_id,
                },
            })

        # Expo accepts batches of up to 100 messages.
        for start in range(0, len(messages), 100):
            batch = messages[start:start + 100]
            batch_devices = devices[start:start + 100]

            send_expo_batch(batch, batch_devices)

    except Exception:
        logger.exception(
            "Failed to prepare push notification %s",
            notification_id,
        )


def send_expo_batch(messages, devices):
    try:
        payload = json.dumps(messages).encode("utf-8")

        request = Request(
            EXPO_PUSH_URL,
            data=payload,
            headers={
                "Accept": "application/json",
                "Accept-encoding": "gzip, deflate",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        with urlopen(request, timeout=5) as response:
            result = json.loads(response.read().decode("utf-8"))

        tickets = result.get("data", [])

        for device, ticket in zip(devices, tickets):
            ticket_error = (
                ticket.get("details", {}).get("error")
            )

            if ticket_error == "DeviceNotRegistered":
                DevicePushToken.objects.filter(
                    id=device[0]
                ).update(is_active=False)

    except HTTPError as error:
        logger.error(
            "Expo push request returned HTTP %s",
            error.code,
        )

    except (URLError, TimeoutError):
        logger.exception("Could not connect to Expo Push Service.")

    except Exception:
        logger.exception("Unexpected Expo push delivery error.")