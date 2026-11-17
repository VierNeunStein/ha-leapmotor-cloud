"""The integration talking to the local stand-in of the Leapmotor cloud."""

from __future__ import annotations

import base64
from collections.abc import AsyncIterator
from unittest.mock import MagicMock

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.http import KEY_HASS
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.leapmotor_cloud.const import DOMAIN
from custom_components.leapmotor_cloud.picture_store import (
    LeapmotorPictureView,
    picture_key,
    picture_root,
)

from ..mock_cloud import PICTURE_LAYERS, PNG, MockCloud
from .conftest import entity_id, unload


@pytest.fixture
async def cloud(socket_enabled: None) -> AsyncIterator[MockCloud]:
    server = MockCloud()
    await server.start()
    yield server
    await server.stop()


def make_entry(cloud: MockCloud, **options: object) -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        unique_id=cloud.email,
        title=f"Leapmotor ({cloud.email})",
        data={
            "username": cloud.email,
            "password": cloud.password,
            "device_id": "f" * 32,
            "app_cert": cloud.app_cert_pem.decode(),
            "app_key": cloud.app_key_pem.decode(),
            "base_url": cloud.url,
            "server_cert": base64.b64encode(cloud.server_cert_der).decode(),
        },
        options={"pins": {cloud.vin: cloud.pin}, **options},
    )


async def test_cloud_vehicle(hass: HomeAssistant, cloud: MockCloud) -> None:
    entry = make_entry(cloud)
    entry.add_to_hass(hass)
    try:
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        assert entry.state is ConfigEntryState.LOADED
        assert cloud.logins == 1

        assert hass.states.get(entity_id(hass, "sensor", "soc", cloud.vin)).state == "65"
        assert hass.states.get(entity_id(hass, "sensor", "range", cloud.vin)).state == "278"
        assert (
            hass.states.get(entity_id(hass, "sensor", "consumption_average", cloud.vin)).state
            == "17.6"
        )
        assert (
            hass.states.get(entity_id(hass, "sensor", "last_charge_energy", cloud.vin)).state
            == "21.5"
        )
        assert (
            hass.states.get(entity_id(hass, "sensor", "charging_state", cloud.vin)).state
            == "unplugged"
        )
        lock = entity_id(hass, "lock", "lock", cloud.vin)
        assert hass.states.get(lock).state == "locked"

        await hass.services.async_call("lock", "unlock", {"entity_id": lock}, blocking=True)
        assert cloud.commands[-1] == {"cmdId": "110", "content": {"value": "unlock"}}
        assert hass.states.get(lock).state == "unlocked"

        await hass.services.async_call(
            "number",
            "set_value",
            {"entity_id": entity_id(hass, "number", "charge_limit", cloud.vin), "value": 80},
            blocking=True,
        )
        assert cloud.commands[-1] == {
            "cmdId": "190",
            "content": {
                "chargeEnable": 0,
                "chargesoc": 80,
                "circulation": 1,
                "cycles": "1,1,1,1,1,1,1",
                "endtime": "08:00",
                "recharge": 0,
                "starttime": "22:00",
            },
        }

        # The app pictures are fetched once in the background and offered as layers.
        await hass.async_block_till_done(wait_background_tasks=True)
        picture = hass.states.get(entity_id(hass, "image", "picture", cloud.vin))
        assert picture is not None and picture.state not in ("unknown", "unavailable")
        layers = picture.attributes["layers"]
        assert len(layers) == len(PICTURE_LAYERS) and "carpic_leftfront_open.png" in layers
        path = picture.attributes["layer_path"]
        assert path.startswith("/api/leapmotor_cloud/picture/") and cloud.vin not in path
        assert cloud.picture_downloads == 1

        view = LeapmotorPictureView()
        request = MagicMock()
        request.app = {KEY_HASS: hass}
        key = path.rstrip("/").rsplit("/", 1)[-1]
        response = await view.get(request, key, "carpic_body.png")
        assert response.status == 200 and response.body == PNG + b"carpic_body-xxhdpi"
        assert response.headers["Cache-Control"].startswith("private")
        assert view.requires_auth
        for bad_key, bad_name in (
            (key, "../index.json"),
            (key, "index.json"),
            (key, "carpic_missing.png"),
            ("0" * 16, "carpic_body.png"),
            ("..", "carpic_body.png"),
        ):
            assert (await view.get(request, bad_key, bad_name)).status == 404

        # A restart reuses the stored session and the stored pictures.
        await unload(hass, entry)
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done(wait_background_tasks=True)
        assert entry.state is ConfigEntryState.LOADED
        assert cloud.logins == 1 and cloud.picture_downloads == 1
        picture = hass.states.get(entity_id(hass, "image", "picture", cloud.vin))
        assert picture.attributes["layers"] == layers
    finally:
        await unload(hass, entry)
        await hass.config_entries.async_remove(entry.entry_id)
        assert not (picture_root(hass) / picture_key(cloud.vin)).exists()


async def test_renewed_server_certificate_is_trusted(hass: HomeAssistant, cloud: MockCloud) -> None:
    # The test certificates expire within 30 days: a new one counts as a regular renewal.
    entry = make_entry(cloud)
    await cloud.replace_server_certificate()
    entry.add_to_hass(hass)
    try:
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        assert entry.state is ConfigEntryState.LOADED
        assert base64.b64decode(entry.data["server_cert"]) == cloud.server_cert_der
        assert (
            hass.states.get("persistent_notification.leapmotor_cloud_certificate_" + entry.entry_id)
            is None
        )
    finally:
        await unload(hass, entry)


async def test_changed_server_certificate_is_not_trusted(
    hass: HomeAssistant, cloud: MockCloud
) -> None:
    entry = make_entry(cloud, tls_mode="strict")
    await cloud.replace_server_certificate()
    entry.add_to_hass(hass)
    try:
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        assert entry.state is ConfigEntryState.SETUP_RETRY
        # Nothing, not even the login, reached the server.
        assert cloud.logins == 0 and cloud.requests == []
        issue = ir.async_get(hass).async_get_issue(
            DOMAIN, f"server_certificate_changed_{entry.entry_id}"
        )
        assert issue is not None and issue.is_fixable

        # The user trusts the new certificate in the repair flow.
        from custom_components.leapmotor_cloud.repairs import async_create_fix_flow

        flow = await async_create_fix_flow(hass, issue.issue_id, issue.data)
        flow.hass = hass
        flow.issue_id = issue.issue_id
        result = await flow.async_step_init()
        assert result["step_id"] == "confirm"
        assert result["description_placeholders"]["fingerprint"]
        result = await flow.async_step_confirm({})
        assert result["type"] == "create_entry"
        assert base64.b64decode(entry.data["server_cert"]) == cloud.server_cert_der
    finally:
        await unload(hass, entry)


async def test_unverified_mode(hass: HomeAssistant, cloud: MockCloud) -> None:
    entry = make_entry(cloud, tls_mode="off")
    await cloud.replace_server_certificate()
    entry.add_to_hass(hass)
    try:
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        assert entry.state is ConfigEntryState.LOADED
    finally:
        await unload(hass, entry)
