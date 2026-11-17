"""Tests for reading the picture package of the app."""

from __future__ import annotations

import io
import zipfile

from leapmotor_api.pictures import (
    MAX_FILE_SIZE,
    PNG_SIGNATURE,
    extract_pictures,
    preview_name,
)


def _zip(files: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    return buffer.getvalue()


def test_highest_resolution_wins() -> None:
    package = _zip(
        {
            "android/xhdpi/carpic_body.png": PNG_SIGNATURE + b"small",
            "android/xxxhdpi/CARPIC_BODY.PNG": PNG_SIGNATURE + b"the largest one",
            "android/xxhdpi/carpic_body.png": PNG_SIGNATURE + b"medium",
        }
    )
    assert extract_pictures(package) == {"carpic_body.png": PNG_SIGNATURE + b"the largest one"}


def test_only_png_layers_are_taken() -> None:
    package = _zip(
        {
            "a/carpic_tailgate_open.png": PNG_SIGNATURE + b"x",
            "a/carpic_charge7.png": PNG_SIGNATURE + b"y",
            "a/carpic_text.png": b"not a png",
            "a/notes.txt": b"text",
            "a/other_image.png": PNG_SIGNATURE,
            "a/carpic_../evil.png": PNG_SIGNATURE,
            "a/carpic_body.jpg": b"\xff\xd8",
        }
    )
    assert sorted(extract_pictures(package)) == ["carpic_charge7.png", "carpic_tailgate_open.png"]


def test_broken_or_huge_input() -> None:
    assert extract_pictures(b"") == {}
    assert extract_pictures(b"PK\x03\x04 broken") == {}
    huge = _zip({"carpic_body.png": PNG_SIGNATURE + b"\0" * (MAX_FILE_SIZE + 1)})
    assert extract_pictures(huge) == {}


def test_preview_name() -> None:
    assert preview_name({"carpic_body.png", "carpic_for_tripsum.png"}) == "carpic_for_tripsum.png"
    assert preview_name(["carpic_body.png"]) == "carpic_body.png"
    assert preview_name([]) is None
