"""Tests for the interpretation of cloud payloads."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from leapmotor_api import VehicleInfo, parser

C10 = VehicleInfo(vin="LTEST00000000C10", car_type="C10")
B10 = VehicleInfo(vin="LTEST00000000B10", car_type="B10")
T03 = VehicleInfo(vin="LTEST00000000T03", car_type="T03")

# A parked, locked, unplugged C10 as documented by the community.
C10_PARKED = {
    "privacyGPS": 1,
    "signal": {
        "47": 0, "49": 0, "50": 0, "1010": 0, "1149": 0, "1177": 424.9, "1178": 0.1,
        "1182": 18, "1186": 0, "1197": 0, "1204": 65, "1255": 2, "1256": 0, "1257": 0,
        "1258": 0, "1277": 0, "1278": 0, "1279": 0, "1280": 0, "1281": 0, "1298": 1,
        "1318": 3030, "1319": 0.0, "1349": 21.5, "1480": 1, "1693": 0, "1694": 0,
        "1695": 0, "1696": 0, "1816": 0, "1879": 0, "1880": 0, "1938": 0, "1939": 1,
        "1941": 1, "1943": 0, "1945": 0, "1946": 0, "2100": 0, "2101": 0, "2118": 0,
        "2119": 0, "2183": 23.0, "2188": 278, "2190": 40.858536, "2191": 14.283342,
        "2641": 0, "2646": 255, "2648": 0, "2653": 250, "2655": 0, "2660": 253,
        "2662": 0, "2667": 253, "3257": 283, "3260": 278, "3262": 1, "3636": 0,
        "3713": 0, "3724": 14.28319, "3725": 40.85812, "3727": 0, "3728": 0,
        "3736": 0, "100003": 65.3, "sts": 1778137347360, "2": 14.28319, "3": 40.85812,
    },
    "config": {
        "3": {
            "cycles": "1,1,1,1,1,1,1", "endTime": "08:00", "percent": 100, "isEnable": 0,
            "recharge": 0, "beginTime": "22:00", "circulation": 1,
        }
    },
}  # fmt: skip


def status(vehicle: VehicleInfo, **signals: object) -> dict:
    data = {
        "signal": {
            **C10_PARKED["signal"],
            **{key.lstrip("s"): value for key, value in signals.items()},
        }
    }
    return parser.parse_status(vehicle, data)


def test_parked_c10() -> None:
    state = parser.parse_status(C10, C10_PARKED)
    assert state["soc"] == 65 and state["soc_precise"] == 65.3
    assert state["range"] == 278 and state["range_max"] == 283 and state["range_mode"] == "wltp"
    assert state["odometer"] == 3030 and state["speed"] == 0.0
    assert state["gear"] == "p" and state["is_parked"] is True and state["is_driving"] is False
    assert state["locked"] is True
    assert state["any_door_open"] is False and state["any_window_open"] is False
    assert state["charging_state"] == "unplugged"
    assert state["is_plugged_in"] is False and state["is_charging"] is False
    assert state["charging_power"] == 0.0 and state["charge_finish_time"] is None
    assert state["charge_limit"] == 100 and state["charge_schedule_enabled"] is False
    assert state["charge_schedule_start"] == "22:00" and state["charge_plan_complete"] is True
    assert state["climate_on"] is False and state["climate_action"] == "off"
    assert state["climate_target_temperature"] == 23.0 and state["interior_temperature"] == 21.5
    assert state["latitude"] == pytest.approx(40.85812) and state["longitude"] == pytest.approx(
        14.28319
    )
    assert state["tire_pressure_fl"] == 2.55 and state["tire_pressure_fr"] == 2.5
    assert state["tire_pressure_rl"] == 2.53 and state["tire_warning"] is False
    assert state["battery_temperature"] == 18 and state["battery_heating"] is False
    assert state["vehicle_timestamp"] == datetime.fromtimestamp(1778137347.36, UTC)
    assert state["is_reev"] is False


def test_every_parsed_state_uses_a_known_charging_state() -> None:
    assert parser.parse_status(C10, C10_PARKED)["charging_state"] in parser.CHARGING_STATES


def test_ac_charging() -> None:
    state = status(C10, s1149=1, s47=1, s1178=-16.4, s1177=410.0, s1200=95)
    assert state["charging_state"] == "charging" and state["is_charging"] is True
    assert state["is_plugged_in"] is True and state["charging_type"] == "ac"
    assert state["charging_power"] == pytest.approx(6.72)
    assert state["battery_power"] == pytest.approx(6.72)
    assert state["charge_time_remaining"] == 95
    assert state["charge_finish_time"] == datetime(2026, 5, 7, 8, 37, tzinfo=UTC)


def test_dc_charging_is_detected_by_flag_or_power() -> None:
    assert (
        status(B10, s1149=1, s1197=1, s1178=-150.0, s1177=400.0, s1200=20)["charging_type"] == "dc"
    )
    assert (
        status(B10, s1149=1, s1197=0, s1178=-150.0, s1177=400.0, s1200=20)["charging_type"] == "dc"
    )
    # On the T03 the flag is ambiguous: only the power counts.
    assert (
        status(T03, s1149=1, s1197=1, s1178=-12.0, s1177=350.0, s1200=20)["charging_type"] == "ac"
    )


def test_connection_code_alone_is_not_charging() -> None:
    # The backend can keep reporting "charging" after the session has ended.
    state = status(C10, s1149=1, s47=1, s1178=0.0, s1200=0)
    assert state["is_charging"] is False and state["charging_state"] == "plugged_in"
    assert state["charging_power"] == 0.0 and state["charge_time_remaining"] == 0


def test_finished_scheduled_and_paused() -> None:
    assert status(C10, s1149=2, s47=1, s1178=0.0, s1200=0)["charging_state"] == "finished"
    assert status(C10, s1149=1, s47=1, s1178=0.2, s1200=0, s3736=1)["charging_state"] == "finished"
    assert status(C10, s1149=4, s47=1, s1178=0.0, s1200=0)["charging_state"] == "scheduled"
    assert status(C10, s1149=6, s47=1, s1178=0.0, s1200=0)["charging_state"] == "paused"
    # A real current wins even while the plan says "waiting".
    assert status(C10, s1149=4, s47=1, s1178=-15.0, s1200=60)["charging_state"] == "charging"


def test_slow_charging_without_pack_current() -> None:
    state = status(C10, s1149=2, s47=1, s1178=0.3, s1200=180, s3235=40)
    assert state["is_reev"] is True
    assert state["is_charging"] is True and state["charging_state"] == "charging"


def test_low_current_needs_confirmation() -> None:
    assert status(C10, s1149=1, s47=1, s1178=-1.5, s1177=400.0, s1200=0)["is_charging"] is False
    assert status(C10, s1149=1, s47=1, s1178=-2.6, s1177=400.0, s1200=0)["is_charging"] is True
    assert status(C10, s1149=1, s47=1, s1178=-1.5, s1177=400.0, s1200=30)["is_charging"] is True


def test_driving_never_counts_as_charging() -> None:
    state = status(C10, s1010=3, s1319=62.0, s1149=5, s1178=-40.0, s1258=1)
    assert state["is_driving"] is True and state["is_parked"] is False and state["gear"] == "d"
    assert state["is_plugged_in"] is False and state["is_charging"] is False
    assert state["charging_state"] == "unplugged" and state["charging_power"] == 0.0
    assert state["battery_power"] == pytest.approx(17.0)


def test_t03_pause_keeps_cable_connected() -> None:
    assert status(T03, s1149=0, s1197=1, s1178=0, s1200=0)["charging_state"] == "plugged_in"
    assert status(C10, s1149=0, s1197=1, s1178=0, s1200=0)["charging_state"] == "unplugged"


def test_climate_and_comfort() -> None:
    state = status(C10, s1938=1, s3713=3, s1941=5, s2100=2, s2119=3, s1816=2, s49=1, s3636=1)
    assert state["climate_on"] is True and state["climate_action"] == "heating"
    assert state["climate_fan_level"] == 5
    assert state["seat_heat_driver"] == 2 and state["seat_ventilation_passenger"] == 3
    assert state["steering_wheel_heat"] is True and state["mirror_heat"] is True
    assert state["sentry_mode"] is True
    assert status(C10, s1938=1, s3713=1)["climate_action"] == "cooling"
    assert status(C10, s1938=1, s1945=2)["climate_action"] == "defrost"
    assert status(C10, s1938=1, s3713=4)["climate_action"] == "fan"
    assert status(VehicleInfo(vin="A", car_type="A10"), s1816=1)["steering_wheel_heat"] is True
    assert status(C10, s1816=1)["steering_wheel_heat"] is False


def test_openings() -> None:
    state = status(C10, s1277=1, s1281=1, s1694=1, s3727=40, s1298=0)
    assert state["locked"] is False
    assert state["door_driver"] is True and state["door_passenger"] is False
    assert state["trunk"] is True and state["any_door_open"] is True
    assert state["window_passenger"] is True and state["any_window_open"] is True
    # Flag based models ignore the position for the open state, the T03 uses it.
    assert state["window_driver"] is False and state["windows_position"] == 40
    assert status(T03, s3727=40)["window_driver"] is True


def test_t03_named_fields() -> None:
    data = {
        "soc": 85, "chargeState": 1, "chargeRemainTime": 30, "batteryCurrent": -9.5,
        "batteryVoltage": 340.0, "dcInputFastCharge": 0, "dumpEnergy": 28500,
        "expectedMileage": 220, "speed": 0, "totalMileage": 15000, "gearStatus": 0,
        "latitude": 45.123, "longitude": 7.456, "acSwitch": False, "acSetting": 22.0,
        "driverDoorLockStatus": True, "lbcmDriverDoorStatus": False, "bbcmBackDoorStatus": False,
        "leftFrontTirePressure": 250, "rightFrontTirePressure": 255,
        "collectTime": "2026-05-07 10:30:00", "chargesocSetting": 80, "chargeTimeSetting": "22:00",
        "outdoorTemp": 11.5,
    }  # fmt: skip
    state = parser.parse_status(T03, data)
    assert state["soc"] == 85 and state["range"] == 220 and state["odometer"] == 15000
    assert state["locked"] is True and state["trunk"] is False
    assert state["is_charging"] is True and state["charging_power"] == pytest.approx(3.23)
    assert state["available_energy"] == 28.5 and state["outdoor_temperature"] == 11.5
    assert state["charge_limit"] == 80 and state["charge_schedule_start"] == "22:00"
    assert state["charge_plan_complete"] is False
    assert state["latitude"] == 45.123 and state["tire_pressure_fl"] == 2.5
    assert state["vehicle_timestamp"] == datetime(2026, 5, 7, 10, 30, tzinfo=UTC)


def test_missing_data_stays_unknown() -> None:
    state = parser.parse_status(C10, {})
    assert state["soc"] is None and state["locked"] is None and state["latitude"] is None
    assert state["charging_state"] is None and state["is_charging"] is None
    assert state["charging_power"] is None and state["any_door_open"] is None
    assert state["climate_action"] is None and state["vehicle_timestamp"] is None
    assert not parser.status_has_data({}) and parser.status_has_data(C10_PARKED)


def test_unsigned_coordinates_take_the_hemisphere_of_home() -> None:
    data = {"signal": {"3725": 33.9, "3724": 18.4}}
    north = parser.parse_status(C10, data, home=(52.0, 13.0))
    south = parser.parse_status(C10, data, home=(-33.9, 18.4))
    assert north["latitude"] == 33.9 and south["latitude"] == -33.9 and south["longitude"] == 18.4


def test_timestamps() -> None:
    assert parser.parse_timestamp(1778137347360) == datetime.fromtimestamp(1778137347.36, UTC)
    assert parser.parse_timestamp(1778137347) == datetime.fromtimestamp(1778137347, UTC)
    assert parser.parse_timestamp(0) is None and parser.parse_timestamp("nonsense") is None


def test_history_parsers() -> None:
    mileage = parser.parse_mileage(
        {
            "totalEnergy": 512.4,
            "deliveryDays": 120,
            "totalAccumulatedMileage": 84.5,
            "detail": [
                {"day": "2026-11-10", "accumulatedMileage": 40.0, "accumulatedEnergyConsume": 7},
                {"day": "2026-11-11", "accumulatedMileage": 44.5},
            ],
        }
    )
    assert mileage["total_energy"] == 512.4 and mileage["mileage_7d"] == 84.5
    assert mileage["energy_7d"] == 7.0 and len(mileage["daily_history"]) == 2
    assert (
        parser.parse_mileage({"detail": [{"accumulatedEnergyConsume": 7400}]}, energy_in_wh=True)[
            "energy_7d"
        ]
        == 7.4
    )
    assert parser.parse_mileage({})["energy_7d"] is None

    rank = parser.parse_consumption_rank(
        {"rankResult": {"rank": "12%", "hundredKmEC": "17.6"}, "weeklyEC": [{"hundredKmEC": 17.9}]}
    )
    assert (
        rank["consumption_average"] == 17.6 and rank["weekly_consumption"][0]["consumption"] == 17.9
    )

    window = parser.parse_energy_window(
        {"driverEC": "30.5", "acEC": "4.2", "otherEC": "1.3"}, "energy_today"
    )
    assert window == {
        "energy_today_driving": 30.5, "energy_today_climate": 4.2,
        "energy_today_other": 1.3, "energy_today_total": 36.0,
    }  # fmt: skip
    assert parser.parse_energy_window({}, "x")["x_total"] is None


def test_charge_records_messages_and_software() -> None:
    records = parser.parse_charge_records(
        {
            "list": [
                {
                    "chargeGunStartTs": 1778000000000,
                    "chargeGunEndTs": 1778003600000,
                    "chargeType": "2",
                    "chargeInEnergy": 30,
                },
                {
                    "chargeGunStartTs": 1778130000000,
                    "chargeGunEndTs": 1778137200000,
                    "chargeType": "1",
                    "chargeInEnergy": 21.5,
                },
            ]
        }
    )
    assert records["last_charge_energy"] == 21.5 and records["last_charge_type"] == "ac"
    assert records["last_charge_duration"] == 120 and len(records["charge_sessions"]) == 2
    assert parser.parse_charge_records({})["last_charge_energy"] is None

    assert parser.parse_unread_count({"unread": 3}) == 3
    assert parser.parse_unread_count("2") == 2 and parser.parse_unread_count(None) is None
    assert (
        parser.parse_messages({"list": [{"title": "Hi", "sendTime": 1778137200000}]})[
            "last_message_title"
        ]
        == "Hi"
    )
    assert parser.parse_messages(None)["last_message_title"] is None

    software = parser.parse_software(
        {
            "currentVersion": {"generalVersion": "1.2.3"},
            "newVersion": {
                "generalVersion": "1.3.0",
                "logJsonMultiLang": [{"data": [{"title": "New", "content": "Things"}]}],
            },
        }
    )
    assert software["software_version"] == "1.2.3" and software["software_latest"] == "1.3.0"
    assert "Things" in software["software_release_notes"]
    assert (
        parser.parse_software({"currentVersion": {"generalVersion": "0.00.00"}})["software_version"]
        is None
    )


def test_charge_plan_helpers() -> None:
    plan = parser.normalize_charge_plan({"chargeEnable": 1, "chargesoc": 90, "starttime": "23:30"})
    assert plan["isEnable"] == 1 and plan["percent"] == 90 and plan["beginTime"] == "23:30"
    assert not parser.charge_plan_complete(plan)
    assert parser.charge_plan_complete(parser.raw_charge_plan(C10_PARKED))
