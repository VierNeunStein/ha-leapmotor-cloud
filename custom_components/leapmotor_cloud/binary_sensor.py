"""Binary sensors of a Leapmotor vehicle."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import LeapmotorConfigEntry, LeapmotorCoordinator, VehicleData
from .entity import LeapmotorEntity, async_add_vehicle_entities

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class LeapmotorBinarySensorDescription(BinarySensorEntityDescription):
    """Describe a binary sensor."""

    state_key: str | None = None
    value_fn: Callable[[LeapmotorCoordinator, VehicleData], bool | None] | None = None
    always: bool = False


BINARY_SENSORS: tuple[LeapmotorBinarySensorDescription, ...] = (
    LeapmotorBinarySensorDescription(
        key="plugged_in",
        state_key="is_plugged_in",
        device_class=BinarySensorDeviceClass.PLUG,
        always=True,
    ),
    LeapmotorBinarySensorDescription(
        key="charging",
        state_key="is_charging",
        device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
        always=True,
    ),
    LeapmotorBinarySensorDescription(
        key="charge_completed",
        state_key="charge_completed",
    ),
    LeapmotorBinarySensorDescription(
        key="driving",
        state_key="is_driving",
        device_class=BinarySensorDeviceClass.MOVING,
    ),
    LeapmotorBinarySensorDescription(
        key="doors",
        state_key="any_door_open",
        device_class=BinarySensorDeviceClass.DOOR,
    ),
    LeapmotorBinarySensorDescription(
        key="door_driver",
        state_key="door_driver",
        device_class=BinarySensorDeviceClass.DOOR,
    ),
    LeapmotorBinarySensorDescription(
        key="door_passenger",
        state_key="door_passenger",
        device_class=BinarySensorDeviceClass.DOOR,
    ),
    LeapmotorBinarySensorDescription(
        key="door_rear_left",
        state_key="door_rear_left",
        device_class=BinarySensorDeviceClass.DOOR,
    ),
    LeapmotorBinarySensorDescription(
        key="door_rear_right",
        state_key="door_rear_right",
        device_class=BinarySensorDeviceClass.DOOR,
    ),
    LeapmotorBinarySensorDescription(
        key="trunk",
        state_key="trunk",
        device_class=BinarySensorDeviceClass.DOOR,
    ),
    LeapmotorBinarySensorDescription(
        key="windows",
        state_key="any_window_open",
        device_class=BinarySensorDeviceClass.WINDOW,
    ),
    LeapmotorBinarySensorDescription(
        key="window_driver",
        state_key="window_driver",
        device_class=BinarySensorDeviceClass.WINDOW,
        entity_registry_enabled_default=False,
    ),
    LeapmotorBinarySensorDescription(
        key="window_passenger",
        state_key="window_passenger",
        device_class=BinarySensorDeviceClass.WINDOW,
        entity_registry_enabled_default=False,
    ),
    LeapmotorBinarySensorDescription(
        key="window_rear_left",
        state_key="window_rear_left",
        device_class=BinarySensorDeviceClass.WINDOW,
        entity_registry_enabled_default=False,
    ),
    LeapmotorBinarySensorDescription(
        key="window_rear_right",
        state_key="window_rear_right",
        device_class=BinarySensorDeviceClass.WINDOW,
        entity_registry_enabled_default=False,
    ),
    LeapmotorBinarySensorDescription(
        key="climate_active",
        state_key="climate_on",
        device_class=BinarySensorDeviceClass.RUNNING,
    ),
    LeapmotorBinarySensorDescription(
        key="defrost",
        state_key="defrost",
        device_class=BinarySensorDeviceClass.RUNNING,
    ),
    LeapmotorBinarySensorDescription(
        key="rear_window_heating",
        state_key="rear_window_heating",
        device_class=BinarySensorDeviceClass.RUNNING,
        entity_registry_enabled_default=False,
    ),
    LeapmotorBinarySensorDescription(
        key="battery_heating",
        state_key="battery_heating",
        device_class=BinarySensorDeviceClass.HEAT,
    ),
    LeapmotorBinarySensorDescription(
        key="tire_warning",
        state_key="tire_warning",
        device_class=BinarySensorDeviceClass.PROBLEM,
    ),
    LeapmotorBinarySensorDescription(
        key="vehicle_ready",
        state_key="vehicle_ready",
        device_class=BinarySensorDeviceClass.POWER,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    LeapmotorBinarySensorDescription(
        key="parking_brake",
        state_key="parking_brake",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    LeapmotorBinarySensorDescription(
        key="alarm_armed",
        state_key="alarm_armed",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    LeapmotorBinarySensorDescription(
        key="cloud_connection",
        value_fn=lambda coordinator, _data: coordinator.cloud_ok,
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        always=True,
    ),
)


def _value(
    coordinator: LeapmotorCoordinator,
    data: VehicleData,
    description: LeapmotorBinarySensorDescription,
) -> bool | None:
    if description.value_fn is not None:
        return description.value_fn(coordinator, data)
    return data.state.get(description.state_key or "")


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LeapmotorConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the binary sensors."""
    async_add_vehicle_entities(
        entry,
        async_add_entities,
        BINARY_SENSORS,
        LeapmotorBinarySensor,
        lambda coordinator, data, description: (
            description.always or _value(coordinator, data, description) is not None
        ),
    )


class LeapmotorBinarySensor(LeapmotorEntity, BinarySensorEntity):
    """A binary sensor of a vehicle."""

    entity_description: LeapmotorBinarySensorDescription

    def __init__(
        self,
        coordinator: LeapmotorCoordinator,
        vin: str,
        description: LeapmotorBinarySensorDescription,
    ) -> None:
        super().__init__(coordinator, vin, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        """Return the state."""
        return _value(self.coordinator, self.vehicle, self.entity_description)
