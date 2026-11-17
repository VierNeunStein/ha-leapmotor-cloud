"""Coordinator: fetches vehicle data and sends commands.

Polling is adaptive.  While a vehicle is charging, driving, air-conditioned
or was just used, the *active* interval applies; otherwise the much longer
*idle* interval.  Slow-changing data (history, statistics, messages) is
fetched on its own, even slower schedule.  A daily request budget and an
error back-off keep the load on the cloud low in every situation.
"""

from __future__ import annotations

import asyncio
import base64
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
import logging
import time
from typing import Any

from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_UNIT_OF_MEASUREMENT, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import CALLBACK_TYPE, Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    HomeAssistantError,
    ServiceValidationError,
)
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.debounce import Debouncer
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.event import async_call_later, async_track_state_change_event
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import (
    CommandResult,
    LeapmotorAuthError,
    LeapmotorCertificateError,
    LeapmotorClient,
    LeapmotorConnectionError,
    LeapmotorError,
    LeapmotorPermissionError,
    LeapmotorPinError,
    LeapmotorRateLimitError,
    LeapmotorServerIdentityError,
    RemoteCommand,
    VehicleInfo,
    commands,
)
from .api.const import LEGACY_MODELS
from .api.parser import (
    charge_plan_complete,
    parse_charge_records,
    parse_consumption_rank,
    parse_energy_window,
    parse_messages,
    parse_mileage,
    parse_software,
    parse_status,
    parse_unread_count,
    status_has_data,
)
from .api.tls import describe_certificate
from .const import (
    ACTIVITY_HOLD,
    BATTERY_CAPACITY,
    BATTERY_CAPACITY_REEV,
    CERT_RENEWAL_WINDOW_DAYS,
    CHARGER_REFRESH_DELAY,
    COMMAND_REFRESH_DELAYS,
    CONF_CHARGER_POWER_ENTITY,
    CONF_CHARGER_POWER_THRESHOLD,
    CONF_DAILY_REQUEST_LIMIT,
    CONF_INTERVAL_ACTIVE,
    CONF_INTERVAL_HISTORY,
    CONF_INTERVAL_IDLE,
    CONF_PINS,
    CONF_SERVER_CERT,
    CONF_TLS_MODE,
    DAILY_DATA_INTERVAL,
    DEFAULT_CHARGER_POWER_THRESHOLD,
    DEFAULT_DAILY_REQUEST_LIMIT,
    DEFAULT_INTERVAL_ACTIVE,
    DEFAULT_INTERVAL_HISTORY,
    DEFAULT_INTERVAL_IDLE,
    DOMAIN,
    ERROR_GRACE,
    ISSUE_APP_CERT,
    ISSUE_PIN_REJECTED,
    ISSUE_SERVER_CERT,
    ISSUE_SESSION_CONFLICT,
    MANUFACTURER,
    MAX_BACKOFF,
    MIN_REFRESH_GAP,
    OPTIMISTIC_TTL,
    RATE_LIMIT_PAUSE,
    TLS_MODE_AUTO,
    TLS_MODE_STRICT,
    VEHICLE_LIST_INTERVAL,
)
from .picture_store import load_pictures, picture_root, store_pictures

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1

# State keys whose change means "somebody is using the car".
_ACTIVITY_KEYS = (
    "locked",
    "any_door_open",
    "any_window_open",
    "is_plugged_in",
    "charging_state",
    "gear",
    "climate_on",
    "odometer",
)

type LeapmotorConfigEntry = ConfigEntry[LeapmotorCoordinator]


@dataclass(slots=True)
class VehicleData:
    """Everything known about one vehicle."""

    info: VehicleInfo
    state: dict[str, Any] = field(default_factory=dict)
    extras: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)
    polled_at: datetime | None = None


class LeapmotorCoordinator(DataUpdateCoordinator[dict[str, VehicleData]]):
    """Fetch data for all vehicles of one account."""

    config_entry: LeapmotorConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: LeapmotorConfigEntry,
        client: LeapmotorClient,
        store: Store[dict[str, Any]],
        stored: dict[str, Any],
    ) -> None:
        options = entry.options
        self.interval_active = int(options.get(CONF_INTERVAL_ACTIVE, DEFAULT_INTERVAL_ACTIVE))
        self.interval_idle = int(options.get(CONF_INTERVAL_IDLE, DEFAULT_INTERVAL_IDLE))
        self.interval_history = int(options.get(CONF_INTERVAL_HISTORY, DEFAULT_INTERVAL_HISTORY))
        self.daily_limit = int(options.get(CONF_DAILY_REQUEST_LIMIT, DEFAULT_DAILY_REQUEST_LIMIT))
        self.tls_mode = str(options.get(CONF_TLS_MODE, TLS_MODE_AUTO))
        self.pins: dict[str, str] = {
            str(vin): str(pin) for vin, pin in (options.get(CONF_PINS) or {}).items() if pin
        }
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN} {entry.title}",
            update_interval=timedelta(minutes=self.interval_idle),
            request_refresh_debouncer=Debouncer(
                hass, _LOGGER, cooldown=MIN_REFRESH_GAP, immediate=True
            ),
        )
        self.client = client
        self._store = store

        self.vehicles: dict[str, VehicleInfo] = {}
        for item in stored.get("vehicles") or []:
            if (info := VehicleInfo.from_dict(item)) is not None:
                self.vehicles[info.vin] = info
        self._vehicles_fetched = 0.0
        self.capacity: dict[str, float] = {
            str(vin): float(value)
            for vin, value in (stored.get("capacity") or {}).items()
            if isinstance(value, (int, float))
        }
        counter = stored.get("requests") or {}
        self._request_day: date = dt_util.now().date()
        self.requests_today = (
            int(counter.get("count") or 0)
            if counter.get("day") == self._request_day.isoformat()
            else 0
        )

        self.polling_mode = "idle"
        self.last_error: str | None = None
        self.last_success: datetime | None = None
        self.pin_rejected: set[str] = set()
        self.pending_certificate: bytes | None = None
        # App pictures per VIN: {"key", "layers", "version", "path"}.
        self.pictures: dict[str, dict[str, Any]] = {}

        self._closed = False
        self._failures = 0
        self._active_until = 0.0
        self._charger_active = False
        self._fingerprints: dict[str, tuple[Any, ...]] = {}
        self._overrides: dict[str, dict[str, tuple[Any, float]]] = {}
        self._history_due: dict[str, float] = {}
        self._daily_due: dict[str, float] = {}
        self._unsupported: dict[tuple[str, str], float] = {}
        self._timers: set[CALLBACK_TYPE] = set()
        self._charger_timer: CALLBACK_TYPE | None = None
        self._command_locks: dict[str, asyncio.Lock] = {}

        client.on_request = self._count_request
        client.on_session_changed = lambda _session: self._save()
        client.on_server_certificate_changed = self._async_server_certificate_changed

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _storage_data(self) -> dict[str, Any]:
        session = self.client.session
        return {
            "session": session.to_dict() if session is not None else None,
            "vehicles": [info.as_dict() for info in self.vehicles.values()],
            "capacity": dict(self.capacity),
            "requests": {"day": self._request_day.isoformat(), "count": self.requests_today},
        }

    @callback
    def _save(self) -> None:
        self._store.async_delay_save(self._storage_data, 2)

    async def async_shutdown(self) -> None:
        """Stop timers and persist the session."""
        if self._closed:
            return
        self._closed = True
        for cancel in list(self._timers):
            cancel()
        self._timers.clear()
        if self._charger_timer is not None:
            self._charger_timer()
            self._charger_timer = None
        await self._store.async_save(self._storage_data())
        await self.client.close()
        await super().async_shutdown()

    # ------------------------------------------------------------------
    # Helpers used by entities
    # ------------------------------------------------------------------

    def vehicle(self, vin: str) -> VehicleData:
        """Return the data of one vehicle or raise a user-facing error."""
        data = (self.data or {}).get(vin)
        if data is None:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="unknown_vehicle",
                translation_placeholders={"vin": vin[-6:]},
            )
        return data

    def device_info(self, vin: str) -> DeviceInfo:
        """Return the device registry entry of a vehicle."""
        info = self.vehicles[vin]
        name = info.nickname
        if not name or name.upper() == info.model:
            name = info.model_name
        extras = self.data[vin].extras if self.data and vin in self.data else {}
        return DeviceInfo(
            identifiers={(DOMAIN, vin)},
            manufacturer=MANUFACTURER,
            model=info.model,
            name=name,
            serial_number=vin,
            sw_version=extras.get("software_version"),
        )

    def battery_capacity(self, vin: str) -> float | None:
        """Return the usable battery capacity in kWh used for estimates."""
        if vin in self.capacity:
            return self.capacity[vin]
        data = (self.data or {}).get(vin)
        if data is not None and data.state.get("is_reev"):
            return BATTERY_CAPACITY_REEV
        info = self.vehicles.get(vin)
        return BATTERY_CAPACITY.get(info.model) if info else None

    def set_battery_capacity(self, vin: str, value: float) -> None:
        """Store a user-defined battery capacity."""
        self.capacity[vin] = float(value)
        self._save()
        self.async_update_listeners()

    @property
    def cloud_ok(self) -> bool:
        """Return whether the last poll reached the cloud."""
        return self.last_error is None

    # ------------------------------------------------------------------
    # Request accounting
    # ------------------------------------------------------------------

    def _roll_request_day(self) -> None:
        today = dt_util.now().date()
        if today != self._request_day:
            self._request_day = today
            self.requests_today = 0

    @callback
    def _count_request(self, _label: str) -> None:
        self._roll_request_day()
        self.requests_today += 1

    # ------------------------------------------------------------------
    # Polling
    # ------------------------------------------------------------------

    async def _async_update_data(self) -> dict[str, VehicleData]:
        try:
            data = await self._poll()
        except LeapmotorAuthError as err:
            self.last_error = str(err)
            raise ConfigEntryAuthFailed(str(err)) from err
        except LeapmotorRateLimitError as err:
            self._failures += 1
            self.polling_mode = "paused"
            self.update_interval = timedelta(seconds=RATE_LIMIT_PAUSE)
            if err.endpoint == "login" and "budget" in str(err).lower():
                self._create_issue(ISSUE_SESSION_CONFLICT, severity=ir.IssueSeverity.WARNING)
            return self._keep_or_fail(err)
        except LeapmotorCertificateError as err:
            self._failures += 1
            self._back_off()
            self._create_issue(ISSUE_APP_CERT, severity=ir.IssueSeverity.ERROR)
            return self._keep_or_fail(err)
        except LeapmotorError as err:
            self._failures += 1
            self._back_off()
            return self._keep_or_fail(err)

        if self._failures:
            _LOGGER.info("Connection to the Leapmotor cloud restored")
        self._failures = 0
        self.last_error = None
        self.last_success = dt_util.utcnow()
        for issue in (ISSUE_APP_CERT, ISSUE_SESSION_CONFLICT):
            ir.async_delete_issue(self.hass, DOMAIN, f"{issue}_{self.config_entry.entry_id}")
        self.update_interval = self._next_interval(data)
        self._save()
        return data

    def _back_off(self) -> None:
        seconds = min(self.interval_idle * 60 * 2 ** min(self._failures - 1, 4), MAX_BACKOFF)
        self.polling_mode = "backoff"
        self.update_interval = timedelta(seconds=max(seconds, 300))

    def _keep_or_fail(self, err: Exception) -> dict[str, VehicleData]:
        """Keep the last data during short outages instead of flapping entities."""
        self.last_error = str(err)
        if self.data and self.last_success is not None:
            age = (dt_util.utcnow() - self.last_success).total_seconds()
            if age < ERROR_GRACE:
                _LOGGER.debug("Leapmotor update failed, keeping previous data: %s", err)
                return self.data
        raise UpdateFailed(str(err)) from err

    async def _poll(self) -> dict[str, VehicleData]:
        self._roll_request_day()
        if not self.vehicles or time.time() - self._vehicles_fetched > VEHICLE_LIST_INTERVAL:
            vehicles = await self.client.get_vehicles()
            if vehicles:
                self.vehicles = {info.vin: info for info in vehicles}
                self._vehicles_fetched = time.time()
            elif not self.vehicles:
                raise UpdateFailed(translation_domain=DOMAIN, translation_key="no_vehicles")

        home = (self.hass.config.latitude, self.hass.config.longitude)
        now = dt_util.utcnow()
        result: dict[str, VehicleData] = {}
        for vin, info in self.vehicles.items():
            previous = (self.data or {}).get(vin)
            try:
                raw = await self.client.get_status(info)
            except LeapmotorPermissionError as err:
                _LOGGER.debug("No permission to read %s: %s", info.vin_tail, err)
                if previous is not None:
                    result[vin] = previous
                continue
            if status_has_data(raw) or previous is None:
                state = parse_status(info, raw, home=home, now=now)
            else:
                state = dict(previous.state)
            self._track_activity(vin, state)
            self._apply_overrides(vin, state)
            extras = await self._update_extras(info, previous)
            result[vin] = VehicleData(info=info, state=state, extras=extras, raw=raw, polled_at=now)
        if not result:
            raise UpdateFailed(translation_domain=DOMAIN, translation_key="no_vehicles")
        return result

    async def _optional(
        self, vin: str, feature: str, call: Callable[[], Awaitable[Any]]
    ) -> Any | None:
        """Fetch non-essential data; failures never break the main update."""
        until = self._unsupported.get((vin, feature))
        if until is not None and time.time() < until:
            return None
        try:
            return await call()
        except LeapmotorPermissionError:
            # Not available for this account (e.g. shared vehicle): ask again tomorrow.
            self._unsupported[(vin, feature)] = time.time() + DAILY_DATA_INTERVAL
        except (LeapmotorAuthError, LeapmotorRateLimitError, LeapmotorServerIdentityError):
            raise
        except LeapmotorError as err:
            _LOGGER.debug("Optional data '%s' not available: %s", feature, err)
        return None

    async def _update_extras(
        self, info: VehicleInfo, previous: VehicleData | None
    ) -> dict[str, Any]:
        vin = info.vin
        extras: dict[str, Any] = dict(previous.extras) if previous is not None else {}
        now_ts = time.time()
        client = self.client

        if now_ts >= self._history_due.get(vin, 0.0):
            self._history_due[vin] = now_ts + self.interval_history * 60
            local_now = dt_util.now()
            midnight = local_now.replace(hour=0, minute=0, second=0, microsecond=0)

            data = await self._optional(
                vin,
                "mileage",
                lambda: client.get_mileage(info, midnight - timedelta(days=6), local_now),
            )
            if data is not None:
                extras.update(parse_mileage(data, energy_in_wh=info.model in LEGACY_MODELS))
            data = await self._optional(
                vin, "energy_today", lambda: client.get_energy_window(info, midnight, local_now)
            )
            if data is not None:
                extras.update(parse_energy_window(data, "energy_today"))
            data = await self._optional(
                vin,
                "charge_records",
                lambda: client.get_charge_records(
                    info,
                    local_now.date() - timedelta(days=14),
                    local_now.date(),
                    reference=local_now,
                ),
            )
            if data is not None:
                extras.update(parse_charge_records(data))
            unread = parse_unread_count(
                await self._optional(vin, "unread", client.get_unread_count)
            )
            if unread is not None:
                if unread != extras.get("messages_unread") or "last_message_title" not in extras:
                    messages = await self._optional(vin, "messages", client.get_messages)
                    if messages is not None:
                        extras.update(parse_messages(messages))
                extras["messages_unread"] = unread

        if now_ts >= self._daily_due.get(vin, 0.0):
            self._daily_due[vin] = now_ts + DAILY_DATA_INTERVAL
            local_now = dt_util.now()
            monday = (local_now - timedelta(days=local_now.weekday())).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            data = await self._optional(vin, "rank", lambda: client.get_consumption_rank(info))
            if data is not None:
                extras.update(parse_consumption_rank(data))
            data = await self._optional(
                vin,
                "energy_last_week",
                lambda: client.get_energy_window(
                    info, monday - timedelta(days=7), monday - timedelta(seconds=1)
                ),
            )
            if data is not None:
                extras.update(parse_energy_window(data, "energy_last_week"))
            if not info.is_shared:
                data = await self._optional(vin, "software", lambda: client.get_software(info))
                if data is not None:
                    extras.update(parse_software(data))
        return extras

    # ------------------------------------------------------------------
    # Adaptive interval
    # ------------------------------------------------------------------

    def _track_activity(self, vin: str, state: dict[str, Any]) -> None:
        fingerprint = tuple(state.get(key) for key in _ACTIVITY_KEYS)
        previous = self._fingerprints.get(vin)
        self._fingerprints[vin] = fingerprint
        if previous is not None and previous != fingerprint:
            self._active_until = time.monotonic() + ACTIVITY_HOLD

    @staticmethod
    def _in_use(state: dict[str, Any]) -> bool:
        return bool(
            state.get("is_charging")
            or state.get("is_driving")
            or state.get("climate_on")
            or state.get("vehicle_ready")
        )

    def _next_interval(self, data: dict[str, VehicleData]) -> timedelta:
        active = (
            self._charger_active
            or time.monotonic() < self._active_until
            or any(self._in_use(vehicle.state) for vehicle in data.values())
        )
        minutes = self.interval_active if active else self.interval_idle
        self.polling_mode = "active" if active else "idle"
        if self.requests_today >= self.daily_limit:
            minutes = max(minutes, self.interval_idle, 60)
            self.polling_mode = "budget"
        return timedelta(minutes=minutes)

    @callback
    def _schedule_followup_refresh(self, delay: float) -> None:
        """Refresh once more after a command, when the vehicle has reacted."""

        @callback
        def _fire(_now: datetime) -> None:
            self._timers.discard(cancel)
            self.hass.async_create_task(self.async_request_refresh())

        cancel = async_call_later(self.hass, delay, _fire)
        self._timers.add(cancel)

    @callback
    def async_setup_listeners(self) -> None:
        """Watch the optional wallbox power sensor."""
        entity_id = self.config_entry.options.get(CONF_CHARGER_POWER_ENTITY)
        if not entity_id:
            return
        self._charger_active = self._charger_power_high(self.hass.states.get(entity_id))
        self.config_entry.async_on_unload(
            async_track_state_change_event(self.hass, [entity_id], self._handle_charger_event)
        )

    def _charger_power_high(self, state: Any) -> bool:
        if state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return False
        try:
            value = float(state.state)
        except (TypeError, ValueError):
            return False
        unit = str(state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) or "").lower()
        if unit == "kw":
            value *= 1000.0
        threshold = float(
            self.config_entry.options.get(
                CONF_CHARGER_POWER_THRESHOLD, DEFAULT_CHARGER_POWER_THRESHOLD
            )
        )
        return value >= threshold

    @callback
    def _handle_charger_event(self, event: Event[EventStateChangedData]) -> None:
        high = self._charger_power_high(event.data["new_state"])
        if high == self._charger_active:
            return
        self._charger_active = high
        self._active_until = time.monotonic() + ACTIVITY_HOLD
        _LOGGER.debug("Wallbox power is %s the threshold: refreshing", "above" if high else "below")
        if self._charger_timer is not None:
            self._charger_timer()

        @callback
        def _fire(_now: datetime) -> None:
            self._charger_timer = None
            self.hass.async_create_task(self.async_request_refresh())

        self._charger_timer = async_call_later(self.hass, CHARGER_REFRESH_DELAY, _fire)

    # ------------------------------------------------------------------
    # Optimistic state
    # ------------------------------------------------------------------

    def _apply_overrides(self, vin: str, state: dict[str, Any]) -> None:
        overrides = self._overrides.get(vin)
        if not overrides:
            return
        now = time.monotonic()
        for key in list(overrides):
            value, expires = overrides[key]
            if now >= expires or state.get(key) == value:
                del overrides[key]
            else:
                state[key] = value

    @callback
    def set_optimistic(self, vin: str, values: dict[str, Any]) -> None:
        """Show the expected result of a command until the cloud confirms it."""
        data = (self.data or {}).get(vin)
        if data is None:
            return
        expires = time.monotonic() + OPTIMISTIC_TTL
        overrides = self._overrides.setdefault(vin, {})
        for key, value in values.items():
            overrides[key] = (value, expires)
            data.state[key] = value
        self.async_update_listeners()

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    def _error(self, key: str, **placeholders: str) -> HomeAssistantError:
        return HomeAssistantError(
            translation_domain=DOMAIN, translation_key=key, translation_placeholders=placeholders
        )

    async def async_send_command(
        self,
        vin: str,
        command: RemoteCommand,
        *,
        optimistic: dict[str, Any] | None = None,
    ) -> CommandResult:
        """Send a remote command, using the stored PIN of the vehicle if needed."""
        vehicle = self.vehicle(vin)
        pin = self.pins.get(vin)
        if command.requires_pin:
            if not pin:
                raise ServiceValidationError(
                    translation_domain=DOMAIN, translation_key="pin_missing"
                )
            if vin in self.pin_rejected:
                # Never repeat a rejected PIN: too many wrong attempts lock remote control.
                raise ServiceValidationError(
                    translation_domain=DOMAIN, translation_key="pin_rejected"
                )

        lock = self._command_locks.setdefault(vin, asyncio.Lock())
        async with lock:
            _LOGGER.debug("Sending command %s to %s", command.name, vehicle.info.vin_tail)
            try:
                result = await self.client.send_command(vehicle.info, command, pin)
            except LeapmotorPinError as err:
                if pin:
                    self.pin_rejected.add(vin)
                    self._create_issue(
                        ISSUE_PIN_REJECTED,
                        severity=ir.IssueSeverity.ERROR,
                        suffix=vin,
                        placeholders={"vehicle": self.device_info(vin).get("name") or vin[-6:]},
                    )
                raise self._error("pin_rejected") from err
            except LeapmotorPermissionError as err:
                raise self._error("command_not_permitted", error=str(err)) from err
            except LeapmotorAuthError as err:
                self.config_entry.async_start_reauth(self.hass)
                raise self._error("auth_failed") from err
            except LeapmotorRateLimitError as err:
                raise self._error("rate_limited", error=str(err)) from err
            except LeapmotorConnectionError as err:
                raise self._error("cannot_connect", error=str(err)) from err
            except LeapmotorError as err:
                raise self._error("command_failed", error=str(err)) from err

        self._active_until = time.monotonic() + ACTIVITY_HOLD
        for delay in COMMAND_REFRESH_DELAYS:
            self._schedule_followup_refresh(delay)
        if not result.confirmed:
            raise self._error("command_unconfirmed")
        if optimistic:
            self.set_optimistic(vin, optimistic)
        return result

    async def async_set_charge_plan(
        self,
        vin: str,
        *,
        enabled: bool | None = None,
        limit: int | None = None,
        start: Any = None,
        end: Any = None,
    ) -> CommandResult:
        """Change parts of the charging plan while keeping the rest of it."""
        vehicle = self.vehicle(vin)
        if vehicle.info.model in LEGACY_MODELS:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="charge_plan_unsupported"
            )
        state = vehicle.state
        plan: dict[str, Any] = {
            "isEnable": None
            if state.get("charge_schedule_enabled") is None
            else int(bool(state["charge_schedule_enabled"])),
            "percent": state.get("charge_limit"),
            "beginTime": state.get("charge_schedule_start"),
            "endTime": state.get("charge_schedule_end"),
            "cycles": state.get("charge_schedule_cycles"),
            "circulation": state.get("charge_schedule_circulation"),
            "recharge": state.get("charge_schedule_recharge"),
        }
        if not charge_plan_complete(plan):
            try:
                stored = await self.client.get_charge_plan(vehicle.info)
            except LeapmotorError as err:
                _LOGGER.debug("Stored charging plan not available: %s", err)
                stored = {}
            for key, value in stored.items():
                if plan.get(key) in (None, "") and value not in (None, ""):
                    plan[key] = value

        def _number(raw: Any) -> int | None:
            try:
                return int(float(raw))
            except (TypeError, ValueError):
                return None

        new_limit = limit if limit is not None else _number(plan.get("percent"))
        new_enabled = enabled if enabled is not None else bool(_number(plan.get("isEnable")))
        new_start = start if start is not None else plan.get("beginTime")
        new_end = end if end is not None else plan.get("endTime")
        if new_limit is None or (new_enabled and not (new_start and new_end)):
            # Guessing the missing part could silently change the user's plan.
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="charge_plan_incomplete"
            )
        try:
            command = commands.charge_plan(
                enabled=new_enabled,
                limit_percent=int(new_limit),
                start=new_start or "22:00",
                end=new_end or "06:00",
                cycles=plan.get("cycles"),
                circulation=_number(plan.get("circulation")) or 0,
                recharge=_number(plan.get("recharge")) or 0,
            )
        except ValueError as err:
            raise ServiceValidationError(str(err)) from err
        return await self.async_send_command(
            vin,
            command,
            optimistic={
                "charge_limit": int(new_limit),
                "charge_schedule_enabled": new_enabled,
                "charge_schedule_start": commands.normalize_clock(new_start or "22:00"),
                "charge_schedule_end": commands.normalize_clock(new_end or "06:00"),
            },
        )

    async def async_load_pictures(self) -> None:
        """Make the app pictures of each vehicle available.

        Stored pictures are used as they are; a vehicle without stored
        pictures is asked for its picture package once (two requests).
        """
        root = picture_root(self.hass)
        changed = False
        for vin, info in list(self.vehicles.items()):
            if vin in self.pictures:
                continue
            pictures = await self.hass.async_add_executor_job(load_pictures, root, vin)
            if pictures is None and not self.client.is_demo:
                try:
                    result = await self._optional(
                        vin, "picture", lambda info=info: self.client.get_picture_package(info)
                    )
                except LeapmotorError as err:
                    _LOGGER.debug("Vehicle pictures are not available: %s", err)
                    result = None
                if result:
                    picture_id, package = result
                    pictures = await self.hass.async_add_executor_job(
                        store_pictures, root, vin, picture_id, package
                    )
                    _LOGGER.debug(
                        "Stored %d picture layers for %s",
                        len(pictures["layers"]) if pictures else 0,
                        info.vin_tail,
                    )
            if pictures:
                self.pictures[vin] = pictures
                changed = True
        if changed:
            self.async_update_listeners()

    # ------------------------------------------------------------------
    # Issues
    # ------------------------------------------------------------------

    def _create_issue(
        self,
        issue: str,
        *,
        severity: ir.IssueSeverity,
        suffix: str | None = None,
        fixable: bool = False,
        placeholders: dict[str, str] | None = None,
        data: dict[str, Any] | None = None,
    ) -> None:
        ir.async_create_issue(
            self.hass,
            DOMAIN,
            f"{issue}_{suffix or self.config_entry.entry_id}",
            is_fixable=fixable,
            is_persistent=False,
            severity=severity,
            translation_key=issue,
            translation_placeholders={"account": self.config_entry.title, **(placeholders or {})},
            data=data,
        )

    async def _async_server_certificate_changed(
        self, previous: bytes | None, presented: bytes
    ) -> bool:
        """Decide whether a new server certificate may be trusted."""
        new = describe_certificate(presented)
        accept = previous is None
        reason = "first contact"
        if previous is not None and self.tls_mode != TLS_MODE_STRICT:
            old = describe_certificate(previous)
            remaining = old.not_after - dt_util.utcnow()
            if remaining <= timedelta(days=CERT_RENEWAL_WINDOW_DAYS):
                # The pinned certificate was about to expire: a regular renewal.
                accept = True
                reason = "regular renewal"
        if accept:
            _LOGGER.warning(
                "Trusting new Leapmotor server certificate %s, valid until %s (%s)",
                new.short_fingerprint,
                new.not_after.date(),
                reason,
            )
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data={
                    **self.config_entry.data,
                    CONF_SERVER_CERT: base64.b64encode(presented).decode("ascii"),
                },
            )
            if previous is not None:
                persistent_notification.async_create(
                    self.hass,
                    (
                        "The Leapmotor server renewed its certificate. The new one "
                        f"(`{new.short_fingerprint}`, valid until {new.not_after.date()}) "
                        "is trusted from now on."
                    ),
                    title="Leapmotor Cloud",
                    notification_id=f"{DOMAIN}_certificate_{self.config_entry.entry_id}",
                )
            return True

        self.pending_certificate = presented
        self._create_issue(
            ISSUE_SERVER_CERT,
            severity=ir.IssueSeverity.ERROR,
            fixable=True,
            placeholders={
                "fingerprint": new.short_fingerprint,
                "issuer": new.issuer,
                "valid_until": new.not_after.date().isoformat(),
            },
            data={
                "entry_id": self.config_entry.entry_id,
                "certificate": base64.b64encode(presented).decode("ascii"),
            },
        )
        return False
