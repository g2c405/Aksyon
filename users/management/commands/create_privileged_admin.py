import os

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = "Creates the built-in privileged admin account if it does not exist."

    def handle(self, *args, **options):
        User = get_user_model()

        username = os.environ["PRIVILEGED_ADMIN_USERNAME"]
        password = os.environ["PRIVILEGED_ADMIN_PASSWORD"]

        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "first_name": "System",
                "last_name": "Administrator",
                "email": "privileged.admin@example.com",
                "contact_number": None,
                "role": "privileged_admin",
                "email_verified": True,
                "is_active": True,
            },
        )

        if created:
            user.set_password(password)
            user.save(update_fields=["password"])

            self.stdout.write(
                self.style.SUCCESS(
                    "Privileged admin account created successfully."
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    "Privileged admin account already exists. Skipping creation."
                )
            )