"""Position of a Leapmotor vehicle."""

from __future__ import annotations

from typing import Any

from homeassistant.components.device_tracker import SourceType, TrackerEntity
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
    """Set up the tracker."""
    coordinator = entry.runtime_data
    async_add_entities(LeapmotorTracker(coordinator, vin) for vin in coordinator.data)


class LeapmotorTracker(LeapmotorEntity, TrackerEntity):
    """The GPS position reported by the vehicle."""

    _attr_source_type = SourceType.GPS

    def __init__(self, coordinator: LeapmotorCoordinator, vin: str) -> None:
        super().__init__(coordinator, vin, "location")

    @property
    def latitude(self) -> float | None:
        """Return the latitude."""
        return self.state_data.get("latitude")

    @property
    def longitude(self) -> float | None:
        """Return the longitude."""
        return self.state_data.get("longitude")

    @property
    def location_accuracy(self) -> float:
        """Return the accuracy in metres."""
        return 10

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return details useful on a map."""
        state = self.state_data
        attributes = {
            "speed": state.get("speed"),
            "last_update": state.get("vehicle_timestamp"),
        }
        return {key: value for key, value in attributes.items() if value is not None}
