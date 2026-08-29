from homeassistant import config_entries
import voluptuous as vol

from .serial.client import probe_ups_model
from .serial.models import UPS_MODELS
from .utils.const import (
    DOMAIN,
    CONF_NAME_KEY,
    CONF_SERIAL_PORT_KEY,
    CONF_SERIAL_PORT_DEFAULT_VALUE,
    CONF_BAUD_RATE_KEY,
    CONF_BAUD_RATE_DEFAULT_VALUE,
    CONF_TIMEOUT_KEY,
    CONF_TIMEOUT_DEFAULT_VALUE,
    CONF_POLLING_INTERVAL_KEY,
    CONF_POLLING_INTERVAL_DEFAULT_VALUE,
    CONF_MODEL_KEY,
    CONF_MODEL_DEFAULT_VALUE,
)


def _model_choices():
    return {key: prof["label"] for key, prof in UPS_MODELS.items()}


class RagtechConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self):
        self._pending: dict | None = None
        self._detection_error: str | None = None

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            self._pending = user_input
            detection = await self.hass.async_add_executor_job(
                probe_ups_model,
                user_input[CONF_SERIAL_PORT_KEY],
                user_input[CONF_BAUD_RATE_KEY],
                user_input[CONF_TIMEOUT_KEY],
            )
            if detection.model:
                return self.async_create_entry(
                    title=user_input[CONF_NAME_KEY],
                    data={**user_input, CONF_MODEL_KEY: detection.model},
                )
            self._detection_error = detection.error or "Unknown detection failure"
            return await self.async_step_pick_model()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME_KEY): str,
                    vol.Required(
                        CONF_SERIAL_PORT_KEY,
                        default=CONF_SERIAL_PORT_DEFAULT_VALUE,
                    ): str,
                    vol.Optional(
                        CONF_BAUD_RATE_KEY,
                        default=CONF_BAUD_RATE_DEFAULT_VALUE,
                    ): int,
                    vol.Optional(
                        CONF_TIMEOUT_KEY,
                        default=CONF_TIMEOUT_DEFAULT_VALUE,
                    ): int,
                    vol.Optional(
                        CONF_POLLING_INTERVAL_KEY,
                        default=CONF_POLLING_INTERVAL_DEFAULT_VALUE,
                    ): int,
                }
            ),
        )

    async def async_step_pick_model(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(
                title=self._pending[CONF_NAME_KEY],
                data={**self._pending, **user_input},
            )
        return self.async_show_form(
            step_id="pick_model",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_MODEL_KEY,
                        default=CONF_MODEL_DEFAULT_VALUE,
                    ): vol.In(_model_choices()),
                }
            ),
            errors={"base": "detect_failed"},
            description_placeholders={"detail": self._detection_error or ""},
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        return RagtechConfigFlowOptionsFlowHandler()


class RagtechConfigFlowOptionsFlowHandler(config_entries.OptionsFlow):
    # HA 2024.12+ makes OptionsFlow.config_entry a read-only property populated
    # by the framework, so assigning to it in __init__ raises AttributeError.
    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_options = self.config_entry.options or {}
        current_data = self.config_entry.data or {}

        def current(key, default):
            return current_options.get(key, current_data.get(key, default))

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SERIAL_PORT_KEY,
                        default=current(
                            CONF_SERIAL_PORT_KEY, CONF_SERIAL_PORT_DEFAULT_VALUE
                        ),
                    ): str,
                    vol.Optional(
                        CONF_BAUD_RATE_KEY,
                        default=current(
                            CONF_BAUD_RATE_KEY, CONF_BAUD_RATE_DEFAULT_VALUE
                        ),
                    ): int,
                    vol.Optional(
                        CONF_TIMEOUT_KEY,
                        default=current(CONF_TIMEOUT_KEY, CONF_TIMEOUT_DEFAULT_VALUE),
                    ): int,
                    vol.Optional(
                        CONF_POLLING_INTERVAL_KEY,
                        default=current(
                            CONF_POLLING_INTERVAL_KEY,
                            CONF_POLLING_INTERVAL_DEFAULT_VALUE,
                        ),
                    ): int,
                    vol.Required(
                        CONF_MODEL_KEY,
                        default=current(CONF_MODEL_KEY, CONF_MODEL_DEFAULT_VALUE),
                    ): vol.In(_model_choices()),
                }
            ),
        )
