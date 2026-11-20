from uuid import uuid4

from django.conf import settings
from supabase import create_client

BUCKET_NAME = "reports"
import logging
import time

logger = logging.getLogger(__name__)
# Create one client and reuse it.
supabase = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_SECRET_KEY,
)


def create_upload_url(report_id: int, content_type: str, extension: str):
    filename = f"{uuid4()}.{extension}"
    path = f"{report_id}/{filename}"

    response = (
        supabase.storage
        .from_(BUCKET_NAME)
        .create_signed_upload_url(path)
    )

    return {
        "path": path,
        "upload_url": response["signed_url"],
    }


def create_signed_read_url(path: str, expires_in: int = 3600):
    response = (
        supabase.storage
        .from_(BUCKET_NAME)
        .create_signed_url(path, expires_in)
    )

    return response["signedURL"]


def create_signed_read_urls(
    paths: list[str],
    expires_in: int = 3600,
):
    if not paths:
        return {}

    unique_paths = list(dict.fromkeys(paths))

    start = time.perf_counter()

    response = (
        supabase.storage
        .from_(BUCKET_NAME)
        .create_signed_urls(unique_paths, expires_in)
    )

    duration = time.perf_counter() - start

    signed_urls = {}

    for path, item in zip(unique_paths, response):
        signed_url = item.get("signedURL")

        if not signed_url:
            raise RuntimeError(
                f"Failed to generate signed URL for media path: {path}"
            )

        signed_urls[path] = signed_url

    logger.warning(
        "[SIGNED_URL_BATCH] Count=%s | Duration=%.3fs",
        len(unique_paths),
        duration,
    )

    return signed_urls