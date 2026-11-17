"""Air conditioning of a Leapmotor vehicle."""

from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    ATTR_HVAC_MODE,
    PRESET_NONE,
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import RemoteCommand, commands
from .api.const import RIGHT_CLIMATE
from .coordinator import LeapmotorConfigEntry, LeapmotorCoordinator
from .entity import LeapmotorEntity

PARALLEL_UPDATES = 1

PRESET_QUICK_COOL = "quick_cool"
PRESET_QUICK_HEAT = "quick_heat"
PRESET_DEFROST = "defrost"

_MODE_TO_API = {HVACMode.COOL: "cold", HVACMode.HEAT: "hot", HVACMode.FAN_ONLY: "nohotcold"}
_ACTION_TO_MODE = {
    "cooling": HVACMode.COOL,
    "heating": HVACMode.HEAT,
    "defrost": HVACMode.HEAT,
    "fan": HVACMode.FAN_ONLY,
}
_ACTION_TO_HVAC_ACTION = {
    "off": HVACAction.OFF,
    "cooling": HVACAction.COOLING,
    "heating": HVACAction.HEATING,
    "defrost": HVACAction.DEFROSTING,
    "fan": HVACAction.FAN,
}
_ACTION_OF_MODE = {HVACMode.COOL: "cooling", HVACMode.HEAT: "heating", HVACMode.FAN_ONLY: "fan"}

# Home Assistant 2026.11 renamed the temperature members of climate entities.
_NATIVE_TEMPERATURE = hasattr(ClimateEntity, "native_current_temperature")


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LeapmotorConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the climate entity."""
    coordinator = entry.runtime_data
    async_add_entities(LeapmotorClimate(coordinator, vin) for vin in coordinator.data)


class LeapmotorClimate(LeapmotorEntity, ClimateEntity):
    """Remote air conditioning.

    The vehicle only accepts complete settings, so mode, temperature and fan
    level are remembered here and sent together.
    """

    if _NATIVE_TEMPERATURE:
        _attr_native_temperature_unit = UnitOfTemperature.CELSIUS
    else:
        _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_min_temp = commands.TEMPERATURE_MIN
    _attr_max_temp = commands.TEMPERATURE_MAX
    _attr_target_temperature_step = 1
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT, HVACMode.COOL, HVACMode.FAN_ONLY]
    _attr_fan_modes = [str(level) for level in range(commands.FAN_MIN, commands.FAN_MAX + 1)]
    _attr_preset_modes = [PRESET_NONE, PRESET_QUICK_COOL, PRESET_QUICK_HEAT, PRESET_DEFROST]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.FAN_MODE
        | ClimateEntityFeature.PRESET_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )

    def __init__(self, coordinator: LeapmotorCoordinator, vin: str) -> None:
        super().__init__(coordinator, vin, "climate", right=RIGHT_CLIMATE)
        self._mode: HVACMode = HVACMode.FAN_ONLY
        self._target: float | None = None
        self._fan: int | None = None
        self._preset: str = PRESET_NONE

    # -- state -------------------------------------------------------------------

    @property
    def hvac_mode(self) -> HVACMode | None:
        """Return the mode the air conditioning runs in."""
        on = self.state_data.get("climate_on")
        if on is None:
            return None
        if not on:
            return HVACMode.OFF
        return _ACTION_TO_MODE.get(self.state_data.get("climate_action") or "", self._mode)

    @property
    def hvac_action(self) -> HVACAction | None:
        """Return what the air conditioning is doing."""
        return _ACTION_TO_HVAC_ACTION.get(self.state_data.get("climate_action") or "")

    def _cabin_temperature(self) -> float | None:
        return self.state_data.get("interior_temperature")

    def _shown_target(self) -> float | None:
        if self._target is not None and not self.state_data.get("climate_on"):
            return self._target
        reported = self.state_data.get("climate_target_temperature")
        return reported if reported is not None else self._target

    if _NATIVE_TEMPERATURE:

        @property
        def native_current_temperature(self) -> float | None:
            """Return the cabin temperature."""
            return self._cabin_temperature()

        @property
        def native_target_temperature(self) -> float | None:
            """Return the set temperature."""
            return self._shown_target()

    else:

        @property
        def current_temperature(self) -> float | None:
            """Return the cabin temperature."""
            return self._cabin_temperature()

        @property
        def target_temperature(self) -> float | None:
            """Return the set temperature."""
            return self._shown_target()

    @property
    def fan_mode(self) -> str | None:
        """Return the fan level."""
        level = self.state_data.get("climate_fan_level")
        if level is None or not commands.FAN_MIN <= level <= commands.FAN_MAX:
            level = self._fan
        return str(level) if level is not None else None

    @property
    def preset_mode(self) -> str:
        """Return the active preset."""
        if not self.state_data.get("climate_on"):
            return PRESET_NONE
        if self.state_data.get("climate_action") == "defrost":
            return PRESET_DEFROST
        return self._preset

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return further climate details."""
        state = self.state_data
        attributes = {
            "recirculation": state.get("climate_recirculation"),
            "automatic": state.get("climate_auto"),
            "target_temperature_right": state.get("climate_target_temperature_right"),
        }
        return {key: value for key, value in attributes.items() if value is not None}

    # -- commands ------------------------------------------------------------------

    def _temperature(self) -> int:
        value = self._target
        if value is None:
            value = self.state_data.get("climate_target_temperature")
        if value is None:
            value = 22
        return int(max(commands.TEMPERATURE_MIN, min(commands.TEMPERATURE_MAX, round(value))))

    def _fan_level(self) -> int:
        level = self._fan or self.state_data.get("climate_fan_level") or 4
        return int(max(commands.FAN_MIN, min(commands.FAN_MAX, level)))

    async def _send(self, command: RemoteCommand, optimistic: dict[str, Any]) -> None:
        await self.coordinator.async_send_command(self.vin, command, optimistic=optimistic)

    async def _apply(self) -> None:
        """Send the remembered settings to the vehicle."""
        temperature, fan = self._temperature(), self._fan_level()
        await self._send(
            commands.climate(mode=_MODE_TO_API[self._mode], temperature=temperature, fan=fan),
            {
                "climate_on": True,
                "climate_action": _ACTION_OF_MODE[self._mode],
                "climate_target_temperature": float(temperature),
                "climate_fan_level": fan,
                "defrost": False,
            },
        )

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Change the mode or switch off."""
        if hvac_mode == HVACMode.OFF:
            await self.async_turn_off()
            return
        self._mode = hvac_mode
        self._preset = PRESET_NONE
        await self._apply()

    async def async_turn_on(self) -> None:
        """Switch on with the last settings."""
        self._preset = PRESET_NONE
        await self._apply()

    async def async_turn_off(self) -> None:
        """Switch the air conditioning off."""
        self._preset = PRESET_NONE
        await self._send(
            commands.climate_off(self.info.model),
            {"climate_on": False, "climate_action": "off", "defrost": False},
        )

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set the temperature; while off it is only remembered."""
        if (temperature := kwargs.get(ATTR_TEMPERATURE)) is not None:
            self._target = float(temperature)
        mode = kwargs.get(ATTR_HVAC_MODE)
        if mode == HVACMode.OFF:
            await self.async_turn_off()
        elif mode is not None:
            await self.async_set_hvac_mode(mode)
        elif self.state_data.get("climate_on"):
            self._mode = self.hvac_mode or self._mode
            await self._apply()
        else:
            self.async_write_ha_state()

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set the fan level; while off it is only remembered."""
        self._fan = int(fan_mode)
        if self.state_data.get("climate_on"):
            self._mode = self.hvac_mode or self._mode
            await self._apply()
        else:
            self.async_write_ha_state()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Start one of the quick programmes."""
        if preset_mode == PRESET_QUICK_COOL:
            command, action = commands.quick_cool(), "cooling"
        elif preset_mode == PRESET_QUICK_HEAT:
            command, action = commands.quick_heat(), "heating"
        elif preset_mode == PRESET_DEFROST:
            command, action = commands.windshield_defrost(), "defrost"
        else:
            self._preset = PRESET_NONE
            if self.state_data.get("climate_on"):
                await self._apply()
            else:
                self.async_write_ha_state()
            return
        await self._send(
            command,
            {"climate_on": True, "climate_action": action, "defrost": action == "defrost"},
        )
        self._preset = preset_mode
        self.async_write_ha_state()
