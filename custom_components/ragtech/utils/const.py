from datetime import timedelta

DOMAIN = "ragtech"

CONF_NAME_KEY = "name"

CONF_SERIAL_PORT_KEY = "serial_port"
CONF_SERIAL_PORT_DEFAULT_VALUE = "/dev/ttyACM0"

CONF_BAUD_RATE_KEY = "baud_rate"
CONF_BAUD_RATE_DEFAULT_VALUE = 2560

CONF_TIMEOUT_KEY = "timeout"
CONF_TIMEOUT_DEFAULT_VALUE = 5

CONF_POLLING_INTERVAL_KEY = "polling_interval"
CONF_POLLING_INTERVAL_DEFAULT_VALUE = 30

# UPS model key. Kept optional; missing entries default to the legacy Easy Pro
# profile so existing installs keep working after upgrade.
CONF_MODEL_KEY = "model"
CONF_MODEL_DEFAULT_VALUE = "easy_pro"

ENTITIES_SCAN_INTERVAL = timedelta(seconds=1)
