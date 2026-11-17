"""Windows, sunshade and tailgate of a Leapmotor vehicle."""

from __future__ import annotations

from typing import Any

from homeassistant.components.cover import (
    ATTR_POSITION,
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import commands
from .api.const import RIGHT_SUNSHADE, RIGHT_TRUNK, RIGHT_WINDOWS
from .coordinator import LeapmotorConfigEntry, LeapmotorCoordinator
from .entity import LeapmotorEntity

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LeapmotorConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the covers."""
    coordinator = entry.runtime_data
    entities: list[CoverEntity] = []
    for vin, data in coordinator.data.items():
        entities.append(LeapmotorWindows(coordinator, vin))
        entities.append(LeapmotorTrunk(coordinator, vin))
        # Only cars with an electric sunshade know this right.
        if data.info.has_right(RIGHT_SUNSHADE) or data.state.get("sunshade_position") is not None:
            entities.append(LeapmotorSunshade(coordinator, vin))
    async_add_entities(entities)


class LeapmotorWindows(LeapmotorEntity, CoverEntity):
    """All side windows at once (the cloud has no per-window command)."""

    _attr_device_class = CoverDeviceClass.WINDOW
    _attr_supported_features = (
        CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE | CoverEntityFeature.SET_POSITION
    )

    def __init__(self, coordinator: LeapmotorCoordinator, vin: str) -> None:
        super().__init__(coordinator, vin, "windows", right=RIGHT_WINDOWS)

    @property
    def current_cover_position(self) -> int | None:
        """Return the widest opening of all windows."""
        position = self.state_data.get("windows_position")
        if position is None:
            return None
        return max(0, min(100, int(position)))

    @property
    def is_closed(self) -> bool | None:
        """Return whether all windows are closed."""
        is_open = self.state_data.get("any_window_open")
        position = self.state_data.get("windows_position")
        if is_open is None and position is None:
            return None
        return not is_open and not position

    async def _move(self, position: int) -> None:
        await self.coordinator.async_send_command(
            self.vin,
            commands.windows(position, self.info.model),
            optimistic={"windows_position": position, "any_window_open": position > 0},
        )

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open all windows completely."""
        await self._move(100)

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close all windows."""
        await self._move(0)

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Move all windows to a position (20 % is the usual vent gap)."""
        await self._move(int(kwargs[ATTR_POSITION]))


class LeapmotorSunshade(LeapmotorEntity, CoverEntity):
    """The sunshade of the panoramic roof."""

    _attr_device_class = CoverDeviceClass.SHADE
    _attr_supported_features = (
        CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE | CoverEntityFeature.SET_POSITION
    )

    def __init__(self, coordinator: LeapmotorCoordinator, vin: str) -> None:
        super().__init__(coordinator, vin, "sunshade", right=RIGHT_SUNSHADE)

    @property
    def assumed_state(self) -> bool:
        """Most models do not report the position of the shade."""
        return self.state_data.get("sunshade_position") is None

    @property
    def current_cover_position(self) -> int | None:
        """Return the position if the vehicle reports it."""
        position = self.state_data.get("sunshade_position")
        if position is None:
            return None
        # The vehicle counts 0..10.
        return max(0, min(100, int(position) * 10 if position <= 10 else int(position)))

    @property
    def is_closed(self) -> bool | None:
        """Return whether the shade is closed."""
        position = self.current_cover_position
        return None if position is None else position == 0

    async def _move(self, position: int) -> None:
        await self.coordinator.async_send_command(
            self.vin,
            commands.sunshade(position),
            optimistic={"sunshade_position": round(position / 10)},
        )

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the shade."""
        await self._move(100)

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the shade."""
        await self._move(0)

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Move the shade."""
        await self._move(int(kwargs[ATTR_POSITION]))


class LeapmotorTrunk(LeapmotorEntity, CoverEntity):
    """The tailgate."""

    _attr_device_class = CoverDeviceClass.DOOR
    _attr_supported_features = CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE

    def __init__(self, coordinator: LeapmotorCoordinator, vin: str) -> None:
        super().__init__(coordinator, vin, "trunk", right=RIGHT_TRUNK)

    @property
    def is_closed(self) -> bool | None:
        """Return whether the tailgate is closed."""
        is_open = self.state_data.get("trunk")
        return None if is_open is None else not is_open

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the tailgate."""
        await self.coordinator.async_send_command(
            self.vin, commands.trunk(True), optimistic={"trunk": True}
        )

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the tailgate."""
        await self.coordinator.async_send_command(
            self.vin, commands.trunk(False), optimistic={"trunk": False}
        )
