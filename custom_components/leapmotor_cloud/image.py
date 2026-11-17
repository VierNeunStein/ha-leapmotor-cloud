"""Picture of the vehicle as the app shows it (model and colour of this car)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.image import ImageEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .api.pictures import preview_name
from .coordinator import LeapmotorConfigEntry, LeapmotorCoordinator
from .entity import LeapmotorEntity
from .picture_store import picture_root, read_picture

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LeapmotorConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the picture; the demo vehicle has none."""
    coordinator = entry.runtime_data
    if coordinator.client.is_demo:
        return
    async_add_entities(LeapmotorPicture(hass, coordinator, vin) for vin in coordinator.data)


class LeapmotorPicture(LeapmotorEntity, ImageEntity):
    """The complete picture of the vehicle.

    The attributes tell the dashboard cards which picture layers exist, so
    they can stack them like the app does (open doors, charging, ...).
    """

    _attr_content_type = "image/png"

    def __init__(self, hass: HomeAssistant, coordinator: LeapmotorCoordinator, vin: str) -> None:
        LeapmotorEntity.__init__(self, coordinator, vin, "picture")
        ImageEntity.__init__(self, hass)
        self._version: str | None = None
        self._image: bytes | None = None
        self._track_pictures()

    @property
    def _pictures(self) -> dict[str, Any] | None:
        return self.coordinator.pictures.get(self.vin)

    @property
    def available(self) -> bool:
        """Return whether the pictures have been loaded."""
        return super().available and self._pictures is not None

    def _track_pictures(self) -> None:
        pictures = self._pictures
        version = pictures["version"] if pictures else None
        if version != self._version:
            self._version = version
            self._image = None
            self._attr_image_last_updated = dt_util.utcnow() if pictures else None

    def _handle_coordinator_update(self) -> None:
        """Pick up pictures that were loaded in the background."""
        self._track_pictures()
        super()._handle_coordinator_update()

    async def async_image(self) -> bytes | None:
        """Return the complete picture."""
        pictures = self._pictures
        if pictures is None:
            return None
        name = preview_name(pictures["layers"])
        if name is None:
            return None
        if self._image is None:
            self._image = await self.hass.async_add_executor_job(
                read_picture, picture_root(self.hass), pictures["key"], name
            )
        return self._image

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return where the cards find the picture layers."""
        pictures = self._pictures
        if pictures is None:
            return None
        return {
            "layers": pictures["layers"],
            "layer_path": pictures["path"],
            "layer_version": pictures["version"],
        }
