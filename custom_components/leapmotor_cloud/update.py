"""Software version of a Leapmotor vehicle.

Read-only: updates are installed from the vehicle or the official app.
"""

from __future__ import annotations

from homeassistant.components.update import UpdateDeviceClass, UpdateEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import LeapmotorConfigEntry, LeapmotorCoordinator
from .entity import LeapmotorEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LeapmotorConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the update entity once the vehicle reported a version."""
    coordinator = entry.runtime_data
    known: set[str] = set()

    def _discover() -> None:
        new = [
            vin
            for vin, data in (coordinator.data or {}).items()
            if vin not in known and data.extras.get("software_version")
        ]
        known.update(new)
        if new:
            async_add_entities(LeapmotorSoftware(coordinator, vin) for vin in new)

    _discover()
    entry.async_on_unload(coordinator.async_add_listener(_discover))


class LeapmotorSoftware(LeapmotorEntity, UpdateEntity):
    """Installed and available vehicle software."""

    _attr_device_class = UpdateDeviceClass.FIRMWARE

    def __init__(self, coordinator: LeapmotorCoordinator, vin: str) -> None:
        super().__init__(coordinator, vin, "software")

    @property
    def installed_version(self) -> str | None:
        """Return the installed version."""
        return self.vehicle.extras.get("software_version")

    @property
    def latest_version(self) -> str | None:
        """Return the version offered by the manufacturer."""
        return self.vehicle.extras.get("software_latest") or self.installed_version

    @property
    def release_summary(self) -> str | None:
        """Return the first lines of the release notes."""
        notes = self.vehicle.extras.get("software_release_notes")
        return notes[:255] if notes else None
