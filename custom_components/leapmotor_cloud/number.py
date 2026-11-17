"""Numbers of a Leapmotor vehicle."""

from __future__ import annotations

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfEnergy
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
    """Set up the numbers."""
    coordinator = entry.runtime_data
    entities: list[NumberEntity] = []
    for vin, data in coordinator.data.items():
        entities.append(LeapmotorBatteryCapacity(coordinator, vin))
        if data.info.model not in LEGACY_MODELS:
            entities.append(LeapmotorChargeLimit(coordinator, vin))
    async_add_entities(entities)


class LeapmotorChargeLimit(LeapmotorEntity, NumberEntity):
    """The state of charge at which the vehicle stops charging."""

    _attr_native_min_value = 20
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator: LeapmotorCoordinator, vin: str) -> None:
        super().__init__(coordinator, vin, "charge_limit", right=RIGHT_CHARGE_LIMIT)

    @property
    def native_value(self) -> float | None:
        """Return the current limit."""
        return self.state_data.get("charge_limit")

    async def async_set_native_value(self, value: float) -> None:
        """Write the limit; the rest of the charging plan stays as it is."""
        await self.coordinator.async_set_charge_plan(self.vin, limit=int(value))


class LeapmotorBatteryCapacity(LeapmotorEntity, NumberEntity):
    """Usable battery capacity, the basis of the energy estimates.

    This is a setting of the integration, nothing is sent to the vehicle.
    """

    _attr_native_min_value = 10
    _attr_native_max_value = 150
    _attr_native_step = 0.1
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = NumberDeviceClass.ENERGY_STORAGE
    _attr_mode = NumberMode.BOX
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: LeapmotorCoordinator, vin: str) -> None:
        super().__init__(coordinator, vin, "battery_capacity")

    @property
    def native_value(self) -> float | None:
        """Return the configured or the default capacity."""
        return self.coordinator.battery_capacity(self.vin)

    async def async_set_native_value(self, value: float) -> None:
        """Store the capacity."""
        self.coordinator.set_battery_capacity(self.vin, value)
