
import shutil

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Check whether PostgreSQL backup utilities are available."

    def handle(self, *args, **options):
        for utility in ("pg_dump", "pg_restore"):
            path = shutil.which(utility)

            if path:
                self.stdout.write(
                    self.style.SUCCESS(f"{utility}: available at {path}")
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f"{utility}: NOT FOUND")
                )
