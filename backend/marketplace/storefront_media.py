import base64
import binascii
import mimetypes
import re
from pathlib import Path
from uuid import uuid4

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

DATA_URL_RE = re.compile(r"^data:(?P<mime>[^;]+);base64,(?P<data>.+)$", re.DOTALL)
IMAGE_KEYS = {"imageUrl", "image_url"}


def _save_data_url(data_url: str, section_id: int | str) -> str:
    match = DATA_URL_RE.match(str(data_url or ""))
    if not match:
        return str(data_url or "")

    mime = match.group("mime").lower().strip()
    encoded = match.group("data")
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error):
        return ""

    extension = mimetypes.guess_extension(mime) or ".jpg"
    if extension == ".jpe":
        extension = ".jpg"
    path = f"storefront/{section_id}/{uuid4().hex}{extension}"
    default_storage.save(path, ContentFile(raw))
    return f"/media/{path}"


def materialize_storefront_images(config: dict, section_id: int | str) -> dict:
    changed = False

    def walk(value):
        nonlocal changed
        if isinstance(value, list):
            return [walk(item) for item in value]
        if not isinstance(value, dict):
            return value

        output = {}
        for key, item in value.items():
            if key in IMAGE_KEYS and isinstance(item, str) and item.startswith("data:image/"):
                saved = _save_data_url(item, section_id)
                if saved:
                    output[key] = saved
                    changed = True
                else:
                    output[key] = item
            else:
                output[key] = walk(item)
        return output

    result = walk(config or {})
    return result if isinstance(result, dict) else config
