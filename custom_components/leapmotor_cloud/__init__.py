"""Leapmotor Cloud: control and monitor Leapmotor vehicles (unofficial)."""

from __future__ import annotations

import base64
import binascii
import logging
from pathlib import Path
from typing import Any

from homeassistant.components import frontend
from homeassistant.components.http import StaticPathConfig
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import (
    config_validation as cv,
    device_registry as dr,
    issue_registry as ir,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.helpers.typing import ConfigType
from homeassistant.loader import async_get_integration

from .api import (
    DEFAULT_BASE_URL,
    LeapmotorClient,
    LeapmotorCloudClient,
    LeapmotorDemoClient,
    LeapmotorError,
    SessionState,
)
from .const import (
    CONF_APP_CERT,
    CONF_APP_KEY,
    CONF_BASE_URL,
    CONF_DEMO,
    CONF_DEVICE_ID,
    CONF_SERVER_CERT,
    CONF_TLS_MODE,
    DATA_PENDING_SESSIONS,
    DOMAIN,
    FRONTEND_FILE,
    FRONTEND_URL,
    ISSUE_APP_CERT,
    ISSUE_PIN_REJECTED,
    ISSUE_SERVER_CERT,
    ISSUE_SESSION_CONFLICT,
    PLATFORMS,
    TLS_MODE_AUTO,
    TLS_MODE_OFF,
)
from .coordinator import STORAGE_VERSION, LeapmotorConfigEntry, LeapmotorCoordinator
from .picture_store import LeapmotorPictureView, picture_root, remove_pictures
from .services import async_setup_services

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


def _store(hass: HomeAssistant, entry_id: str) -> Store[dict[str, Any]]:
    return Store(hass, STORAGE_VERSION, f"{DOMAIN}.{entry_id}", private=True)


def _platforms(entry: LeapmotorConfigEntry) -> list[Platform]:
    """The simulated vehicle has no rendered picture."""
    if entry.data.get(CONF_DEMO):
        return [platform for platform in PLATFORMS if platform is not Platform.IMAGE]
    return list(PLATFORMS)


async def _async_register_frontend(hass: HomeAssistant) -> None:
    """Serve the dashboard cards and load them in every browser."""
    if hass.http is None:
        return
    directory = Path(__file__).parent / "frontend"
    integration = await async_get_integration(hass, DOMAIN)

    def _stamp() -> int:
        try:
            return int((directory / FRONTEND_FILE).stat().st_mtime)
        except OSError:
            return 0

    stamp = await hass.async_add_executor_job(_stamp)
    await hass.http.async_register_static_paths(
        [StaticPathConfig(FRONTEND_URL, str(directory), cache_headers=False)]
    )
    try:
        frontend.add_extra_js_url(
            hass, f"{FRONTEND_URL}/{FRONTEND_FILE}?v={integration.version}-{stamp}"
        )
    except KeyError:
        _LOGGER.debug("Frontend is not loaded; dashboard cards are not registered")


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up services, the dashboard cards and the picture delivery."""
    async_setup_services(hass)
    await _async_register_frontend(hass)
    if hass.http is not None:
        hass.http.register_view(LeapmotorPictureView())
    return True


async def _async_create_client(
    hass: HomeAssistant, entry: LeapmotorConfigEntry, stored: dict[str, Any]
) -> LeapmotorClient:
    if entry.data.get(CONF_DEMO):
        return LeapmotorDemoClient(home=(hass.config.latitude, hass.config.longitude))

    verify = entry.options.get(CONF_TLS_MODE, TLS_MODE_AUTO) != TLS_MODE_OFF
    pinned: bytes | None = None
    try:
        pinned = base64.b64decode(entry.data.get(CONF_SERVER_CERT) or "", validate=True) or None
    except (ValueError, binascii.Error):
        pinned = None
    integration = await async_get_integration(hass, DOMAIN)
    client = LeapmotorCloudClient(
        # Every request brings its own TLS context, so the shared session is fine.
        async_get_clientsession(hass),
        user_agent=f"ha-leapmotor-cloud/{integration.version}",
        username=entry.data[CONF_USERNAME],
        password=entry.data[CONF_PASSWORD],
        app_cert_pem=entry.data[CONF_APP_CERT],
        app_key_pem=entry.data[CONF_APP_KEY],
        device_id=entry.data[CONF_DEVICE_ID],
        base_url=entry.data.get(CONF_BASE_URL) or DEFAULT_BASE_URL,
        pinned_certificate=pinned,
        verify_server=verify,
        session=SessionState.from_dict(stored.get("session")),
    )
    if verify and pinned is None:
        # No certificate pinned yet: trust the one presented now (trust on first use).
        try:
            pinned = await client.fetch_server_certificate()
        except LeapmotorError as err:
            raise ConfigEntryNotReady(str(err)) from err
        client.set_pinned_certificate(pinned)
        hass.config_entries.async_update_entry(
            entry,
            data={**entry.data, CONF_SERVER_CERT: base64.b64encode(pinned).decode("ascii")},
        )
    return client


async def async_setup_entry(hass: HomeAssistant, entry: LeapmotorConfigEntry) -> bool:
    """Set up one Leapmotor account."""
    store = _store(hass, entry.entry_id)
    stored = await store.async_load() or {}
    # A session obtained while the entry was created saves a second login.
    pending = hass.data.get(DATA_PENDING_SESSIONS, {}).pop(entry.unique_id, None)
    if pending is not None and not stored.get("session"):
        stored = {**stored, "session": pending}
    client = await _async_create_client(hass, entry, stored)
    coordinator = LeapmotorCoordinator(hass, entry, client, store, stored)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    coordinator.async_setup_listeners()

    # Options were just (re)loaded: a corrected PIN gets a fresh chance.
    for vin in coordinator.vehicles:
        ir.async_delete_issue(hass, DOMAIN, f"{ISSUE_PIN_REJECTED}_{vin}")
    ir.async_delete_issue(hass, DOMAIN, f"{ISSUE_SERVER_CERT}_{entry.entry_id}")

    await hass.config_entries.async_forward_entry_setups(entry, _platforms(entry))
    # The app pictures are not needed for the start; fetch them in the background.
    entry.async_create_background_task(
        hass, coordinator.async_load_pictures(), f"{DOMAIN} pictures {entry.entry_id}"
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: LeapmotorConfigEntry) -> bool:
    """Unload an account."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, _platforms(entry))
    if unloaded:
        await entry.runtime_data.async_shutdown()
    return unloaded


async def async_remove_entry(hass: HomeAssistant, entry: LeapmotorConfigEntry) -> None:
    """Forget the stored session, pictures and open issues of a removed account."""
    store = _store(hass, entry.entry_id)
    stored = await store.async_load() or {}
    vins = [
        str(item["vin"])
        for item in stored.get("vehicles") or []
        if isinstance(item, dict) and item.get("vin")
    ]
    if vins:
        await hass.async_add_executor_job(remove_pictures, picture_root(hass), vins)
    await store.async_remove()
    for issue in (ISSUE_APP_CERT, ISSUE_SERVER_CERT, ISSUE_SESSION_CONFLICT):
        ir.async_delete_issue(hass, DOMAIN, f"{issue}_{entry.entry_id}")


async def async_remove_config_entry_device(
    hass: HomeAssistant, entry: LeapmotorConfigEntry, device: dr.DeviceEntry
) -> bool:
    """Allow removing vehicles that are no longer part of the account."""
    coordinator = entry.runtime_data
    return not any(
        domain == DOMAIN and identifier in coordinator.vehicles
        for domain, identifier in device.identifiers
    )
