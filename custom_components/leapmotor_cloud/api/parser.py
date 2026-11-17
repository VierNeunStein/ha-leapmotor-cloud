"""Turn raw cloud payloads into a flat, model-independent vehicle state.

Newer models (C10, B10, ...) report numeric signal ids, the T03 reports named
fields.  Both are merged into one signal map first, then interpreted once.
All ``parse_*`` functions take the ``data`` member of an API response.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import math
from typing import Any

from .const import LEGACY_MODELS
from .models import VehicleInfo

# Charging states exposed to Home Assistant.
CHARGING_STATES = (
    "unplugged",
    "plugged_in",
    "scheduled",
    "charging",
    "paused",
    "finished",
)
GEARS = ("p", "r", "n", "d")
CLIMATE_ACTIONS = ("off", "cooling", "heating", "fan", "defrost")

# T03-style named fields -> signal id.
_NAMED_VALUES = {
    "soc": "1204",
    "chargeRemainTime": "1200",
    "batteryCurrent": "1178",
    "batteryVoltage": "1177",
    "dcInputFastCharge": "1197",
    "expectedMileage": "3260",
    "speed": "1319",
    "totalMileage": "1318",
    "gearStatus": "1010",
    "latitude": "3725",
    "longitude": "3724",
    "acSetting": "2183",
    "interiorTemp": "1349",
    "minBatteryTemp": "1182",
    "acAirVolume": "1941",
    "leftFrontWindowPercent": "3727",
    "rightFrontWindowPercent": "3728",
    "leftRearWindowPercent": "1879",
    "rightRearWindowPercent": "1880",
    "leftFrontTirePressure": "2646",
    "rightFrontTirePressure": "2653",
    "leftRearTirePressure": "2660",
    "rightRearTirePressure": "2667",
    "leftFrontTirePressureState": "2641",
    "rightFrontTirePressureState": "2648",
    "leftRearTirePressureState": "2655",
    "rightRearTirePressureState": "2662",
}
_NAMED_FLAGS = {
    "acSwitch": "1938",
    "driverDoorLockStatus": "1298",
    "lbcmDriverDoorStatus": "1277",
    "rbcmDriverDoorStatus": "1278",
    "lbcmLeftRearDoorStatus": "1279",
    "rbcmRightRearDoorStatus": "1280",
    "bbcmBackDoorStatus": "1281",
    "driverWindowStatus": "1693",
    "rightFrontWindowStatus": "1694",
    "leftRearWindowStatus": "1695",
    "rightRearWindowStatus": "1696",
    "bcmKeyPositionOn1": "1256",
    "bcmKeyPositionOn2": "1257",
    "bcmKeyPositionOn3": "1258",
    "chargeCompleted": "3736",
    "acCircleMode": "1943",
}


# ---------------------------------------------------------------------------
# Value helpers
# ---------------------------------------------------------------------------


def _float(raw: Any) -> float | None:
    if raw is None or isinstance(raw, bool):
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def _int(raw: Any) -> int | None:
    value = _float(raw)
    return int(value) if value is not None else None


def _flag(raw: Any) -> bool | None:
    """Interpret 0/1, booleans and common strings as a flag."""
    if raw is None:
        return None
    if isinstance(raw, bool):
        return raw
    value = _float(raw)
    if value is not None:
        return value != 0
    text = str(raw).strip().lower()
    if text in ("true", "yes", "on"):
        return True
    if text in ("false", "no", "off"):
        return False
    return None


def _equals(raw: Any, expected: int) -> bool | None:
    value = _int(raw)
    return None if value is None else value == expected


def _positive(raw: Any) -> bool | None:
    value = _float(raw)
    return None if value is None else value > 0


def _any(*flags: bool | None) -> bool | None:
    """Logical OR that stays unknown when nothing is known."""
    known = [flag for flag in flags if flag is not None]
    if not known:
        return None
    return any(known)


def parse_timestamp(raw: Any) -> datetime | None:
    """Parse the vehicle timestamp (epoch seconds/milliseconds or a string)."""
    if raw is None:
        return None
    number = _float(raw)
    if number is not None:
        if number > 10_000_000_000:
            number /= 1000.0
        if number < 1_000_000_000:
            return None
        return datetime.fromtimestamp(number, UTC)
    try:
        parsed = datetime.fromisoformat(str(raw).strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------


def merge_signals(data: dict[str, Any]) -> dict[str, Any]:
    """Return one signal map for both payload styles."""
    raw_signal = data.get("signal")
    signals: dict[str, Any] = (
        {str(key): value for key, value in raw_signal.items()}
        if isinstance(raw_signal, dict)
        else {}
    )
    for name, signal_id in _NAMED_VALUES.items():
        if data.get(name) is not None:
            signals.setdefault(signal_id, data[name])
    for name, signal_id in _NAMED_FLAGS.items():
        flag = _flag(data.get(name))
        if flag is not None:
            signals.setdefault(signal_id, 1 if flag else 0)
    if data.get("expectedMileage") is not None:
        signals.setdefault("2188", data["expectedMileage"])
    charge_state = _int(data.get("chargeState"))
    if charge_state is not None:
        signals.setdefault("1149", charge_state)
        signals.setdefault("47", 1 if charge_state in (1, 2) else 0)
    for name in ("collectTimeMs", "collectTime"):
        if data.get(name) is not None:
            signals.setdefault("sts", data[name])
            break
    return signals


def status_has_data(data: Any) -> bool:
    """Return whether a status payload contains any vehicle data."""
    return isinstance(data, dict) and bool(merge_signals(data))


def raw_charge_plan(data: dict[str, Any]) -> dict[str, Any]:
    """Return the charging plan found in a status payload (normalised keys)."""
    config = data.get("config")
    plan = config.get("3") if isinstance(config, dict) else None
    if isinstance(plan, dict):
        return normalize_charge_plan(plan)
    named: dict[str, Any] = {}
    if data.get("chargesocSetting") is not None:
        named["percent"] = data["chargesocSetting"]
    if data.get("chargeTimeSetting") is not None:
        named["beginTime"] = data["chargeTimeSetting"]
    return normalize_charge_plan(named)


def normalize_charge_plan(plan: Any) -> dict[str, Any]:
    """Unify the key variants of the status and the appointment endpoint."""
    if not isinstance(plan, dict):
        plan = {}
    return {
        "isEnable": plan.get("isEnable", plan.get("chargeEnable")),
        "percent": plan.get("percent", plan.get("chargesoc")),
        "beginTime": plan.get("beginTime", plan.get("starttime")),
        "endTime": plan.get("endTime", plan.get("endtime")),
        "cycles": plan.get("cycles"),
        "circulation": plan.get("circulation"),
        "recharge": plan.get("recharge"),
        "updateTime": plan.get("updateTime"),
    }


def charge_plan_complete(plan: dict[str, Any]) -> bool:
    """Return whether a plan holds every field needed to rewrite it safely."""
    return (
        _int(plan.get("isEnable")) in (0, 1)
        and _int(plan.get("percent")) is not None
        and bool(plan.get("beginTime"))
        and bool(plan.get("endTime"))
        and bool(plan.get("cycles"))
    )


def _charging(signals: dict[str, Any], model: str, reev: bool) -> dict[str, Any]:
    """Derive the charging state.

    The connection code alone is not reliable (it can stay on "charging" after
    the session ended), so current and remaining time decide.
    """
    code = _int(signals.get("1149"))
    current = _float(signals.get("1178"))
    voltage = _float(signals.get("1177"))
    remaining = _int(signals.get("1200"))
    plug_ac = _flag(signals.get("47"))
    plug_dc = _flag(signals.get("1197"))
    gear = _int(signals.get("1010"))
    speed = _float(signals.get("1319"))
    moving = (
        gear in (1, 2, 3) or (speed is not None and speed > 0) or _flag(signals.get("1258")) is True
    )

    abs_current = abs(current) if current is not None else None
    power = abs(current * voltage) / 1000.0 if current is not None and voltage is not None else None
    has_eta = remaining is not None and remaining > 0

    plugged: bool | None
    if moving:
        plugged = False
    elif code is not None:
        plugged = code in (1, 2, 3, 4, 6)
        # A T03 paused by the wallbox reports "not charging" but keeps this flag.
        if (
            not plugged
            and model == "T03"
            and code == 0
            and plug_dc
            and current == 0
            and remaining == 0
        ):
            plugged = True
    elif plug_ac is not None or plug_dc is not None:
        plugged = bool(plug_ac) or bool(plug_dc)
    else:
        plugged = None

    charging: bool | None
    if plugged is None:
        charging = None
    elif not plugged:
        charging = False
    elif abs_current is None:
        charging = code == 1 or (code == 2 and has_eta)
    elif abs_current < 1.0:
        # Some drivetrains charge slowly on AC without the pack current showing it.
        charging = code == 2 and has_eta
    else:
        strong = abs_current >= 3.0 or (power is not None and power >= 1.0)
        charging = strong if code in (4, 6) else strong or has_eta

    idle = abs_current is None or abs_current < 1.0
    completed = _equals(signals.get("3736"), 1)
    state: str | None
    if plugged is None:
        state = None
    elif not plugged:
        state = "unplugged"
    elif charging:
        state = "charging"
    elif code == 4:
        state = "scheduled"
    elif code == 6:
        state = "paused"
    elif (completed and not reev) or (code == 2 and idle):
        state = "finished"
    else:
        state = "plugged_in"

    charging_power: float | None
    if charging:
        charging_power = round(power, 2) if power is not None else None
    elif charging is False:
        charging_power = 0.0
    else:
        charging_power = None

    charging_type: str | None = None
    if charging:
        fast = (plug_dc and model not in LEGACY_MODELS) or (power is not None and power > 12.0)
        charging_type = "dc" if fast else "ac"

    return {
        "charging_state": state,
        "charge_state_code": code,
        "is_charging": charging,
        "is_plugged_in": plugged,
        "charging_type": charging_type,
        "charging_power": charging_power,
        "charge_time_remaining": remaining if charging else (0 if charging is False else None),
        "charge_completed": completed if not reev else (state == "finished" if state else None),
    }


def _climate_action(signals: dict[str, Any]) -> str | None:
    on = _equals(signals.get("1938"), 1)
    if on is None:
        return None
    if not on:
        return "off"
    if _positive(signals.get("1945")):
        return "defrost"
    mode = _int(signals.get("3713"))
    if mode == 1 or _equals(signals.get("2669"), 2):
        return "cooling"
    if mode == 3 or _equals(signals.get("2681"), 2):
        return "heating"
    cooling = _int(signals.get("1940"))
    if cooling is not None and cooling > 0:
        return "cooling"
    if _equals(signals.get("1949"), 1):
        return "heating"
    return "fan"


def _steering_wheel_heat(raw: Any, model: str) -> bool | None:
    value = _int(raw)
    if value is None:
        return None
    if model == "A10":
        return value != 0 if value in (0, 1, 2, 3) else None
    return value == 2


def _window(flag_raw: Any, position_raw: Any, use_position: bool) -> bool | None:
    flag = _flag(flag_raw)
    position = _flag(position_raw) if use_position else None
    return _any(flag, position)


def _scaled(raw: Any, divisor: float) -> float | None:
    value = _float(raw)
    return round(value / divisor, 2) if value is not None else None


def _pressure(raw: Any) -> float | None:
    return _scaled(raw, 100.0)


def _coordinate(signed: Any, *fallbacks: Any, home: float | None) -> float | None:
    """Return a coordinate; unsigned variants get the hemisphere of the home."""
    value = _float(signed)
    if value is not None and value != 0:
        return value
    for raw in fallbacks:
        value = _float(raw)
        if value is not None and value != 0:
            return -abs(value) if home is not None and home < 0 else value
    return None


def parse_status(
    info: VehicleInfo,
    data: dict[str, Any],
    *,
    home: tuple[float, float] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Interpret one status payload."""
    signals = merge_signals(data)
    model = info.model
    legacy = model in LEGACY_MODELS
    reev = signals.get("3235") is not None
    plan = raw_charge_plan(data)
    timestamp = parse_timestamp(signals.get("sts"))

    gear_code = _int(signals.get("1010"))
    speed = _float(signals.get("1319"))
    if gear_code is not None and 0 <= gear_code <= 3:
        gear: str | None = GEARS[gear_code]
        driving: bool | None = gear_code in (1, 3)
    else:
        gear = None
        driving = speed > 0 if speed is not None else None
    if driving is False and speed is not None and speed > 0:
        driving = True

    state: dict[str, Any] = {
        # battery
        "soc": _int(signals.get("1204")),
        "soc_precise": _float(signals.get("100003")),
        "range": _int(signals.get("3260")),
        "range_live": _int(signals.get("2188")),
        "range_max": _int(signals.get("3257")),
        "range_mode": {0: "cltc", 1: "wltp"}.get(_int(signals.get("3262"))),
        "battery_current": _float(signals.get("1178")),
        "battery_voltage": _float(signals.get("1177")),
        "battery_temperature": _int(signals.get("1182")),
        "battery_heating": _equals(signals.get("1186"), 4),
        "healthy_charging": _equals(signals.get("48"), 1),
        "available_energy": _scaled(data.get("dumpEnergy"), 1000.0),
        # charging plan
        "charge_limit": _int(plan.get("percent")),
        "charge_schedule_enabled": _equals(plan.get("isEnable"), 1),
        "charge_schedule_start": plan.get("beginTime"),
        "charge_schedule_end": plan.get("endTime"),
        "charge_schedule_cycles": plan.get("cycles"),
        "charge_schedule_circulation": _int(plan.get("circulation")),
        "charge_schedule_recharge": _int(plan.get("recharge")),
        "charge_plan_complete": charge_plan_complete(plan),
        # driving
        "odometer": _int(signals.get("1318")),
        "speed": speed,
        "gear": gear,
        "is_driving": driving,
        "is_parked": None if driving is None else not driving,
        "vehicle_ready": _equals(signals.get("1258"), 1),
        "parking_brake": _equals(signals.get("1480"), 1),
        "speed_limit": _int(signals.get("6048")),
        "speed_limit_active": _equals(signals.get("12054"), 1),
        # location
        "latitude": _coordinate(
            signals.get("3"),
            signals.get("3725"),
            signals.get("2190"),
            home=home[0] if home else None,
        ),
        "longitude": _coordinate(
            signals.get("2"),
            signals.get("3724"),
            signals.get("2191"),
            home=home[1] if home else None,
        ),
        "gps_privacy": _flag(data.get("privacyGPS")),
        # climate
        "climate_on": _equals(signals.get("1938"), 1),
        "climate_action": _climate_action(signals),
        "climate_target_temperature": _float(signals.get("2183")),
        "climate_target_temperature_right": _float(signals.get("2184")),
        "climate_fan_level": _int(signals.get("1941")),
        "climate_auto": _equals(signals.get("1939"), 0),
        "climate_recirculation": _flag(signals.get("1943")),
        "interior_temperature": _float(signals.get("1349")),
        "outdoor_temperature": _float(data.get("outdoorTemp")),
        "defrost": _positive(signals.get("1945")),
        "rear_window_heating": _equals(signals.get("1946"), 1),
        # comfort
        "seat_heat_driver": _int(signals.get("2100")),
        "seat_heat_passenger": _int(signals.get("2118")),
        "seat_ventilation_driver": _int(signals.get("2101")),
        "seat_ventilation_passenger": _int(signals.get("2119")),
        "steering_wheel_heat": _steering_wheel_heat(signals.get("1816"), model),
        "mirror_heat": _any(_equals(signals.get("49"), 1), _equals(signals.get("50"), 1)),
        # body
        "locked": _equals(signals.get("1298"), 1),
        "door_driver": _flag(signals.get("1277")),
        "door_passenger": _flag(signals.get("1278")),
        "door_rear_left": _flag(signals.get("1279")),
        "door_rear_right": _flag(signals.get("1280")),
        "trunk": _equals(signals.get("1281"), 1),
        "window_driver": _window(signals.get("1693"), signals.get("3727"), legacy),
        "window_passenger": _window(signals.get("1694"), signals.get("3728"), legacy),
        "window_rear_left": _window(signals.get("1695"), signals.get("1879"), legacy),
        "window_rear_right": _window(signals.get("1696"), signals.get("1880"), legacy),
        "window_position_driver": _int(signals.get("3727")),
        "window_position_passenger": _int(signals.get("3728")),
        "window_position_rear_left": _int(signals.get("1879")),
        "window_position_rear_right": _int(signals.get("1880")),
        "sunshade_position": _int(data.get("sunShade")),
        "roof_position": _int(signals.get("1724")),
        "tire_pressure_fl": _pressure(signals.get("2646")),
        "tire_pressure_fr": _pressure(signals.get("2653")),
        "tire_pressure_rl": _pressure(signals.get("2660")),
        "tire_pressure_rr": _pressure(signals.get("2667")),
        "tire_warning": _any(
            *(_flag(signals.get(signal_id)) for signal_id in ("2641", "2648", "2655", "2662"))
        ),
        # security
        "sentry_mode": _equals(signals.get("3636"), 1),
        "alarm_armed": _positive(signals.get("1255")),
        # range extender
        "fuel_level": _float(signals.get("3235")),
        "fuel_range": _int(signals.get("3259")),
        "combined_range": _int(signals.get("3261")),
        # meta
        "is_reev": reev,
        "vehicle_timestamp": timestamp,
        "signal_count": len(signals),
    }
    state["any_door_open"] = _any(
        state["door_driver"],
        state["door_passenger"],
        state["door_rear_left"],
        state["door_rear_right"],
        state["trunk"],
    )
    state["any_window_open"] = _any(
        state["window_driver"],
        state["window_passenger"],
        state["window_rear_left"],
        state["window_rear_right"],
    )
    positions = [
        state[key]
        for key in (
            "window_position_driver",
            "window_position_passenger",
            "window_position_rear_left",
            "window_position_rear_right",
        )
        if state[key] is not None
    ]
    state["windows_position"] = max(positions) if positions else None

    state.update(_charging(signals, model, reev))
    current, voltage = state["battery_current"], state["battery_voltage"]
    state["battery_power"] = (
        round(-current * voltage / 1000.0, 2)
        if current is not None and voltage is not None
        else None
    )
    remaining = state["charge_time_remaining"]
    if state["is_charging"] and remaining:
        base = timestamp or now or datetime.now(UTC)
        state["charge_finish_time"] = (base + timedelta(minutes=remaining)).replace(
            second=0, microsecond=0
        )
    else:
        state["charge_finish_time"] = None
    return state


# ---------------------------------------------------------------------------
# History, statistics, messages, software
# ---------------------------------------------------------------------------


def parse_mileage(data: dict[str, Any], *, energy_in_wh: bool = False) -> dict[str, Any]:
    """Parse the mileage/energy endpoint (totals plus a per-day window)."""
    divisor = 1000.0 if energy_in_wh else 1.0
    days: list[dict[str, Any]] = []
    energy_total = 0.0
    energy_known = False
    for item in data.get("detail") or []:
        if not isinstance(item, dict):
            continue
        energy = _float(item.get("accumulatedEnergyConsume"))
        if energy is not None:
            energy = round(energy / divisor, 2)
            energy_total += energy
            energy_known = True
        days.append(
            {
                "date": item.get("day"),
                "distance": _float(item.get("accumulatedMileage")),
                "energy": energy,
                "odometer": _float(item.get("currentMileage")),
            }
        )
    return {
        "total_energy": _float(data.get("totalEnergy")),
        "delivery_days": _int(data.get("deliveryDays")),
        "mileage_7d": _float(data.get("totalAccumulatedMileage")),
        "energy_7d": round(energy_total, 2) if energy_known else None,
        "daily_history": days,
    }


def parse_consumption_rank(data: dict[str, Any]) -> dict[str, Any]:
    """Parse average consumption and the weekly series."""
    rank = data.get("rankResult") if isinstance(data.get("rankResult"), dict) else {}
    weeks = [
        {
            "start": item.get("weekStart"),
            "end": item.get("weekEnd"),
            "consumption": _float(item.get("hundredKmEC")),
        }
        for item in data.get("weeklyEC") or []
        if isinstance(item, dict)
    ]
    return {
        "consumption_average": _float(rank.get("hundredKmEC")),
        "consumption_rank": rank.get("rank"),
        "weekly_consumption": weeks,
    }


def parse_energy_window(data: dict[str, Any], prefix: str) -> dict[str, Any]:
    """Parse an energy breakdown (driving / climate / other) for a time window."""
    values = {
        "driving": _float(data.get("driverEC")),
        "climate": _float(data.get("acEC")),
        "other": _float(data.get("otherEC")),
    }
    known = [value for value in values.values() if value is not None]
    result = {f"{prefix}_{name}": value for name, value in values.items()}
    result[f"{prefix}_total"] = round(sum(known), 2) if known else None
    return result


def parse_charge_records(data: dict[str, Any]) -> dict[str, Any]:
    """Parse the list of recent charging sessions (newest first)."""
    sessions: list[dict[str, Any]] = []
    for item in data.get("list") or []:
        if not isinstance(item, dict):
            continue
        start = parse_timestamp(item.get("chargeGunStartTs"))
        end = parse_timestamp(item.get("chargeGunEndTs"))
        sessions.append(
            {
                "start": start,
                "end": end,
                "energy": _float(item.get("chargeInEnergy")),
                "type": {"1": "ac", "2": "dc"}.get(str(item.get("chargeType"))),
                "duration_minutes": (
                    round((end - start).total_seconds() / 60) if start and end else None
                ),
            }
        )
    sessions.sort(
        key=lambda entry: entry["start"] or datetime.min.replace(tzinfo=UTC), reverse=True
    )
    last = sessions[0] if sessions else {}
    return {
        "last_charge_energy": last.get("energy"),
        "last_charge_type": last.get("type"),
        "last_charge_start": last.get("start"),
        "last_charge_end": last.get("end"),
        "last_charge_duration": last.get("duration_minutes"),
        "charge_sessions": sessions[:10],
    }


def parse_unread_count(data: Any) -> int | None:
    """Parse the unread-message counter (the backend uses several shapes)."""
    if isinstance(data, dict):
        for key in ("unread", "unreadCount", "count"):
            if key in data:
                return _int(data[key])
        return None
    return _int(data)


def parse_messages(data: Any) -> dict[str, Any]:
    """Parse the newest message of the message list."""
    items: Any = data
    if isinstance(data, dict):
        items = data.get("list") or data.get("records") or data.get("rows")
    latest = next((item for item in items or [] if isinstance(item, dict)), {})
    return {
        "last_message_title": latest.get("title"),
        "last_message_text": latest.get("content") or latest.get("body"),
        "last_message_time": parse_timestamp(latest.get("sendTime")),
    }


def parse_software(data: dict[str, Any]) -> dict[str, Any]:
    """Parse installed and pending software versions."""

    def _notes(version: dict[str, Any]) -> str | None:
        lines: list[str] = []
        for language in version.get("logJsonMultiLang") or []:
            if not isinstance(language, dict):
                continue
            for entry in language.get("data") or []:
                if isinstance(entry, dict):
                    title, content = entry.get("title"), entry.get("content")
                    lines.append(f"**{title}**\n{content}" if title else str(content or ""))
            if lines:
                break
        return "\n\n".join(line for line in lines if line) or None

    current = data.get("currentVersion") if isinstance(data.get("currentVersion"), dict) else {}
    new = data.get("newVersion") if isinstance(data.get("newVersion"), dict) else {}
    installed = current.get("generalVersion")
    if installed in ("0.00.00", ""):
        installed = None
    return {
        "software_version": installed,
        "software_latest": new.get("generalVersion") or installed,
        "software_release_notes": _notes(new) if new else None,
    }
