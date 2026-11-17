"""End-to-end tests of the cloud client against the local mock backend."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, date, datetime, timedelta

import aiohttp
import pytest
import pytest_asyncio

from leapmotor_api import (
    LeapmotorApiError,
    LeapmotorAuthError,
    LeapmotorCertificateError,
    LeapmotorCloudClient,
    LeapmotorCommandError,
    LeapmotorPermissionError,
    LeapmotorPinError,
    LeapmotorRateLimitError,
    LeapmotorServerIdentityError,
    SessionState,
    client as client_module,
    commands,
)
from leapmotor_api.pictures import extract_pictures
from leapmotor_api.tls import fetch_server_certificate

from .mock_cloud import PICTURE_LAYERS, PNG, MockCloud


@pytest_asyncio.fixture
async def cloud() -> AsyncIterator[MockCloud]:
    server = MockCloud()
    await server.start()
    yield server
    await server.stop()


@pytest_asyncio.fixture
async def http() -> AsyncIterator[aiohttp.ClientSession]:
    async with aiohttp.ClientSession() as session:
        yield session


def make_client(cloud: MockCloud, http: aiohttp.ClientSession, **overrides) -> LeapmotorCloudClient:
    options = {
        "username": cloud.email,
        "password": cloud.password,
        "app_cert_pem": cloud.app_cert_pem.decode(),
        "app_key_pem": cloud.app_key_pem.decode(),
        "device_id": "local-device-id",
        "base_url": cloud.url,
        "pinned_certificate": cloud.server_cert_der,
        "min_request_gap": 0.0,
    }
    options.update(overrides)
    return LeapmotorCloudClient(http, **options)


async def test_login_and_read_everything(cloud: MockCloud, http: aiohttp.ClientSession) -> None:
    client = make_client(cloud, http)
    sessions: list[SessionState | None] = []
    client.on_session_changed = sessions.append

    vehicles = await client.get_vehicles()
    assert [vehicle.vin for vehicle in vehicles] == [cloud.vin]
    vehicle = vehicles[0]
    assert vehicle.model == "C10" and not vehicle.is_shared
    assert vehicle.has_right(193) is True and vehicle.has_right(301) is False
    assert cloud.logins == 1
    assert sessions and sessions[-1] is client.session
    # The device id of the session comes from the token, not from the login.
    assert client.session is not None and client.session.device_id == cloud.device_id

    status = await client.get_status(vehicle)
    assert status["signal"]["1204"] == 65

    now = datetime.now(UTC)
    mileage = await client.get_mileage(vehicle, now - timedelta(days=7), now)
    assert mileage["totalEnergy"] == 512.4
    assert (await client.get_consumption_rank(vehicle))["rankResult"]["hundredKmEC"] == "17.6"
    assert (await client.get_energy_window(vehicle, now - timedelta(days=1), now))["acEC"] == "4.2"
    records = await client.get_charge_records(
        vehicle, date(2026, 11, 1), date(2026, 11, 8), reference=now
    )
    assert records["list"][0]["chargeInEnergy"] == 21.5
    assert await client.get_unread_count() == {"unread": 3}
    assert (await client.get_messages())["list"][0]["title"] == "Hello"
    assert (await client.get_software(vehicle))["currentVersion"]["generalVersion"] == "1.2.3"
    plan = await client.get_charge_plan(vehicle)
    assert plan["percent"] == 90 and plan["beginTime"] == "23:30" and plan["isEnable"] == 1
    key, package = await client.get_picture_package(vehicle)
    pictures = extract_pictures(package)
    assert key == "pic-key" and cloud.picture_downloads == 1
    assert len(pictures) == len(PICTURE_LAYERS)
    # The higher density wins; files without PNG signature or other names are ignored.
    assert pictures["carpic_body.png"] == PNG + b"carpic_body-xxhdpi"
    assert "carpic_fake.png" not in pictures and "carpic_body@3x.png" not in pictures
    assert cloud.logins == 1
    assert client.request_count == len(cloud.requests)


async def test_wrong_password_is_not_retried(cloud: MockCloud, http: aiohttp.ClientSession) -> None:
    client = make_client(cloud, http, password="wrong")
    with pytest.raises(LeapmotorAuthError) as info:
        await client.get_vehicles()
    assert "Incorrect account" in str(info.value)
    assert cloud.logins == 1
    # A second attempt right away is stopped locally, before it reaches the cloud.
    with pytest.raises(LeapmotorRateLimitError):
        await client.get_vehicles()
    assert cloud.logins == 1


async def test_login_budget(
    cloud: MockCloud, http: aiohttp.ClientSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(client_module, "LOGIN_MIN_INTERVAL", 0.0)
    client = make_client(cloud, http, password="wrong")
    for _ in range(client_module.LOGIN_BUDGET):
        with pytest.raises(LeapmotorAuthError):
            await client.login()
    with pytest.raises(LeapmotorRateLimitError):
        await client.login()
    assert cloud.logins == client_module.LOGIN_BUDGET


async def test_expired_token_is_refreshed(cloud: MockCloud, http: aiohttp.ClientSession) -> None:
    client = make_client(cloud, http)
    vehicle = (await client.get_vehicles())[0]
    cloud.expire_token()
    assert (await client.get_status(vehicle))["signal"]["1204"] == 65
    assert cloud.refreshes == 1 and cloud.logins == 1


async def test_failed_refresh_falls_back_to_login(
    cloud: MockCloud, http: aiohttp.ClientSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(client_module, "LOGIN_MIN_INTERVAL", 0.0)
    client = make_client(cloud, http)
    vehicle = (await client.get_vehicles())[0]
    cloud.expire_token()
    cloud.fail_refresh = True
    assert (await client.get_status(vehicle))["signal"]["1204"] == 65
    assert cloud.logins == 2


async def test_stored_session_avoids_login(cloud: MockCloud, http: aiohttp.ClientSession) -> None:
    first = make_client(cloud, http)
    await first.get_vehicles()
    assert first.session is not None
    stored = first.session.to_dict()

    second = make_client(cloud, http, session=SessionState.from_dict(stored))
    vehicle = (await second.get_vehicles())[0]
    assert (await second.get_status(vehicle))["signal"]["1204"] == 65
    assert cloud.logins == 1


async def test_status_falls_back_to_c10_endpoint(
    cloud: MockCloud, http: aiohttp.ClientSession
) -> None:
    cloud.car_type = "X99"
    cloud.status_404_for = {"x99"}
    client = make_client(cloud, http)
    vehicle = (await client.get_vehicles())[0]
    assert (await client.get_status(vehicle))["signal"]["1204"] == 65
    before = len(cloud.requests)
    await client.get_status(vehicle)
    # The working endpoint is remembered: one request instead of two.
    assert len(cloud.requests) == before + 1
    assert cloud.requests[-1].endswith("/status/get/c10")


async def test_b10_uses_c10_endpoint(cloud: MockCloud, http: aiohttp.ClientSession) -> None:
    cloud.car_type = "B10"
    cloud.status_404_for = {"b10"}
    client = make_client(cloud, http)
    vehicle = (await client.get_vehicles())[0]
    await client.get_status(vehicle)
    assert not any(path.endswith("/status/get/b10") for path in cloud.requests)


async def test_command_with_pin(cloud: MockCloud, http: aiohttp.ClientSession) -> None:
    client = make_client(cloud, http)
    vehicle = (await client.get_vehicles())[0]
    result = await client.send_command(vehicle, commands.lock(), cloud.pin)
    assert result.accepted and result.confirmed and result.remote_ctl_id == "ctl-1"
    assert cloud.commands == [{"cmdId": "110", "content": {"value": "lock"}}]
    assert cloud.cert_syncs == 1 and cloud.pin_checks == 1

    await client.send_command(vehicle, commands.charging(start=True), cloud.pin)
    assert cloud.commands[-1] == {"cmdId": "193", "content": {"value": "start"}}
    # The certificate is announced only once per session.
    assert cloud.cert_syncs == 1


async def test_command_without_pin(cloud: MockCloud, http: aiohttp.ClientSession) -> None:
    client = make_client(cloud, http)
    vehicle = (await client.get_vehicles())[0]
    command = commands.send_destination(name="Home", latitude=52.5, longitude=13.4)
    result = await client.send_command(vehicle, command)
    assert result.confirmed
    assert cloud.pin_checks == 0
    assert cloud.commands[-1]["content"]["addressname"] == "Home"


async def test_missing_and_wrong_pin(cloud: MockCloud, http: aiohttp.ClientSession) -> None:
    client = make_client(cloud, http)
    vehicle = (await client.get_vehicles())[0]
    with pytest.raises(LeapmotorPinError):
        await client.send_command(vehicle, commands.unlock())
    assert cloud.pin_checks == 0
    with pytest.raises(LeapmotorPinError):
        await client.send_command(vehicle, commands.unlock(), "0000")
    assert cloud.pin_checks == 1 and cloud.commands == []
    with pytest.raises(LeapmotorPinError):
        await client.verify_pin(vehicle, "0000")
    await client.verify_pin(vehicle, cloud.pin)


async def test_command_survives_expired_token(
    cloud: MockCloud, http: aiohttp.ClientSession
) -> None:
    client = make_client(cloud, http)
    vehicle = (await client.get_vehicles())[0]
    await client.send_command(vehicle, commands.lock(), cloud.pin)
    cloud.expire_token()
    result = await client.send_command(vehicle, commands.unlock(), cloud.pin)
    assert result.confirmed
    assert cloud.commands[-1]["content"] == {"value": "unlock"}
    assert cloud.refreshes == 1


async def test_command_errors(cloud: MockCloud, http: aiohttp.ClientSession) -> None:
    client = make_client(cloud, http)
    vehicle = (await client.get_vehicles())[0]
    with pytest.raises(LeapmotorPermissionError):
        await client.send_command(vehicle, commands.raw(999, {"value": "x"}), cloud.pin)
    cloud.result_after = 10_000
    result = await client.send_command(vehicle, commands.find_car(), cloud.pin)
    assert result.accepted and not result.confirmed


async def test_unconfirmed_command_can_skip_waiting(
    cloud: MockCloud, http: aiohttp.ClientSession
) -> None:
    client = make_client(cloud, http)
    vehicle = (await client.get_vehicles())[0]
    result = await client.send_command(
        vehicle, commands.find_car(), cloud.pin, wait_for_result=False
    )
    assert result.accepted and not result.confirmed and result.remote_ctl_id


async def test_permission_error_on_shared_car(
    cloud: MockCloud, http: aiohttp.ClientSession
) -> None:
    cloud.shared = True
    client = make_client(cloud, http)
    vehicle = (await client.get_vehicles())[0]
    assert vehicle.is_shared
    with pytest.raises(LeapmotorPermissionError):
        await client.get_software(vehicle)


async def test_wrong_app_certificate(cloud: MockCloud, http: aiohttp.ClientSession) -> None:
    other_cert, other_key, _ = cloud.pki.issue("somebody-else")
    client = make_client(
        cloud, http, app_cert_pem=other_cert.decode(), app_key_pem=other_key.decode()
    )
    with pytest.raises(LeapmotorCertificateError):
        await client.get_vehicles()
    assert cloud.logins == 0


async def test_server_certificate_pinning(cloud: MockCloud, http: aiohttp.ClientSession) -> None:
    assert await fetch_server_certificate("127.0.0.1", cloud.port) == cloud.server_cert_der
    client = make_client(cloud, http)
    vehicle = (await client.get_vehicles())[0]

    old = cloud.server_cert_der
    await cloud.replace_server_certificate()
    assert cloud.server_cert_der != old

    # Nobody accepts the new certificate: the request must not be sent.
    before = len(cloud.requests)
    with pytest.raises(LeapmotorServerIdentityError) as info:
        await client.get_status(vehicle)
    assert info.value.presented == cloud.server_cert_der
    assert len(cloud.requests) == before

    seen: list[tuple[bytes | None, bytes]] = []

    async def accept(previous: bytes | None, presented: bytes) -> bool:
        seen.append((previous, presented))
        return True

    client.on_server_certificate_changed = accept
    assert (await client.get_status(vehicle))["signal"]["1204"] == 65
    assert seen == [(old, cloud.server_cert_der)]
    assert client.pinned_certificate == cloud.server_cert_der


async def test_unverified_mode_ignores_certificate_changes(
    cloud: MockCloud, http: aiohttp.ClientSession
) -> None:
    client = make_client(cloud, http, verify_server=False)
    vehicle = (await client.get_vehicles())[0]
    await cloud.replace_server_certificate()
    assert (await client.get_status(vehicle))["signal"]["1204"] == 65


async def test_api_error_carries_details(cloud: MockCloud, http: aiohttp.ClientSession) -> None:
    client = make_client(cloud, http)
    vehicle = (await client.get_vehicles())[0]
    # A schedule type the account may not read is simply empty.
    assert await client.get_appointment(vehicle, "171") == {}
    # A broken signature is reported with the code of the backend.
    assert client.session is not None
    client.session.sign_ikm = "tampered"
    client.session._sign_key = None
    with pytest.raises(LeapmotorApiError) as info:
        await client.get_status(vehicle)
    assert info.value.code == 39 and info.value.http_status == 200
    assert not isinstance(info.value, (LeapmotorCommandError, LeapmotorAuthError))
