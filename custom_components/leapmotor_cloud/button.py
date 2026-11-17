"""Buttons of a Leapmotor vehicle."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import RemoteCommand, VehicleInfo, commands
from .api.const import (
    RIGHT_FIND_CAR,
    RIGHT_QUICK_CLIMATE,
    RIGHT_UNLOCK_CHARGER,
    RIGHT_WINDSHIELD_DEFROST,
)
from .coordinator import LeapmotorConfigEntry, LeapmotorCoordinator
from .entity import LeapmotorEntity, async_add_vehicle_entities

PARALLEL_UPDATES = 1


@dataclass(frozen=True, kw_only=True)
class LeapmotorButtonDescription(ButtonEntityDescription):
    """Describe a button. Without ``command_fn`` it refreshes the data."""

    command_fn: Callable[[VehicleInfo], RemoteCommand] | None = None
    optimistic: dict[str, object] | None = None
    right: int | None = None


BUTTONS: tuple[LeapmotorButtonDescription, ...] = (
    LeapmotorButtonDescription(key="refresh", entity_category=EntityCategory.DIAGNOSTIC),
    LeapmotorButtonDescription(
        key="find_vehicle",
        command_fn=lambda _info: commands.find_car(),
        right=RIGHT_FIND_CAR,
    ),
    LeapmotorButtonDescription(
        key="unlock_charger",
        command_fn=lambda _info: commands.unlock_charger(),
        right=RIGHT_UNLOCK_CHARGER,
    ),
    LeapmotorButtonDescription(
        key="quick_cool",
        command_fn=lambda _info: commands.quick_cool(),
        optimistic={"climate_on": True, "climate_action": "cooling"},
        right=RIGHT_QUICK_CLIMATE,
    ),
    LeapmotorButtonDescription(
        key="quick_heat",
        command_fn=lambda _info: commands.quick_heat(),
        optimistic={"climate_on": True, "climate_action": "heating"},
        right=RIGHT_QUICK_CLIMATE,
    ),
    LeapmotorButtonDescription(
        key="windshield_defrost",
        command_fn=lambda _info: commands.windshield_defrost(),
        optimistic={"climate_on": True, "climate_action": "defrost", "defrost": True},
        right=RIGHT_WINDSHIELD_DEFROST,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LeapmotorConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the buttons."""
    async_add_vehicle_entities(
        entry, async_add_entities, BUTTONS, LeapmotorButton, lambda _c, _d, _description: True
    )


class LeapmotorButton(LeapmotorEntity, ButtonEntity):
    """A button that triggers one action."""

    entity_description: LeapmotorButtonDescription

    def __init__(
        self,
        coordinator: LeapmotorCoordinator,
        vin: str,
        description: LeapmotorButtonDescription,
    ) -> None:
        super().__init__(coordinator, vin, description.key, right=description.right)
        self.entity_description = description

    async def async_press(self) -> None:
        """Run the action."""
        description = self.entity_description
        if description.command_fn is None:
            await self.coordinator.async_request_refresh()
            return
        await self.coordinator.async_send_command(
            self.vin,
            description.command_fn(self.info),
            optimistic=dict(description.optimistic) if description.optimistic else None,
        )
