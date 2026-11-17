"""Config, options, reauthentication and repair flows."""

from __future__ import annotations

import base64
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, patch

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.leapmotor_cloud.api import (
    DEMO_VIN,
    LeapmotorAuthError,
    LeapmotorPinError,
    VehicleInfo,
)
from custom_components.leapmotor_cloud.const import DOMAIN

from .conftest import unload

VIN = "LTESTB10000000077"


def _certificate() -> tuple[str, str]:
    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "app")])
    now = datetime.now(UTC)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=365))
        .sign(key, hashes.SHA256())
    )
    return (
        cert.public_bytes(serialization.Encoding.PEM).decode(),
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ).decode(),
    )


class FakeClient:
    """Stands in for the cloud client during the flows."""

    instances: list[FakeClient] = []

    def __init__(self, _http: Any, **kwargs: Any) -> None:
        self.kwargs = kwargs
        self.session = None
        self.pinned: bytes | None = None
        self.pin_checks: list[str] = []
        FakeClient.instances.append(self)

    async def fetch_server_certificate(self) -> bytes:
        return b"server-certificate"

    def set_pinned_certificate(self, der: bytes) -> None:
        self.pinned = der

    async def get_vehicles(self) -> list[VehicleInfo]:
        if self.kwargs["password"] != "secret":
            raise LeapmotorAuthError("Incorrect account or password", code=21)
        return [VehicleInfo(vin=VIN, car_type="B10", nickname="Family car")]

    async def verify_pin(self, _vehicle: VehicleInfo, pin: str) -> None:
        self.pin_checks.append(pin)
        if pin != "4711":
            raise LeapmotorPinError("Operation password error", code=5001)


@pytest.fixture
def fake_client() -> Iterator[type[FakeClient]]:
    FakeClient.instances = []
    with (
        patch("custom_components.leapmotor_cloud.config_flow.LeapmotorCloudClient", FakeClient),
        patch("custom_components.leapmotor_cloud.async_setup_entry", AsyncMock(return_value=True)),
    ):
        yield FakeClient


async def test_demo_flow(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.MENU
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "demo"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {"demo": True}
    assert result["options"] == {"pins": {DEMO_VIN: "1234"}}
    await hass.async_block_till_done()
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    assert entry.state is config_entries.ConfigEntryState.LOADED
    await unload(hass, entry)


async def test_account_flow(hass: HomeAssistant, fake_client: type[FakeClient]) -> None:
    cert, key = _certificate()
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "account"}
    )
    assert result["step_id"] == "certificate"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["errors"] == {"base": "certificate_required"}
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"cert_text": cert, "key_text": _certificate()[1]}
    )
    assert result["errors"] == {"base": "invalid_certificate"}
    # A certificate pasted into a single line is repaired.
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"cert_text": cert.replace("\n", " "), "key_text": key}
    )
    assert result["step_id"] == "credentials"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"username": "Driver@Example.org", "password": "wrong"}
    )
    assert result["errors"] == {"base": "invalid_auth"}
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"username": "Driver@Example.org", "password": "secret"}
    )
    assert result["step_id"] == "pin"
    assert result["description_placeholders"] == {
        "vehicle": "Family car (Leapmotor B10)",
        "vin": VIN[-6:],
    }

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"pin": "1111"})
    assert result["errors"] == {"base": "invalid_pin"}
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"pin": "4711"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Leapmotor (Driver@Example.org)"
    data = result["data"]
    assert data["username"] == "Driver@Example.org" and data["password"] == "secret"
    assert data["app_cert"] == cert and data["app_key"] == key
    assert base64.b64decode(data["server_cert"]) == b"server-certificate"
    assert len(data["device_id"]) == 32
    assert result["options"] == {"pins": {VIN: "4711"}}
    assert result["result"].unique_id == "driver@example.org"
    assert fake_client.instances[-1].pinned == b"server-certificate"


async def test_account_flow_without_pin_and_duplicate(
    hass: HomeAssistant, fake_client: type[FakeClient]
) -> None:
    cert, key = _certificate()
    for expected in (FlowResultType.CREATE_ENTRY, FlowResultType.ABORT):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"next_step_id": "account"}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"cert_text": cert, "key_text": key}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"username": "driver@example.org", "password": "secret"}
        )
        if expected is FlowResultType.CREATE_ENTRY:
            result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
            assert result["type"] is FlowResultType.CREATE_ENTRY
            assert result["options"] == {"pins": {}}
            assert fake_client.instances[-1].pin_checks == []
        else:
            assert result["type"] is FlowResultType.ABORT
            assert result["reason"] == "already_configured"


async def test_too_many_wrong_pins_abort(
    hass: HomeAssistant, fake_client: type[FakeClient]
) -> None:
    cert, key = _certificate()
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "account"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"cert_text": cert, "key_text": key}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"username": "driver@example.org", "password": "secret"}
    )
    for _ in range(2):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {"pin": "0"})
        assert result["errors"] == {"base": "invalid_pin"}
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"pin": "0"})
    assert result["type"] is FlowResultType.ABORT and result["reason"] == "pin_attempts"


def _account_entry(cert: str, key: str) -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        unique_id="driver@example.org",
        title="Leapmotor (driver@example.org)",
        data={
            "username": "driver@example.org",
            "password": "old",
            "device_id": "a" * 32,
            "app_cert": cert,
            "app_key": key,
            "base_url": "https://example.invalid",
            "server_cert": base64.b64encode(b"old").decode(),
        },
        options={"pins": {VIN: "4711"}},
    )


async def test_reauth(hass: HomeAssistant, fake_client: type[FakeClient]) -> None:
    cert, key = _certificate()
    entry = _account_entry(cert, key)
    entry.add_to_hass(hass)
    result = await entry.start_reauth_flow(hass)
    assert result["step_id"] == "reauth_confirm"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"password": "nope"})
    assert result["errors"] == {"base": "invalid_auth"}
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"password": "secret"}
    )
    assert result["type"] is FlowResultType.ABORT and result["reason"] == "reauth_successful"
    assert entry.data["password"] == "secret"
    assert base64.b64decode(entry.data["server_cert"]) == b"server-certificate"
    # The device id is kept, so the backend sees the same "phone".
    assert fake_client.instances[-1].kwargs["device_id"] == "a" * 32


async def test_reconfigure(hass: HomeAssistant, fake_client: type[FakeClient]) -> None:
    cert, key = _certificate()
    entry = _account_entry(cert, key)
    entry.add_to_hass(hass)
    new_cert, new_key = _certificate()
    result = await entry.start_reconfigure_flow(hass)
    assert result["step_id"] == "reconfigure"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"password": "secret", "cert_text": new_cert, "key_text": new_key}
    )
    assert result["type"] is FlowResultType.ABORT and result["reason"] == "reconfigure_successful"
    assert entry.data["app_cert"] == new_cert and entry.data["password"] == "secret"


async def test_options_polling(hass: HomeAssistant, demo_entry: MockConfigEntry) -> None:
    result = await hass.config_entries.options.async_init(demo_entry.entry_id)
    assert result["type"] is FlowResultType.MENU
    assert result["menu_options"] == ["polling", "pins"]
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "polling"}
    )
    values = {
        "interval_active": 30,
        "interval_idle": 20,
        "interval_history": 60,
        "charger_power_threshold": 500,
        "daily_request_limit": 1500,
    }
    result = await hass.config_entries.options.async_configure(result["flow_id"], values)
    assert result["errors"] == {"interval_idle": "idle_below_active"}
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {**values, "interval_idle": 45}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert demo_entry.options["interval_idle"] == 45
    assert demo_entry.options["pins"] == {DEMO_VIN: "1234"}
    # The entry was reloaded with the new settings.
    assert demo_entry.runtime_data.interval_idle == 45
    demo_entry.runtime_data.client.command_delay = 0


async def test_options_pins(hass: HomeAssistant, demo_entry: MockConfigEntry) -> None:
    result = await hass.config_entries.options.async_init(demo_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "pins"}
    )
    assert result["step_id"] == "pins"
    assert result["description_placeholders"]["status"] == "✓"
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"pin": "9999"})
    assert result["errors"] == {"base": "invalid_pin"}
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"remove_pin": True}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert demo_entry.options["pins"] == {}
