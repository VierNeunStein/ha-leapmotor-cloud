"""Tests for PEM handling and certificate checks."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID
import pytest

from leapmotor_api import LeapmotorCertificateError
from leapmotor_api.tls import build_ssl_context, normalize_pem, validate_client_certificate


def _pair() -> tuple[str, str]:
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
        .not_valid_after(now + timedelta(days=30))
        .sign(key, hashes.SHA256())
    )
    return (
        cert.public_bytes(serialization.Encoding.PEM).decode(),
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        ).decode(),
    )


def test_openssl_bag_attributes_are_dropped() -> None:
    cert, key = _pair()
    exported = (
        "Bag Attributes\n    localKeyID: 01 00 00 00\n    friendlyName: app\n"
        "subject=CN = app\nissuer=CN = app\n" + cert
    )
    assert normalize_pem(exported) == cert
    assert (
        normalize_pem(
            "Bag Attributes\r\n    localKeyID: 01\r\nKey Attributes: <No Attributes>\r\n"
            + key.replace("\n", "\r\n")
        )
        == key
    )


def test_single_line_paste_is_repaired() -> None:
    cert, key = _pair()
    assert normalize_pem(cert.replace("\n", " ")) == cert
    assert normalize_pem(key.replace("\n", "\\n")) == key
    combined = normalize_pem(cert + key)
    assert combined == cert + key


def test_text_without_pem_is_returned_for_a_clear_error() -> None:
    assert normalize_pem("  not a certificate \n") == "not a certificate"
    with pytest.raises(LeapmotorCertificateError):
        validate_client_certificate(normalize_pem("nope"), normalize_pem("nope"))


def test_validate_and_build_context() -> None:
    cert, key = _pair()
    info = validate_client_certificate(cert, key)
    assert info.subject == "app" and len(info.short_fingerprint) == 23
    assert build_ssl_context(cert, key) is not None
    other_cert, _ = _pair()
    with pytest.raises(LeapmotorCertificateError):
        validate_client_certificate(other_cert, key)
