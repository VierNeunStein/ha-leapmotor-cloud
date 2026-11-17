"""Services (actions) of the integration."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import (
    ATTR_DEVICE_ID,
    CONF_ADDRESS,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_NAME,
)
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv, device_registry as dr
from homeassistant.util import dt as dt_util
import voluptuous as vol

from .api import RemoteCommand, commands
from .const import (
    DOMAIN,
    SERVICE_CANCEL_CLIMATE_SCHEDULE,
    SERVICE_PREPARE_CAR,
    SERVICE_REFRESH,
    SERVICE_SEND_COMMAND,
    SERVICE_SEND_DESTINATION,
    SERVICE_SET_CHARGE_SCHEDULE,
    SERVICE_SET_CLIMATE,
    SERVICE_SET_CLIMATE_SCHEDULE,
)
from .coordinator import LeapmotorCoordinator

ATTR_MODE = "mode"
ATTR_TEMPERATURE = "temperature"
ATTR_FAN = "fan_level"
ATTR_RECIRCULATE = "recirculate"
ATTR_DEFROST = "defrost"
ATTR_ENABLED = "enabled"
ATTR_START = "start"
ATTR_END = "end"
ATTR_LIMIT = "limit"
ATTR_START_TIME = "start_time"
ATTR_DAYS = "days"
ATTR_DRIVER_SEAT = "driver_seat"
ATTR_DRIVER_SEAT_LEVEL = "driver_seat_level"
ATTR_PASSENGER_SEAT = "passenger_seat"
ATTR_PASSENGER_SEAT_LEVEL = "passenger_seat_level"
ATTR_STEERING_WHEEL = "steering_wheel"
ATTR_MIRRORS = "mirrors"
ATTR_CLIMATE = "climate"
ATTR_COMMAND_ID = "command_id"
ATTR_CONTENT = "content"
ATTR_USE_PIN = "use_pin"

MODES = {"cool": "cold", "heat": "hot", "fan": "nohotcold"}
WEEKDAYS = ["sun", "mon", "tue", "wed", "thu", "fri", "sat"]
SEAT_MODES = ["off", "heat", "ventilation"]

_DEVICE = {vol.Optional(ATTR_DEVICE_ID): cv.string}
_CLIMATE = {
    vol.Optional(ATTR_MODE, default="fan"): vol.In(list(MODES)),
    vol.Optional(ATTR_TEMPERATURE, default=22): vol.All(vol.Coerce(int), vol.Range(18, 32)),
    vol.Optional(ATTR_FAN, default=4): vol.All(vol.Coerce(int), vol.Range(1, 7)),
    vol.Optional(ATTR_RECIRCULATE, default=False): cv.boolean,
    vol.Optional(ATTR_DEFROST, default=False): cv.boolean,
}

SCHEMA_DEVICE = vol.Schema(_DEVICE)
SCHEMA_SET_CLIMATE = vol.Schema({**_DEVICE, **_CLIMATE})
SCHEMA_SET_CHARGE_SCHEDULE = vol.All(
    vol.Schema(
        {
            **_DEVICE,
            vol.Optional(ATTR_ENABLED): cv.boolean,
            vol.Optional(ATTR_START): cv.time,
            vol.Optional(ATTR_END): cv.time,
            vol.Optional(ATTR_LIMIT): vol.All(vol.Coerce(int), vol.Range(1, 100)),
        }
    ),
    cv.has_at_least_one_key(ATTR_ENABLED, ATTR_START, ATTR_END, ATTR_LIMIT),
)
SCHEMA_SET_CLIMATE_SCHEDULE = vol.Schema(
    {
        **_DEVICE,
        **_CLIMATE,
        vol.Required(ATTR_START_TIME): cv.datetime,
        vol.Optional(ATTR_DAYS, default=list): vol.All(cv.ensure_list, [vol.In(WEEKDAYS)]),
    }
)
SCHEMA_PREPARE_CAR = vol.Schema(
    {
        **_DEVICE,
        **_CLIMATE,
        vol.Optional(ATTR_CLIMATE, default=True): cv.boolean,
        vol.Optional(ATTR_DRIVER_SEAT, default="off"): vol.In(SEAT_MODES),
        vol.Optional(ATTR_DRIVER_SEAT_LEVEL, default=3): vol.All(vol.Coerce(int), vol.Range(1, 3)),
        vol.Optional(ATTR_PASSENGER_SEAT, default="off"): vol.In(SEAT_MODES),
        vol.Optional(ATTR_PASSENGER_SEAT_LEVEL, default=3): vol.All(
            vol.Coerce(int), vol.Range(1, 3)
        ),
        vol.Optional(ATTR_STEERING_WHEEL, default=False): cv.boolean,
        vol.Optional(ATTR_MIRRORS, default=False): cv.boolean,
    }
)
SCHEMA_SEND_DESTINATION = vol.Schema(
    {
        **_DEVICE,
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_LATITUDE): cv.latitude,
        vol.Required(CONF_LONGITUDE): cv.longitude,
        vol.Optional(CONF_ADDRESS): cv.string,
    }
)
SCHEMA_SEND_COMMAND = vol.Schema(
    {
        **_DEVICE,
        vol.Required(ATTR_COMMAND_ID): vol.All(vol.Coerce(int), vol.Range(100, 999)),
        vol.Required(ATTR_CONTENT): vol.Any(dict, cv.string),
        vol.Optional(ATTR_USE_PIN, default=True): cv.boolean,
    }
)


def _error(key: str, **placeholders: str) -> ServiceValidationError:
    return ServiceValidationError(
        translation_domain=DOMAIN, translation_key=key, translation_placeholders=placeholders
    )


@callback
def _resolve(hass: HomeAssistant, call: ServiceCall) -> tuple[LeapmotorCoordinator, str]:
    """Find the vehicle a service call is meant for."""
    vehicles: dict[str, LeapmotorCoordinator] = {}
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.state is ConfigEntryState.LOADED:
            for vin in entry.runtime_data.data or {}:
                vehicles[vin] = entry.runtime_data

    device_id = call.data.get(ATTR_DEVICE_ID)
    if device_id is None:
        if len(vehicles) == 1:
            vin = next(iter(vehicles))
            return vehicles[vin], vin
        raise _error("device_required" if vehicles else "no_vehicles")

    device = dr.async_get(hass).async_get(device_id)
    if device is not None:
        for domain, identifier in device.identifiers:
            if domain == DOMAIN and identifier in vehicles:
                return vehicles[identifier], identifier
    raise _error("unknown_vehicle", vin=str(device_id)[-6:])


def _climate_arguments(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "mode": MODES[data[ATTR_MODE]],
        "temperature": data[ATTR_TEMPERATURE],
        "fan": data[ATTR_FAN],
        "recirculate": data[ATTR_RECIRCULATE],
        "defrost": data[ATTR_DEFROST],
    }


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register the services."""

    def _build(builder: Callable[[], RemoteCommand]) -> RemoteCommand:
        try:
            return builder()
        except ValueError as err:
            raise ServiceValidationError(str(err)) from err

    async def refresh(call: ServiceCall) -> None:
        coordinator, _vin = _resolve(hass, call)
        await coordinator.async_request_refresh()

    async def set_climate(call: ServiceCall) -> None:
        coordinator, vin = _resolve(hass, call)
        arguments = _climate_arguments(call.data)
        action = {"cold": "cooling", "hot": "heating"}.get(arguments["mode"], "fan")
        await coordinator.async_send_command(
            vin,
            _build(lambda: commands.climate(**arguments)),
            optimistic={
                "climate_on": True,
                "climate_action": "defrost" if arguments["defrost"] else action,
                "climate_target_temperature": float(arguments["temperature"]),
                "climate_fan_level": arguments["fan"],
            },
        )

    async def set_charge_schedule(call: ServiceCall) -> None:
        coordinator, vin = _resolve(hass, call)
        await coordinator.async_set_charge_plan(
            vin,
            enabled=call.data.get(ATTR_ENABLED),
            limit=call.data.get(ATTR_LIMIT),
            start=call.data.get(ATTR_START),
            end=call.data.get(ATTR_END),
        )

    async def set_climate_schedule(call: ServiceCall) -> None:
        coordinator, vin = _resolve(hass, call)
        days = [WEEKDAYS.index(day) for day in call.data[ATTR_DAYS]]
        start_time = call.data[ATTR_START_TIME]
        if start_time.tzinfo is not None:
            # The vehicle expects local wall-clock time.
            start_time = dt_util.as_local(start_time)
        await coordinator.async_send_command(
            vin,
            _build(
                lambda: commands.climate_schedule(
                    start_time=start_time, days=days, **_climate_arguments(call.data)
                )
            ),
        )

    async def cancel_climate_schedule(call: ServiceCall) -> None:
        coordinator, vin = _resolve(hass, call)
        await coordinator.async_send_command(vin, commands.cancel_climate_schedule())

    async def prepare_car(call: ServiceCall) -> None:
        coordinator, vin = _resolve(hass, call)
        data = call.data
        expected: dict[str, Any] = {}
        if data[ATTR_CLIMATE]:
            arguments = _climate_arguments(data)
            action = {"cold": "cooling", "hot": "heating"}.get(arguments["mode"], "fan")
            expected.update(
                climate_on=True,
                climate_action="defrost" if arguments["defrost"] else action,
                climate_target_temperature=float(arguments["temperature"]),
            )
        if data[ATTR_STEERING_WHEEL]:
            expected["steering_wheel_heat"] = True
        if data[ATTR_MIRRORS]:
            expected["mirror_heat"] = True
        for seat, key in (("driver", ATTR_DRIVER_SEAT), ("passenger", ATTR_PASSENGER_SEAT)):
            if data[key] == "heat":
                expected[f"seat_heat_{seat}"] = data[f"{key}_level"]
            elif data[key] == "ventilation":
                expected[f"seat_ventilation_{seat}"] = data[f"{key}_level"]
        await coordinator.async_send_command(
            vin,
            _build(
                lambda: commands.prepare_car(
                    climate_enabled=data[ATTR_CLIMATE],
                    driver_seat=data[ATTR_DRIVER_SEAT],
                    driver_seat_level=data[ATTR_DRIVER_SEAT_LEVEL],
                    passenger_seat=data[ATTR_PASSENGER_SEAT],
                    passenger_seat_level=data[ATTR_PASSENGER_SEAT_LEVEL],
                    steering_wheel=data[ATTR_STEERING_WHEEL],
                    mirrors=data[ATTR_MIRRORS],
                    **_climate_arguments(data),
                )
            ),
            optimistic=expected,
        )

    async def send_destination(call: ServiceCall) -> None:
        coordinator, vin = _resolve(hass, call)
        await coordinator.async_send_command(
            vin,
            _build(
                lambda: commands.send_destination(
                    name=call.data[CONF_NAME],
                    latitude=call.data[CONF_LATITUDE],
                    longitude=call.data[CONF_LONGITUDE],
                    address=call.data.get(CONF_ADDRESS),
                )
            ),
        )

    async def send_command(call: ServiceCall) -> None:
        coordinator, vin = _resolve(hass, call)
        await coordinator.async_send_command(
            vin,
            _build(
                lambda: commands.raw(
                    call.data[ATTR_COMMAND_ID],
                    call.data[ATTR_CONTENT],
                    requires_pin=call.data[ATTR_USE_PIN],
                )
            ),
        )

    for name, handler, schema in (
        (SERVICE_REFRESH, refresh, SCHEMA_DEVICE),
        (SERVICE_SET_CLIMATE, set_climate, SCHEMA_SET_CLIMATE),
        (SERVICE_SET_CHARGE_SCHEDULE, set_charge_schedule, SCHEMA_SET_CHARGE_SCHEDULE),
        (SERVICE_SET_CLIMATE_SCHEDULE, set_climate_schedule, SCHEMA_SET_CLIMATE_SCHEDULE),
        (SERVICE_CANCEL_CLIMATE_SCHEDULE, cancel_climate_schedule, SCHEMA_DEVICE),
        (SERVICE_PREPARE_CAR, prepare_car, SCHEMA_PREPARE_CAR),
        (SERVICE_SEND_DESTINATION, send_destination, SCHEMA_SEND_DESTINATION),
        (SERVICE_SEND_COMMAND, send_command, SCHEMA_SEND_COMMAND),
    ):
        hass.services.async_register(DOMAIN, name, handler, schema=schema)
