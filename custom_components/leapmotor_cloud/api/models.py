"""Data classes shared by the cloud client, the demo client and Home Assistant."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
import time
from typing import Any

from .crypto import derive_sign_key


def _codes(raw: Any) -> frozenset[int]:
    """Parse a list of numeric codes given as list or comma separated string."""
    if raw is None:
        return frozenset()
    if isinstance(raw, str):
        items: Iterable[Any] = raw.replace(";", ",").split(",")
    elif isinstance(raw, Iterable):
        items = raw
    else:
        items = [raw]
    codes: set[int] = set()
    for item in items:
        try:
            codes.add(int(str(item).strip()))
        except (TypeError, ValueError):
            continue
    return frozenset(codes)


def _text(raw: Any) -> str | None:
    if raw is None:
        return None
    text = str(raw).strip()
    return text or None


@dataclass(frozen=True, slots=True)
class VehicleInfo:
    """One vehicle of the account, as returned by the vehicle list."""

    vin: str
    car_type: str = "C10"
    car_id: str | None = None
    nickname: str | None = None
    plate: str | None = None
    color: str | None = None
    year: int | None = None
    is_shared: bool = False
    rights: frozenset[int] = frozenset()
    abilities: frozenset[int] = frozenset()
    module_rights: frozenset[int] = frozenset()

    @classmethod
    def from_api(cls, item: dict[str, Any], *, is_shared: bool) -> VehicleInfo:
        """Build the object from one entry of ``bindcars`` / ``sharedcars``."""
        year: int | None
        try:
            year = int(item["year"]) if item.get("year") not in (None, "") else None
        except (TypeError, ValueError):
            year = None
        return cls(
            vin=str(item["vin"]),
            car_type=(_text(item.get("carType")) or "C10").upper(),
            car_id=_text(item.get("carId")),
            nickname=_text(item.get("vinNickname")) or _text(item.get("nickName")),
            plate=_text(item.get("plateNumber")),
            color=_text(item.get("outColor")),
            year=year,
            is_shared=is_shared,
            rights=_codes(item.get("rightList")),
            abilities=_codes(item.get("abilities")),
            module_rights=_codes(item.get("moduleRights")),
        )

    @property
    def model(self) -> str:
        """Return the model code, e.g. ``C10``."""
        return self.car_type.upper()

    @property
    def model_name(self) -> str:
        """Return the model name including the brand."""
        return f"Leapmotor {self.model}"

    @property
    def vin_tail(self) -> str:
        """Return the last characters of the VIN for log output."""
        return f"…{self.vin[-4:]}" if len(self.vin) > 4 else "…"

    def has_right(self, right: int | None) -> bool | None:
        """Return whether the account may use a command.

        ``None`` means unknown: the backend did not report any rights.
        """
        if right is None:
            return True
        if not self.rights:
            return None
        return right in self.rights

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON serialisable representation."""
        data = asdict(self)
        for key in ("rights", "abilities", "module_rights"):
            data[key] = sorted(data[key])
        return data

    @classmethod
    def from_dict(cls, data: Any) -> VehicleInfo | None:
        """Restore an object written by :meth:`as_dict`."""
        if not isinstance(data, dict) or not data.get("vin"):
            return None
        return cls(
            vin=str(data["vin"]),
            car_type=str(data.get("car_type") or "C10").upper(),
            car_id=_text(data.get("car_id")),
            nickname=_text(data.get("nickname")),
            plate=_text(data.get("plate")),
            color=_text(data.get("color")),
            year=data.get("year") if isinstance(data.get("year"), int) else None,
            is_shared=bool(data.get("is_shared")),
            rights=_codes(data.get("rights")),
            abilities=_codes(data.get("abilities")),
            module_rights=_codes(data.get("module_rights")),
        )


@dataclass(slots=True)
class SessionState:
    """Everything needed to keep talking to the cloud without a new login."""

    token: str
    user_id: str
    device_id: str
    sign_ikm: str
    sign_salt: str
    sign_info: str
    account_cert_pem: str
    account_key_pem: str
    refresh_token: str | None = None
    created_at: float = field(default_factory=time.time)
    refreshed_at: float | None = None
    _sign_key: bytes | None = field(default=None, repr=False, compare=False)

    @property
    def sign_key(self) -> bytes:
        """Return the (cached) request signing key."""
        if self._sign_key is None:
            self._sign_key = derive_sign_key(self.sign_ikm, self.sign_salt, self.sign_info)
        return self._sign_key

    def to_dict(self) -> dict[str, Any]:
        """Serialise for persistent storage."""
        return {
            "token": self.token,
            "user_id": self.user_id,
            "device_id": self.device_id,
            "sign_ikm": self.sign_ikm,
            "sign_salt": self.sign_salt,
            "sign_info": self.sign_info,
            "account_cert_pem": self.account_cert_pem,
            "account_key_pem": self.account_key_pem,
            "refresh_token": self.refresh_token,
            "created_at": self.created_at,
            "refreshed_at": self.refreshed_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> SessionState | None:
        """Restore a stored session; returns ``None`` when data is incomplete."""
        if not isinstance(data, dict):
            return None
        required = (
            "token",
            "user_id",
            "device_id",
            "sign_ikm",
            "sign_salt",
            "sign_info",
            "account_cert_pem",
            "account_key_pem",
        )
        if any(not data.get(key) for key in required):
            return None
        return cls(
            token=str(data["token"]),
            user_id=str(data["user_id"]),
            device_id=str(data["device_id"]),
            sign_ikm=str(data["sign_ikm"]),
            sign_salt=str(data["sign_salt"]),
            sign_info=str(data["sign_info"]),
            account_cert_pem=str(data["account_cert_pem"]),
            account_key_pem=str(data["account_key_pem"]),
            refresh_token=_text(data.get("refresh_token")),
            created_at=float(data.get("created_at") or time.time()),
            refreshed_at=data.get("refreshed_at"),
        )


@dataclass(frozen=True, slots=True)
class RemoteCommand:
    """A remote-control command ready to be sent."""

    name: str
    cmd_id: str
    content: str
    requires_pin: bool = True
    right: int | None = None


@dataclass(frozen=True, slots=True)
class CommandResult:
    """Outcome of a remote command."""

    command: str
    accepted: bool
    confirmed: bool
    remote_ctl_id: str | None = None
    message: str | None = None
