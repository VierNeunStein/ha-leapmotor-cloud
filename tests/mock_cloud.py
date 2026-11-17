"""A local stand-in for the Leapmotor cloud, used by the client tests.

It speaks TLS with client certificates and checks every request the way the
real backend is understood to do: right certificate for the endpoint, valid
token and a signature over headers and body.  The signature check is written
independently of the client code (it uses ``cryptography``'s HKDF).
"""

from __future__ import annotations

import base64
from datetime import UTC, datetime, timedelta
import hashlib
import hmac
import io
import json
from pathlib import Path
import ssl
import tempfile
import time
from typing import Any
from urllib.parse import parse_qsl
import zipfile

from aiohttp import web
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID

from leapmotor_api import crypto

BASE_HEADERS = (
    "acceptLanguage",
    "channel",
    "deviceId",
    "deviceType",
    "nonce",
    "source",
    "timestamp",
    "version",
)
PNG = b"\x89PNG\r\n\x1a\n" + b"demo-picture"

# Layer names as found in the app's picture package.
PICTURE_LAYERS = (
    "carpic_body",
    "carpic_hood_close",
    "carpic_leftfront_close",
    "carpic_leftfront_open",
    "carpic_leftbehind_close",
    "carpic_leftbehind_open",
    "carpic_rightfront_close",
    "carpic_rightfront_open",
    "carpic_rightbehind_close",
    "carpic_rightbehind_open",
    "carpic_leftfront_window_close",
    "carpic_leftbehind_window_close",
    "carpic_tailgate_open",
    "carpic_charge_open",
    *(f"carpic_charge{index}" for index in range(1, 16)),
    "carpic_for_tripsum",
)


def picture_package() -> bytes:
    """A package like the app's: two densities, plus files that must be ignored."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name in PICTURE_LAYERS:
            archive.writestr(f"android/xhdpi/{name}.png", PNG + name.encode())
            archive.writestr(f"android/xxhdpi/{name}.png", PNG + name.encode() + b"-xxhdpi")
        archive.writestr("android/xxhdpi/readme.txt", b"not a picture")
        archive.writestr("android/xxhdpi/carpic_fake.png", b"no png signature")
        archive.writestr("ios/carpic_body@3x.png", PNG + b"other naming")
    return buffer.getvalue()


def _name(common_name: str) -> x509.Name:
    return x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])


def _key() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _pem_key(key: rsa.RSAPrivateKey) -> bytes:
    return key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    )


class Pki:
    """A throw-away certificate authority with server and client certificates."""

    def __init__(self) -> None:
        self.ca_key = _key()
        now = datetime.now(UTC)
        self.ca_cert = (
            x509.CertificateBuilder()
            .subject_name(_name("Test Sub CA"))
            .issuer_name(_name("Test Sub CA"))
            .public_key(self.ca_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(days=1))
            .not_valid_after(now + timedelta(days=30))
            .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
            .sign(self.ca_key, hashes.SHA256())
        )

    def issue(
        self, common_name: str, *, server: bool = False
    ) -> tuple[bytes, bytes, x509.Certificate]:
        """Return ``(cert_pem, key_pem, certificate)``."""
        key = _key()
        now = datetime.now(UTC)
        builder = (
            x509.CertificateBuilder()
            .subject_name(_name(common_name))
            .issuer_name(self.ca_cert.subject)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(days=1))
            .not_valid_after(now + timedelta(days=30))
        )
        if server:
            import ipaddress

            builder = builder.add_extension(
                x509.SubjectAlternativeName(
                    [x509.DNSName("localhost"), x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]
                ),
                critical=False,
            )
        cert = builder.sign(self.ca_key, hashes.SHA256())
        return cert.public_bytes(serialization.Encoding.PEM), _pem_key(key), cert

    def account_p12(self, account_id: int, uid: str) -> str:
        """Return a base64 PKCS#12 protected the way the backend does it."""
        key = _key()
        now = datetime.now(UTC)
        cert = (
            x509.CertificateBuilder()
            .subject_name(_name(f"account-{account_id}"))
            .issuer_name(self.ca_cert.subject)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(days=1))
            .not_valid_after(now + timedelta(days=30))
            .sign(self.ca_key, hashes.SHA256())
        )
        password = crypto.derive_p12_password(account_id, uid).encode()
        blob = pkcs12.serialize_key_and_certificates(
            b"account", key, cert, None, serialization.BestAvailableEncryption(password)
        )
        return base64.b64encode(blob).decode()


class MockCloud:
    """The fake backend."""

    def __init__(self) -> None:
        self.pki = Pki()
        self.app_cert_pem, self.app_key_pem, _ = self.pki.issue("app-client")
        self.server_cert_pem, self.server_key_pem, server_cert = self.pki.issue(
            "localhost", server=True
        )
        self.server_cert_der = server_cert.public_bytes(serialization.Encoding.DER)

        self.email = "driver@example.org"
        self.password = "correct horse"
        self.pin = "4711"
        self.account_id = 900123
        self.uid = "a1b2c3d4e5f60718"
        self.vin = "LTESTVIN000000042"
        self.car_type = "C10"
        self.shared = False
        self.rights = "110,120,130,170,171,180,190,192,193,230,340"

        self.token: str | None = None
        self.refresh: str | None = None
        self.sign_material = ("", "", "")
        self.device_id = "server-device-id"
        self.logins = 0
        self.refreshes = 0
        self.cert_syncs = 0
        self.requests: list[str] = []
        self.commands: list[dict[str, Any]] = []
        self.pin_checks = 0
        self.picture_downloads = 0
        self.fail_refresh = False
        self.status_404_for: set[str] = set()
        self.result_after = 2
        self._result_polls: dict[str, int] = {}
        self.status_payload: dict[str, Any] = {
            "privacyGPS": 1,
            "signal": {
                "1204": 65,
                "100003": 65.3,
                "3260": 278,
                "1149": 0,
                "1178": 0.1,
                "1177": 424.9,
                "1200": 0,
                "1298": 1,
                "1010": 0,
                "1319": 0.0,
                "1318": 3030,
                "3": 40.85812,
                "2": 14.28319,
                "sts": int(time.time() * 1000),
            },
            "config": {
                "3": {
                    "percent": 100,
                    "isEnable": 0,
                    "beginTime": "22:00",
                    "endTime": "08:00",
                    "cycles": "1,1,1,1,1,1,1",
                    "circulation": 1,
                    "recharge": 0,
                }
            },
        }
        self.port = 0
        self._runner: web.AppRunner | None = None
        self._tmp: tempfile.TemporaryDirectory[str] | None = None

    # -- lifecycle ---------------------------------------------------------------

    @property
    def url(self) -> str:
        return f"https://127.0.0.1:{self.port}"

    def _ssl_context(self, cert_pem: bytes, key_pem: bytes) -> ssl.SSLContext:
        assert self._tmp is not None
        directory = Path(self._tmp.name)
        (directory / "server.pem").write_bytes(cert_pem)
        (directory / "server.key").write_bytes(key_pem)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(str(directory / "server.pem"), str(directory / "server.key"))
        context.verify_mode = ssl.CERT_OPTIONAL
        context.load_verify_locations(
            cadata=self.pki.ca_cert.public_bytes(serialization.Encoding.PEM).decode()
        )
        return context

    async def start(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        app = web.Application()
        app.router.add_post("/{tail:.*}", self._handle)
        self._runner = web.AppRunner(app)
        await self._runner.setup()
        site = web.TCPSite(
            self._runner,
            "127.0.0.1",
            self.port,
            ssl_context=self._ssl_context(self.server_cert_pem, self.server_key_pem),
        )
        await site.start()
        self.port = site._server.sockets[0].getsockname()[1]

    async def stop(self) -> None:
        if self._runner is not None:
            await self._runner.cleanup()
            self._runner = None
        if self._tmp is not None:
            self._tmp.cleanup()
            self._tmp = None

    async def replace_server_certificate(self) -> None:
        """Restart on the same port with a brand-new server certificate."""
        await self.stop()
        self.server_cert_pem, self.server_key_pem, server_cert = self.pki.issue(
            "localhost", server=True
        )
        self.server_cert_der = server_cert.public_bytes(serialization.Encoding.DER)
        await self.start()

    # -- helpers -----------------------------------------------------------------

    def expire_token(self) -> None:
        """Invalidate the access token (the refresh token keeps working)."""
        self.token = "expired-" + (self.token or "")

    def _new_token(self) -> str:
        payload = {
            "user_name": f"{self.email},{self.account_id},{self.device_id},x",
            "n": time.time_ns(),
        }
        body = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
        return f"eyJhbGciOiJIUzI1NiJ9.{body}." + hashlib.sha256(body.encode()).hexdigest()

    def _sign_key(self) -> bytes:
        ikm, salt, info = self.sign_material
        return HKDF(
            algorithm=hashes.SHA256(), length=32, salt=salt.encode(), info=info.encode()
        ).derive(ikm.encode())

    @staticmethod
    def _ok(data: Any = None) -> web.Response:
        return web.json_response(
            {"code": 0, "result": 0, "message": "Request successful", "data": data}
        )

    @staticmethod
    def _error(code: int, message: str, status: int = 200) -> web.Response:
        return web.json_response({"code": code, "message": message, "data": None}, status=status)

    @staticmethod
    def _client_cn(request: web.Request) -> str | None:
        peer = request.transport.get_extra_info("peercert") if request.transport else None
        if not peer:
            return None
        for rdn in peer.get("subject", ()):
            for key, value in rdn:
                if key == "commonName":
                    return str(value)
        return None

    # -- request handling ----------------------------------------------------------

    async def _handle(self, request: web.Request) -> web.Response:
        path = "/" + request.match_info["tail"]
        self.requests.append(path)
        raw = await request.read()
        content_type = request.headers.get("Content-Type", "")
        if content_type.startswith("application/json"):
            body = json.loads(raw or b"{}")
            params = {key: str(value) for key, value in body.items()}
        else:
            params = dict(parse_qsl(raw.decode(), keep_blank_values=True))
            body = params

        headers = request.headers
        if any(name not in headers for name in BASE_HEADERS) or "sign" not in headers:
            return self._error(39, "Missing signature headers")
        if headers.get("X-P12_ENC_ALG") != "1":
            return self._error(39, "Missing encryption header")
        fields = {name: headers[name] for name in BASE_HEADERS}
        fields.update(params)
        message = "".join(fields[key] for key in sorted(fields)).encode()
        cn = self._client_cn(request)

        if path.endswith("/acct/v1/login"):
            if cn != "app-client":
                return web.Response(status=400, text="No required SSL certificate was sent")
            if headers["sign"] != hashlib.sha256(message).hexdigest():
                return self._error(39, "Signature verification failed")
            self.logins += 1
            if params.get("email") != self.email or params.get("password") != self.password:
                return self._error(21, "Incorrect account or password")
            if params.get("policyId") != "20260204" or params.get("loginMethod") != "1":
                return self._error(22, "Invalid login parameters")
            self.token = self._new_token()
            self.refresh = f"refresh-{time.time_ns()}"
            self.sign_material = (f"ikm-{time.time_ns()}", "salt-value", "info-value")
            return self._ok(
                {
                    "id": self.account_id,
                    "uid": self.uid,
                    "token": self.token,
                    "refreshToken": self.refresh,
                    "signIkm": self.sign_material[0],
                    "signSalt": self.sign_material[1],
                    "signInfo": self.sign_material[2],
                    "base64Cert": self.pki.account_p12(self.account_id, self.uid),
                }
            )

        # Everything else needs a session.
        expected_cn = "app-client" if path.endswith("/cert/sync") else f"account-{self.account_id}"
        if cn != expected_cn:
            return web.Response(status=400, text="No required SSL certificate was sent")
        if not self.sign_material[0]:
            return self._error(10001, "token invalid")
        expected = hmac.new(self._sign_key(), message, hashlib.sha256).hexdigest()
        if headers["sign"] != expected:
            return self._error(39, "Signature verification failed")
        if headers.get("deviceId") != self.device_id:
            return self._error(39, "Device mismatch")
        if headers.get("userId") != str(self.account_id):
            return self._error(10001, "token invalid")

        if path.endswith("/acct/v1/token/refresh"):
            if self.fail_refresh or params.get("refreshToken") != self.refresh:
                return self._error(10002, "refresh token invalid")
            self.refreshes += 1
            self.token = self._new_token()
            self.refresh = f"refresh-{time.time_ns()}"
            return self._ok({"token": self.token, "refreshToken": self.refresh})

        if headers.get("token") != self.token:
            return self._error(10001, "token expired")

        if path.endswith("/vehicle/v1/list"):
            car = {
                "vin": self.vin,
                "carId": 77,
                "carType": self.car_type,
                "nickName": "Test car",
                "outColor": "Grey",
                "year": "2025",
                "rightList": self.rights,
                "abilities": [1, 2, 3, 12, 35, 48],
                "moduleRights": "100,200,300,400",
            }
            key = "sharedcars" if self.shared else "bindcars"
            return self._ok({"bindcars": [], "sharedcars": [], key: [car]})
        if "/vehicle/v1/status/get/" in path:
            segment = path.rsplit("/", 1)[-1]
            if segment in self.status_404_for:
                return web.json_response(
                    {"status": 404, "error": "Not Found", "message": "No message available"},
                    status=404,
                )
            if params.get("vin") != self.vin:
                return self._error(40, "No such permission")
            return self._ok(self.status_payload)
        if path.endswith("/mileage/energy/detail"):
            return self._ok(
                {
                    "totalmileage": 3030,
                    "deliveryDays": 120,
                    "totalEnergy": 512.4,
                    "totalAccumulatedMileage": 84.5,
                    "detail": [
                        {
                            "day": "2026-11-10",
                            "accumulatedMileage": 40.0,
                            "accumulatedEnergyConsume": 7,
                        },
                        {
                            "day": "2026-11-11",
                            "accumulatedMileage": 44.5,
                            "accumulatedEnergyConsume": 8,
                        },
                    ],
                }
            )
        if path.endswith("/getLastNweeks100kmECAndRank"):
            return self._ok(
                {
                    "rankResult": {"result": 0, "rank": "12%", "hundredKmEC": "17.6"},
                    "weeklyEC": [
                        {"weekStart": "2026-11-02", "weekEnd": "2026-11-08", "hundredKmEC": 17.9}
                    ],
                }
            )
        if path.endswith("/getLastweekEC"):
            return self._ok({"driverEC": "30.5", "acEC": "4.2", "otherEC": "1.3"})
        if path.endswith("/charge/daily/detail/page"):
            if not isinstance(body.get("pageNum"), int):
                return self._error(39, "pageNum must be a number")
            return self._ok(
                {
                    "list": [
                        {
                            "chargeGunStartTs": 1778130000000,
                            "chargeGunEndTs": 1778137200000,
                            "chargeType": "1",
                            "chargeInEnergy": 21.5,
                        }
                    ]
                }
            )
        if path.endswith("/message/v1/unread/count"):
            return self._ok({"unread": 3})
        if path.endswith("/message/v1/list"):
            return self._ok({"list": [{"title": "Hello", "sendTime": 1778137200000}]})
        if path.endswith("/hotspot/fetch"):
            if self.shared:
                return self._error(40, "No such permission")
            return self._ok({"currentVersion": {"generalVersion": "1.2.3"}})
        if path.endswith("/getAppointment"):
            if params.get("cmdId") == "190":
                return self._ok(
                    json.dumps({"chargeEnable": 1, "chargesoc": 90, "starttime": "23:30"})
                )
            return self._error(40, "No such permission")
        if path.endswith("/carpicture/key"):
            if params.get("deviceID") != self.device_id:
                return self._error(39, "deviceID mismatch")
            return self._ok({"key": "pic-key", "whole": 1})
        if path.endswith("/carpicture/package"):
            self.picture_downloads += 1
            if params.get("key") != "pic-key":
                return self._error(39, "unknown picture key")
            return web.Response(body=picture_package(), content_type="application/zip")
        if path.endswith("/cert/sync"):
            self.cert_syncs += 1
            return self._ok()
        if path.endswith("/operPwd/verify"):
            self.pin_checks += 1
            try:
                pin = crypto.decrypt_pin(params.get("operatePassword", ""), self.token)
            except Exception:
                pin = None
            if pin != self.pin:
                return self._error(5001, "Operation password error")
            return self._ok()
        if path.endswith("/app/remote/ctl"):
            if "operatePassword" in params:
                try:
                    pin = crypto.decrypt_pin(params["operatePassword"], self.token)
                except Exception:
                    pin = None
                if pin != self.pin:
                    return self._error(5001, "Operation password error")
            elif params.get("cmdId") != "180":
                return self._error(5002, "Operation password required")
            if params.get("cmdId") == "999":
                return self._error(40, "No such permission")
            remote_id = f"ctl-{len(self.commands) + 1}"
            self.commands.append(
                {
                    "cmdId": params.get("cmdId"),
                    "content": json.loads(params.get("cmdContent", "{}")),
                }
            )
            return self._ok(
                {
                    "remoteCtlId": remote_id,
                    "queryRemoteCtlResultTimeout": 6000,
                    "queryInterval": 100,
                }
            )
        if path.endswith("/remote/ctl/result/query"):
            remote_id = params.get("remoteCtlId", "")
            polls = self._result_polls.get(remote_id, 0) + 1
            self._result_polls[remote_id] = polls
            return self._ok(1 if polls >= self.result_after else 0)
        return web.json_response({"status": 404, "message": "No message available"}, status=404)
