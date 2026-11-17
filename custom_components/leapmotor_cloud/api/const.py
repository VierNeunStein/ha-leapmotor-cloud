"""Protocol constants of the Leapmotor international cloud API.

The values mirror what the official mobile app sends.  They are plain
interface facts (endpoint paths, header values) and contain no secrets.
"""

from __future__ import annotations

from typing import Final

DEFAULT_BASE_URL: Final = "https://appgateway.leapmotor-international.de"

# Values of the app headers. The backend validates the signature over them,
# so they have to stay consistent with each other.
APP_VERSION: Final = "1.12.3"
APP_SOURCE: Final = "leapmotor"
APP_CHANNEL: Final = "1"
APP_DEVICE_TYPE: Final = "1"
APP_LANGUAGE: Final = "en-GB"
APP_P12_ENC_ALG: Final = "1"
LOGIN_POLICY_ID: Final = "20260204"

_BASE: Final = "/carownerservice/oversea"

PATH_LOGIN: Final = f"{_BASE}/acct/v1/login"
PATH_TOKEN_REFRESH: Final = f"{_BASE}/acct/v1/token/refresh"
PATH_VEHICLE_LIST: Final = f"{_BASE}/vehicle/v1/list"
PATH_VEHICLE_STATUS: Final = f"{_BASE}/vehicle/v1/status/get/{{model}}"
PATH_MILEAGE: Final = f"{_BASE}/drivingRecord/v1/mileage/energy/detail"
PATH_CONSUMPTION_RANK: Final = f"{_BASE}/drivingRecord/v1/getLastNweeks100kmECAndRank"
PATH_CONSUMPTION_WINDOW: Final = f"{_BASE}/drivingRecord/v1/getLastweekEC"
PATH_CHARGE_RECORDS: Final = "/carownerservice/charge/daily/detail/page"
PATH_PICTURE_KEY: Final = f"{_BASE}/vehicle/v1/carpicture/key"
PATH_PICTURE_PACKAGE: Final = f"{_BASE}/vehicle/v1/carpicture/package"
PATH_MESSAGE_LIST: Final = f"{_BASE}/message/v1/list"
PATH_MESSAGE_UNREAD: Final = f"{_BASE}/message/v1/unread/count"
PATH_SOFTWARE: Final = f"{_BASE}/hotspot/fetch"
PATH_CERT_SYNC: Final = f"{_BASE}/vehicle/v1/cert/sync"
PATH_PIN_VERIFY: Final = f"{_BASE}/vehicle/v1/operPwd/verify"
PATH_REMOTE_CTL: Final = f"{_BASE}/vehicle/v1/app/remote/ctl"
PATH_REMOTE_RESULT: Final = f"{_BASE}/vehicle/v1/app/remote/ctl/result/query"
PATH_APPOINTMENT: Final = f"{_BASE}/vehicle/v1/app/remote/ctl/getAppointment"

# Models that are served by the status endpoint of another model.
STATUS_PATH_ALIASES: Final[dict[str, str]] = {
    "b05": "c10",
    "b10": "c10",
    "b11": "c10",
}
STATUS_PATH_FALLBACK: Final = "c10"

# Appointment (schedule) ids of the getAppointment endpoint.
APPOINTMENT_BATTERY_PREHEAT: Final = "161"
APPOINTMENT_CLIMATE: Final = "171"
APPOINTMENT_CHARGE: Final = "190"
APPOINTMENT_PREPARE_CAR: Final = "361"

# Rights (``rightList``) a vehicle/account needs for a remote command.
RIGHT_LOCK: Final = 110
RIGHT_FIND_CAR: Final = 120
RIGHT_TRUNK: Final = 130
RIGHT_SUNROOF: Final = 160
RIGHT_SUNSHADE: Final = 161
RIGHT_CLIMATE: Final = 170
RIGHT_QUICK_CLIMATE: Final = 171
RIGHT_SEND_DESTINATION: Final = 180
RIGHT_BATTERY_PREHEAT: Final = 190
RIGHT_UNLOCK_CHARGER: Final = 192
RIGHT_TOGGLE_CHARGE: Final = 193
RIGHT_SENTRY_MODE: Final = 220
RIGHT_WINDOWS: Final = 230
RIGHT_SEAT_HEAT: Final = 301
RIGHT_STEERING_WHEEL_HEAT: Final = 320
RIGHT_CHARGE_LIMIT: Final = 340
RIGHT_PREPARE_CAR: Final = 360
RIGHT_SEAT_VENTILATION: Final = 370
RIGHT_MIRROR_HEAT: Final = 440
RIGHT_WINDSHIELD_DEFROST: Final = 460
RIGHT_HEALTHY_CHARGING: Final = 480
RIGHT_SPEED_LIMIT: Final = 510

# Models whose window command uses a 0..10 scale instead of 0..100.
WINDOW_SCALE_TEN_MODELS: Final = frozenset({"B05", "B10", "C10"})

# Models with a reduced feature set (no charge-plan writes, own A/C-off body).
LEGACY_MODELS: Final = frozenset({"T03", "S01"})
