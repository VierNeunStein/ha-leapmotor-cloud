"""Start and end time of the charging schedule."""

from __future__ import annotations

from datetime import time

from homeassistant.components.time import TimeEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api.const import LEGACY_MODELS, RIGHT_CHARGE_LIMIT
from .coordinator import LeapmotorConfigEntry, LeapmotorCoordinator
from .entity import LeapmotorEntity

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LeapmotorConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the time entities."""
    coordinator = entry.runtime_data
    async_add_entities(
        LeapmotorScheduleTime(coordinator, vin, which)
        for vin, data in coordinator.data.items()
        if data.info.model not in LEGACY_MODELS
        for which in ("start", "end")
    )


class LeapmotorScheduleTime(LeapmotorEntity, TimeEntity):
    """One end of the daily charging window."""

    def __init__(self, coordinator: LeapmotorCoordinator, vin: str, which: str) -> None:
        super().__init__(coordinator, vin, f"charge_schedule_{which}", right=RIGHT_CHARGE_LIMIT)
        self._which = which

    @property
    def native_value(self) -> time | None:
        """Return the configured time."""
        raw = self.state_data.get(f"charge_schedule_{self._which}")
        if not raw:
            return None
        try:
            hour, minute = str(raw).split(":")[:2]
            return time(int(hour), int(minute))
        except (ValueError, TypeError):
            return None

    async def async_set_value(self, value: time) -> None:
        """Write the time; the rest of the charging plan stays as it is."""
        if self._which == "start":
            await self.coordinator.async_set_charge_plan(self.vin, start=value)
        else:
            await self.coordinator.async_set_charge_plan(self.vin, end=value)
