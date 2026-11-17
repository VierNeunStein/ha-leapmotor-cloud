"""Exceptions raised by the Leapmotor cloud client."""

from __future__ import annotations


class LeapmotorError(Exception):
    """Base class for every error of this package."""


class LeapmotorConnectionError(LeapmotorError):
    """The cloud could not be reached (network, DNS, TLS, timeout)."""


class LeapmotorServerIdentityError(LeapmotorConnectionError):
    """The server presented a certificate that does not match the pinned one."""

    def __init__(self, message: str, *, presented: bytes | None = None) -> None:
        super().__init__(message)
        self.presented = presented


class LeapmotorCertificateError(LeapmotorError):
    """The app certificate or the account certificate is missing or unusable."""


class LeapmotorApiError(LeapmotorError):
    """The cloud answered, but with an error."""

    def __init__(
        self,
        message: str,
        *,
        code: int | str | None = None,
        http_status: int | None = None,
        endpoint: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.http_status = http_status
        self.endpoint = endpoint


class LeapmotorAuthError(LeapmotorApiError):
    """Email or password were rejected. Retrying with the same data is pointless."""


class LeapmotorTokenError(LeapmotorApiError):
    """The session token is no longer valid; a refresh or login is needed."""


class LeapmotorRateLimitError(LeapmotorApiError):
    """The cloud asks us to slow down (or temporarily locked the account)."""


class LeapmotorPermissionError(LeapmotorApiError):
    """The account lacks the right for this vehicle, data set or command."""


class LeapmotorPinError(LeapmotorApiError):
    """The vehicle PIN is missing or was rejected."""


class LeapmotorCommandError(LeapmotorApiError):
    """A remote command was rejected or not confirmed by the vehicle."""

    def __init__(
        self,
        message: str,
        *,
        code: int | str | None = None,
        http_status: int | None = None,
        endpoint: str | None = None,
        timed_out: bool = False,
    ) -> None:
        super().__init__(message, code=code, http_status=http_status, endpoint=endpoint)
        self.timed_out = timed_out
