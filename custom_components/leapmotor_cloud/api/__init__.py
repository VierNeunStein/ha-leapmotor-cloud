"""Client library for the Leapmotor international cloud.

This package does not depend on Home Assistant and can be used on its own.
"""

from __future__ import annotations

from . import commands
from .client import LeapmotorCloudClient
from .const import DEFAULT_BASE_URL
from .demo import DEMO_PIN, DEMO_SCENARIOS, DEMO_VIN, LeapmotorDemoClient
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

type LeapmotorClient = LeapmotorCloudClient | LeapmotorDemoClient

__all__ = [
    "DEFAULT_BASE_URL",
    "DEMO_PIN",
    "DEMO_SCENARIOS",
    "DEMO_VIN",
    "CommandResult",
    "LeapmotorApiError",
    "LeapmotorAuthError",
    "LeapmotorCertificateError",
    "LeapmotorClient",
    "LeapmotorCloudClient",
    "LeapmotorCommandError",
    "LeapmotorConnectionError",
    "LeapmotorDemoClient",
    "LeapmotorError",
    "LeapmotorPermissionError",
    "LeapmotorPinError",
    "LeapmotorRateLimitError",
    "LeapmotorServerIdentityError",
    "LeapmotorTokenError",
    "RemoteCommand",
    "SessionState",
    "VehicleInfo",
    "commands",
]
