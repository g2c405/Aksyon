
import os

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = "Creates the built-in privileged admin account if it does not exist."

    def add_arguments(self, parser):
        # TEMPORARY: Allow specifying a separate database.
        parser.add_argument(
            "--database",
            default="default",
            help="Database alias to use.",
        )

    def handle(self, *args, **options):
        User = get_user_model()

        # TEMPORARY: Select the requested database.
        db_alias = options["database"]

        username = os.environ["PRIVILEGED_ADMIN_USERNAME"]
        password = os.environ["PRIVILEGED_ADMIN_PASSWORD"]

        # ORIGINAL:
        # user, created = User.objects.get_or_create(
        #     username=username,
        #     defaults={...},
        # )

        # TEMPORARY:
        user, created = User.objects.using(db_alias).get_or_create(
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

            # ORIGINAL:
            # user.save(update_fields=["password"])

            # TEMPORARY:
            user.save(
                using=db_alias,
                update_fields=["password"],
            )

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

        # ============================================================
        # DEV TESTING ADMIN
        # Delete this entire section when no longer needed.
        # ============================================================

        dev_username = "devadmin"
        dev_password = "DevAdmin123!"
        dev_email = "devadmin@example.com"

        # ORIGINAL:
        # dev_user, dev_created = User.objects.get_or_create(...)

        # TEMPORARY:
        dev_user, dev_created = User.objects.using(
            db_alias
        ).get_or_create(
            username=dev_username,
            defaults={
                "first_name": "Dev",
                "last_name": "Admin",
                "email": dev_email,
                "contact_number": None,
                "role": "admin",
                "assigned_barangay": "Santa Trinidad",
                "email_verified": True,
                "is_active": True,
            },
        )

        if dev_created:
            dev_user.set_password(dev_password)

            # ORIGINAL:
            # dev_user.save(update_fields=["password"])

            # TEMPORARY:
            dev_user.save(
                using=db_alias,
                update_fields=["password"],
            )

            self.stdout.write(
                self.style.SUCCESS(
                    "Dev admin account created successfully."
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    "Dev admin account already exists. Skipping creation."
                )
            )

        # ============================================================
        # END DEV TESTING ADMIN
        # ============================================================
