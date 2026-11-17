"""The integration with the simulated vehicle: entities, commands and services."""

from __future__ import annotations

from datetime import timedelta
import json

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import device_registry as dr, issue_registry as ir
from homeassistant.helpers.json import ExtendedJSONEncoder
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.leapmotor_cloud.api import DEMO_VIN
from custom_components.leapmotor_cloud.const import DOMAIN
from custom_components.leapmotor_cloud.diagnostics import async_get_config_entry_diagnostics

from .conftest import entity_id


def state(hass: HomeAssistant, platform: str, key: str) -> str:
    current = hass.states.get(entity_id(hass, platform, key))
    assert current is not None
    return current.state


async def call(hass: HomeAssistant, domain: str, service: str, target: str | None, **data) -> None:
    if target is not None:
        data["entity_id"] = target
    await hass.services.async_call(domain, service, data, blocking=True)


async def test_setup_creates_vehicle(hass: HomeAssistant, demo_entry: MockConfigEntry) -> None:
    assert demo_entry.state is ConfigEntryState.LOADED

    device = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, DEMO_VIN), demo_entry.entry_id
    )
    assert device is not None
    assert (device.manufacturer, device.model, device.name) == ("Leapmotor", "C10", "Demo C10")
    assert device.sw_version == "1.08.21"

    soc = hass.states.get(entity_id(hass, "sensor", "soc"))
    assert soc is not None and 40 <= float(soc.state) <= 80
    assert soc.attributes["friendly_name"] == "Demo C10 State of charge"
    assert soc.attributes["unit_of_measurement"] == "%"
    assert state(hass, "sensor", "charging_state") == "charging"
    assert float(state(hass, "sensor", "charging_power")) == pytest.approx(10.8, abs=0.2)
    assert state(hass, "binary_sensor", "plugged_in") == "on"
    assert state(hass, "binary_sensor", "charging") == "on"
    assert state(hass, "lock", "lock") == "locked"
    assert state(hass, "climate", "climate") == "off"
    assert state(hass, "cover", "trunk") == "closed"
    assert state(hass, "binary_sensor", "cloud_connection") == "on"
    assert state(hass, "sensor", "polling_mode") == "active"
    assert state(hass, "update", "software") == "on"
    assert float(state(hass, "sensor", "energy_to_limit")) > 0
    assert float(state(hass, "number", "battery_capacity")) == 69.9
    assert float(state(hass, "sensor", "mileage_7d")) > 0
    assert state(hass, "sensor", "charge_finish_time") not in ("unknown", "unavailable")

    tracker = hass.states.get(entity_id(hass, "device_tracker", "location"))
    assert tracker is not None and tracker.state == "home"

    # Features of the C10 that the T03 does not have.
    for platform, key in (
        ("switch", "charging"),
        ("switch", "charge_schedule"),
        ("number", "charge_limit"),
        ("time", "charge_schedule_start"),
        ("time", "charge_schedule_end"),
        ("cover", "windows"),
        ("select", "seat_heat_driver"),
        ("select", "seat_ventilation_passenger"),
        ("switch", "steering_wheel_heat"),
        ("button", "find_vehicle"),
        ("select", "demo_scenario"),
    ):
        entity_id(hass, platform, key)


async def test_lock(hass: HomeAssistant, demo_entry: MockConfigEntry) -> None:
    lock = entity_id(hass, "lock", "lock")
    await call(hass, "lock", "unlock", lock)
    assert hass.states.get(lock).state == "unlocked"
    await call(hass, "lock", "lock", lock)
    assert hass.states.get(lock).state == "locked"


async def test_missing_pin(hass: HomeAssistant, demo_entry: MockConfigEntry) -> None:
    coordinator = demo_entry.runtime_data
    coordinator.pins = {}
    requests = coordinator.client.request_count
    with pytest.raises(ServiceValidationError) as err:
        await call(hass, "lock", "unlock", entity_id(hass, "lock", "lock"))
    assert err.value.translation_key == "pin_missing"
    assert coordinator.client.request_count == requests


async def test_wrong_pin_is_never_repeated(
    hass: HomeAssistant, demo_entry: MockConfigEntry
) -> None:
    coordinator = demo_entry.runtime_data
    coordinator.pins = {DEMO_VIN: "0000"}
    lock = entity_id(hass, "lock", "lock")
    with pytest.raises(HomeAssistantError) as err:
        await call(hass, "lock", "unlock", lock)
    assert err.value.translation_key == "pin_rejected"
    assert ir.async_get(hass).async_get_issue(DOMAIN, f"pin_rejected_{DEMO_VIN}") is not None

    requests = coordinator.client.request_count
    with pytest.raises(ServiceValidationError) as err:
        await call(hass, "lock", "unlock", lock)
    assert err.value.translation_key == "pin_rejected"
    assert coordinator.client.request_count == requests
    assert hass.states.get(lock).state == "locked"

    # Commands without a PIN keep working.
    await hass.services.async_call(
        DOMAIN,
        "send_destination",
        {"name": "Station", "latitude": 52.52, "longitude": 13.37},
        blocking=True,
    )


async def test_charging_controls(hass: HomeAssistant, demo_entry: MockConfigEntry) -> None:
    limit = entity_id(hass, "number", "charge_limit")
    await call(hass, "number", "set_value", limit, value=90)
    assert float(hass.states.get(limit).state) == 90

    start = entity_id(hass, "time", "charge_schedule_start")
    await call(hass, "time", "set_value", start, time="23:15:00")
    assert hass.states.get(start).state == "23:15:00"

    schedule = entity_id(hass, "switch", "charge_schedule")
    await call(hass, "switch", "turn_on", schedule)
    assert hass.states.get(schedule).state == "on"

    charging = entity_id(hass, "switch", "charging")
    await call(hass, "switch", "turn_off", charging)
    assert hass.states.get(charging).state == "off"
    assert state(hass, "sensor", "charging_state") == "paused"
    assert float(state(hass, "sensor", "charging_power")) == 0

    await call(hass, "switch", "turn_on", charging)
    assert state(hass, "sensor", "charging_state") == "charging"

    # The whole plan survives the changes.
    plan = demo_entry.runtime_data.client._s["plan"]
    assert plan == {
        "isEnable": 1,
        "percent": 90,
        "beginTime": "23:15",
        "endTime": "06:00",
        "cycles": "1,1,1,1,1,1,1",
        "circulation": 1,
        "recharge": 0,
    }


async def test_climate(hass: HomeAssistant, demo_entry: MockConfigEntry) -> None:
    climate = entity_id(hass, "climate", "climate")
    requests = demo_entry.runtime_data.client.request_count
    await call(hass, "climate", "set_temperature", climate, temperature=24)
    current = hass.states.get(climate)
    assert current.state == "off" and current.attributes["temperature"] == 24
    # While off the temperature is only remembered, nothing is sent.
    assert demo_entry.runtime_data.client.request_count == requests

    await call(hass, "climate", "set_hvac_mode", climate, hvac_mode="heat")
    current = hass.states.get(climate)
    assert current.state == "heat"
    assert current.attributes["hvac_action"] == "heating"
    assert current.attributes["temperature"] == 24

    await call(hass, "climate", "set_fan_mode", climate, fan_mode="6")
    assert hass.states.get(climate).attributes["fan_mode"] == "6"

    await call(hass, "climate", "set_preset_mode", climate, preset_mode="defrost")
    current = hass.states.get(climate)
    assert current.attributes["preset_mode"] == "defrost"
    assert current.attributes["hvac_action"] == "defrosting"

    await call(hass, "climate", "turn_off", climate)
    assert hass.states.get(climate).state == "off"


async def test_body_and_comfort(hass: HomeAssistant, demo_entry: MockConfigEntry) -> None:
    windows = entity_id(hass, "cover", "windows")
    await call(hass, "cover", "set_cover_position", windows, position=20)
    current = hass.states.get(windows)
    assert current.state == "open" and current.attributes["current_position"] == 20
    await call(hass, "cover", "close_cover", windows)
    assert hass.states.get(windows).state == "closed"

    trunk = entity_id(hass, "cover", "trunk")
    await call(hass, "cover", "open_cover", trunk)
    assert hass.states.get(trunk).state == "open"

    heat = entity_id(hass, "select", "seat_heat_driver")
    await call(hass, "select", "select_option", heat, option="high")
    assert hass.states.get(heat).state == "high"
    vent = entity_id(hass, "select", "seat_ventilation_driver")
    await call(hass, "select", "select_option", vent, option="low")
    assert hass.states.get(vent).state == "low"
    # Heating and ventilation of one seat exclude each other.
    assert hass.states.get(heat).state == "off"

    wheel = entity_id(hass, "switch", "steering_wheel_heat")
    await call(hass, "switch", "turn_on", wheel)
    assert hass.states.get(wheel).state == "on"

    await call(hass, "button", "press", entity_id(hass, "button", "find_vehicle"))
    await call(hass, "button", "press", entity_id(hass, "button", "quick_cool"))
    assert state(hass, "climate", "climate") == "cool"


async def test_services(hass: HomeAssistant, demo_entry: MockConfigEntry) -> None:
    client = demo_entry.runtime_data.client
    await hass.services.async_call(
        DOMAIN,
        "set_charge_schedule",
        {"enabled": True, "start": "22:30:00", "end": "05:45:00", "limit": 85},
        blocking=True,
    )
    assert client._s["plan"]["beginTime"] == "22:30"
    assert client._s["plan"]["endTime"] == "05:45"
    assert float(state(hass, "number", "charge_limit")) == 85

    await hass.services.async_call(
        DOMAIN, "set_climate", {"mode": "cool", "temperature": 19, "fan_level": 5}, blocking=True
    )
    assert state(hass, "climate", "climate") == "cool"

    device = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, DEMO_VIN), demo_entry.entry_id
    )
    assert device is not None
    await hass.services.async_call(
        DOMAIN,
        "prepare_car",
        {"device_id": device.id, "mode": "heat", "steering_wheel": True, "driver_seat": "heat"},
        blocking=True,
    )
    assert state(hass, "switch", "steering_wheel_heat") == "on"

    await hass.services.async_call(
        DOMAIN,
        "set_climate_schedule",
        {"start_time": "2026-12-01 07:30:00", "days": ["mon", "fri"], "mode": "heat"},
        blocking=True,
    )
    await hass.services.async_call(DOMAIN, "cancel_climate_schedule", {}, blocking=True)
    await hass.services.async_call(
        DOMAIN, "send_command", {"command_id": 120, "content": {"value": "true"}}, blocking=True
    )
    await hass.services.async_call(DOMAIN, "refresh", {}, blocking=True)

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN, "send_command", {"command_id": 120, "content": "not json"}, blocking=True
        )
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN, "refresh", {"device_id": "does-not-exist"}, blocking=True
        )


async def test_demo_scenarios(hass: HomeAssistant, demo_entry: MockConfigEntry) -> None:
    scenario = entity_id(hass, "select", "demo_scenario")
    await call(hass, "select", "select_option", scenario, option="driving")
    assert state(hass, "binary_sensor", "driving") == "on"
    assert state(hass, "sensor", "charging_state") == "unplugged"
    assert state(hass, "sensor", "gear") == "d"
    with pytest.raises(HomeAssistantError):
        await call(hass, "switch", "turn_on", entity_id(hass, "switch", "charging"))

    await call(hass, "select", "select_option", scenario, option="charging_dc")
    assert float(state(hass, "sensor", "charging_power")) > 50


async def test_adaptive_polling(hass: HomeAssistant, demo_entry: MockConfigEntry) -> None:
    coordinator = demo_entry.runtime_data
    assert coordinator.polling_mode == "active"
    assert coordinator.update_interval == timedelta(minutes=5)

    coordinator.requests_today = coordinator.daily_limit
    await coordinator.async_refresh()
    assert coordinator.polling_mode == "budget"
    assert coordinator.update_interval >= timedelta(minutes=60)


async def test_diagnostics_are_redacted(hass: HomeAssistant, demo_entry: MockConfigEntry) -> None:
    diagnostics = await async_get_config_entry_diagnostics(hass, demo_entry)
    text = json.dumps(diagnostics, cls=ExtendedJSONEncoder)
    assert DEMO_VIN not in text
    vehicle = diagnostics["vehicles"][0]
    assert vehicle["state"]["latitude"] == "**REDACTED**"
    assert vehicle["raw_status"]["signal"]["3"] == "**REDACTED**"
    assert vehicle["state"]["soc"] is not None
    assert diagnostics["entry"]["options"]["pins"] == "**REDACTED**"
