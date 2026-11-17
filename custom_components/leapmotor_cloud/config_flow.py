"""Config flow: app certificate -> account -> vehicle PIN."""

from __future__ import annotations

import base64
from collections.abc import Mapping
import logging
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
import uuid

from homeassistant.components.file_upload import process_uploaded_file
from homeassistant.config_entries import (
    ConfigEntryState,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import section
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    FileSelector,
    FileSelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)
import voluptuous as vol

from .api import (
    DEFAULT_BASE_URL,
    DEMO_PIN,
    DEMO_VIN,
    LeapmotorAuthError,
    LeapmotorCertificateError,
    LeapmotorCloudClient,
    LeapmotorConnectionError,
    LeapmotorError,
    LeapmotorPinError,
    LeapmotorRateLimitError,
    VehicleInfo,
)
from .api.tls import normalize_pem, validate_client_certificate
from .const import (
    CERT_DIRECTORIES,
    CERT_FILE_NAMES,
    CONF_APP_CERT,
    CONF_APP_KEY,
    CONF_BASE_URL,
    CONF_CERT_FILE,
    CONF_CERT_TEXT,
    CONF_CHARGER_POWER_ENTITY,
    CONF_CHARGER_POWER_THRESHOLD,
    CONF_DAILY_REQUEST_LIMIT,
    CONF_DEMO,
    CONF_DEVICE_ID,
    CONF_INTERVAL_ACTIVE,
    CONF_INTERVAL_HISTORY,
    CONF_INTERVAL_IDLE,
    CONF_KEY_FILE,
    CONF_KEY_TEXT,
    CONF_PIN,
    CONF_PINS,
    CONF_SERVER_CERT,
    CONF_TLS_MODE,
    DATA_PENDING_SESSIONS,
    DEFAULT_CHARGER_POWER_THRESHOLD,
    DEFAULT_DAILY_REQUEST_LIMIT,
    DEFAULT_INTERVAL_ACTIVE,
    DEFAULT_INTERVAL_HISTORY,
    DEFAULT_INTERVAL_IDLE,
    DOMAIN,
    KEY_FILE_NAMES,
    MAX_INTERVAL,
    MIN_DAILY_REQUEST_LIMIT,
    MIN_INTERVAL_ACTIVE,
    MIN_INTERVAL_HISTORY,
    MIN_INTERVAL_IDLE,
    TLS_MODE_AUTO,
    TLS_MODES,
)

_LOGGER = logging.getLogger(__name__)

CONF_REMOVE_PIN = "remove_pin"
SECTION_ADVANCED = "advanced"
MAX_PIN_ATTEMPTS = 3

_PASSWORD = TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))
_MULTILINE = TextSelector(TextSelectorConfig(multiline=True))

CERTIFICATE_FIELDS: dict[Any, Any] = {
    vol.Optional(CONF_CERT_FILE): FileSelector(FileSelectorConfig(accept=".pem,.crt,.cer,.cert")),
    vol.Optional(CONF_KEY_FILE): FileSelector(FileSelectorConfig(accept=".pem,.key")),
    vol.Optional(CONF_CERT_TEXT): _MULTILINE,
    vol.Optional(CONF_KEY_TEXT): _MULTILINE,
}


def _find_certificate(config_dir: str) -> tuple[str, str] | None:
    """Look for app certificate files the user placed in the config folder."""
    for directory in CERT_DIRECTORIES:
        base = Path(config_dir) / directory
        cert = next((base / name for name in CERT_FILE_NAMES if (base / name).is_file()), None)
        key = next((base / name for name in KEY_FILE_NAMES if (base / name).is_file()), None)
        if cert is not None and key is not None:
            try:
                return (
                    cert.read_text(encoding="utf-8", errors="replace"),
                    key.read_text(encoding="utf-8", errors="replace"),
                )
            except OSError:
                continue
    return None


def _read_upload(hass: HomeAssistant, file_id: str) -> str:
    with process_uploaded_file(hass, file_id) as path:
        return path.read_text(encoding="utf-8", errors="replace")


async def _async_certificate_from_input(
    hass: HomeAssistant, user_input: Mapping[str, Any]
) -> tuple[str, str] | None:
    """Return ``(cert, key)`` from uploads or pasted text; ``None`` if nothing was given."""
    parts: list[str] = []
    for file_key, text_key in ((CONF_CERT_FILE, CONF_CERT_TEXT), (CONF_KEY_FILE, CONF_KEY_TEXT)):
        text = str(user_input.get(text_key) or "").strip()
        if file_id := user_input.get(file_key):
            try:
                text = await hass.async_add_executor_job(_read_upload, hass, file_id)
            except (ValueError, OSError) as err:
                raise LeapmotorCertificateError("The uploaded file could not be read") from err
        parts.append(normalize_pem(text) if text else "")
    cert, key = parts
    if not cert and not key:
        return None
    if not cert or not key:
        raise LeapmotorCertificateError("Certificate and private key are both required")
    # A combined PEM file may have been given for either field.
    if "PRIVATE KEY" in cert and "CERTIFICATE" in key:
        cert, key = key, cert
    await hass.async_add_executor_job(validate_client_certificate, cert, key)
    return cert, key


def _vehicle_name(vehicle: VehicleInfo) -> str:
    if vehicle.nickname and vehicle.nickname.upper() != vehicle.model:
        return f"{vehicle.nickname} ({vehicle.model_name})"
    return vehicle.model_name


class LeapmotorConfigFlow(ConfigFlow, domain=DOMAIN):
    """Set up a Leapmotor account."""

    VERSION = 1

    def __init__(self) -> None:
        self._cert: str | None = None
        self._key: str | None = None
        self._data: dict[str, Any] = {}
        self._client: LeapmotorCloudClient | None = None
        self._vehicles: list[VehicleInfo] = []
        self._pins: dict[str, str] = {}
        self._pin_index = 0
        self._pin_attempts = 0

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: Any) -> LeapmotorOptionsFlow:
        """Return the options flow."""
        return LeapmotorOptionsFlow()

    # -- entry points ------------------------------------------------------------

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Choose between a real account and the simulated vehicle."""
        return self.async_show_menu(step_id="user", menu_options=["account", "demo"])

    async def async_step_demo(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Create the simulated vehicle."""
        await self.async_set_unique_id("demo")
        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title="Leapmotor Demo",
            data={CONF_DEMO: True},
            options={CONF_PINS: {DEMO_VIN: DEMO_PIN}},
        )

    async def async_step_account(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Use certificate files from the config folder, or ask for them."""
        found = await self.hass.async_add_executor_job(_find_certificate, self.hass.config.path())
        if found is not None:
            cert, key = normalize_pem(found[0]), normalize_pem(found[1])
            try:
                await self.hass.async_add_executor_job(validate_client_certificate, cert, key)
            except LeapmotorCertificateError as err:
                _LOGGER.warning("Ignoring unusable app certificate files: %s", err)
            else:
                self._cert, self._key = cert, key
                return await self.async_step_credentials()
        return await self.async_step_certificate()

    # -- steps ---------------------------------------------------------------------

    async def async_step_certificate(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the app certificate and its private key."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                material = await _async_certificate_from_input(self.hass, user_input)
            except LeapmotorCertificateError as err:
                _LOGGER.debug("App certificate rejected: %s", err)
                errors["base"] = "invalid_certificate"
            else:
                if material is None:
                    errors["base"] = "certificate_required"
                else:
                    self._cert, self._key = material
                    return await self.async_step_credentials()
        # Uploads are consumed when read, so only pasted text can be offered again.
        suggested = {
            key: value
            for key, value in (user_input or {}).items()
            if key in (CONF_CERT_TEXT, CONF_KEY_TEXT)
        }
        return self.async_show_form(
            step_id="certificate",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(CERTIFICATE_FIELDS), suggested
            ),
            errors=errors,
            description_placeholders={"folder": f"/config/{CERT_DIRECTORIES[0]}"},
        )

    async def _async_login(
        self, username: str, password: str, base_url: str, device_id: str, cert: str, key: str
    ) -> tuple[LeapmotorCloudClient, list[VehicleInfo], bytes]:
        """Pin the server certificate, log in and list the vehicles."""
        client = LeapmotorCloudClient(
            async_get_clientsession(self.hass),
            user_agent="ha-leapmotor-cloud",
            username=username,
            password=password,
            app_cert_pem=cert,
            app_key_pem=key,
            device_id=device_id,
            base_url=base_url,
        )
        server_cert = await client.fetch_server_certificate()
        client.set_pinned_certificate(server_cert)
        vehicles = await client.get_vehicles()
        return client, vehicles, server_cert

    @staticmethod
    def _login_error(err: LeapmotorError) -> str:
        if isinstance(err, LeapmotorAuthError):
            return "invalid_auth"
        if isinstance(err, LeapmotorCertificateError):
            return "certificate_rejected"
        if isinstance(err, LeapmotorRateLimitError):
            return "rate_limited"
        if isinstance(err, LeapmotorConnectionError):
            return "cannot_connect"
        return "unknown"

    async def async_step_credentials(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the Leapmotor account."""
        errors: dict[str, str] = {}
        detail = ""
        if user_input is not None:
            assert self._cert is not None and self._key is not None
            username = str(user_input[CONF_USERNAME]).strip()
            advanced = user_input.get(SECTION_ADVANCED) or {}
            base_url = (
                str(
                    advanced.get(CONF_BASE_URL) or user_input.get(CONF_BASE_URL) or DEFAULT_BASE_URL
                )
                .strip()
                .rstrip("/")
            )
            await self.async_set_unique_id(username.lower())
            self._abort_if_unique_id_configured()
            if urlsplit(base_url).scheme != "https" or not urlsplit(base_url).hostname:
                errors["base"] = "invalid_url"
            else:
                device_id = uuid.uuid4().hex
                try:
                    client, vehicles, server_cert = await self._async_login(
                        username,
                        user_input[CONF_PASSWORD],
                        base_url,
                        device_id,
                        self._cert,
                        self._key,
                    )
                except LeapmotorError as err:
                    _LOGGER.warning("Leapmotor login failed: %s", err)
                    errors["base"] = self._login_error(err)
                    detail = str(err)
                else:
                    if not vehicles:
                        errors["base"] = "no_vehicles"
                    else:
                        self._client = client
                        self._vehicles = vehicles
                        self._data = {
                            CONF_USERNAME: username,
                            CONF_PASSWORD: user_input[CONF_PASSWORD],
                            CONF_DEVICE_ID: device_id,
                            CONF_APP_CERT: self._cert,
                            CONF_APP_KEY: self._key,
                            CONF_BASE_URL: base_url,
                            CONF_SERVER_CERT: base64.b64encode(server_cert).decode("ascii"),
                        }
                        return await self.async_step_pin()

        fields: dict[Any, Any] = {
            vol.Required(CONF_USERNAME): TextSelector(
                TextSelectorConfig(type=TextSelectorType.EMAIL, autocomplete="username")
            ),
            vol.Required(CONF_PASSWORD): _PASSWORD,
            # Rarely needed, so it sits in a collapsed section.
            vol.Optional(SECTION_ADVANCED): section(
                vol.Schema(
                    {
                        vol.Optional(CONF_BASE_URL, default=DEFAULT_BASE_URL): TextSelector(
                            TextSelectorConfig(type=TextSelectorType.URL)
                        )
                    }
                ),
                {"collapsed": True},
            ),
        }
        suggested = {
            key: value for key, value in (user_input or {}).items() if key != CONF_PASSWORD
        }
        return self.async_show_form(
            step_id="credentials",
            data_schema=self.add_suggested_values_to_schema(vol.Schema(fields), suggested),
            errors=errors,
            description_placeholders={"error": detail},
        )

    async def async_step_pin(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Ask for the PIN of each vehicle; it is used automatically later."""
        assert self._client is not None
        vehicle = self._vehicles[self._pin_index]
        errors: dict[str, str] = {}
        if user_input is not None:
            pin = str(user_input.get(CONF_PIN) or "").strip()
            if pin:
                try:
                    await self._client.verify_pin(vehicle, pin)
                except LeapmotorPinError:
                    self._pin_attempts += 1
                    if self._pin_attempts >= MAX_PIN_ATTEMPTS:
                        # More wrong guesses could lock remote control of the car.
                        return self.async_abort(reason="pin_attempts")
                    errors["base"] = "invalid_pin"
                except LeapmotorError as err:
                    # The PIN could not be checked now; it will be on first use.
                    _LOGGER.debug("PIN could not be verified during setup: %s", err)
            if not errors:
                if pin:
                    self._pins[vehicle.vin] = pin
                self._pin_index += 1
                self._pin_attempts = 0
                if self._pin_index >= len(self._vehicles):
                    return self._async_finish()
                return await self.async_step_pin()
        return self.async_show_form(
            step_id="pin",
            data_schema=vol.Schema({vol.Optional(CONF_PIN): _PASSWORD}),
            errors=errors,
            description_placeholders={
                "vehicle": _vehicle_name(self._vehicles[self._pin_index]),
                "vin": self._vehicles[self._pin_index].vin[-6:],
            },
        )

    def _async_finish(self) -> ConfigFlowResult:
        assert self._client is not None
        if self._client.session is not None:
            self.hass.data.setdefault(DATA_PENDING_SESSIONS, {})[self.unique_id] = (
                self._client.session.to_dict()
            )
        return self.async_create_entry(
            title=f"Leapmotor ({self._data[CONF_USERNAME]})",
            data=self._data,
            options={CONF_PINS: self._pins},
        )

    # -- reauthentication and reconfiguration -------------------------------------------

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        """The cloud rejected the stored password."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the new password."""
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        detail = ""
        if user_input is not None:
            try:
                _client, _vehicles, server_cert = await self._async_login(
                    entry.data[CONF_USERNAME],
                    user_input[CONF_PASSWORD],
                    entry.data.get(CONF_BASE_URL) or DEFAULT_BASE_URL,
                    entry.data[CONF_DEVICE_ID],
                    entry.data[CONF_APP_CERT],
                    entry.data[CONF_APP_KEY],
                )
            except LeapmotorError as err:
                _LOGGER.warning("Leapmotor login failed: %s", err)
                errors["base"] = self._login_error(err)
                detail = str(err)
            else:
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                        CONF_SERVER_CERT: base64.b64encode(server_cert).decode("ascii"),
                    },
                )
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): _PASSWORD}),
            errors=errors,
            description_placeholders={
                "username": entry.data.get(CONF_USERNAME, ""),
                "error": detail,
            },
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Replace the password and/or the app certificate."""
        entry = self._get_reconfigure_entry()
        if entry.data.get(CONF_DEMO):
            return self.async_abort(reason="demo_not_configurable")
        errors: dict[str, str] = {}
        detail = ""
        if user_input is not None:
            cert, key = entry.data[CONF_APP_CERT], entry.data[CONF_APP_KEY]
            try:
                material = await _async_certificate_from_input(self.hass, user_input)
            except LeapmotorCertificateError as err:
                _LOGGER.debug("App certificate rejected: %s", err)
                errors["base"] = "invalid_certificate"
            else:
                if material is not None:
                    cert, key = material
                password = user_input.get(CONF_PASSWORD) or entry.data[CONF_PASSWORD]
                try:
                    _client, _vehicles, server_cert = await self._async_login(
                        entry.data[CONF_USERNAME],
                        password,
                        entry.data.get(CONF_BASE_URL) or DEFAULT_BASE_URL,
                        entry.data[CONF_DEVICE_ID],
                        cert,
                        key,
                    )
                except LeapmotorError as err:
                    _LOGGER.warning("Leapmotor login failed: %s", err)
                    errors["base"] = self._login_error(err)
                    detail = str(err)
                else:
                    return self.async_update_reload_and_abort(
                        entry,
                        data_updates={
                            CONF_PASSWORD: password,
                            CONF_APP_CERT: cert,
                            CONF_APP_KEY: key,
                            CONF_SERVER_CERT: base64.b64encode(server_cert).decode("ascii"),
                        },
                    )
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema({vol.Optional(CONF_PASSWORD): _PASSWORD, **CERTIFICATE_FIELDS}),
            errors=errors,
            description_placeholders={
                "username": entry.data.get(CONF_USERNAME, ""),
                "error": detail,
            },
        )


class LeapmotorOptionsFlow(OptionsFlowWithReload):
    """Polling, vehicle PINs and connection security."""

    def __init__(self) -> None:
        self._pins: dict[str, str] = {}
        self._pin_index = 0
        self._pin_attempts = 0

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Show the menu."""
        options = ["polling", "pins"]
        if not self.config_entry.data.get(CONF_DEMO):
            options.append("security")
        return self.async_show_menu(step_id="init", menu_options=options)

    def _save(self, changes: dict[str, Any], remove: tuple[str, ...] = ()) -> ConfigFlowResult:
        options = {**self.config_entry.options, **changes}
        for key in remove:
            options.pop(key, None)
        return self.async_create_entry(data=options)

    async def async_step_polling(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """How often the cloud is asked."""
        options = self.config_entry.options
        errors: dict[str, str] = {}
        if user_input is not None:
            if user_input[CONF_INTERVAL_IDLE] < user_input[CONF_INTERVAL_ACTIVE]:
                errors[CONF_INTERVAL_IDLE] = "idle_below_active"
            else:
                changes: dict[str, Any] = {
                    key: int(user_input[key])
                    for key in (
                        CONF_INTERVAL_ACTIVE,
                        CONF_INTERVAL_IDLE,
                        CONF_INTERVAL_HISTORY,
                        CONF_CHARGER_POWER_THRESHOLD,
                        CONF_DAILY_REQUEST_LIMIT,
                    )
                }
                if entity_id := user_input.get(CONF_CHARGER_POWER_ENTITY):
                    changes[CONF_CHARGER_POWER_ENTITY] = entity_id
                    return self._save(changes)
                return self._save(changes, remove=(CONF_CHARGER_POWER_ENTITY,))

        def _minutes(minimum: int, maximum: int) -> NumberSelector:
            return NumberSelector(
                NumberSelectorConfig(
                    min=minimum,
                    max=maximum,
                    step=1,
                    unit_of_measurement="min",
                    mode=NumberSelectorMode.BOX,
                )
            )

        schema = vol.Schema(
            {
                vol.Required(CONF_INTERVAL_ACTIVE): _minutes(MIN_INTERVAL_ACTIVE, 60),
                vol.Required(CONF_INTERVAL_IDLE): _minutes(MIN_INTERVAL_IDLE, MAX_INTERVAL),
                vol.Required(CONF_INTERVAL_HISTORY): _minutes(MIN_INTERVAL_HISTORY, MAX_INTERVAL),
                vol.Optional(CONF_CHARGER_POWER_ENTITY): EntitySelector(
                    EntitySelectorConfig(domain="sensor", device_class="power")
                ),
                vol.Required(CONF_CHARGER_POWER_THRESHOLD): NumberSelector(
                    NumberSelectorConfig(
                        min=50,
                        max=22000,
                        step=50,
                        unit_of_measurement="W",
                        mode=NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(CONF_DAILY_REQUEST_LIMIT): NumberSelector(
                    NumberSelectorConfig(
                        min=MIN_DAILY_REQUEST_LIMIT, max=5000, step=50, mode=NumberSelectorMode.BOX
                    )
                ),
            }
        )
        current = {
            CONF_INTERVAL_ACTIVE: options.get(CONF_INTERVAL_ACTIVE, DEFAULT_INTERVAL_ACTIVE),
            CONF_INTERVAL_IDLE: options.get(CONF_INTERVAL_IDLE, DEFAULT_INTERVAL_IDLE),
            CONF_INTERVAL_HISTORY: options.get(CONF_INTERVAL_HISTORY, DEFAULT_INTERVAL_HISTORY),
            CONF_CHARGER_POWER_ENTITY: options.get(CONF_CHARGER_POWER_ENTITY),
            CONF_CHARGER_POWER_THRESHOLD: options.get(
                CONF_CHARGER_POWER_THRESHOLD, DEFAULT_CHARGER_POWER_THRESHOLD
            ),
            CONF_DAILY_REQUEST_LIMIT: options.get(
                CONF_DAILY_REQUEST_LIMIT, DEFAULT_DAILY_REQUEST_LIMIT
            ),
        }
        return self.async_show_form(
            step_id="polling",
            data_schema=self.add_suggested_values_to_schema(schema, user_input or current),
            errors=errors,
        )

    async def async_step_pins(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Set, change or remove the PIN of each vehicle."""
        entry = self.config_entry
        if entry.state is not ConfigEntryState.LOADED:
            return self.async_abort(reason="not_loaded")
        coordinator = entry.runtime_data
        vehicles = list(coordinator.vehicles.values())
        if self._pin_index == 0 and user_input is None:
            self._pins = dict(entry.options.get(CONF_PINS) or {})
        vehicle = vehicles[self._pin_index]
        errors: dict[str, str] = {}
        if user_input is not None:
            pin = str(user_input.get(CONF_PIN) or "").strip()
            if user_input.get(CONF_REMOVE_PIN):
                self._pins.pop(vehicle.vin, None)
            elif pin:
                try:
                    await coordinator.client.verify_pin(vehicle, pin)
                except LeapmotorPinError:
                    self._pin_attempts += 1
                    if self._pin_attempts >= MAX_PIN_ATTEMPTS:
                        return self.async_abort(reason="pin_attempts")
                    errors["base"] = "invalid_pin"
                except LeapmotorError as err:
                    _LOGGER.debug("PIN could not be verified: %s", err)
                if not errors:
                    self._pins[vehicle.vin] = pin
            if not errors:
                self._pin_index += 1
                self._pin_attempts = 0
                if self._pin_index >= len(vehicles):
                    return self._save({CONF_PINS: self._pins})
                return await self.async_step_pins()
        vehicle = vehicles[self._pin_index]
        return self.async_show_form(
            step_id="pins",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_PIN): _PASSWORD,
                    vol.Optional(CONF_REMOVE_PIN, default=False): bool,
                }
            ),
            errors=errors,
            description_placeholders={
                "vehicle": _vehicle_name(vehicle),
                "vin": vehicle.vin[-6:],
                "status": "✓" if vehicle.vin in self._pins else "–",
            },
        )

    async def async_step_security(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """How the identity of the server is checked."""
        if user_input is not None:
            return self._save({CONF_TLS_MODE: user_input[CONF_TLS_MODE]})
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_TLS_MODE,
                    default=self.config_entry.options.get(CONF_TLS_MODE, TLS_MODE_AUTO),
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=TLS_MODES,
                        mode=SelectSelectorMode.LIST,
                        translation_key=CONF_TLS_MODE,
                    )
                )
            }
        )
        return self.async_show_form(step_id="security", data_schema=schema)
