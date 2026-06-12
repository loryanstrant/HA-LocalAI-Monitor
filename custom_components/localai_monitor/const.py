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
ENDPOINT_VERSION = "/version"
# Per-model detail endpoints (used to enrich running models)
ENDPOINT_MODEL_CONFIG = "/api/models/config-json/{name}"  # GET -> full model config (incl. backend)
ENDPOINT_VRAM_ESTIMATE = "/api/models/vram-estimate"  # POST {"model": name} -> VRAM estimate
ENDPOINT_BACKEND_MONITOR = "/backend/monitor"  # GET ?model=name -> live process memory/state (best effort)

# Mapping for the numeric backend state returned by /backend/monitor
BACKEND_STATE_NAMES = {
    0: "uninitialized",
    1: "busy",
    2: "ready",
    -1: "error",
}

# Sensor types
SENSOR_BACKENDS = "backends"
SENSOR_MODELS = "models"
SENSOR_MODELS_JOBS = "models_jobs"
SENSOR_RUNNING_MODELS = "running_models"
SENSOR_SYSTEM = "system"
SENSOR_RESOURCES = "resources"
SENSOR_VERSION = "version"

# Attributes
ATTR_LAST_UPDATE = "last_update"
