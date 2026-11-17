"""Tests for signatures and key derivations."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from leapmotor_api import crypto


def test_signature_input_orders_values_by_key() -> None:
    fields = {
        "vin": "V",
        "acceptLanguage": "en-GB",
        "deviceId": "d",
        "deviceID": "D",
        "channel": "1",
    }
    # Case-sensitive order: acceptLanguage, channel, deviceID, deviceId, vin
    assert crypto.signature_input(fields) == "en-GB1DdV"


def test_signature_input_matches_documented_remote_control_order() -> None:
    fields = {
        "acceptLanguage": "L",
        "channel": "C",
        "cmdContent": "{}",
        "cmdId": "110",
        "deviceId": "DEV",
        "deviceType": "T",
        "nonce": "N",
        "operatePassword": "PWD",
        "source": "S",
        "timestamp": "TS",
        "version": "VER",
        "vin": "VIN",
    }
    assert crypto.signature_input(fields) == "LC{}110DEVTNPWDSTSVERVIN"


def test_login_and_request_signatures() -> None:
    fields = {"b": "2", "a": "1"}
    assert crypto.login_signature(fields) == hashlib.sha256(b"12").hexdigest()
    key = b"k" * 32
    assert crypto.request_signature(key, fields) == hmac.new(key, b"12", hashlib.sha256).hexdigest()


def test_hkdf_rfc5869_case_1() -> None:
    okm = crypto.hkdf_sha256(
        bytes.fromhex("0b" * 22),
        bytes.fromhex("000102030405060708090a0b0c"),
        bytes.fromhex("f0f1f2f3f4f5f6f7f8f9"),
        42,
    )
    assert okm.hex() == (
        "3cb25f25faacd57a90434f64d0362f2a2d2d0a90cf1a5a4c5db02d56ecc4c5bf34007208d5b887185865"
    )


def test_sign_key_matches_reference_hkdf() -> None:
    expected = HKDF(algorithm=hashes.SHA256(), length=32, salt=b"salt", info=b"info").derive(b"ikm")
    assert crypto.derive_sign_key("ikm", "salt", "info") == expected


def _sm4_round_keys(key: bytes) -> tuple[int, ...]:
    """Standard SM4 key schedule (only needed to check the block function)."""
    fk = (0xA3B1BAC6, 0x56AA3350, 0x677D9197, 0xB27022DC)
    ck = tuple(
        int.from_bytes(bytes((4 * i + j) * 7 % 256 for j in range(4)), "big") for i in range(32)
    )
    sbox = crypto._SM4_SBOX
    k = [int.from_bytes(key[i : i + 4], "big") ^ fk[i // 4] for i in range(0, 16, 4)]
    keys = []
    for i in range(32):
        t = k[1] ^ k[2] ^ k[3] ^ ck[i]
        b = int.from_bytes(bytes(sbox[x] for x in t.to_bytes(4, "big")), "big")
        rk = k[0] ^ b ^ crypto._rotl(b, 13) ^ crypto._rotl(b, 23)
        k = [k[1], k[2], k[3], rk]
        keys.append(rk)
    return tuple(keys)


def test_sm4_block_function_with_standard_vector() -> None:
    key = bytes.fromhex("0123456789abcdeffedcba9876543210")
    cipher = crypto.sm4_encrypt_block(key, _sm4_round_keys(key))
    assert cipher.hex() == "681edf34d206965e86b3e94f536e4246"


def test_p12_password_shape() -> None:
    password = crypto.derive_p12_password(123456, "0a1b2c3d4e5f")
    assert len(password) == 15
    assert password == crypto.derive_p12_password("123456", "0a1b2c3d4e5f")
    assert password != crypto.derive_p12_password("123457", "0a1b2c3d4e5f")
    assert password != crypto.derive_p12_password("123456", "0b1c2d3e4f5a")


def test_pin_key_iv_derivation() -> None:
    token = "a" * 32 + "b" * 32 + ".rest"
    key, iv = crypto.pin_key_iv(token)
    assert key.decode() == hashlib.md5(b"a" * 32).hexdigest()[8:24]
    assert iv.decode() == hashlib.md5(b"b" * 32).hexdigest()[8:24]
    assert crypto.pin_key_iv(None) == (b"f1cf0c025baec0e2", b"6b6a1fe94e133fd7")
    assert crypto.pin_key_iv("short") == (b"f1cf0c025baec0e2", b"6b6a1fe94e133fd7")


def test_pin_roundtrip() -> None:
    token = "x" * 70
    encrypted = crypto.encrypt_pin("1234", token)
    assert len(base64.b64decode(encrypted)) == 16
    assert crypto.decrypt_pin(encrypted, token) == "1234"
    assert crypto.encrypt_pin("1234", token) != crypto.encrypt_pin("1234", "y" * 70)
    long_pin = "1234567890123456"
    assert crypto.decrypt_pin(crypto.encrypt_pin(long_pin, token), token) == long_pin


def _jwt(payload: dict) -> str:
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    return f"header.{body}.signature"


def test_session_device_id() -> None:
    assert crypto.session_device_id(_jwt({"user_name": "u,1,dev42,x"}), "fallback") == "dev42"
    assert crypto.session_device_id(_jwt({"user_name": "u,1,,x"}), "fallback") == "fallback"
    assert crypto.session_device_id(_jwt({"user_name": "u,1,dev"}), "fallback") == "fallback"
    assert crypto.session_device_id("garbage", "fallback") == "fallback"
    assert crypto.session_device_id(None, "fallback") == "fallback"


def test_token_expiry() -> None:
    assert crypto.token_expiry(_jwt({"exp": 1900000000})) == 1900000000.0
    assert crypto.token_expiry(_jwt({})) is None
    assert crypto.token_expiry("nope") is None
