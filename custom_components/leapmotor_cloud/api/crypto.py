"""Signatures and key derivations used by the Leapmotor cloud API.

Everything in here is pure computation: no network, no files.
"""

from __future__ import annotations

import base64
import binascii
from collections.abc import Mapping
import hashlib
import hmac
import json
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.serialization import pkcs12

from .errors import LeapmotorCertificateError

# ---------------------------------------------------------------------------
# Request signatures
# ---------------------------------------------------------------------------


def signature_input(fields: Mapping[str, str]) -> str:
    """Return the string the backend signs.

    Header fields and body parameters are merged into one mapping; the values
    are concatenated in the (case-sensitive) order of their keys.
    """
    return "".join(str(fields[key]) for key in sorted(fields))


def login_signature(fields: Mapping[str, str]) -> str:
    """Signature of the login request (no session key exists yet)."""
    return hashlib.sha256(signature_input(fields).encode("utf-8")).hexdigest()


def request_signature(sign_key: bytes, fields: Mapping[str, str]) -> str:
    """Signature of every request after login."""
    return hmac.new(sign_key, signature_input(fields).encode("utf-8"), hashlib.sha256).hexdigest()


def hkdf_sha256(ikm: bytes, salt: bytes, info: bytes, length: int = 32) -> bytes:
    """HKDF (RFC 5869) with SHA-256."""
    if not salt:
        salt = b"\x00" * hashlib.sha256().digest_size
    prk = hmac.new(salt, ikm, hashlib.sha256).digest()
    okm = b""
    block = b""
    counter = 1
    while len(okm) < length:
        block = hmac.new(prk, block + info + bytes([counter]), hashlib.sha256).digest()
        okm += block
        counter += 1
    return okm[:length]


def derive_sign_key(sign_ikm: str, sign_salt: str, sign_info: str) -> bytes:
    """Derive the per-session signing key from the login response."""
    return hkdf_sha256(
        sign_ikm.encode("utf-8"), sign_salt.encode("utf-8"), sign_info.encode("utf-8")
    )


# ---------------------------------------------------------------------------
# Session token helpers
# ---------------------------------------------------------------------------


def token_payload(token: str | None) -> dict[str, Any]:
    """Return the (unverified) payload of the session JWT, or an empty dict."""
    if not token:
        return {}
    parts = token.split(".")
    if len(parts) < 2:
        return {}
    segment = parts[1] + "=" * (-len(parts[1]) % 4)
    try:
        payload = json.loads(base64.urlsafe_b64decode(segment.encode("ascii")))
    except (ValueError, binascii.Error, UnicodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def session_device_id(token: str | None, fallback: str) -> str:
    """Return the device id the backend bound to this session.

    After login the signature has to use the id from the token, which may
    differ from the one the login was sent with.
    """
    user_name = str(token_payload(token).get("user_name") or "")
    parts = user_name.split(",")
    if len(parts) >= 4 and parts[2]:
        return parts[2]
    return fallback


def token_expiry(token: str | None) -> float | None:
    """Return the ``exp`` claim (epoch seconds) of the session token, if any."""
    exp = token_payload(token).get("exp")
    try:
        return float(exp) if exp is not None else None
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Vehicle PIN ("operatePassword")
# ---------------------------------------------------------------------------

_PIN_FALLBACK_KEY = "f1cf0c025baec0e2"
_PIN_FALLBACK_IV = "6b6a1fe94e133fd7"


def pin_key_iv(token: str | None) -> tuple[bytes, bytes]:
    """Return the AES key and IV the PIN is encrypted with for this session."""
    if not token or len(token) < 64:
        return _PIN_FALLBACK_KEY.encode("ascii"), _PIN_FALLBACK_IV.encode("ascii")
    key = hashlib.md5(token[:32].encode("utf-8")).hexdigest()[8:24]
    iv = hashlib.md5(token[32:64].encode("utf-8")).hexdigest()[8:24]
    return key.encode("ascii"), iv.encode("ascii")


def encrypt_pin(pin: str, token: str | None) -> str:
    """Encrypt the vehicle PIN the way the app does (AES-128-CBC, PKCS#7)."""
    key, iv = pin_key_iv(token)
    data = pin.encode("utf-8")
    pad = 16 - len(data) % 16
    data += bytes([pad]) * pad
    encryptor = Cipher(algorithms.AES(key), modes.CBC(iv)).encryptor()
    return base64.b64encode(encryptor.update(data) + encryptor.finalize()).decode("ascii")


def decrypt_pin(encrypted: str, token: str | None) -> str:
    """Inverse of :func:`encrypt_pin` (used by the test server and the demo)."""
    key, iv = pin_key_iv(token)
    decryptor = Cipher(algorithms.AES(key), modes.CBC(iv)).decryptor()
    data = decryptor.update(base64.b64decode(encrypted)) + decryptor.finalize()
    if not data or not 1 <= data[-1] <= 16:
        raise ValueError("invalid padding")
    return data[: -data[-1]].decode("utf-8")


# ---------------------------------------------------------------------------
# Account certificate (PKCS#12 from the login response)
# ---------------------------------------------------------------------------

# The standard SM4 S-box (GB/T 32907-2016).
_SM4_SBOX = bytes.fromhex(
    "d690e9fecce13db716b614c228fb2c05"
    "2b679a762abe04c3aa44132649860699"
    "9c4250f491ef987a33540b43edcfac62"
    "e4b31ca9c908e89580df94fa758f3fa6"
    "4707a7fcf37317ba83593c19e6854fa8"
    "686b81b27164da8bf8eb0f4b70569d35"
    "1e240e5e6358d1a225227c3b01217887"
    "d40046579fd327524c3602e7a0c4c89e"
    "eabf8ad240c738b5a3f7f2cef96115a1"
    "e0ae5da49b341a55ad933230f58cb1e3"
    "1df6e22e8266ca60c02923ab0d534e6f"
    "d5db3745defd8e2f03ff6a726d6c5b51"
    "8d1baf92bbddbc7f11d95c411f105ad8"
    "0ac13188a5cd7bbd2d74d012b8e5b4b0"
    "8969974a0c96777e65b9f109c56ec684"
    "18f07dec3adc4d2079ee5f3ed7cb3948"
)

# Round keys of the fixed SM4 key the backend protects the account
# certificate password with.
_P12_ROUND_KEYS = (
    0x818FA553, 0xEBA3318D, 0x5FC3C93A, 0xBD1DADD9,
    0xBB61CAB9, 0x000FD7EA, 0xDC6E0166, 0xDA937279,
    0x607EE786, 0xB548754C, 0x107330E4, 0xEA17C186,
    0x0F56F74B, 0xB21E443C, 0xE1210FE2, 0x009995C8,
    0xE7529A48, 0x6EF474F6, 0x2AB06DF6, 0x43B11BE8,
    0x359D4A14, 0xC29E2CDE, 0x30CF6A3E, 0x79D1C806,
    0x7C502387, 0xAAAB9BC6, 0xF0FE744B, 0x1CAFC872,
    0x95A9D075, 0x88070D58, 0x22800475, 0x8391938B,
)  # fmt: skip


def _rotl(value: int, bits: int) -> int:
    return ((value << bits) & 0xFFFFFFFF) | (value >> (32 - bits))


def sm4_encrypt_block(block: bytes, round_keys: tuple[int, ...]) -> bytes:
    """Encrypt one 16-byte block with SM4 using expanded round keys."""
    x = [int.from_bytes(block[i : i + 4], "big") for i in range(0, 16, 4)]
    for round_key in round_keys:
        t = x[1] ^ x[2] ^ x[3] ^ round_key
        b = int.from_bytes(bytes(_SM4_SBOX[byte] for byte in t.to_bytes(4, "big")), "big")
        x = [x[1], x[2], x[3], x[0] ^ b ^ _rotl(b, 2) ^ _rotl(b, 10) ^ _rotl(b, 18) ^ _rotl(b, 24)]
    return b"".join(value.to_bytes(4, "big") for value in reversed(x))


def derive_p12_password(account_id: str | int, uid: str) -> str:
    """Derive the password of the account PKCS#12 from the login response."""
    cn = hashlib.md5(str(account_id).encode("ascii")).hexdigest()
    digest = hashlib.sha256(f"{cn}{cn[::2]}{uid[1::2]}".encode("ascii")).digest()
    pad = 16 - len(digest) % 16
    padded = digest + bytes([pad]) * pad
    encoded = b"".join(
        sm4_encrypt_block(padded[offset : offset + 16], _P12_ROUND_KEYS)
        for offset in range(0, len(padded), 16)
    )
    return base64.b64encode(encoded[:12]).decode("ascii")[:15]


def load_account_certificate(base64_p12: str, passwords: list[str]) -> tuple[bytes, bytes]:
    """Open the account PKCS#12 and return ``(certificate_pem, private_key_pem)``."""
    try:
        p12 = base64.b64decode(base64_p12)
    except (ValueError, binascii.Error) as err:
        raise LeapmotorCertificateError("Account certificate is not valid base64") from err
    if not p12:
        raise LeapmotorCertificateError("Login response contained no account certificate")

    last_error: Exception | None = None
    for password in passwords:
        try:
            key, cert, _extra = pkcs12.load_key_and_certificates(p12, password.encode("utf-8"))
        except Exception as err:
            last_error = err
            continue
        if key is None or cert is None:
            continue
        return (
            cert.public_bytes(serialization.Encoding.PEM),
            key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            ),
        )
    reason = type(last_error).__name__ if last_error else "empty"
    raise LeapmotorCertificateError(f"Account certificate could not be opened ({reason})")
