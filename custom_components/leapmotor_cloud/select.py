"""Selects of a Leapmotor vehicle."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import DEMO_SCENARIOS, LeapmotorDemoClient, RemoteCommand, commands
from .api.const import LEGACY_MODELS, RIGHT_SEAT_HEAT, RIGHT_SEAT_VENTILATION
from .coordinator import LeapmotorConfigEntry, LeapmotorCoordinator, VehicleData
from .entity import LeapmotorEntity, async_add_vehicle_entities

PARALLEL_UPDATES = 1

LEVELS = ["off", "low", "medium", "high"]


@dataclass(frozen=True, kw_only=True)
class LeapmotorSeatDescription(SelectEntityDescription):
    """Describe a seat comfort level."""

    state_key: str
    counterpart_key: str
    command_fn: Callable[[str, int], RemoteCommand]
    seat: str
    right: int


SEATS: tuple[LeapmotorSeatDescription, ...] = (
    LeapmotorSeatDescription(
        key="seat_heat_driver",
        state_key="seat_heat_driver",
        counterpart_key="seat_ventilation_driver",
        command_fn=commands.seat_heat,
        seat="driver",
        right=RIGHT_SEAT_HEAT,
    ),
    LeapmotorSeatDescription(
        key="seat_heat_passenger",
        state_key="seat_heat_passenger",
        counterpart_key="seat_ventilation_passenger",
        command_fn=commands.seat_heat,
        seat="copilot",
        right=RIGHT_SEAT_HEAT,
    ),
    LeapmotorSeatDescription(
        key="seat_ventilation_driver",
        state_key="seat_ventilation_driver",
        counterpart_key="seat_heat_driver",
        command_fn=commands.seat_ventilation,
        seat="driver",
        right=RIGHT_SEAT_VENTILATION,
    ),
    LeapmotorSeatDescription(
        key="seat_ventilation_passenger",
        state_key="seat_ventilation_passenger",
        counterpart_key="seat_heat_passenger",
        command_fn=commands.seat_ventilation,
        seat="copilot",
        right=RIGHT_SEAT_VENTILATION,
    ),
)


def _supported(
    _coordinator: LeapmotorCoordinator, data: VehicleData, description: LeapmotorSeatDescription
) -> bool:
    if data.info.model in LEGACY_MODELS:
        return False
    return bool(data.info.has_right(description.right)) or (
        data.state.get(description.state_key) is not None
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LeapmotorConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the selects."""
    coordinator = entry.runtime_data
    async_add_vehicle_entities(entry, async_add_entities, SEATS, LeapmotorSeatSelect, _supported)
    if isinstance(coordinator.client, LeapmotorDemoClient):
        async_add_entities(
            LeapmotorDemoScenario(coordinator, vin, coordinator.client) for vin in coordinator.data
        )


class LeapmotorSeatSelect(LeapmotorEntity, SelectEntity):
    """Heating or ventilation level of a front seat."""

    entity_description: LeapmotorSeatDescription
    _attr_options = LEVELS

    def __init__(
        self,
        coordinator: LeapmotorCoordinator,
        vin: str,
        description: LeapmotorSeatDescription,
    ) -> None:
        super().__init__(coordinator, vin, description.key, right=description.right)
        self.entity_description = description

    @property
    def current_option(self) -> str | None:
        """Return the active level."""
        level = self.state_data.get(self.entity_description.state_key)
        if level is None or not 0 <= level < len(LEVELS):
            return None
        return LEVELS[level]

    async def async_select_option(self, option: str) -> None:
        """Set the level. Heating and ventilation exclude each other."""
        description = self.entity_description
        level = LEVELS.index(option)
        optimistic: dict[str, object] = {description.state_key: level}
        if level and self.state_data.get(description.counterpart_key):
            optimistic[description.counterpart_key] = 0
        await self.coordinator.async_send_command(
            self.vin, description.command_fn(description.seat, level), optimistic=optimistic
        )


class LeapmotorDemoScenario(LeapmotorEntity, SelectEntity):
    """Switch the simulated vehicle between typical situations."""

    _attr_options = list(DEMO_SCENARIOS)
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self, coordinator: LeapmotorCoordinator, vin: str, client: LeapmotorDemoClient
    ) -> None:
        super().__init__(coordinator, vin, "demo_scenario")
        self._client = client

    @property
    def current_option(self) -> str:
        """Return the active scenario."""
        return self._client.scenario

    async def async_select_option(self, option: str) -> None:
        """Activate a scenario and show it right away."""
        self._client.set_scenario(option)
        await self.coordinator.async_refresh()
