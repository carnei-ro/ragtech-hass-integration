from homeassistant import config_entries
import voluptuous as vol

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
)


class RagtechConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(
                title=user_input[CONF_NAME_KEY],
                data=user_input,
            )

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

    @staticmethod
    def async_get_options_flow(config_entry):
        return RagtechConfigFlowOptionsFlowHandler(config_entry)


class RagtechConfigFlowOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

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
                }
            ),
        )
