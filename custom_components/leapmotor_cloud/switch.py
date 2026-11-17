"""Switches of a Leapmotor vehicle."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import (
    SwitchDeviceClass,
    SwitchEntity,
    SwitchEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import RemoteCommand, commands
from .api.const import (
    LEGACY_MODELS,
    RIGHT_BATTERY_PREHEAT,
    RIGHT_CHARGE_LIMIT,
    RIGHT_HEALTHY_CHARGING,
    RIGHT_MIRROR_HEAT,
    RIGHT_SENTRY_MODE,
    RIGHT_STEERING_WHEEL_HEAT,
    RIGHT_TOGGLE_CHARGE,
)
from .const import DOMAIN
from .coordinator import LeapmotorConfigEntry, LeapmotorCoordinator, VehicleData
from .entity import LeapmotorEntity, async_add_vehicle_entities

PARALLEL_UPDATES = 1


@dataclass(frozen=True, kw_only=True)
class LeapmotorSwitchDescription(SwitchEntityDescription):
    """Describe a switch.

    ``state_key`` is the vehicle state that mirrors the switch.  A switch is
    offered when the account has ``right``; when the backend reports no rights
    at all, the presence of the state decides (``needs_state``).
    """

    state_key: str
    command_fn: Callable[[bool], RemoteCommand] | None = None
    right: int | None = None
    needs_state: bool = True
    skip_models: frozenset[str] = frozenset()


SWITCHES: tuple[LeapmotorSwitchDescription, ...] = (
    LeapmotorSwitchDescription(
        key="charging",
        state_key="is_charging",
        command_fn=commands.charging,
        right=RIGHT_TOGGLE_CHARGE,
        needs_state=False,
        skip_models=LEGACY_MODELS,
    ),
    LeapmotorSwitchDescription(
        key="charge_schedule",
        state_key="charge_schedule_enabled",
        right=RIGHT_CHARGE_LIMIT,
        skip_models=LEGACY_MODELS,
    ),
    LeapmotorSwitchDescription(
        key="healthy_charging",
        state_key="healthy_charging",
        command_fn=commands.healthy_charging,
        right=RIGHT_HEALTHY_CHARGING,
    ),
    LeapmotorSwitchDescription(
        key="battery_preheat",
        state_key="battery_heating",
        command_fn=commands.battery_preheat,
        right=RIGHT_BATTERY_PREHEAT,
    ),
    LeapmotorSwitchDescription(
        key="steering_wheel_heat",
        state_key="steering_wheel_heat",
        command_fn=commands.steering_wheel_heat,
        right=RIGHT_STEERING_WHEEL_HEAT,
        skip_models=LEGACY_MODELS,
    ),
    LeapmotorSwitchDescription(
        key="mirror_heat",
        state_key="mirror_heat",
        command_fn=commands.mirror_heat,
        right=RIGHT_MIRROR_HEAT,
    ),
    LeapmotorSwitchDescription(
        key="sentry_mode",
        state_key="sentry_mode",
        command_fn=commands.sentry_mode,
        right=RIGHT_SENTRY_MODE,
    ),
)


def _supported(
    _coordinator: LeapmotorCoordinator, data: VehicleData, description: LeapmotorSwitchDescription
) -> bool:
    if data.info.model in description.skip_models:
        return False
    if data.info.has_right(description.right):
        return True
    return not description.needs_state or data.state.get(description.state_key) is not None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LeapmotorConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the switches."""
    async_add_vehicle_entities(entry, async_add_entities, SWITCHES, LeapmotorSwitch, _supported)


class LeapmotorSwitch(LeapmotorEntity, SwitchEntity):
    """A switch that sends a remote command."""

    entity_description: LeapmotorSwitchDescription
    _attr_device_class = SwitchDeviceClass.SWITCH

    def __init__(
        self,
        coordinator: LeapmotorCoordinator,
        vin: str,
        description: LeapmotorSwitchDescription,
    ) -> None:
        super().__init__(coordinator, vin, description.key, right=description.right)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        """Return the state reported by the vehicle."""
        return self.state_data.get(self.entity_description.state_key)

    async def _set(self, on: bool) -> None:
        description = self.entity_description
        if description.key == "charge_schedule":
            await self.coordinator.async_set_charge_plan(self.vin, enabled=on)
            return
        optimistic: dict[str, Any] = {description.state_key: on}
        if description.key == "charging":
            if on and self.state_data.get("is_plugged_in") is False:
                raise ServiceValidationError(
                    translation_domain=DOMAIN, translation_key="not_plugged_in"
                )
            optimistic["charging_state"] = "charging" if on else "paused"
            if not on:
                optimistic["charging_power"] = 0.0
        assert description.command_fn is not None
        await self.coordinator.async_send_command(
            self.vin, description.command_fn(on), optimistic=optimistic
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Switch on."""
        await self._set(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Switch off."""
        await self._set(False)
