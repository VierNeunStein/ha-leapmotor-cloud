"""A simulated vehicle.

The demo client produces the same raw payloads as the cloud, so the complete
pipeline (parser, entities, dashboard, commands, PIN handling) can be tried
without a car and without any network traffic.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime, timedelta
import json
import math
import time
from typing import Any

from .errors import LeapmotorCommandError, LeapmotorPinError
from .models import CommandResult, RemoteCommand, SessionState, VehicleInfo
from .parser import normalize_charge_plan

DEMO_VIN = "LDEMO000000000001"
DEMO_PIN = "1234"
DEMO_SCENARIOS = ("charging_ac", "charging_dc", "plugged_in", "parked", "driving", "climate")
_CAPACITY_KWH = 69.9
_FULL_RANGE_KM = 420


class LeapmotorDemoClient:
    """Simulate one Leapmotor C10 that reacts to commands."""

    def __init__(
        self,
        *,
        home: tuple[float, float] | None = None,
        pin: str = DEMO_PIN,
        command_delay: float = 1.2,
    ) -> None:
        self._pin = pin
        # A real command takes a few seconds until the vehicle confirms it.
        self.command_delay = command_delay
        self._home = home or (52.5163, 13.3777)
        self._vehicle = VehicleInfo(
            vin=DEMO_VIN,
            car_type="C10",
            car_id="demo",
            nickname="Demo C10",
            color="Glazed Green",
            year=2025,
        )
        self._last = time.monotonic()
        self._started = time.time()
        self._scenario = "charging_ac"
        self._s: dict[str, Any] = {
            "soc": 54.0,
            "odometer": 12480.0,
            "limit": 80,
            "plugged": True,
            "charging": True,
            "paused": False,
            "power": 10.8,
            "dc": False,
            "locked": True,
            "doors": [0, 0, 0, 0],
            "trunk": 0,
            "window": 0,
            "sunshade": 0,
            "climate": False,
            "climate_mode": "nohotcold",
            "climate_temp": 22.0,
            "climate_fan": 4,
            "climate_recirc": False,
            "defrost": False,
            "interior": 17.5,
            "seat_heat": {"driver": 0, "copilot": 0},
            "seat_vent": {"driver": 0, "copilot": 0},
            "steering": False,
            "mirror": False,
            "sentry": False,
            "healthy": False,
            "preheat": False,
            "speed": 0.0,
            "gear": 0,
            "plan": {
                "isEnable": 0,
                "percent": 80,
                "beginTime": "22:00",
                "endTime": "06:00",
                "cycles": "1,1,1,1,1,1,1",
                "circulation": 1,
                "recharge": 0,
            },
        }
        self.request_count = 0
        self.on_session_changed = None
        self.on_server_certificate_changed = None
        self.on_request = None

    # -- interface shared with the cloud client -------------------------------

    @property
    def is_demo(self) -> bool:
        """Return whether this client simulates a vehicle."""
        return True

    @property
    def session(self) -> SessionState | None:
        """The demo has no cloud session."""
        return None

    @property
    def pinned_certificate(self) -> bytes | None:
        """The demo talks to no server."""
        return None

    @property
    def scenario(self) -> str:
        """Return the active scenario."""
        return self._scenario

    async def close(self) -> None:
        """Nothing to release."""

    async def ensure_session(self) -> None:
        """Nothing to do."""

    async def login(self) -> None:
        """Nothing to do."""

    def _count(self, label: str) -> None:
        self.request_count += 1
        if self.on_request is not None:
            self.on_request(label)

    async def get_vehicles(self) -> list[VehicleInfo]:
        """Return the simulated vehicle."""
        self._count("vehicle list")
        return [self._vehicle]

    # -- simulation ------------------------------------------------------------

    def set_scenario(self, scenario: str) -> None:
        """Jump to a predefined situation."""
        if scenario not in DEMO_SCENARIOS:
            raise ValueError(f"Unknown scenario: {scenario}")
        s = self._s
        self._scenario = scenario
        s.update(speed=0.0, gear=0, climate=False, defrost=False, paused=False, dc=False)
        if scenario == "charging_ac":
            s.update(plugged=True, charging=True, power=10.8, locked=True)
            s["soc"] = min(s["soc"], 60.0)
        elif scenario == "charging_dc":
            s.update(plugged=True, charging=True, power=82.0, dc=True, locked=True)
            s["soc"] = min(s["soc"], 35.0)
        elif scenario == "plugged_in":
            s.update(plugged=True, charging=False, power=0.0, locked=True)
        elif scenario == "parked":
            s.update(plugged=False, charging=False, power=0.0, locked=True)
        elif scenario == "driving":
            s.update(plugged=False, charging=False, power=0.0, locked=True, speed=87.0, gear=3)
            s.update(climate=True, climate_mode="nohotcold")
        elif scenario == "climate":
            s.update(plugged=False, charging=False, power=0.0, climate=True, climate_mode="hot")
            s.update(climate_temp=22.0, climate_fan=5, locked=True)

    def _advance(self) -> None:
        now = time.monotonic()
        hours = (now - self._last) / 3600.0
        self._last = now
        s = self._s
        if s["charging"]:
            target = min(float(s["limit"]), 100.0)
            s["soc"] = min(target, s["soc"] + s["power"] * hours / _CAPACITY_KWH * 100.0)
            if s["soc"] >= target:
                s.update(charging=False, power=0.0)
        if s["speed"] > 0:
            distance = s["speed"] * hours
            s["odometer"] += distance
            s["soc"] = max(5.0, s["soc"] - distance * 17.5 / _CAPACITY_KWH)
        if s["climate"]:
            s["soc"] = max(5.0, s["soc"] - 1.8 * hours / _CAPACITY_KWH * 100.0)
            step = min(1.0, hours * 60.0 / 4.0)
            s["interior"] += (s["climate_temp"] - s["interior"]) * step
        else:
            s["interior"] += (16.0 - s["interior"]) * min(1.0, hours * 2.0)

    def _remaining_minutes(self) -> int:
        s = self._s
        if not s["charging"] or s["power"] <= 0:
            return 0
        missing = max(0.0, min(float(s["limit"]), 100.0) - s["soc"]) / 100.0 * _CAPACITY_KWH
        return max(1, round(missing / s["power"] * 60.0))

    async def get_status(self, vehicle: VehicleInfo) -> dict[str, Any]:
        """Return a status payload in the format of the cloud."""
        self._count("vehicle status")
        self._advance()
        s = self._s
        voltage = 348.0 + s["soc"] * 0.62
        if s["charging"]:
            current = -s["power"] * 1000.0 / voltage
            code = 1
        elif s["speed"] > 0:
            current = 41.0 + 6.0 * math.sin(time.time() / 30.0)
            code = 5
        else:
            current = 0.2
            code = 0 if not s["plugged"] else (6 if s["paused"] else 2)
        drift = (time.time() - self._started) / 3600.0 * 0.01 if s["speed"] > 0 else 0.0
        mode = s["climate_mode"]
        signal: dict[str, Any] = {
            "1204": int(s["soc"]),
            "100003": round(s["soc"], 1),
            "3260": round(s["soc"] / 100.0 * _FULL_RANGE_KM),
            "2188": round(s["soc"] / 100.0 * _FULL_RANGE_KM),
            "3257": _FULL_RANGE_KM,
            "3262": 1,
            "1149": code,
            "47": 1 if s["plugged"] and not s["dc"] else 0,
            "1197": 1 if s["plugged"] and s["dc"] else 0,
            "1178": round(current, 1),
            "1177": round(voltage, 1),
            "1200": self._remaining_minutes(),
            "1182": 24 if s["charging"] else 18,
            "1186": 4 if s["preheat"] else 0,
            "3736": 1 if s["plugged"] and not s["charging"] and s["soc"] >= s["limit"] else 0,
            "48": 1 if s["healthy"] else 0,
            "1318": int(s["odometer"]),
            "1319": round(s["speed"], 1),
            "1010": s["gear"],
            "1258": 1 if s["speed"] > 0 else 0,
            "1480": 0 if s["speed"] > 0 else 1,
            "3": round(self._home[0] + drift, 6),
            "2": round(self._home[1] + drift, 6),
            "1938": 1 if s["climate"] else 0,
            "1939": 1,
            "1941": s["climate_fan"],
            "1943": 1 if s["climate_recirc"] else 0,
            "1945": 1 if s["climate"] and s["defrost"] else 0,
            "1946": 0,
            "3713": {"cold": 1, "hot": 3}.get(mode, 4) if s["climate"] else 0,
            "2183": s["climate_temp"],
            "2184": s["climate_temp"],
            "1349": round(s["interior"], 1),
            "1298": 1 if s["locked"] else 0,
            "1277": s["doors"][0],
            "1278": s["doors"][1],
            "1279": s["doors"][2],
            "1280": s["doors"][3],
            "1281": s["trunk"],
            "1693": 1 if s["window"] else 0,
            "1694": 1 if s["window"] else 0,
            "1695": 1 if s["window"] else 0,
            "1696": 1 if s["window"] else 0,
            "3727": s["window"],
            "3728": s["window"],
            "1879": s["window"],
            "1880": s["window"],
            "2646": 252,
            "2653": 250,
            "2660": 248,
            "2667": 251,
            "2641": 0,
            "2648": 0,
            "2655": 0,
            "2662": 0,
            "2100": s["seat_heat"]["driver"],
            "2118": s["seat_heat"]["copilot"],
            "2101": s["seat_vent"]["driver"],
            "2119": s["seat_vent"]["copilot"],
            "1816": 2 if s["steering"] else 0,
            "49": 1 if s["mirror"] else 0,
            "50": 1 if s["mirror"] else 0,
            "3636": 1 if s["sentry"] else 0,
            "1255": 2 if s["locked"] else 0,
            "sts": int(time.time() * 1000),
        }
        return {
            "privacyGPS": 1,
            "privacyData": 1,
            "signal": signal,
            "config": {"3": dict(s["plan"])},
        }

    async def get_mileage(
        self, vehicle: VehicleInfo, begin: datetime, end: datetime
    ) -> dict[str, Any]:
        """Return a plausible week of driving."""
        self._count("mileage")
        today = datetime.now(UTC).date()
        distances = (34.0, 0.0, 61.5, 18.2, 122.4, 9.6, 27.3)
        detail = [
            {
                "day": (today - timedelta(days=6 - index)).isoformat(),
                "accumulatedMileage": distance,
                "accumulatedEnergyConsume": round(distance * 0.172, 1),
                "currentMileage": int(self._s["odometer"]) - int(sum(distances[index + 1 :])),
            }
            for index, distance in enumerate(distances)
        ]
        return {
            "totalmileage": int(self._s["odometer"]),
            "deliveryDays": 312,
            "totalEnergy": round(self._s["odometer"] * 0.178, 1),
            "totalAccumulatedMileage": round(sum(distances), 1),
            "detail": detail,
        }

    async def get_consumption_rank(self, vehicle: VehicleInfo) -> dict[str, Any]:
        """Return a plausible consumption history."""
        self._count("consumption rank")
        monday = datetime.now(UTC).date() - timedelta(days=datetime.now(UTC).weekday())
        weeks = [
            {
                "weekStart": (monday - timedelta(weeks=index + 1)).isoformat(),
                "weekEnd": (monday - timedelta(weeks=index, days=1)).isoformat(),
                "hundredKmEC": value,
            }
            for index, value in enumerate((17.4, 18.1, 16.9, 19.3, 18.6, 17.8))
        ]
        return {
            "rankResult": {"result": 0, "rank": "38%", "hundredKmEC": "18.0"},
            "weeklyEC": weeks,
        }

    async def get_energy_window(
        self, vehicle: VehicleInfo, begin: datetime, end: datetime
    ) -> dict[str, Any]:
        """Return an energy split that grows with the length of the window."""
        self._count("energy window")
        days = max((end - begin).total_seconds() / 86400.0, 0.02)
        return {
            "driverEC": f"{7.1 * days:.1f}",
            "acEC": f"{1.3 * days:.1f}",
            "otherEC": f"{0.6 * days:.1f}",
        }

    async def get_charge_records(
        self, vehicle: VehicleInfo, start: date, end: date, *, reference: datetime | None = None
    ) -> dict[str, Any]:
        """Return a few charging sessions."""
        self._count("charge records")
        now = datetime.now(UTC)
        sessions = ((1, 6.5, "1", 31.4), (3, 0.6, "2", 38.9), (5, 5.2, "1", 24.7))
        return {
            "list": [
                {
                    "chargeGunStartTs": int(
                        (now - timedelta(days=days, hours=hours)).timestamp() * 1000
                    ),
                    "chargeGunEndTs": int((now - timedelta(days=days)).timestamp() * 1000),
                    "chargeType": kind,
                    "chargeInEnergy": energy,
                }
                for days, hours, kind, energy in sessions
            ]
        }

    async def get_unread_count(self) -> Any:
        """Return the unread-message counter."""
        self._count("unread messages")
        return {"unread": 1}

    async def get_messages(self, page_size: int = 1) -> Any:
        """Return the newest message."""
        self._count("messages")
        return {
            "list": [
                {
                    "title": "Demo",
                    "content": "This vehicle is simulated by the integration.",
                    "sendTime": int(self._started * 1000),
                }
            ]
        }

    async def get_software(self, vehicle: VehicleInfo) -> dict[str, Any]:
        """Return software information with a pending update."""
        self._count("software")
        return {
            "currentVersion": {"generalVersion": "1.08.21"},
            "newVersion": {
                "generalVersion": "1.09.03",
                "logJsonMultiLang": [
                    {
                        "language": "en-GB",
                        "data": [{"title": "Demo update", "content": "Nothing to install."}],
                    }
                ],
            },
        }

    async def get_charge_plan(self, vehicle: VehicleInfo) -> dict[str, Any]:
        """Return the stored charging plan."""
        self._count("appointment")
        return normalize_charge_plan(self._s["plan"])

    async def get_picture_package(self, vehicle: VehicleInfo) -> tuple[str, bytes] | None:
        """The simulated vehicle has no pictures from the cloud."""
        return None

    # -- commands --------------------------------------------------------------

    async def verify_pin(self, vehicle: VehicleInfo, pin: str) -> None:
        """Check the PIN of the simulated vehicle."""
        self._count("pin verify")
        if pin != self._pin:
            raise LeapmotorPinError("Operation password error (demo PIN is 1234)", code=5001)

    async def send_command(
        self,
        vehicle: VehicleInfo,
        command: RemoteCommand,
        pin: str | None = None,
        *,
        wait_for_result: bool = True,
    ) -> CommandResult:
        """Apply a command to the simulated vehicle."""
        if command.requires_pin:
            if not pin:
                raise LeapmotorPinError("No vehicle PIN configured", endpoint=command.name)
            await self.verify_pin(vehicle, pin)
        self._count(f"command {command.name}")
        if self.command_delay > 0:
            await asyncio.sleep(self.command_delay)
        self._advance()
        try:
            content = json.loads(command.content)
        except ValueError as err:
            raise LeapmotorCommandError("Invalid command payload") from err
        self._apply(command.cmd_id, content if isinstance(content, dict) else {})
        return CommandResult(command.name, accepted=True, confirmed=True, remote_ctl_id="demo")

    def _apply(self, cmd_id: str, content: dict[str, Any]) -> None:
        s = self._s
        value = str(content.get("value", ""))
        if cmd_id == "110":
            s["locked"] = value == "lock"
        elif cmd_id == "130":
            s["trunk"] = 1 if value == "true" else 0
        elif cmd_id == "230":
            s["window"] = min(100, int(value or 0) * 10)
        elif cmd_id == "240":
            s["sunshade"] = int(value or 0) * 10
        elif cmd_id == "220":
            s["sentry"] = value == "1"
        elif cmd_id == "480":
            s["healthy"] = value == "1"
        elif cmd_id == "160":
            s["preheat"] = value == "ptcon"
        elif cmd_id == "193":
            if value == "start":
                if not s["plugged"]:
                    raise LeapmotorCommandError("The charging cable is not connected")
                s.update(
                    charging=s["soc"] < s["limit"], power=82.0 if s["dc"] else 10.8, paused=False
                )
            else:
                s.update(charging=False, power=0.0, paused=True)
        elif cmd_id == "190":
            s["plan"] = {
                "isEnable": int(content.get("chargeEnable", 0)),
                "percent": int(content.get("chargesoc", s["limit"])),
                "beginTime": content.get("starttime", s["plan"]["beginTime"]),
                "endTime": content.get("endtime", s["plan"]["endTime"]),
                "cycles": content.get("cycles", s["plan"]["cycles"]),
                "circulation": int(content.get("circulation", 0)),
                "recharge": int(content.get("recharge", 0)),
            }
            s["limit"] = s["plan"]["percent"]
            if s["charging"] and s["soc"] >= s["limit"]:
                s.update(charging=False, power=0.0)
        elif cmd_id == "170":
            if content.get("operate") == "off":
                s.update(climate=False, defrost=False)
            else:
                s.update(
                    climate=True,
                    climate_mode=str(content.get("mode", "nohotcold")),
                    climate_temp=float(content.get("temperature", 22)),
                    climate_fan=int(content.get("windlevel", 4)),
                    climate_recirc=content.get("circle") == "in",
                    defrost=str(content.get("wshld")) == "2",
                )
        elif cmd_id == "320":
            s["steering"] = str(content.get("level")) == "2"
        elif cmd_id == "440":
            s["mirror"] = value == "2"
        elif cmd_id in ("301", "370"):
            target = s["seat_heat"] if cmd_id == "301" else s["seat_vent"]
            other = s["seat_vent"] if cmd_id == "301" else s["seat_heat"]
            position = str(content.get("position", "driver"))
            target[position] = int(content.get("level", 0))
            if target[position]:
                other[position] = 0
        elif cmd_id == "360":
            air = content.get("air_condition")
            if isinstance(air, dict):
                s.update(
                    climate=True,
                    climate_mode=str(air.get("mode", "nohotcold")),
                    climate_temp=float(air.get("temperature", 22)),
                    climate_fan=int(air.get("windlevel", 4)),
                    defrost=str(air.get("wshld")) == "2",
                )
            if "steeringWheelHeatCtrl" in content:
                s["steering"] = True
            if "rearMirrorHeating" in content:
                s["mirror"] = True
