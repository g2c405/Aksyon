from uuid import uuid4

from django.conf import settings
from supabase import create_client


BUCKET_NAME = "reports"


def create_upload_url(report_id: int, content_type: str, extension: str):
    filename = f"{uuid4()}.{extension}"
    path = f"{report_id}/{filename}"

    supabase = create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_SECRET_KEY,
    )

    response = (supabase.storage
        .from_(BUCKET_NAME)
        .create_signed_upload_url(path)
    )

    print("SUPABASE RESPONSE:", response)
    return {
        "path": path,
        "upload_url": response["signed_url"],
    }

def create_signed_read_url(path: str, expires_in: int = 3600):
    supabase = create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_SECRET_KEY,
    )

    response = (
        supabase.storage
        .from_(BUCKET_NAME)
        .create_signed_url(path, expires_in)
    )
    print("SUPABASE RESPONSE:", response)
    return response["signedURL"]