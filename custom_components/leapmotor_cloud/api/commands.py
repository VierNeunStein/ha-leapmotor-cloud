"""Builders for remote-control commands.

Each function returns a :class:`RemoteCommand`.  Payload shapes follow what
the official app sends; where a model needs a different shape the builder
takes the model code.
"""

from __future__ import annotations

from datetime import datetime
import json
import time
from typing import Any
import uuid

from .const import (
    LEGACY_MODELS,
    RIGHT_BATTERY_PREHEAT,
    RIGHT_CHARGE_LIMIT,
    RIGHT_CLIMATE,
    RIGHT_FIND_CAR,
    RIGHT_HEALTHY_CHARGING,
    RIGHT_LOCK,
    RIGHT_MIRROR_HEAT,
    RIGHT_PREPARE_CAR,
    RIGHT_QUICK_CLIMATE,
    RIGHT_SEAT_HEAT,
    RIGHT_SEAT_VENTILATION,
    RIGHT_SEND_DESTINATION,
    RIGHT_SENTRY_MODE,
    RIGHT_SPEED_LIMIT,
    RIGHT_STEERING_WHEEL_HEAT,
    RIGHT_SUNROOF,
    RIGHT_SUNSHADE,
    RIGHT_TOGGLE_CHARGE,
    RIGHT_TRUNK,
    RIGHT_UNLOCK_CHARGER,
    RIGHT_WINDOWS,
    RIGHT_WINDSHIELD_DEFROST,
    WINDOW_SCALE_TEN_MODELS,
)
from .models import RemoteCommand

CLIMATE_MODES = ("cold", "hot", "nohotcold")
SEAT_POSITIONS = ("driver", "copilot")
TEMPERATURE_MIN = 18
TEMPERATURE_MAX = 32
FAN_MIN = 1
FAN_MAX = 7
DEFAULT_CYCLES = "1,1,1,1,1,1,1"


def _json(payload: Any) -> str:
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)


def _value(name: str, cmd_id: str, value: Any, right: int | None) -> RemoteCommand:
    return RemoteCommand(name, cmd_id, _json({"value": str(value)}), right=right)


def _range(label: str, value: Any, low: int, high: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as err:
        raise ValueError(f"{label} must be a number") from err
    if isinstance(value, bool) or not low <= number <= high:
        raise ValueError(f"{label} must be between {low} and {high}")
    return number


# -- access ------------------------------------------------------------------


def lock() -> RemoteCommand:
    """Lock the doors."""
    return _value("lock", "110", "lock", RIGHT_LOCK)


def unlock() -> RemoteCommand:
    """Unlock the doors."""
    return _value("unlock", "110", "unlock", RIGHT_LOCK)


def find_car() -> RemoteCommand:
    """Flash the lights / sound the horn."""
    return _value("find_car", "120", "true", RIGHT_FIND_CAR)


def trunk(open_: bool) -> RemoteCommand:
    """Open or close the tailgate."""
    name = "trunk_open" if open_ else "trunk_close"
    return _value(name, "130", "true" if open_ else "false", RIGHT_TRUNK)


def windows(position_percent: int, model: str) -> RemoteCommand:
    """Move all windows to a position (0 = closed, 100 = fully open)."""
    percent = _range("Window position", position_percent, 0, 100)
    scale = 10 if model.upper() in WINDOW_SCALE_TEN_MODELS else 100
    native = round(percent / 100 * scale)
    if percent > 0 and native == 0:
        native = 1
    name = "windows_close" if native == 0 else "windows_open"
    return _value(name, "230", native, RIGHT_WINDOWS)


def sunshade(position_percent: int) -> RemoteCommand:
    """Move the sunshade (0 = closed, 100 = fully open)."""
    percent = _range("Sunshade position", position_percent, 0, 100)
    native = round(percent / 10)
    name = "sunshade_close" if native == 0 else "sunshade_open"
    return _value(name, "240", native, RIGHT_SUNSHADE)


def sunroof(open_: bool) -> RemoteCommand:
    """Open or close the sunroof (models with a moving roof)."""
    name = "sunroof_open" if open_ else "sunroof_close"
    return _value(name, "300", "open" if open_ else "close", RIGHT_SUNROOF)


def sentry_mode(on: bool) -> RemoteCommand:
    """Switch sentry mode."""
    name = "sentry_mode_on" if on else "sentry_mode_off"
    return _value(name, "220", "1" if on else "0", RIGHT_SENTRY_MODE)


def speed_limit(kmh: int) -> RemoteCommand:
    """Set the speed limit."""
    return _value("speed_limit", "510", _range("Speed limit", kmh, 20, 200), RIGHT_SPEED_LIMIT)


# -- charging ------------------------------------------------------------------


def charging(start: bool) -> RemoteCommand:
    """Start or stop charging while the cable is connected."""
    name = "charge_start" if start else "charge_stop"
    return _value(name, "193", "start" if start else "stop", RIGHT_TOGGLE_CHARGE)


def unlock_charger() -> RemoteCommand:
    """Release the charging connector."""
    return RemoteCommand(
        "unlock_charger", "192", _json({"operation": "unlock"}), right=RIGHT_UNLOCK_CHARGER
    )


def healthy_charging(on: bool) -> RemoteCommand:
    """Switch the battery-friendly charging mode."""
    name = "healthy_charging_on" if on else "healthy_charging_off"
    return _value(name, "480", "1" if on else "0", RIGHT_HEALTHY_CHARGING)


def battery_preheat(on: bool) -> RemoteCommand:
    """Switch battery preheating."""
    name = "battery_preheat_on" if on else "battery_preheat_off"
    return _value(name, "160", "ptcon" if on else "ptcoff", RIGHT_BATTERY_PREHEAT)


def normalize_clock(value: Any) -> str:
    """Return a time of day as ``HH:MM``."""
    if hasattr(value, "strftime"):
        return value.strftime("%H:%M")
    text = str(value).strip()
    parts = text.split(":")
    if len(parts) < 2:
        raise ValueError(f"Invalid time: {value!r}")
    hour = _range("Hour", parts[0], 0, 23)
    minute = _range("Minute", parts[1], 0, 59)
    return f"{hour:02d}:{minute:02d}"


def charge_plan(
    *,
    enabled: bool,
    limit_percent: int,
    start: Any,
    end: Any,
    cycles: str | None = None,
    circulation: int = 0,
    recharge: int = 0,
) -> RemoteCommand:
    """Write the charging plan (schedule and charge limit) as a whole."""
    payload = {
        "chargeEnable": 1 if enabled else 0,
        "chargesoc": _range("Charge limit", limit_percent, 1, 100),
        "circulation": int(circulation or 0),
        "cycles": str(cycles or DEFAULT_CYCLES),
        "endtime": normalize_clock(end),
        "recharge": int(recharge or 0),
        "starttime": normalize_clock(start),
    }
    return RemoteCommand("charge_plan", "190", _json(payload), right=RIGHT_CHARGE_LIMIT)


# -- climate -------------------------------------------------------------------


def _climate_body(
    *,
    mode: str,
    temperature: int,
    fan: int,
    recirculate: bool,
    defrost: bool,
    operate: str,
) -> dict[str, str]:
    if mode == "wind":
        mode = "nohotcold"
    if mode not in CLIMATE_MODES:
        raise ValueError(f"Climate mode must be one of {', '.join(CLIMATE_MODES)}")
    if operate not in ("manual", "auto"):
        raise ValueError("Climate operation must be manual or auto")
    return {
        "circle": "in" if recirculate else "out",
        "mode": mode,
        "operate": operate,
        "position": "all",
        "temperature": str(_range("Temperature", temperature, TEMPERATURE_MIN, TEMPERATURE_MAX)),
        "windlevel": str(_range("Fan level", fan, FAN_MIN, FAN_MAX)),
        "wshld": "2" if defrost else "1",
    }


def climate(
    *,
    mode: str = "nohotcold",
    temperature: int = 22,
    fan: int = 4,
    recirculate: bool = False,
    defrost: bool = False,
    operate: str = "manual",
    name: str = "climate_on",
) -> RemoteCommand:
    """Switch the air conditioning on with the given settings."""
    body = _climate_body(
        mode=mode,
        temperature=temperature,
        fan=fan,
        recirculate=recirculate,
        defrost=defrost,
        operate=operate,
    )
    right = RIGHT_WINDSHIELD_DEFROST if defrost else RIGHT_CLIMATE
    return RemoteCommand(name, "170", _json(body), right=right)


def climate_off(model: str) -> RemoteCommand:
    """Switch the air conditioning off."""
    if model.upper() in LEGACY_MODELS:
        body: dict[str, str] = {
            "circle": "out",
            "mode": "wind",
            "operate": "off",
            "position": "all",
            "temperature": "26",
            "windlevel": "3",
            "wshld": "0",
        }
    else:
        body = {"operate": "off"}
    return RemoteCommand("climate_off", "170", _json(body), right=RIGHT_CLIMATE)


def quick_cool() -> RemoteCommand:
    """Cool the cabin down as fast as possible."""
    command = climate(mode="cold", temperature=18, fan=7, recirculate=True, name="quick_cool")
    return RemoteCommand(command.name, command.cmd_id, command.content, right=RIGHT_QUICK_CLIMATE)


def quick_heat() -> RemoteCommand:
    """Heat the cabin up as fast as possible."""
    command = climate(mode="hot", temperature=32, fan=7, recirculate=True, name="quick_heat")
    return RemoteCommand(command.name, command.cmd_id, command.content, right=RIGHT_QUICK_CLIMATE)


def windshield_defrost() -> RemoteCommand:
    """Defrost the windshield."""
    return climate(
        mode="hot", temperature=32, fan=7, recirculate=True, defrost=True, name="windshield_defrost"
    )


def steering_wheel_heat(on: bool) -> RemoteCommand:
    """Switch the steering wheel heating."""
    name = "steering_wheel_heat_on" if on else "steering_wheel_heat_off"
    return RemoteCommand(
        name, "320", _json({"level": "2" if on else "1"}), right=RIGHT_STEERING_WHEEL_HEAT
    )


def mirror_heat(on: bool) -> RemoteCommand:
    """Switch the exterior mirror heating."""
    name = "mirror_heat_on" if on else "mirror_heat_off"
    return _value(name, "440", "2" if on else "1", RIGHT_MIRROR_HEAT)


def _seat(name: str, cmd_id: str, position: str, level: int, right: int) -> RemoteCommand:
    if position not in SEAT_POSITIONS:
        raise ValueError(f"Seat must be one of {', '.join(SEAT_POSITIONS)}")
    payload = {"position": position, "level": str(_range("Seat level", level, 0, 3))}
    return RemoteCommand(f"{name}_{position}", cmd_id, _json(payload), right=right)


def seat_heat(position: str, level: int) -> RemoteCommand:
    """Set a front seat's heating level (0 = off .. 3)."""
    return _seat("seat_heat", "301", position, level, RIGHT_SEAT_HEAT)


def seat_ventilation(position: str, level: int) -> RemoteCommand:
    """Set a front seat's ventilation level (0 = off .. 3)."""
    return _seat("seat_ventilation", "370", position, level, RIGHT_SEAT_VENTILATION)


# -- schedules & navigation ------------------------------------------------------


def _schedule_id(now_ms: int) -> str:
    return f"ios_{uuid.uuid4().hex}{now_ms // 1000}"


def _schedule_time(value: Any) -> str:
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:00")
    return datetime.fromisoformat(str(value).strip().replace("Z", "+00:00")).strftime(
        "%Y-%m-%d %H:%M:00"
    )


def _schedule_days(days: list[int] | None) -> list[int]:
    """Validate weekdays in the app's numbering (0 = Sunday .. 6 = Saturday)."""
    result: list[int] = []
    for day in days or []:
        number = _range("Weekday", day, 0, 6)
        if number not in result:
            result.append(number)
    return result


def climate_schedule(
    *,
    start_time: Any,
    mode: str = "nohotcold",
    temperature: int = 22,
    fan: int = 4,
    recirculate: bool = False,
    defrost: bool = False,
    operate: str = "manual",
    days: list[int] | None = None,
    enabled: bool = True,
) -> RemoteCommand:
    """Replace all climate timers with a single one."""
    now_ms = int(time.time() * 1000)
    body = _climate_body(
        mode=mode,
        temperature=temperature,
        fan=fan,
        recirculate=recirculate,
        defrost=defrost,
        operate=operate,
    )
    entry = {
        "mode": body["mode"],
        "operate": body["operate"],
        "temperature": body["temperature"],
        "circle": body["circle"],
        "windlevel": body["windlevel"],
        "wshld": body["wshld"],
        "days": _schedule_days(days),
        "on": "1" if enabled else "0",
        "position": "all",
        "start_time": _schedule_time(start_time),
        "set_id": _schedule_id(now_ms),
        "update_time": str(now_ms),
    }
    return RemoteCommand(
        "climate_schedule", "171", _json({"controls": [entry]}), right=RIGHT_QUICK_CLIMATE
    )


def cancel_climate_schedule() -> RemoteCommand:
    """Remove all climate timers."""
    return RemoteCommand(
        "cancel_climate_schedule", "171", _json({"controls": []}), right=RIGHT_QUICK_CLIMATE
    )


def _coordinate(value: float) -> str:
    return f"{float(value):.8f}".rstrip("0").rstrip(".")


def send_destination(
    *, name: str, latitude: float, longitude: float, address: str | None = None
) -> RemoteCommand:
    """Send a destination to the car's navigation (no PIN needed)."""
    name = name.strip()
    if not name:
        raise ValueError("Destination needs a name")
    if not -90 <= float(latitude) <= 90 or not -180 <= float(longitude) <= 180:
        raise ValueError("Destination coordinates are out of range")
    payload = {
        "address": (address or name).strip(),
        "addressname": name,
        "latitude": _coordinate(latitude),
        "linenum": "0",
        "longitude": _coordinate(longitude),
    }
    return RemoteCommand(
        "send_destination", "180", _json(payload), requires_pin=False, right=RIGHT_SEND_DESTINATION
    )


def _prepare_seat(mode: str, level: int) -> str:
    if mode == "off":
        return "0"
    number = _range("Seat level", level, 1, 3)
    if mode == "heat":
        return str(number)
    if mode == "ventilation":
        return str(10 + number)
    raise ValueError("Seat mode must be off, heat or ventilation")


def prepare_car(
    *,
    climate_enabled: bool = True,
    mode: str = "nohotcold",
    temperature: int = 22,
    fan: int = 4,
    recirculate: bool = False,
    defrost: bool = False,
    operate: str = "manual",
    driver_seat: str = "off",
    driver_seat_level: int = 3,
    passenger_seat: str = "off",
    passenger_seat_level: int = 3,
    steering_wheel: bool = False,
    mirrors: bool = False,
) -> RemoteCommand:
    """Prepare the car in one go: climate, seats, steering wheel and mirrors."""
    content: dict[str, Any] = {}
    if climate_enabled:
        body = _climate_body(
            mode=mode,
            temperature=temperature,
            fan=fan,
            recirculate=recirculate,
            defrost=defrost,
            operate=operate,
        )
        content["air_condition"] = {
            "mode": body["mode"],
            "temperature": body["temperature"],
            "circle": body["circle"],
            "windlevel": body["windlevel"],
            "wshld": body["wshld"],
            "operate": body["operate"],
            "position": "all",
            "enable": True,
        }
    seats = {
        "driver": _prepare_seat(driver_seat, driver_seat_level),
        "copilot": _prepare_seat(passenger_seat, passenger_seat_level),
        "left_rear": "0",
        "right_rear": "0",
    }
    if any(value != "0" for value in seats.values()):
        content["seat_setting"] = {**seats, "enable": True}
    if steering_wheel:
        content["steeringWheelHeatCtrl"] = {"enable": True, "level": "2"}
    if mirrors:
        content["rearMirrorHeating"] = {"enable": True, "value": "2"}
    if not content:
        raise ValueError("Nothing to prepare: enable at least one function")
    return RemoteCommand("prepare_car", "360", _json(content), right=RIGHT_PREPARE_CAR)


def raw(cmd_id: str | int, content: Any, *, requires_pin: bool = True) -> RemoteCommand:
    """Build a command from a raw id and payload (for experiments)."""
    cmd = str(cmd_id).strip()
    if not cmd.isdigit():
        raise ValueError("Command id must be numeric")
    if isinstance(content, str):
        json.loads(content)  # must be valid JSON
        body = content
    else:
        body = _json(content)
    return RemoteCommand(f"raw_{cmd}", cmd, body, requires_pin=requires_pin)
