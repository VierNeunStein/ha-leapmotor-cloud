"""Sensors of a Leapmotor vehicle."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfEnergyDistance,
    UnitOfLength,
    UnitOfPower,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.typing import StateType

from .api.parser import CHARGING_STATES, GEARS
from .coordinator import LeapmotorConfigEntry, LeapmotorCoordinator, VehicleData
from .entity import LeapmotorEntity, async_add_vehicle_entities

PARALLEL_UPDATES = 0

POLLING_MODES = ["idle", "active", "budget", "backoff", "paused"]

type SensorValue = StateType | datetime | date


@dataclass(frozen=True, kw_only=True)
class LeapmotorSensorDescription(SensorEntityDescription):
    """Describe a sensor.

    The value comes from ``state_key`` (vehicle state), ``extra_key`` (history
    and statistics) or ``value_fn``.
    """

    state_key: str | None = None
    extra_key: str | None = None
    value_fn: Callable[[LeapmotorCoordinator, VehicleData], SensorValue] | None = None
    attrs_fn: Callable[[LeapmotorCoordinator, VehicleData], dict[str, Any]] | None = None
    always: bool = False


def _energy_to_limit(coordinator: LeapmotorCoordinator, data: VehicleData) -> float | None:
    capacity = coordinator.battery_capacity(data.info.vin)
    soc = data.state.get("soc_precise") or data.state.get("soc")
    limit = data.state.get("charge_limit")
    if capacity is None or soc is None or limit is None:
        return None
    return round(max(0.0, capacity * (limit - soc) / 100.0), 1)


def _battery_energy(coordinator: LeapmotorCoordinator, data: VehicleData) -> float | None:
    if (reported := data.state.get("available_energy")) is not None:
        return reported
    capacity = coordinator.battery_capacity(data.info.vin)
    soc = data.state.get("soc_precise") or data.state.get("soc")
    if capacity is None or soc is None:
        return None
    return round(capacity * soc / 100.0, 1)


def _interval(coordinator: LeapmotorCoordinator, _data: VehicleData) -> float | None:
    interval = coordinator.update_interval
    return round(interval.total_seconds() / 60.0, 1) if interval else None


SENSORS: tuple[LeapmotorSensorDescription, ...] = (
    # --- battery and charging ---------------------------------------------------
    LeapmotorSensorDescription(
        key="soc",
        state_key="soc",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        always=True,
        attrs_fn=lambda _c, data: {"precise": data.state.get("soc_precise")},
    ),
    LeapmotorSensorDescription(
        key="range",
        state_key="range",
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        suggested_display_precision=0,
        always=True,
        attrs_fn=lambda _c, data: {
            "standard": data.state.get("range_mode"),
            "at_full_charge": data.state.get("range_max"),
        },
    ),
    LeapmotorSensorDescription(
        key="range_max",
        state_key="range_max",
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        suggested_display_precision=0,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    LeapmotorSensorDescription(
        key="charging_state",
        state_key="charging_state",
        device_class=SensorDeviceClass.ENUM,
        options=list(CHARGING_STATES),
        always=True,
        attrs_fn=lambda _c, data: {
            "code": data.state.get("charge_state_code"),
            "type": data.state.get("charging_type"),
        },
    ),
    LeapmotorSensorDescription(
        key="charging_power",
        state_key="charging_power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        suggested_display_precision=1,
        always=True,
    ),
    LeapmotorSensorDescription(
        key="battery_power",
        state_key="battery_power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        suggested_display_precision=1,
        entity_registry_enabled_default=False,
    ),
    LeapmotorSensorDescription(
        key="battery_current",
        state_key="battery_current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        suggested_display_precision=1,
        entity_registry_enabled_default=False,
    ),
    LeapmotorSensorDescription(
        key="battery_voltage",
        state_key="battery_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        suggested_display_precision=0,
        entity_registry_enabled_default=False,
    ),
    LeapmotorSensorDescription(
        key="charge_time_remaining",
        state_key="charge_time_remaining",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        always=True,
    ),
    LeapmotorSensorDescription(
        key="charge_finish_time",
        state_key="charge_finish_time",
        device_class=SensorDeviceClass.TIMESTAMP,
        always=True,
    ),
    LeapmotorSensorDescription(
        key="energy_to_limit",
        value_fn=_energy_to_limit,
        device_class=SensorDeviceClass.ENERGY_STORAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=1,
    ),
    LeapmotorSensorDescription(
        key="battery_energy",
        value_fn=_battery_energy,
        device_class=SensorDeviceClass.ENERGY_STORAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=1,
    ),
    LeapmotorSensorDescription(
        key="battery_temperature",
        state_key="battery_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    # --- driving -----------------------------------------------------------------
    LeapmotorSensorDescription(
        key="odometer",
        state_key="odometer",
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        suggested_display_precision=0,
        always=True,
    ),
    LeapmotorSensorDescription(
        key="speed",
        state_key="speed",
        device_class=SensorDeviceClass.SPEED,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
        suggested_display_precision=0,
    ),
    LeapmotorSensorDescription(
        key="gear",
        state_key="gear",
        device_class=SensorDeviceClass.ENUM,
        options=list(GEARS),
    ),
    LeapmotorSensorDescription(
        key="fuel_level",
        state_key="fuel_level",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=0,
    ),
    LeapmotorSensorDescription(
        key="fuel_range",
        state_key="fuel_range",
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
    ),
    LeapmotorSensorDescription(
        key="combined_range",
        state_key="combined_range",
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
    ),
    # --- climate and body ----------------------------------------------------------
    LeapmotorSensorDescription(
        key="interior_temperature",
        state_key="interior_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
    ),
    LeapmotorSensorDescription(
        key="outdoor_temperature",
        state_key="outdoor_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
    ),
    *(
        LeapmotorSensorDescription(
            key=f"tire_pressure_{wheel}",
            state_key=f"tire_pressure_{wheel}",
            device_class=SensorDeviceClass.PRESSURE,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfPressure.BAR,
            suggested_display_precision=2,
        )
        for wheel in ("fl", "fr", "rl", "rr")
    ),
    # --- statistics ----------------------------------------------------------------
    LeapmotorSensorDescription(
        key="energy_today",
        extra_key="energy_today_total",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=1,
        attrs_fn=lambda _c, data: {
            "driving": data.extras.get("energy_today_driving"),
            "climate": data.extras.get("energy_today_climate"),
            "other": data.extras.get("energy_today_other"),
        },
    ),
    LeapmotorSensorDescription(
        key="energy_last_week",
        extra_key="energy_last_week_total",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=1,
        attrs_fn=lambda _c, data: {
            "driving": data.extras.get("energy_last_week_driving"),
            "climate": data.extras.get("energy_last_week_climate"),
            "other": data.extras.get("energy_last_week_other"),
        },
    ),
    LeapmotorSensorDescription(
        key="total_energy",
        extra_key="total_energy",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=0,
    ),
    LeapmotorSensorDescription(
        key="mileage_7d",
        extra_key="mileage_7d",
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        suggested_display_precision=0,
        attrs_fn=lambda _c, data: {"days": data.extras.get("daily_history")},
    ),
    LeapmotorSensorDescription(
        key="energy_7d",
        extra_key="energy_7d",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=1,
    ),
    LeapmotorSensorDescription(
        key="consumption_average",
        extra_key="consumption_average",
        device_class=SensorDeviceClass.ENERGY_DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfEnergyDistance.KILO_WATT_HOUR_PER_100_KM,
        suggested_display_precision=1,
        attrs_fn=lambda _c, data: {
            "rank": data.extras.get("consumption_rank"),
            "weeks": data.extras.get("weekly_consumption"),
        },
    ),
    LeapmotorSensorDescription(
        key="last_charge_energy",
        extra_key="last_charge_energy",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=1,
        attrs_fn=lambda _c, data: {
            "type": data.extras.get("last_charge_type"),
            "start": data.extras.get("last_charge_start"),
            "end": data.extras.get("last_charge_end"),
            "duration_minutes": data.extras.get("last_charge_duration"),
            "sessions": data.extras.get("charge_sessions"),
        },
    ),
    LeapmotorSensorDescription(
        key="last_charge_end",
        extra_key="last_charge_end",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_registry_enabled_default=False,
    ),
    LeapmotorSensorDescription(
        key="delivery_days",
        extra_key="delivery_days",
        native_unit_of_measurement=UnitOfTime.DAYS,
        device_class=SensorDeviceClass.DURATION,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    LeapmotorSensorDescription(
        key="messages_unread",
        extra_key="messages_unread",
        state_class=SensorStateClass.MEASUREMENT,
        attrs_fn=lambda _c, data: {
            "title": data.extras.get("last_message_title"),
            "text": data.extras.get("last_message_text"),
            "time": data.extras.get("last_message_time"),
        },
    ),
    # --- diagnostics ------------------------------------------------------------------
    LeapmotorSensorDescription(
        key="last_update",
        state_key="vehicle_timestamp",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        always=True,
    ),
    LeapmotorSensorDescription(
        key="polling_mode",
        value_fn=lambda coordinator, _data: coordinator.polling_mode,
        device_class=SensorDeviceClass.ENUM,
        options=POLLING_MODES,
        entity_category=EntityCategory.DIAGNOSTIC,
        always=True,
        attrs_fn=lambda coordinator, data: {
            "interval_minutes": _interval(coordinator, data),
            "last_poll": data.polled_at,
            "last_error": coordinator.last_error,
        },
    ),
    LeapmotorSensorDescription(
        key="api_requests_today",
        value_fn=lambda coordinator, _data: coordinator.requests_today,
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        always=True,
        attrs_fn=lambda coordinator, _data: {"daily_limit": coordinator.daily_limit},
    ),
)


def _value(
    coordinator: LeapmotorCoordinator, data: VehicleData, description: LeapmotorSensorDescription
) -> SensorValue:
    if description.value_fn is not None:
        return description.value_fn(coordinator, data)
    if description.state_key is not None:
        return data.state.get(description.state_key)
    return data.extras.get(description.extra_key or "")


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LeapmotorConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the sensors."""
    async_add_vehicle_entities(
        entry,
        async_add_entities,
        SENSORS,
        LeapmotorSensor,
        lambda coordinator, data, description: (
            description.always or _value(coordinator, data, description) is not None
        ),
    )


class LeapmotorSensor(LeapmotorEntity, SensorEntity):
    """A sensor of a vehicle."""

    entity_description: LeapmotorSensorDescription

    def __init__(
        self,
        coordinator: LeapmotorCoordinator,
        vin: str,
        description: LeapmotorSensorDescription,
    ) -> None:
        super().__init__(coordinator, vin, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> SensorValue:
        """Return the value of the sensor."""
        value = _value(self.coordinator, self.vehicle, self.entity_description)
        options = self.entity_description.options
        if options is not None and value not in options:
            return None
        return value

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional details."""
        if self.entity_description.attrs_fn is None:
            return None
        attributes = self.entity_description.attrs_fn(self.coordinator, self.vehicle)
        return {key: value for key, value in attributes.items() if value is not None}
