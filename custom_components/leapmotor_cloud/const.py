"""Constants of the Leapmotor Cloud integration."""

from __future__ import annotations

from typing import Final

from homeassistant.const import Platform

DOMAIN: Final = "leapmotor_cloud"
MANUFACTURER: Final = "Leapmotor"

PLATFORMS: Final = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.CLIMATE,
    Platform.COVER,
    Platform.DEVICE_TRACKER,
    Platform.IMAGE,
    Platform.LOCK,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.TIME,
    Platform.UPDATE,
]

# --- config entry data -------------------------------------------------------
CONF_DEMO: Final = "demo"
CONF_DEVICE_ID: Final = "device_id"
CONF_APP_CERT: Final = "app_cert"
CONF_APP_KEY: Final = "app_key"
CONF_BASE_URL: Final = "base_url"
CONF_SERVER_CERT: Final = "server_cert"

# --- config flow only --------------------------------------------------------
CONF_CERT_FILE: Final = "cert_file"
CONF_KEY_FILE: Final = "key_file"
CONF_CERT_TEXT: Final = "cert_text"
CONF_KEY_TEXT: Final = "key_text"
CONF_PIN: Final = "pin"

# --- options -----------------------------------------------------------------
CONF_PINS: Final = "pins"
CONF_INTERVAL_ACTIVE: Final = "interval_active"
CONF_INTERVAL_IDLE: Final = "interval_idle"
CONF_INTERVAL_HISTORY: Final = "interval_history"
CONF_CHARGER_POWER_ENTITY: Final = "charger_power_entity"
CONF_CHARGER_POWER_THRESHOLD: Final = "charger_power_threshold"
CONF_DAILY_REQUEST_LIMIT: Final = "daily_request_limit"
CONF_TLS_MODE: Final = "tls_mode"

TLS_MODE_AUTO: Final = "auto"
TLS_MODE_STRICT: Final = "strict"
TLS_MODE_OFF: Final = "off"
TLS_MODES: Final = [TLS_MODE_AUTO, TLS_MODE_STRICT, TLS_MODE_OFF]

# Polling defaults, in minutes. They are deliberately conservative: the cloud
# has no official third-party access and accounts can be locked.
DEFAULT_INTERVAL_ACTIVE: Final = 5
DEFAULT_INTERVAL_IDLE: Final = 30
DEFAULT_INTERVAL_HISTORY: Final = 60
MIN_INTERVAL_ACTIVE: Final = 2
MIN_INTERVAL_IDLE: Final = 10
MIN_INTERVAL_HISTORY: Final = 30
MAX_INTERVAL: Final = 720
DEFAULT_CHARGER_POWER_THRESHOLD: Final = 500
DEFAULT_DAILY_REQUEST_LIMIT: Final = 1500
MIN_DAILY_REQUEST_LIMIT: Final = 200

# Fixed pacing (seconds).
MIN_REFRESH_GAP: Final = 30
ACTIVITY_HOLD: Final = 10 * 60
COMMAND_REFRESH_DELAYS: Final = (8, 30, 90)
CHARGER_REFRESH_DELAY: Final = 45
OPTIMISTIC_TTL: Final = 150
VEHICLE_LIST_INTERVAL: Final = 12 * 3600
DAILY_DATA_INTERVAL: Final = 24 * 3600
ERROR_GRACE: Final = 2 * 3600
RATE_LIMIT_PAUSE: Final = 2 * 3600
MAX_BACKOFF: Final = 3 * 3600

# A changed server certificate is accepted automatically only when the old
# one was about to expire anyway.
CERT_RENEWAL_WINDOW_DAYS: Final = 60

# Usable battery capacity in kWh, used for energy estimates. Adjustable per
# vehicle with the "battery capacity" number entity.
BATTERY_CAPACITY: Final[dict[str, float]] = {
    "T03": 37.3,
    "B05": 67.1,
    "B10": 67.1,
    "C10": 69.9,
    "C11": 78.5,
    "C16": 81.9,
}
BATTERY_CAPACITY_REEV: Final = 28.4

# Where the app certificate is looked up before the user is asked for it.
CERT_DIRECTORIES: Final = ("leapmotor_cloud", "leapmotor")
CERT_FILE_NAMES: Final = ("app_cert.pem", "app.crt", "app_crt.pem", "cert.pem")
KEY_FILE_NAMES: Final = ("app_key.pem", "app.key", "key.pem")

# Sessions of freshly created entries, so that setup does not log in again.
DATA_PENDING_SESSIONS: Final = f"{DOMAIN}_pending_sessions"

FRONTEND_URL: Final = "/leapmotor_cloud_static"
FRONTEND_FILE: Final = "leapmotor-cloud.js"

ISSUE_SERVER_CERT: Final = "server_certificate_changed"
ISSUE_PIN_REJECTED: Final = "pin_rejected"
ISSUE_APP_CERT: Final = "app_certificate_rejected"
ISSUE_SESSION_CONFLICT: Final = "session_conflict"

SERVICE_REFRESH: Final = "refresh"
SERVICE_SET_CLIMATE: Final = "set_climate"
SERVICE_SET_CHARGE_SCHEDULE: Final = "set_charge_schedule"
SERVICE_SET_CLIMATE_SCHEDULE: Final = "set_climate_schedule"
SERVICE_CANCEL_CLIMATE_SCHEDULE: Final = "cancel_climate_schedule"
SERVICE_PREPARE_CAR: Final = "prepare_car"
SERVICE_SEND_DESTINATION: Final = "send_destination"
SERVICE_SEND_COMMAND: Final = "send_command"
