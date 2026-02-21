"""Constants for the LocalAI Monitor integration."""

DOMAIN = "localai_monitor"
DEFAULT_NAME = "LocalAI Monitor"

# Config flow
CONF_URL = "url"
CONF_API_KEY = "api_key"
CONF_VERIFY_SSL = "verify_ssl"
CONF_SCAN_INTERVAL = "scan_interval"

# Defaults
DEFAULT_SCAN_INTERVAL = 60  # seconds
DEFAULT_VERIFY_SSL = True

# API Endpoints
ENDPOINT_BACKENDS = "/backends"
ENDPOINT_MODELS = "/v1/models"
ENDPOINT_MODELS_JOBS = "/models/jobs"
ENDPOINT_SYSTEM = "/system"
ENDPOINT_RESOURCES = "/api/resources"

# Sensor types
SENSOR_BACKENDS = "backends"
SENSOR_MODELS = "models"
SENSOR_MODELS_JOBS = "models_jobs"
SENSOR_SYSTEM = "system"
SENSOR_RESOURCES = "resources"

# Attributes
ATTR_LAST_UPDATE = "last_update"
