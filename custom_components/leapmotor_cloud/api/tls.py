"""TLS helpers: client certificates and server certificate pinning.

The Leapmotor gateway uses a certificate issued by a private CA, so the
public trust store cannot verify it.  Instead of switching verification off
entirely, the server certificate seen at setup is *pinned*: afterwards the
exact same certificate is required (trust on first use).
"""

from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass
from datetime import datetime
import hashlib
import os
from pathlib import Path
import re
import shutil
import ssl
import tempfile

from cryptography import x509
from cryptography.hazmat.primitives import serialization

from .errors import LeapmotorCertificateError, LeapmotorConnectionError

# OpenSSL: X509_V_FLAG_NO_CHECK_TIME. A pinned certificate is trusted because
# it is the pinned one, independent of clock skew or its validity period.
_X509_V_FLAG_NO_CHECK_TIME = 0x200000


@dataclass(frozen=True, slots=True)
class CertificateInfo:
    """Human-readable facts about a certificate."""

    fingerprint: str
    subject: str
    issuer: str
    not_before: datetime
    not_after: datetime

    @property
    def short_fingerprint(self) -> str:
        """Return a short form of the SHA-256 fingerprint for display."""
        return ":".join(self.fingerprint[i : i + 2] for i in range(0, 16, 2)).upper()


def _common_name(name: x509.Name) -> str:
    attributes = name.get_attributes_for_oid(x509.NameOID.COMMON_NAME)
    return str(attributes[0].value) if attributes else name.rfc4514_string()


def describe_certificate(der: bytes) -> CertificateInfo:
    """Return display information for a DER encoded certificate."""
    cert = x509.load_der_x509_certificate(der)
    return CertificateInfo(
        fingerprint=hashlib.sha256(der).hexdigest(),
        subject=_common_name(cert.subject),
        issuer=_common_name(cert.issuer),
        not_before=cert.not_valid_before_utc,
        not_after=cert.not_valid_after_utc,
    )


_PEM_BLOCK = re.compile(r"-----BEGIN ([A-Z0-9 ]+)-----(.*?)-----END \1-----", re.S)


def normalize_pem(text: str) -> str:
    """Return just the PEM blocks of a text, with clean line breaks.

    Repairs text that lost its line breaks when it was pasted into a single
    line, and drops anything around the blocks, such as the "Bag Attributes"
    that openssl writes when it exports from PKCS#12.
    """
    text = text.replace("\\n", "\n").replace("\r", "")
    blocks = []
    for label, body in _PEM_BLOCK.findall(text):
        data = "".join(body.split())
        lines = "\n".join(data[index : index + 64] for index in range(0, len(data), 64))
        blocks.append(f"-----BEGIN {label}-----\n{lines}\n-----END {label}-----")
    if not blocks:
        return text.strip()
    return "\n".join(blocks) + "\n"


def validate_client_certificate(cert_pem: str, key_pem: str) -> CertificateInfo:
    """Check that a certificate and a private key are usable and belong together."""
    try:
        cert = x509.load_pem_x509_certificate(cert_pem.encode("utf-8"))
    except ValueError as err:
        raise LeapmotorCertificateError("The certificate is not valid PEM") from err
    try:
        key = serialization.load_pem_private_key(key_pem.encode("utf-8"), password=None)
    except (ValueError, TypeError) as err:
        raise LeapmotorCertificateError(
            "The private key is not valid PEM (or it is password protected)"
        ) from err
    fmt = (serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    if cert.public_key().public_bytes(*fmt) != key.public_key().public_bytes(*fmt):
        raise LeapmotorCertificateError("Certificate and private key do not belong together")
    return describe_certificate(cert.public_bytes(serialization.Encoding.DER))


def build_ssl_context(
    cert_pem: str | bytes,
    key_pem: str | bytes,
    *,
    pinned_certificate: bytes | None = None,
) -> ssl.SSLContext:
    """Create a client context that presents ``cert``/``key`` to the server.

    With ``pinned_certificate`` (DER) the handshake only succeeds when the
    server presents exactly that certificate.  Without it the server is not
    verified at all.

    Blocking (touches the file system): run it in an executor.
    """
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    # A pin identifies the server; the name in the certificate adds nothing.
    context.check_hostname = False
    if pinned_certificate:
        context.verify_mode = ssl.CERT_REQUIRED
        context.load_verify_locations(cadata=ssl.DER_cert_to_PEM_cert(pinned_certificate))
        flags = int(context.verify_flags) | int(ssl.VERIFY_X509_PARTIAL_CHAIN)
        flags |= _X509_V_FLAG_NO_CHECK_TIME
        flags &= ~int(getattr(ssl, "VERIFY_X509_STRICT", 0))
        context.verify_flags = ssl.VerifyFlags(flags)
    else:
        context.verify_mode = ssl.CERT_NONE

    # The ssl module can only read key material from files.
    directory = Path(tempfile.mkdtemp(prefix="leapmotor-"))
    try:
        with contextlib.suppress(OSError):
            os.chmod(directory, 0o700)
        cert_file = directory / "cert.pem"
        key_file = directory / "key.pem"
        for path, data in ((cert_file, cert_pem), (key_file, key_pem)):
            raw = data.encode("utf-8") if isinstance(data, str) else data
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "wb") as handle:
                handle.write(raw)
        try:
            context.load_cert_chain(str(cert_file), str(key_file))
        except (ssl.SSLError, OSError) as err:
            raise LeapmotorCertificateError(
                f"Client certificate could not be loaded: {err}"
            ) from err
    finally:
        shutil.rmtree(directory, ignore_errors=True)
    return context


async def fetch_server_certificate(host: str, port: int = 443, *, timeout: float = 15.0) -> bytes:
    """Return the DER certificate the server currently presents.

    Performs a TLS handshake only; nothing is sent to the server.
    """
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    try:
        async with asyncio.timeout(timeout):
            _reader, writer = await asyncio.open_connection(
                host, port, ssl=context, server_hostname=host
            )
    except (OSError, TimeoutError, ssl.SSLError) as err:
        raise LeapmotorConnectionError(
            f"Could not connect to {host}:{port}: {type(err).__name__}: {err}"
        ) from err
    try:
        ssl_object = writer.get_extra_info("ssl_object")
        der = ssl_object.getpeercert(binary_form=True) if ssl_object else None
    finally:
        writer.close()
        with contextlib.suppress(OSError, ssl.SSLError, TimeoutError):
            async with asyncio.timeout(5):
                await writer.wait_closed()
    if not der:
        raise LeapmotorConnectionError(f"{host}:{port} presented no certificate")
    return der
