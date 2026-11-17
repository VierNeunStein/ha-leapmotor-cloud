"""Door lock of a Leapmotor vehicle."""

from __future__ import annotations

from typing import Any

from homeassistant.components.lock import LockEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import commands
from .api.const import RIGHT_LOCK
from .coordinator import LeapmotorConfigEntry, LeapmotorCoordinator
from .entity import LeapmotorEntity

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LeapmotorConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the lock."""
    coordinator = entry.runtime_data
    async_add_entities(LeapmotorLock(coordinator, vin) for vin in coordinator.data)


class LeapmotorLock(LeapmotorEntity, LockEntity):
    """The central locking of the vehicle."""

    def __init__(self, coordinator: LeapmotorCoordinator, vin: str) -> None:
        super().__init__(coordinator, vin, "lock", right=RIGHT_LOCK)

    @property
    def is_locked(self) -> bool | None:
        """Return whether the vehicle is locked."""
        return self.state_data.get("locked")

    async def _send(self, lock: bool) -> None:
        if lock:
            self._attr_is_locking = True
        else:
            self._attr_is_unlocking = True
        self.async_write_ha_state()
        try:
            await self.coordinator.async_send_command(
                self.vin,
                commands.lock() if lock else commands.unlock(),
                optimistic={"locked": lock},
            )
        finally:
            self._attr_is_locking = False
            self._attr_is_unlocking = False
            self.async_write_ha_state()

    async def async_lock(self, **kwargs: Any) -> None:
        """Lock the vehicle."""
        await self._send(True)

    async def async_unlock(self, **kwargs: Any) -> None:
        """Unlock the vehicle."""
        await self._send(False)
