IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
VIDEO_EXTENSIONS = {"mp4", "mov"}


def get_media_type(path: str | None) -> str | None:
    if not path:
        return None

    extension = path.lower().rsplit(".", 1)[-1]

    if extension in IMAGE_EXTENSIONS:
        return "image"

    if extension in VIDEO_EXTENSIONS:
        return "video"

    return None