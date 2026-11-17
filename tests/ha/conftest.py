"""Fixtures for the Home Assistant tests.

These tests need ``pytest-homeassistant-custom-component`` (Python 3.14).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
import sys
from unittest.mock import AsyncMock, MagicMock

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
import pytest_socket

from custom_components.leapmotor_cloud.api import DEMO_PIN, DEMO_VIN
from custom_components.leapmotor_cloud.const import CONF_DEMO, CONF_PINS, DOMAIN

if sys.platform == "win32":
    # Windows event loops need a local TCP socket pair, but Home Assistant's test
    # plugin only allows Unix sockets. Keep its other protections (connections
    # only to 127.0.0.1, no DNS) and skip just the socket ban.
    pytest_socket.disable_socket = lambda allow_unix_socket=False: None


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Allow Home Assistant to load the integration from custom_components."""


@pytest.fixture(autouse=True)
def web_components_loaded(hass: HomeAssistant) -> None:
    """The frontend package is not installed here; pretend its integrations run."""
    hass.config.components.update({"http", "frontend", "file_upload"})
    hass.http = MagicMock()
    hass.http.async_register_static_paths = AsyncMock()


def entity_id(hass: HomeAssistant, platform: str, key: str, vin: str = DEMO_VIN) -> str:
    """Return the entity id of one entity of a vehicle."""
    found = er.async_get(hass).async_get_entity_id(platform, DOMAIN, f"{vin}_{key}")
    assert found is not None, f"{platform}.{key} does not exist"
    return found


async def unload(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """Unload an entry so that no timers outlive the test."""
    if entry.state is ConfigEntryState.LOADED:
        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()


@pytest.fixture
async def demo_entry(hass: HomeAssistant) -> AsyncIterator[MockConfigEntry]:
    """Set up the simulated vehicle."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Leapmotor Demo",
        unique_id="demo",
        data={CONF_DEMO: True},
        options={CONF_PINS: {DEMO_VIN: DEMO_PIN}},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    entry.runtime_data.client.command_delay = 0
    yield entry
    await unload(hass, entry)
