"""Diagnostics download.

Everything that identifies the account, the vehicle or its position is
removed, so the file can be attached to a bug report.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant

from .const import CONF_APP_CERT, CONF_APP_KEY, CONF_DEVICE_ID, CONF_PINS, CONF_SERVER_CERT
from .coordinator import LeapmotorConfigEntry

TO_REDACT = {
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_APP_CERT,
    CONF_APP_KEY,
    CONF_DEVICE_ID,
    CONF_PINS,
    CONF_SERVER_CERT,
    "vin",
    "car_id",
    "nickname",
    "plate",
    "latitude",
    "longitude",
    "title",
    "last_message_title",
    "last_message_text",
    # raw position signals
    "2",
    "3",
    "2190",
    "2191",
    "3724",
    "3725",
    # Bluetooth key data
    "mac",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: LeapmotorConfigEntry
) -> dict[str, Any]:
    """Return redacted diagnostics for a config entry."""
    coordinator = entry.runtime_data
    vehicles = []
    for index, data in enumerate((coordinator.data or {}).values(), start=1):
        vehicles.append(
            {
                "vehicle": index,
                "info": data.info.as_dict(),
                "state": data.state,
                "extras": data.extras,
                "raw_status": data.raw,
                "polled_at": data.polled_at,
            }
        )
    return async_redact_data(
        {
            "entry": {"data": dict(entry.data), "options": dict(entry.options)},
            "demo": coordinator.client.is_demo,
            "polling": {
                "mode": coordinator.polling_mode,
                "interval": str(coordinator.update_interval),
                "interval_active_minutes": coordinator.interval_active,
                "interval_idle_minutes": coordinator.interval_idle,
                "interval_history_minutes": coordinator.interval_history,
                "requests_today": coordinator.requests_today,
                "daily_limit": coordinator.daily_limit,
                "last_success": coordinator.last_success,
                "last_error": coordinator.last_error,
            },
            "vehicles": vehicles,
        },
        TO_REDACT,
    )
