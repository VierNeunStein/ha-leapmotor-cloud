"""Storing and reading the app pictures."""

from __future__ import annotations

import io
import json
from pathlib import Path
import zipfile

from custom_components.leapmotor_cloud.api.pictures import PNG_SIGNATURE
from custom_components.leapmotor_cloud.picture_store import (
    load_pictures,
    picture_key,
    read_picture,
    remove_pictures,
    store_pictures,
)

VIN = "LTESTVIN000000042"


def _package(names: list[str]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name in names:
            archive.writestr(f"android/xxhdpi/{name}", PNG_SIGNATURE + name.encode())
    return buffer.getvalue()


def test_store_load_read_remove(tmp_path: Path) -> None:
    stored = store_pictures(
        tmp_path, VIN, "pic-key", _package(["carpic_body.png", "carpic_charge3.png"])
    )
    assert stored is not None
    key = picture_key(VIN)
    assert stored == {
        "key": key,
        "layers": ["carpic_body.png", "carpic_charge3.png"],
        "version": stored["version"],
        "path": f"/api/leapmotor_cloud/picture/{key}/",
    }
    assert VIN not in key and len(key) == 16
    assert load_pictures(tmp_path, VIN) == stored
    assert read_picture(tmp_path, key, "carpic_body.png") == PNG_SIGNATURE + b"carpic_body.png"
    assert read_picture(tmp_path, key, "index.json") is None
    assert read_picture(tmp_path, "../" + key[:13], "carpic_body.png") is None

    # A new package replaces the old pictures completely.
    newer = store_pictures(tmp_path, VIN, "other-key", _package(["carpic_body.png"]))
    assert newer is not None and newer["version"] != stored["version"]
    assert newer["layers"] == ["carpic_body.png"]
    assert read_picture(tmp_path, key, "carpic_charge3.png") is None

    remove_pictures(tmp_path, [VIN])
    assert load_pictures(tmp_path, VIN) is None


def test_broken_index_and_empty_package(tmp_path: Path) -> None:
    assert store_pictures(tmp_path, VIN, "pic-key", b"not a zip") is None
    assert load_pictures(tmp_path, VIN) is None
    folder = tmp_path / picture_key(VIN)
    folder.mkdir()
    (folder / "index.json").write_text("{broken", encoding="utf-8")
    assert load_pictures(tmp_path, VIN) is None
    (folder / "index.json").write_text(json.dumps({"layers": ["carpic_body.png", "../x.png"]}))
    assert load_pictures(tmp_path, VIN) is None  # listed file is missing
    (folder / "carpic_body.png").write_bytes(PNG_SIGNATURE)
    assert load_pictures(tmp_path, VIN)["layers"] == ["carpic_body.png"]
