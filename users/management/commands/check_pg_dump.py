import shutil

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Checks whether pg_dump is installed."

    def handle(self, *args, **options):
        pg_dump_path = shutil.which("pg_dump")

        if pg_dump_path:
            self.stdout.write(
                self.style.SUCCESS(
                    f"PG_DUMP_CHECK: available at {pg_dump_path}"
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    "PG_DUMP_CHECK: not installed or not in PATH"
                )
            )