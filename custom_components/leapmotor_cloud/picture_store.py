"""Keep the app pictures of each vehicle on disk and hand them to the cards.

The picture package is downloaded once per vehicle and kept, so the cloud is
asked only once. The pictures belong to the user's account; they are served
only to signed-in users through :class:`LeapmotorPictureView`.
"""

from __future__ import annotations

import hashlib
from http import HTTPStatus
import json
from pathlib import Path
import re
import shutil
import time
from typing import Any

from aiohttp import web
from homeassistant.core import HomeAssistant
from homeassistant.helpers.http import KEY_HASS, HomeAssistantView

from .api.pictures import LAYER_NAME, extract_pictures
from .const import DOMAIN

PICTURE_DIR = f"{DOMAIN}_pictures"
PICTURE_URL = f"/api/{DOMAIN}/picture"
INDEX_FILE = "index.json"
KEY_PATTERN = re.compile(r"[0-9a-f]{16}")


def picture_key(vin: str) -> str:
    """Return the folder name of a vehicle's pictures (does not reveal the VIN)."""
    return hashlib.sha256(f"{DOMAIN}:{vin}".encode()).hexdigest()[:16]


def picture_root(hass: HomeAssistant) -> Path:
    """Return the folder that holds the pictures of all vehicles."""
    return Path(hass.config.path(".storage", PICTURE_DIR))


def _result(vin: str, layers: list[str], version: str) -> dict[str, Any]:
    key = picture_key(vin)
    return {
        "key": key,
        "layers": layers,
        "version": version,
        "path": f"{PICTURE_URL}/{key}/",
    }


def load_pictures(root: Path, vin: str) -> dict[str, Any] | None:
    """Return the stored pictures of a vehicle, or None. Runs in the executor."""
    folder = root / picture_key(vin)
    try:
        index = json.loads((folder / INDEX_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(index, dict):
        return None
    layers = [
        name
        for name in index.get("layers") or []
        if isinstance(name, str) and LAYER_NAME.fullmatch(name) and (folder / name).is_file()
    ]
    if not layers:
        return None
    return _result(vin, layers, str(index.get("version") or ""))


def store_pictures(root: Path, vin: str, picture_id: str, package: bytes) -> dict[str, Any] | None:
    """Unpack a picture package and keep its layers. Runs in the executor."""
    pictures = extract_pictures(package)
    if not pictures:
        return None
    folder = root / picture_key(vin)
    temporary = folder.with_name(f"{folder.name}.new")
    shutil.rmtree(temporary, ignore_errors=True)
    temporary.mkdir(parents=True)
    for name, data in pictures.items():
        (temporary / name).write_bytes(data)
    version = hashlib.sha256(picture_id.encode()).hexdigest()[:8]
    layers = sorted(pictures)
    (temporary / INDEX_FILE).write_text(
        json.dumps({"version": version, "layers": layers, "stored": int(time.time())}),
        encoding="utf-8",
    )
    shutil.rmtree(folder, ignore_errors=True)
    temporary.rename(folder)
    return _result(vin, layers, version)


def read_picture(root: Path, key: str, name: str) -> bytes | None:
    """Return one stored layer. Runs in the executor."""
    if not KEY_PATTERN.fullmatch(key) or not LAYER_NAME.fullmatch(name):
        return None
    try:
        return (root / key / name).read_bytes()
    except OSError:
        return None


def remove_pictures(root: Path, vins: list[str]) -> None:
    """Delete the pictures of vehicles. Runs in the executor."""
    for vin in vins:
        shutil.rmtree(root / picture_key(vin), ignore_errors=True)


class LeapmotorPictureView(HomeAssistantView):
    """Serve the picture layers to signed-in users (the cards fetch them with auth)."""

    url = PICTURE_URL + "/{key}/{name}"
    name = f"api:{DOMAIN}:picture"
    requires_auth = True

    async def get(self, request: web.Request, key: str, name: str) -> web.Response:
        """Return one layer."""
        hass = request.app[KEY_HASS]
        data = await hass.async_add_executor_job(read_picture, picture_root(hass), key, name)
        if data is None:
            return web.Response(status=HTTPStatus.NOT_FOUND)
        return web.Response(
            body=data,
            content_type="image/png",
            headers={"Cache-Control": "private, max-age=31536000, immutable"},
        )
