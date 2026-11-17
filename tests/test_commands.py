"""Tests for remote-command payloads and the simulated vehicle."""

from __future__ import annotations

from datetime import time
import json

import pytest

from leapmotor_api import (
    DEMO_PIN,
    LeapmotorCommandError,
    LeapmotorDemoClient,
    LeapmotorPinError,
    VehicleInfo,
    commands,
    parser,
)


def test_simple_commands() -> None:
    assert (commands.lock().cmd_id, commands.lock().content) == ("110", '{"value":"lock"}')
    assert commands.unlock().content == '{"value":"unlock"}'
    assert (commands.find_car().cmd_id, commands.find_car().content) == ("120", '{"value":"true"}')
    assert commands.trunk(True).content == '{"value":"true"}'
    assert commands.trunk(False).content == '{"value":"false"}'
    assert (commands.charging(True).cmd_id, commands.charging(True).content) == (
        "193",
        '{"value":"start"}',
    )
    assert commands.charging(False).content == '{"value":"stop"}'
    assert (commands.unlock_charger().cmd_id, commands.unlock_charger().content) == (
        "192",
        '{"operation":"unlock"}',
    )
    assert commands.battery_preheat(True).content == '{"value":"ptcon"}'
    assert commands.battery_preheat(False).content == '{"value":"ptcoff"}'
    assert (commands.sentry_mode(True).cmd_id, commands.sentry_mode(True).content) == (
        "220",
        '{"value":"1"}',
    )
    assert commands.healthy_charging(False).content == '{"value":"0"}'
    assert commands.steering_wheel_heat(True).content == '{"level":"2"}'
    assert commands.steering_wheel_heat(False).content == '{"level":"1"}'
    assert commands.mirror_heat(True).content == '{"value":"2"}'
    assert commands.mirror_heat(False).content == '{"value":"1"}'
    assert all(command.requires_pin for command in (commands.lock(), commands.charging(True)))


def test_window_scale_depends_on_model() -> None:
    assert commands.windows(100, "B10").content == '{"value":"10"}'
    assert commands.windows(20, "C10").content == '{"value":"2"}'
    assert commands.windows(3, "B10").content == '{"value":"1"}'
    assert commands.windows(0, "B10").content == '{"value":"0"}'
    assert commands.windows(20, "T03").content == '{"value":"20"}'
    assert commands.windows(100, "C16").content == '{"value":"100"}'
    assert commands.sunshade(100).content == '{"value":"10"}'
    assert commands.sunshade(0).content == '{"value":"0"}'
    with pytest.raises(ValueError):
        commands.windows(101, "C10")


def test_climate_payloads() -> None:
    assert json.loads(commands.climate(mode="hot", temperature=26, fan=4, recirculate=True).content) == {
        "circle": "in", "mode": "hot", "operate": "manual", "position": "all",
        "temperature": "26", "windlevel": "4", "wshld": "1",
    }  # fmt: skip
    assert json.loads(commands.climate(mode="wind").content)["mode"] == "nohotcold"
    assert json.loads(commands.quick_cool().content) == {
        "circle": "in", "mode": "cold", "operate": "manual", "position": "all",
        "temperature": "18", "windlevel": "7", "wshld": "1",
    }  # fmt: skip
    assert json.loads(commands.quick_heat().content)["temperature"] == "32"
    assert json.loads(commands.windshield_defrost().content)["wshld"] == "2"
    assert commands.climate_off("C10").content == '{"operate":"off"}'
    assert json.loads(commands.climate_off("T03").content)["operate"] == "off"
    assert len(json.loads(commands.climate_off("T03").content)) == 7
    for bad in ({"temperature": 17}, {"temperature": 33}, {"fan": 0}, {"fan": 8}, {"mode": "x"}):
        with pytest.raises(ValueError):
            commands.climate(**bad)


def test_seats() -> None:
    assert commands.seat_heat("driver", 3).content == '{"position":"driver","level":"3"}'
    assert commands.seat_heat("driver", 3).cmd_id == "301"
    assert commands.seat_ventilation("copilot", 0).content == '{"position":"copilot","level":"0"}'
    assert commands.seat_ventilation("copilot", 0).cmd_id == "370"
    with pytest.raises(ValueError):
        commands.seat_heat("rear", 1)
    with pytest.raises(ValueError):
        commands.seat_heat("driver", 4)


def test_charge_plan() -> None:
    command = commands.charge_plan(
        enabled=True,
        limit_percent=80,
        start=time(22, 0),
        end="6:5",
        cycles="1,1,1,1,1,0,0",
        circulation=1,
    )
    assert command.cmd_id == "190"
    assert json.loads(command.content) == {
        "chargeEnable": 1, "chargesoc": 80, "circulation": 1, "cycles": "1,1,1,1,1,0,0",
        "endtime": "06:05", "recharge": 0, "starttime": "22:00",
    }  # fmt: skip
    assert (
        json.loads(
            commands.charge_plan(enabled=False, limit_percent=100, start="0:00", end="8:00").content
        )["cycles"]
        == "1,1,1,1,1,1,1"
    )
    with pytest.raises(ValueError):
        commands.charge_plan(enabled=True, limit_percent=0, start="22:00", end="06:00")
    with pytest.raises(ValueError):
        commands.charge_plan(enabled=True, limit_percent=80, start="25:00", end="06:00")


def test_destination_and_schedules() -> None:
    command = commands.send_destination(
        name="Bahnhof", latitude=52.52, longitude=13.369, address="Europaplatz 1"
    )
    assert not command.requires_pin and command.cmd_id == "180"
    assert json.loads(command.content) == {
        "address": "Europaplatz 1", "addressname": "Bahnhof", "latitude": "52.52",
        "linenum": "0", "longitude": "13.369",
    }  # fmt: skip
    with pytest.raises(ValueError):
        commands.send_destination(name=" ", latitude=1, longitude=1)
    with pytest.raises(ValueError):
        commands.send_destination(name="x", latitude=91, longitude=1)

    schedule = json.loads(
        commands.climate_schedule(
            start_time="2026-12-01T07:30:00", mode="hot", temperature=22, days=[1, 2, 2]
        ).content
    )
    entry = schedule["controls"][0]
    assert (
        entry["start_time"] == "2026-12-01 07:30:00"
        and entry["days"] == [1, 2]
        and entry["on"] == "1"
    )
    assert commands.cancel_climate_schedule().content == '{"controls":[]}'

    prepared = json.loads(
        commands.prepare_car(mode="hot", temperature=22, driver_seat="heat", driver_seat_level=2,
                             passenger_seat="ventilation", passenger_seat_level=1, steering_wheel=True).content
    )  # fmt: skip
    assert prepared["air_condition"]["mode"] == "hot"
    assert prepared["seat_setting"]["driver"] == "2" and prepared["seat_setting"]["copilot"] == "11"
    assert prepared["steeringWheelHeatCtrl"] == {"enable": True, "level": "2"}
    with pytest.raises(ValueError):
        commands.prepare_car(climate_enabled=False)


def test_raw_command() -> None:
    assert commands.raw(140, {"value": "x"}).content == '{"value":"x"}'
    assert commands.raw("140", '{"a":1}', requires_pin=False).requires_pin is False
    with pytest.raises(ValueError):
        commands.raw("abc", {})
    with pytest.raises(ValueError):
        commands.raw(140, "not json")


async def test_demo_vehicle_reacts_to_commands() -> None:
    demo = LeapmotorDemoClient(home=(52.5, 13.4), command_delay=0)
    vehicle = (await demo.get_vehicles())[0]
    assert isinstance(vehicle, VehicleInfo) and demo.is_demo

    state = parser.parse_status(vehicle, await demo.get_status(vehicle))
    assert state["charging_state"] == "charging" and state["charging_type"] == "ac"
    assert state["charging_power"] == pytest.approx(10.8, abs=0.1) and state["locked"] is True
    assert state["charge_finish_time"] is not None and state["latitude"] == 52.5

    with pytest.raises(LeapmotorPinError):
        await demo.send_command(vehicle, commands.unlock(), "0000")
    with pytest.raises(LeapmotorPinError):
        await demo.send_command(vehicle, commands.unlock())

    async def run(command) -> dict:
        result = await demo.send_command(vehicle, command, DEMO_PIN)
        assert result.confirmed
        return parser.parse_status(vehicle, await demo.get_status(vehicle))

    assert (await run(commands.unlock()))["locked"] is False
    assert (await run(commands.charging(False)))["charging_state"] == "paused"
    assert (await run(commands.charging(True)))["charging_state"] == "charging"
    state = await run(commands.climate(mode="hot", temperature=24, fan=6))
    assert state["climate_on"] is True and state["climate_action"] == "heating"
    assert state["climate_target_temperature"] == 24.0 and state["climate_fan_level"] == 6
    assert (await run(commands.climate_off("C10")))["climate_on"] is False
    assert (await run(commands.windshield_defrost()))["climate_action"] == "defrost"
    assert (await run(commands.windows(50, "C10")))["windows_position"] == 50
    assert (await run(commands.trunk(True)))["trunk"] is True
    assert (await run(commands.seat_heat("driver", 2)))["seat_heat_driver"] == 2
    assert (await run(commands.steering_wheel_heat(True)))["steering_wheel_heat"] is True
    assert (await run(commands.sentry_mode(True)))["sentry_mode"] is True
    state = await run(
        commands.charge_plan(enabled=True, limit_percent=90, start="23:00", end="05:00")
    )
    assert state["charge_limit"] == 90 and state["charge_schedule_enabled"] is True
    assert state["charge_schedule_start"] == "23:00"
    assert (await demo.get_charge_plan(vehicle))["percent"] == 90

    demo.set_scenario("driving")
    state = parser.parse_status(vehicle, await demo.get_status(vehicle))
    assert state["is_driving"] is True and state["charging_state"] == "unplugged"
    with pytest.raises(LeapmotorCommandError):
        await demo.send_command(vehicle, commands.charging(True), DEMO_PIN)
    demo.set_scenario("charging_dc")
    state = parser.parse_status(vehicle, await demo.get_status(vehicle))
    assert state["charging_type"] == "dc" and state["charging_power"] > 50
    with pytest.raises(ValueError):
        demo.set_scenario("flying")


async def test_demo_history_goes_through_the_parsers() -> None:
    from datetime import UTC, datetime, timedelta

    demo = LeapmotorDemoClient()
    vehicle = (await demo.get_vehicles())[0]
    now = datetime.now(UTC)
    assert (
        parser.parse_mileage(await demo.get_mileage(vehicle, now - timedelta(days=7), now))[
            "mileage_7d"
        ]
        > 0
    )
    assert (
        parser.parse_consumption_rank(await demo.get_consumption_rank(vehicle))[
            "consumption_average"
        ]
        == 18.0
    )
    window = parser.parse_energy_window(
        await demo.get_energy_window(vehicle, now - timedelta(days=1), now), "t"
    )
    assert window["t_total"] == pytest.approx(9.0, abs=0.2)
    records = parser.parse_charge_records(
        await demo.get_charge_records(vehicle, now.date(), now.date())
    )
    assert records["last_charge_type"] == "ac" and len(records["charge_sessions"]) == 3
    assert parser.parse_unread_count(await demo.get_unread_count()) == 1
    assert parser.parse_software(await demo.get_software(vehicle))["software_latest"] == "1.09.03"
