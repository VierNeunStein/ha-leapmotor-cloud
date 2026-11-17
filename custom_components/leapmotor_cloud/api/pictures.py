"""Pictures of the vehicle from the picture package of the app.

The package is a ZIP with the images the app shows for exactly this vehicle
(model and colour): the body and separate layers for the doors, the
tailgate, the windows and the charging port, frames of the charging
animation and a complete preview. All layers are transparent PNGs of the
same size, meant to be stacked in a fixed order.
"""

from __future__ import annotations

import io
import re
import zipfile

LAYER_NAME = re.compile(r"^carpic_[a-z0-9_]+\.png$")
PREVIEW = "carpic_for_tripsum.png"
BODY = "carpic_body.png"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

MAX_FILES = 200
MAX_FILE_SIZE = 8 * 1024 * 1024
MAX_TOTAL_SIZE = 64 * 1024 * 1024


def extract_pictures(package: bytes) -> dict[str, bytes]:
    """Return the picture layers of a package, each in its highest resolution.

    The package can hold the same picture for several screen densities in
    different folders; the largest file wins. Anything that is not a PNG
    named ``carpic_*`` is ignored, and size limits protect against broken
    or hostile archives.
    """
    try:
        archive = zipfile.ZipFile(io.BytesIO(package))
    except (zipfile.BadZipFile, OSError):
        return {}
    pictures: dict[str, bytes] = {}
    with archive:
        best: dict[str, zipfile.ZipInfo] = {}
        for info in archive.infolist()[: MAX_FILES * 8]:
            name = info.filename.replace("\\", "/").rsplit("/", 1)[-1].lower()
            if info.is_dir() or not LAYER_NAME.match(name) or info.file_size > MAX_FILE_SIZE:
                continue
            if name not in best or info.file_size > best[name].file_size:
                best[name] = info
        total = 0
        for name, info in sorted(best.items())[:MAX_FILES]:
            total += info.file_size
            if total > MAX_TOTAL_SIZE:
                break
            try:
                data = archive.read(info)
            except (zipfile.BadZipFile, OSError, KeyError, RuntimeError):
                continue
            if data.startswith(PNG_SIGNATURE):
                pictures[name] = data
    return pictures


def preview_name(names: list[str] | set[str]) -> str | None:
    """Return the layer that shows the complete vehicle."""
    for name in (PREVIEW, BODY):
        if name in names:
            return name
    return None
