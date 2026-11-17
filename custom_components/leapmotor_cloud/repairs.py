"""Repair flows."""

from __future__ import annotations

import base64
import binascii
from typing import Any

from homeassistant.components.repairs import ConfirmRepairFlow, RepairsFlow
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import issue_registry as ir
import voluptuous as vol

from .const import CONF_SERVER_CERT, DOMAIN, ISSUE_SERVER_CERT


class TrustCertificateFlow(RepairsFlow):
    """Let the user trust the certificate the server presents now."""

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    async def async_step_init(self, user_input: dict[str, str] | None = None) -> FlowResult:
        """Start with the confirmation."""
        return await self.async_step_confirm()

    async def async_step_confirm(self, user_input: dict[str, str] | None = None) -> FlowResult:
        """Trust the certificate after a confirmation."""
        if user_input is None:
            issue = ir.async_get(self.hass).async_get_issue(DOMAIN, self.issue_id)
            return self.async_show_form(
                step_id="confirm",
                data_schema=vol.Schema({}),
                description_placeholders=issue.translation_placeholders if issue else None,
            )
        entry = self.hass.config_entries.async_get_entry(str(self._data.get("entry_id")))
        try:
            certificate = base64.b64decode(str(self._data.get("certificate") or ""), validate=True)
        except (ValueError, binascii.Error):
            certificate = b""
        if entry is None or not certificate:
            return self.async_abort(reason="not_available")
        self.hass.config_entries.async_update_entry(
            entry,
            data={**entry.data, CONF_SERVER_CERT: base64.b64encode(certificate).decode("ascii")},
        )
        self.hass.config_entries.async_schedule_reload(entry.entry_id)
        return self.async_create_entry(data={})


async def async_create_fix_flow(
    hass: HomeAssistant, issue_id: str, data: dict[str, Any] | None
) -> RepairsFlow:
    """Create the flow for a fixable issue."""
    if issue_id.startswith(ISSUE_SERVER_CERT) and data:
        return TrustCertificateFlow(data)
    return ConfirmRepairFlow()
