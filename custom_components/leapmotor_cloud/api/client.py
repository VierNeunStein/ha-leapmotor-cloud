"""Asynchronous client for the Leapmotor international cloud.

Design goals:

* be gentle to the backend: requests are serialised, logins are rare (the
  session is reused and refreshed) and strictly budgeted,
* never retry something that cannot succeed (wrong password, wrong PIN),
* verify the server by certificate pinning instead of not at all.
"""

from __future__ import annotations

import asyncio
from collections import deque
from collections.abc import Awaitable, Callable
from datetime import date, datetime, timedelta
import json
import logging
import secrets
import ssl
import time
from typing import Any
from urllib.parse import quote, urlsplit

import aiohttp

from . import crypto
from .const import (
    APP_CHANNEL,
    APP_DEVICE_TYPE,
    APP_LANGUAGE,
    APP_P12_ENC_ALG,
    APP_SOURCE,
    APP_VERSION,
    APPOINTMENT_CHARGE,
    DEFAULT_BASE_URL,
    LOGIN_POLICY_ID,
    PATH_APPOINTMENT,
    PATH_CERT_SYNC,
    PATH_CHARGE_RECORDS,
    PATH_CONSUMPTION_RANK,
    PATH_CONSUMPTION_WINDOW,
    PATH_LOGIN,
    PATH_MESSAGE_LIST,
    PATH_MESSAGE_UNREAD,
    PATH_MILEAGE,
    PATH_PICTURE_KEY,
    PATH_PICTURE_PACKAGE,
    PATH_PIN_VERIFY,
    PATH_REMOTE_CTL,
    PATH_REMOTE_RESULT,
    PATH_SOFTWARE,
    PATH_TOKEN_REFRESH,
    PATH_VEHICLE_LIST,
    PATH_VEHICLE_STATUS,
    STATUS_PATH_ALIASES,
    STATUS_PATH_FALLBACK,
)
from .errors import (
    LeapmotorApiError,
    LeapmotorAuthError,
    LeapmotorCertificateError,
    LeapmotorCommandError,
    LeapmotorConnectionError,
    LeapmotorError,
    LeapmotorPermissionError,
    LeapmotorPinError,
    LeapmotorRateLimitError,
    LeapmotorServerIdentityError,
    LeapmotorTokenError,
)
from .models import CommandResult, RemoteCommand, SessionState, VehicleInfo
from .parser import normalize_charge_plan, status_has_data
from .tls import build_ssl_context, fetch_server_certificate

_LOGGER = logging.getLogger(__name__)

DEFAULT_USER_AGENT = "leapmotor-cloud-client"
_FORM = "application/x-www-form-urlencoded; charset=UTF-8"

# Login answers that mean "wrong email or password" (retrying is pointless).
_CREDENTIAL_CODES = frozenset({"21", "302010108"})
_CREDENTIAL_WORDS = ("password", "passwort", "account", "credential", "not registered", "not exist")

# Login protection: a login replaces the session of the same account on other
# devices, and repeated logins are what gets accounts locked.
LOGIN_MIN_INTERVAL = 120.0
LOGIN_BUDGET = 4
LOGIN_BUDGET_WINDOW = 6 * 3600.0

ServerCertificateCallback = Callable[[bytes | None, bytes], Awaitable[bool]]


def _token_problem(status: int, message: str) -> bool:
    lowered = message.lower()
    if status == 401:
        return True
    if "token" in lowered and any(
        marker in lowered
        for marker in ("invalid", "expire", "unauthorized", "not valid", "illegal", "error", "fail")
    ):
        return True
    return any(
        marker in lowered for marker in ("log in again", "login again", "re-login", "relogin")
    )


def _rate_limited(status: int, message: str) -> bool:
    lowered = message.lower()
    return status == 429 or any(
        marker in lowered
        for marker in (
            "too many",
            "too frequent",
            "frequently",
            "rate limit",
            "try again later",
            "locked",
        )
    )


def _gmt_offset(moment: datetime) -> str:
    offset = moment.utcoffset() or timedelta(0)
    minutes = int(offset.total_seconds() // 60)
    sign = "+" if minutes >= 0 else "-"
    minutes = abs(minutes)
    return f"GMT{sign}{minutes // 60:02d}:{minutes % 60:02d}"


class LeapmotorCloudClient:
    """Talk to the Leapmotor cloud on behalf of one account."""

    def __init__(
        self,
        http: aiohttp.ClientSession,
        *,
        username: str,
        password: str,
        app_cert_pem: str,
        app_key_pem: str,
        device_id: str,
        base_url: str = DEFAULT_BASE_URL,
        pinned_certificate: bytes | None = None,
        verify_server: bool = True,
        session: SessionState | None = None,
        request_timeout: float = 30.0,
        min_request_gap: float = 0.3,
        user_agent: str = DEFAULT_USER_AGENT,
    ) -> None:
        self._http = http
        self._user_agent = user_agent
        self._username = username
        self._password = password
        self._app_cert_pem = app_cert_pem
        self._app_key_pem = app_key_pem
        self._login_device_id = device_id
        self._base_url = base_url.rstrip("/")
        self._pinned = pinned_certificate if verify_server else None
        self._verify_server = verify_server
        self._session = session
        self._timeout = aiohttp.ClientTimeout(total=request_timeout)
        self._min_gap = min_request_gap

        self._contexts: dict[str, ssl.SSLContext] = {}
        self._request_lock = asyncio.Lock()
        self._auth_lock = asyncio.Lock()
        self._command_lock = asyncio.Lock()
        self._last_request = 0.0
        self._login_times: deque[float] = deque(maxlen=LOGIN_BUDGET)
        self._cert_synced = False
        self._status_paths: dict[str, str] = {}
        self._vehicles: dict[str, VehicleInfo] = {}

        self.request_count = 0
        self.on_session_changed: Callable[[SessionState | None], None] | None = None
        self.on_server_certificate_changed: ServerCertificateCallback | None = None
        self.on_request: Callable[[str], None] | None = None

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_demo(self) -> bool:
        """Return whether this client simulates a vehicle."""
        return False

    @property
    def session(self) -> SessionState | None:
        """Return the current cloud session (for persistence)."""
        return self._session

    @property
    def pinned_certificate(self) -> bytes | None:
        """Return the pinned server certificate (DER)."""
        return self._pinned

    @property
    def host(self) -> tuple[str, int]:
        """Return host and port of the gateway."""
        parts = urlsplit(self._base_url)
        return parts.hostname or "", parts.port or 443

    def set_pinned_certificate(self, der: bytes | None) -> None:
        """Pin another server certificate (takes effect on new connections)."""
        self._pinned = der if self._verify_server else None
        self._contexts.clear()

    async def close(self) -> None:
        """Release resources. The HTTP session belongs to the caller."""
        self._contexts.clear()

    # ------------------------------------------------------------------
    # TLS
    # ------------------------------------------------------------------

    async def fetch_server_certificate(self) -> bytes:
        """Return the certificate the gateway currently presents (DER)."""
        host, port = self.host
        return await fetch_server_certificate(host, port)

    async def _context(self, kind: str) -> ssl.SSLContext:
        """Return the TLS context for the app or the account certificate."""
        context = self._contexts.get(kind)
        if context is not None:
            return context
        if kind == "app":
            cert, key = self._app_cert_pem, self._app_key_pem
        else:
            if self._session is None:
                raise LeapmotorTokenError("Not logged in")
            cert, key = self._session.account_cert_pem, self._session.account_key_pem
        if not cert or not key:
            raise LeapmotorCertificateError("The app certificate is missing")
        loop = asyncio.get_running_loop()
        context = await loop.run_in_executor(
            None, lambda: build_ssl_context(cert, key, pinned_certificate=self._pinned)
        )
        self._contexts[kind] = context
        return context

    async def _server_identity_changed(self, reason: str) -> None:
        """Handle a failed server verification; returns when a retry is allowed."""
        presented = await self.fetch_server_certificate()
        if self._pinned is not None and presented == self._pinned:
            raise LeapmotorServerIdentityError(
                f"Server verification failed although the certificate is the pinned one: {reason}"
            )
        accepted = False
        if self.on_server_certificate_changed is not None:
            accepted = await self.on_server_certificate_changed(self._pinned, presented)
        if not accepted:
            raise LeapmotorServerIdentityError(
                "The Leapmotor server presented a different certificate than the pinned one",
                presented=presented,
            )
        self.set_pinned_certificate(presented)

    # ------------------------------------------------------------------
    # Low-level request
    # ------------------------------------------------------------------

    def _headers(
        self,
        sign_fields: dict[str, str],
        *,
        login: bool,
        content_type: str,
    ) -> dict[str, str]:
        device_id = self._login_device_id
        if not login:
            if self._session is None:
                raise LeapmotorTokenError("Not logged in")
            device_id = self._session.device_id
        base = {
            "acceptLanguage": APP_LANGUAGE,
            "channel": APP_CHANNEL,
            "deviceId": device_id,
            "deviceType": APP_DEVICE_TYPE,
            "nonce": str(100000 + secrets.randbelow(9900000)),
            "source": APP_SOURCE,
            "timestamp": str(int(time.time() * 1000)),
            "version": APP_VERSION,
        }
        fields = {**base, **sign_fields}
        if login:
            sign = crypto.login_signature(fields)
        else:
            assert self._session is not None
            sign = crypto.request_signature(self._session.sign_key, fields)
        headers = {
            **base,
            "X-P12_ENC_ALG": APP_P12_ENC_ALG,
            "sign": sign,
            "Content-Type": content_type,
            "User-Agent": self._user_agent,
        }
        if not login:
            assert self._session is not None
            headers["userId"] = self._session.user_id
            headers["token"] = self._session.token
        return headers

    async def _send(
        self,
        path: str,
        *,
        label: str,
        body: dict[str, Any] | None = None,
        sign: dict[str, Any] | None = None,
        cert: str = "account",
        login: bool = False,
        as_json: bool = False,
    ) -> tuple[int, bytes]:
        """Send one POST and return ``(http_status, raw_body)``."""
        body = body or {}
        sign_fields = {key: str(value) for key, value in (body if sign is None else sign).items()}
        if as_json:
            payload = json.dumps(body, separators=(",", ":")).encode("utf-8")
            content_type = "application/json"
        else:
            payload = "&".join(
                f"{key}={quote(str(value), safe='')}" for key, value in body.items()
            ).encode("utf-8")
            content_type = _FORM
        url = f"{self._base_url}{path}"

        async with self._request_lock:
            for attempt in (1, 2):
                context = await self._context(cert)
                headers = self._headers(sign_fields, login=login, content_type=content_type)
                wait = self._min_gap - (time.monotonic() - self._last_request)
                if wait > 0:
                    await asyncio.sleep(wait)
                self.request_count += 1
                if self.on_request is not None:
                    self.on_request(label)
                try:
                    async with self._http.post(
                        url, data=payload, headers=headers, ssl=context, timeout=self._timeout
                    ) as response:
                        raw = await response.read()
                        status = response.status
                except aiohttp.ClientConnectorCertificateError as err:
                    self._last_request = time.monotonic()
                    if attempt == 2:
                        raise LeapmotorServerIdentityError(
                            f"Server certificate verification failed: {err}"
                        ) from err
                    await self._server_identity_changed(str(err))
                    continue
                except aiohttp.ClientSSLError as err:
                    self._last_request = time.monotonic()
                    raise LeapmotorCertificateError(
                        f"TLS handshake failed ({label}); the client certificate was probably "
                        f"rejected: {err}"
                    ) from err
                except (aiohttp.ClientError, TimeoutError, OSError) as err:
                    self._last_request = time.monotonic()
                    raise LeapmotorConnectionError(
                        f"Request failed ({label}): {type(err).__name__}: {err}"
                    ) from err
                self._last_request = time.monotonic()
                _LOGGER.debug("%s -> HTTP %s (%d bytes)", label, status, len(raw))
                return status, raw
        raise LeapmotorConnectionError(f"Request failed ({label})")  # pragma: no cover

    async def _call(
        self,
        path: str,
        *,
        label: str,
        body: dict[str, Any] | None = None,
        sign: dict[str, Any] | None = None,
        cert: str = "account",
        login: bool = False,
        as_json: bool = False,
    ) -> dict[str, Any]:
        """Send one request and return the decoded, validated response."""
        status, raw = await self._send(
            path, label=label, body=body, sign=sign, cert=cert, login=login, as_json=as_json
        )
        text = raw.decode("utf-8", errors="replace")
        try:
            payload = json.loads(text)
        except ValueError:
            payload = None
        if not isinstance(payload, dict):
            snippet = " ".join(text.split())[:120]
            if status in (400, 403, 495, 496) and login:
                raise LeapmotorCertificateError(
                    f"The server rejected the app certificate (HTTP {status}: {snippet})"
                )
            if status == 401:
                raise LeapmotorTokenError("Session rejected", http_status=status, endpoint=label)
            if status == 429:
                raise LeapmotorRateLimitError(
                    "Too many requests", http_status=status, endpoint=label
                )
            raise LeapmotorApiError(
                f"Unexpected answer from the server (HTTP {status}: {snippet})",
                http_status=status,
                endpoint=label,
            )

        code = payload.get("code", payload.get("result"))
        if status == 200 and code in (0, "0"):
            return payload

        message = str(payload.get("message") or payload.get("msg") or f"HTTP {status}, code {code}")
        details = {"code": code, "http_status": status, "endpoint": label}
        _LOGGER.debug("%s failed: HTTP %s code=%s message=%s", label, status, code, message)
        if login:
            if _rate_limited(status, message):
                raise LeapmotorRateLimitError(message, **details)
            lowered = message.lower()
            if str(code) in _CREDENTIAL_CODES or any(word in lowered for word in _CREDENTIAL_WORDS):
                raise LeapmotorAuthError(message, **details)
            raise LeapmotorApiError(message, **details)
        if _token_problem(status, message):
            raise LeapmotorTokenError(message, **details)
        if _rate_limited(status, message):
            raise LeapmotorRateLimitError(message, **details)
        if str(code) == "40" or "permission" in message.lower():
            raise LeapmotorPermissionError(message, **details)
        raise LeapmotorApiError(message, **details)

    # ------------------------------------------------------------------
    # Session handling
    # ------------------------------------------------------------------

    def _set_session(self, session: SessionState | None) -> None:
        self._session = session
        self._contexts.pop("account", None)
        self._cert_synced = False
        if self.on_session_changed is not None:
            self.on_session_changed(session)

    def _check_login_budget(self) -> None:
        now = time.monotonic()
        if self._login_times and now - self._login_times[-1] < LOGIN_MIN_INTERVAL:
            raise LeapmotorRateLimitError(
                "Login postponed: the last login was less than two minutes ago",
                endpoint="login",
            )
        recent = [moment for moment in self._login_times if now - moment < LOGIN_BUDGET_WINDOW]
        if len(recent) >= LOGIN_BUDGET:
            raise LeapmotorRateLimitError(
                "Login budget exhausted: too many logins were needed recently. The account is "
                "probably used on another device at the same time; use a second account that "
                "the vehicle is shared with.",
                endpoint="login",
            )

    async def login(self) -> SessionState:
        """Log in with email and password and install a fresh session."""
        self._check_login_budget()
        self._login_times.append(time.monotonic())
        body = {
            "isRecoverAcct": "0",
            "password": self._password,
            "policyId": LOGIN_POLICY_ID,
            "loginMethod": "1",
            "email": self._username,
        }
        payload = await self._call(PATH_LOGIN, label="login", body=body, cert="app", login=True)
        data = payload.get("data") or {}
        token = str(data.get("token") or "")
        if not token or data.get("id") is None:
            raise LeapmotorApiError("Login answer is incomplete", endpoint="login")

        passwords: list[str] = []
        if data.get("uid") is not None:
            try:
                passwords.append(crypto.derive_p12_password(data["id"], str(data["uid"])))
            except (ValueError, UnicodeError):
                _LOGGER.debug("Could not derive the account certificate password")
        cert_pem, key_pem = crypto.load_account_certificate(
            str(data.get("base64Cert") or ""), passwords
        )
        session = SessionState(
            token=token,
            user_id=str(data["id"]),
            device_id=crypto.session_device_id(token, self._login_device_id),
            sign_ikm=str(data.get("signIkm") or ""),
            sign_salt=str(data.get("signSalt") or ""),
            sign_info=str(data.get("signInfo") or ""),
            account_cert_pem=cert_pem.decode("ascii"),
            account_key_pem=key_pem.decode("ascii"),
            refresh_token=str(data.get("refreshToken") or "") or None,
        )
        self._set_session(session)
        _LOGGER.debug("Logged in to the Leapmotor cloud")
        return session

    async def refresh_token(self) -> None:
        """Exchange the refresh token for a new session token."""
        session = self._session
        if session is None or not session.refresh_token:
            raise LeapmotorTokenError("No refresh token available")
        payload = await self._call(
            PATH_TOKEN_REFRESH,
            label="token refresh",
            body={"refreshToken": session.refresh_token},
        )
        data = payload.get("data") or {}
        token = str(data.get("token") or "")
        if not token:
            raise LeapmotorTokenError("Token refresh returned no token")
        session.token = token
        session.refresh_token = str(data.get("refreshToken") or "") or session.refresh_token
        session.refreshed_at = time.time()
        self._cert_synced = False
        if self.on_session_changed is not None:
            self.on_session_changed(session)
        _LOGGER.debug("Leapmotor session token refreshed")

    async def ensure_session(self) -> None:
        """Make sure a session exists; refresh it shortly before it expires."""
        async with self._auth_lock:
            if self._session is None:
                await self.login()
                return
            expiry = crypto.token_expiry(self._session.token)
            if expiry is not None and expiry - time.time() < 300:
                await self._recover(None)

    async def _recover(self, failed_token: str | None) -> None:
        """Get a working session again: refresh first, full login as fallback."""
        if (
            failed_token is not None
            and self._session is not None
            and self._session.token != failed_token
        ):
            return  # another task already renewed the session
        if self._session is not None and self._session.refresh_token:
            try:
                await self.refresh_token()
            except LeapmotorRateLimitError:
                raise
            except LeapmotorError as err:
                _LOGGER.debug("Token refresh failed (%s); logging in again", err)
            else:
                return
        self._set_session(None)
        await self.login()

    async def _authed(
        self,
        path: str,
        *,
        label: str,
        body: dict[str, Any] | None = None,
        sign: dict[str, Any] | None = None,
        cert: str = "account",
        as_json: bool = False,
    ) -> dict[str, Any]:
        """Call an endpoint that needs a session; renew the session once if needed."""
        await self.ensure_session()
        assert self._session is not None
        token = self._session.token
        try:
            return await self._call(
                path, label=label, body=body, sign=sign, cert=cert, as_json=as_json
            )
        except LeapmotorTokenError:
            async with self._auth_lock:
                await self._recover(token)
        return await self._call(path, label=label, body=body, sign=sign, cert=cert, as_json=as_json)

    # ------------------------------------------------------------------
    # Read-only data
    # ------------------------------------------------------------------

    async def get_vehicles(self) -> list[VehicleInfo]:
        """Return the vehicles owned by or shared with the account."""
        payload = await self._authed(PATH_VEHICLE_LIST, label="vehicle list")
        data = payload.get("data") or {}
        vehicles: list[VehicleInfo] = []
        for bucket, shared in (("bindcars", False), ("sharedcars", True)):
            for item in data.get(bucket) or []:
                if isinstance(item, dict) and item.get("vin"):
                    vehicles.append(VehicleInfo.from_api(item, is_shared=shared))
        self._vehicles = {vehicle.vin: vehicle for vehicle in vehicles}
        return vehicles

    async def get_status(self, vehicle: VehicleInfo) -> dict[str, Any]:
        """Return the raw status payload (``data``) of one vehicle."""
        model = vehicle.model.lower()
        segment = self._status_paths.get(model) or STATUS_PATH_ALIASES.get(model, model)
        body = {"vin": vehicle.vin}
        try:
            payload = await self._authed(
                PATH_VEHICLE_STATUS.format(model=segment), label="vehicle status", body=body
            )
        except LeapmotorApiError as err:
            if err.http_status != 404 or segment == STATUS_PATH_FALLBACK:
                raise
            # Unknown models are usually served by the endpoint of the C10.
            payload = await self._authed(
                PATH_VEHICLE_STATUS.format(model=STATUS_PATH_FALLBACK),
                label="vehicle status",
                body=body,
            )
            segment = STATUS_PATH_FALLBACK
            _LOGGER.info(
                "Model %s has no status endpoint of its own; using the one of the C10",
                vehicle.model,
            )
        self._status_paths[model] = segment
        data = payload.get("data")
        if vehicle.is_shared and vehicle.car_id and not status_has_data(data):
            try:
                payload = await self._authed(
                    PATH_VEHICLE_STATUS.format(model=segment),
                    label="vehicle status",
                    body={"vin": vehicle.vin, "carId": vehicle.car_id},
                    sign=body,
                )
            except LeapmotorApiError:
                pass
            else:
                if status_has_data(payload.get("data")):
                    data = payload.get("data")
        return data if isinstance(data, dict) else {}

    async def get_mileage(
        self, vehicle: VehicleInfo, begin: datetime, end: datetime
    ) -> dict[str, Any]:
        """Return totals and per-day mileage/energy for a time window."""
        body = {
            "endtime": str(int(end.timestamp() * 1000)),
            "begintime": str(int(begin.timestamp() * 1000)),
            "vin": vehicle.vin,
        }
        payload = await self._authed(PATH_MILEAGE, label="mileage", body=body)
        return payload.get("data") or {}

    async def get_consumption_rank(self, vehicle: VehicleInfo) -> dict[str, Any]:
        """Return the average consumption of the last weeks."""
        payload = await self._authed(
            PATH_CONSUMPTION_RANK, label="consumption rank", body={"carvin": vehicle.vin}
        )
        return payload.get("data") or {}

    async def get_energy_window(
        self, vehicle: VehicleInfo, begin: datetime, end: datetime
    ) -> dict[str, Any]:
        """Return the energy split (driving / climate / other) of a time window."""
        body = {
            "endtime": str(int(end.timestamp())),
            "begintime": str(int(begin.timestamp())),
            "carvin": vehicle.vin,
        }
        payload = await self._authed(PATH_CONSUMPTION_WINDOW, label="energy window", body=body)
        return payload.get("data") or {}

    async def get_charge_records(
        self, vehicle: VehicleInfo, start: date, end: date, *, reference: datetime | None = None
    ) -> dict[str, Any]:
        """Return recent charging sessions."""
        body = {
            "vin": vehicle.vin,
            "timeZone": _gmt_offset(reference) if reference else "GMT+00:00",
            "startTime": start.isoformat(),
            "endTime": end.isoformat(),
            "pageNum": 1,
            "pageSize": 10,
        }
        payload = await self._authed(
            PATH_CHARGE_RECORDS, label="charge records", body=body, as_json=True
        )
        return payload.get("data") or {}

    async def get_unread_count(self) -> Any:
        """Return the unread-message counter payload."""
        payload = await self._authed(PATH_MESSAGE_UNREAD, label="unread messages")
        return payload.get("data")

    async def get_messages(self, page_size: int = 1) -> Any:
        """Return the newest messages."""
        payload = await self._authed(
            PATH_MESSAGE_LIST, label="messages", body={"pageNo": "1", "pageSize": str(page_size)}
        )
        return payload.get("data")

    async def get_software(self, vehicle: VehicleInfo) -> dict[str, Any]:
        """Return software version information (owner accounts only)."""
        payload = await self._authed(PATH_SOFTWARE, label="software", body={"vin": vehicle.vin})
        return payload.get("data") or {}

    async def get_appointment(self, vehicle: VehicleInfo, cmd_id: str) -> dict[str, Any]:
        """Return a stored schedule (charging plan, climate timer, ...)."""
        try:
            payload = await self._authed(
                PATH_APPOINTMENT, label="appointment", body={"vin": vehicle.vin, "cmdId": cmd_id}
            )
        except LeapmotorPermissionError:
            return {}
        data = payload.get("data")
        if isinstance(data, str):
            try:
                data = json.loads(data) if data else {}
            except ValueError:
                data = {}
        return data if isinstance(data, dict) else {}

    async def get_charge_plan(self, vehicle: VehicleInfo) -> dict[str, Any]:
        """Return the stored charging plan with normalised keys."""
        return normalize_charge_plan(await self.get_appointment(vehicle, APPOINTMENT_CHARGE))

    async def get_picture_package(self, vehicle: VehicleInfo) -> tuple[str, bytes] | None:
        """Return the picture key and the ZIP package with the app's pictures of the vehicle.

        Two requests; the result never changes for a vehicle, so callers
        should keep it.
        """
        await self.ensure_session()
        assert self._session is not None
        payload = await self._authed(
            PATH_PICTURE_KEY,
            label="picture key",
            body={"deviceID": self._session.device_id, "vin": vehicle.vin},
        )
        key = (payload.get("data") or {}).get("key")
        if not key:
            return None
        status, raw = await self._send(
            PATH_PICTURE_PACKAGE, label="picture package", body={"key": str(key)}
        )
        if status != 200 or not raw.startswith(b"PK"):
            _LOGGER.debug("Picture package not available (HTTP %s)", status)
            return None
        return str(key), raw

    # ------------------------------------------------------------------
    # Remote control
    # ------------------------------------------------------------------

    async def _sync_certificate(self) -> None:
        """Announce the account certificate once per session (needs the app certificate)."""
        if self._cert_synced:
            return
        await self._authed(PATH_CERT_SYNC, label="certificate sync", cert="app")
        self._cert_synced = True

    async def verify_pin(self, vehicle: VehicleInfo, pin: str) -> None:
        """Check the vehicle PIN against the cloud without sending a command."""
        async with self._command_lock:
            await self.ensure_session()
            for attempt in (1, 2):
                # Sync first: it may renew the token the PIN is encrypted with.
                await self._sync_certificate()
                assert self._session is not None
                token = self._session.token
                try:
                    await self._verify_pin(vehicle, self._encrypted_pin(pin))
                except LeapmotorTokenError:
                    if attempt == 2:
                        raise
                    async with self._auth_lock:
                        await self._recover(token)
                else:
                    return

    def _encrypted_pin(self, pin: str) -> str:
        assert self._session is not None
        return crypto.encrypt_pin(pin, self._session.token)

    async def _verify_pin(self, vehicle: VehicleInfo, encrypted: str) -> None:
        try:
            await self._call(
                PATH_PIN_VERIFY,
                label="pin verify",
                body={"operatePassword": encrypted, "vin": vehicle.vin},
            )
        except (LeapmotorTokenError, LeapmotorRateLimitError, LeapmotorPermissionError):
            raise
        except LeapmotorApiError as err:
            raise LeapmotorPinError(
                str(err), code=err.code, http_status=err.http_status, endpoint=err.endpoint
            ) from err

    async def send_command(
        self,
        vehicle: VehicleInfo,
        command: RemoteCommand,
        pin: str | None = None,
        *,
        wait_for_result: bool = True,
    ) -> CommandResult:
        """Send a remote command and wait until the vehicle confirms it."""
        if command.requires_pin and not pin:
            raise LeapmotorPinError("No vehicle PIN configured", endpoint=command.name)

        async with self._command_lock:
            await self.ensure_session()
            body: dict[str, Any] = {
                "cmdContent": command.content,
                "vin": vehicle.vin,
                "cmdId": command.cmd_id,
            }
            for attempt in (1, 2):
                if command.requires_pin:
                    # Sync first: it may renew the token the PIN is encrypted with.
                    await self._sync_certificate()
                assert self._session is not None
                token = self._session.token
                try:
                    if command.requires_pin:
                        assert pin is not None
                        encrypted = self._encrypted_pin(pin)
                        await self._verify_pin(vehicle, encrypted)
                        body["operatePassword"] = encrypted
                    payload = await self._call(
                        PATH_REMOTE_CTL, label=f"command {command.name}", body=body
                    )
                    break
                except LeapmotorTokenError:
                    # The PIN is encrypted with the token: renew and start over once.
                    if attempt == 2:
                        raise
                    async with self._auth_lock:
                        await self._recover(token)
                except LeapmotorPermissionError:
                    raise
                except LeapmotorPinError:
                    raise
                except LeapmotorRateLimitError:
                    raise
                except LeapmotorApiError as err:
                    raise LeapmotorCommandError(
                        str(err), code=err.code, http_status=err.http_status, endpoint=err.endpoint
                    ) from err

            data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
            remote_ctl_id = data.get("remoteCtlId")
            if not remote_ctl_id or not wait_for_result:
                return CommandResult(
                    command.name,
                    accepted=True,
                    confirmed=not remote_ctl_id,
                    remote_ctl_id=str(remote_ctl_id) if remote_ctl_id else None,
                    message=str(payload.get("message") or "") or None,
                )
            confirmed, last = await self._wait_for_result(
                str(remote_ctl_id),
                timeout_ms=data.get("queryRemoteCtlResultTimeout"),
                interval_ms=data.get("queryInterval"),
            )
            return CommandResult(
                command.name,
                accepted=True,
                confirmed=confirmed,
                remote_ctl_id=str(remote_ctl_id),
                message=None if confirmed else f"last result: {last!r}",
            )

    async def _wait_for_result(
        self, remote_ctl_id: str, *, timeout_ms: Any, interval_ms: Any
    ) -> tuple[bool, Any]:
        """Poll until the vehicle confirmed the command or the time is up."""
        try:
            timeout = min(max(float(timeout_ms or 30000) / 1000.0, 5.0), 90.0)
        except (TypeError, ValueError):
            timeout = 30.0
        try:
            interval = min(max(float(interval_ms or 2000) / 1000.0, 1.0), 10.0)
        except (TypeError, ValueError):
            interval = 2.0
        deadline = time.monotonic() + timeout
        last: Any = None
        while True:
            try:
                payload = await self._authed(
                    PATH_REMOTE_RESULT, label="command result", body={"remoteCtlId": remote_ctl_id}
                )
            except LeapmotorConnectionError as err:
                _LOGGER.debug("Command result query failed: %s", err)
            except (LeapmotorAuthError, LeapmotorRateLimitError):
                raise
            except LeapmotorApiError as err:
                raise LeapmotorCommandError(
                    str(err), code=err.code, http_status=err.http_status, endpoint=err.endpoint
                ) from err
            else:
                last = payload.get("data")
                if last in (1, "1", True):
                    return True, last
            if time.monotonic() + interval >= deadline:
                return False, last
            await asyncio.sleep(interval)
