"""Constants for cct_virtual_light."""

from logging import Logger, getLogger

import voluptuous as vol

from homeassistant.components.light import (
    ATTR_COLOR_TEMP_KELVIN,
    DOMAIN as LIGHT_DOMAIN,
)
from homeassistant.const import CONF_ENTITY_ID, CONF_NAME
from homeassistant.helpers import selector
import homeassistant.helpers.config_validation as cv

LOGGER: Logger = getLogger(__package__)

NAME = "Color temperature light mixer"
DOMAIN = "color_temperature_light_mixer"


BRIGHTNESS_SENSOR_NAME = "Restored brightness"
TEMPERATURE_SENSOR_NAME = "Restored temperature"

DISPATCHER_SIGNAL_TURN_OFF = f"{DOMAIN}_turn_off"

# Setup types
CONF_SETUP_TYPE = "setup_type"
SETUP_TYPE_DUAL_LIGHT = "dual_light"
SETUP_TYPE_RGBW = "rgbw"

# Dual-light configuration
CONF_WARM_LIGHT = f"warm_light_{CONF_ENTITY_ID}"
CONF_WARM_LIGHT_TEMPERATURE_KELVIN = f"warm_light_{ATTR_COLOR_TEMP_KELVIN}"
CONF_COLD_LIGHT = f"cold_light_{CONF_ENTITY_ID}"
CONF_COLD_LIGHT_TEMPERATURE_KELVIN = f"cold_light_{ATTR_COLOR_TEMP_KELVIN}"

# RGBW controller configuration
CONF_RGBW_CONTROLLER = "rgbw_controller_entity_id"
CONF_WARM_CHANNEL = "warm_channel"
CONF_COLD_CHANNEL = "cold_channel"

# RGBW channel identifiers and their index inside an RGBW tuple (r, g, b, w)
RGBW_CHANNEL_RED = "red"
RGBW_CHANNEL_GREEN = "green"
RGBW_CHANNEL_BLUE = "blue"
RGBW_CHANNEL_WHITE = "white"

RGBW_CHANNEL_MAP: dict[str, int] = {
    RGBW_CHANNEL_RED: 0,
    RGBW_CHANNEL_GREEN: 1,
    RGBW_CHANNEL_BLUE: 2,
    RGBW_CHANNEL_WHITE: 3,
}

CONF_DEFAULT_WARM_LIGHT_TEMPERATURE = 3000
CONF_DEFAULT_COLD_LIGHT_TEMPERATURE = 6000


def is_capitalized(value: str) -> bool:
    """Check if the word is capitalized."""
    return value[0].isupper()


def is_rgbw_config(config: dict) -> bool:
    """Return True if the given config dict represents an RGBW setup.

    Checks the explicit ``setup_type`` key first; falls back to the presence of
    ``CONF_RGBW_CONTROLLER`` for entries created before ``setup_type`` was
    always stamped into the stored data.
    """
    return (
        config.get(CONF_SETUP_TYPE) == SETUP_TYPE_RGBW
        or CONF_RGBW_CONTROLLER in config
    )


# Step 1: choose name and setup type
_SETUP_TYPE_SCHEMA = {
    vol.Required(CONF_NAME): cv.string,
    vol.Required(CONF_SETUP_TYPE, default=SETUP_TYPE_DUAL_LIGHT): selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=[SETUP_TYPE_DUAL_LIGHT, SETUP_TYPE_RGBW],
            mode=selector.SelectSelectorMode.LIST,
            translation_key=CONF_SETUP_TYPE,
        )
    ),
}

# Step 2a: dual-light setup
_DUAL_LIGHT_SCHEMA = {
    vol.Required(CONF_WARM_LIGHT): selector.EntitySelector({"domain": LIGHT_DOMAIN}),
    vol.Required(
        CONF_WARM_LIGHT_TEMPERATURE_KELVIN,
        description={"suggested_value": CONF_DEFAULT_WARM_LIGHT_TEMPERATURE},
    ): cv.positive_int,
    vol.Required(CONF_COLD_LIGHT): selector.EntitySelector({"domain": LIGHT_DOMAIN}),
    vol.Required(
        CONF_COLD_LIGHT_TEMPERATURE_KELVIN,
        description={"suggested_value": CONF_DEFAULT_COLD_LIGHT_TEMPERATURE},
    ): cv.positive_int,
}

# Step 2b: RGBW controller setup
_RGBW_SCHEMA = {
    vol.Required(CONF_RGBW_CONTROLLER): selector.EntitySelector({"domain": LIGHT_DOMAIN}),
    vol.Required(CONF_WARM_CHANNEL, default=RGBW_CHANNEL_WHITE): selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=list(RGBW_CHANNEL_MAP.keys()),
            mode=selector.SelectSelectorMode.LIST,
            translation_key=CONF_WARM_CHANNEL,
        )
    ),
    vol.Required(
        CONF_WARM_LIGHT_TEMPERATURE_KELVIN,
        description={"suggested_value": CONF_DEFAULT_WARM_LIGHT_TEMPERATURE},
    ): cv.positive_int,
    vol.Required(CONF_COLD_CHANNEL, default=RGBW_CHANNEL_BLUE): selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=list(RGBW_CHANNEL_MAP.keys()),
            mode=selector.SelectSelectorMode.LIST,
            translation_key=CONF_COLD_CHANNEL,
        )
    ),
    vol.Required(
        CONF_COLD_LIGHT_TEMPERATURE_KELVIN,
        description={"suggested_value": CONF_DEFAULT_COLD_LIGHT_TEMPERATURE},
    ): cv.positive_int,
}

def _build_dual_light_schema(defaults: dict) -> vol.Schema:
    """Build the dual-light schema pre-populated with the given defaults (for options flow)."""
    return vol.Schema(
        {
            vol.Required(
                CONF_WARM_LIGHT,
                default=defaults.get(CONF_WARM_LIGHT),
            ): selector.EntitySelector({"domain": LIGHT_DOMAIN}),
            vol.Required(
                CONF_WARM_LIGHT_TEMPERATURE_KELVIN,
                default=defaults.get(
                    CONF_WARM_LIGHT_TEMPERATURE_KELVIN,
                    CONF_DEFAULT_WARM_LIGHT_TEMPERATURE,
                ),
            ): cv.positive_int,
            vol.Required(
                CONF_COLD_LIGHT,
                default=defaults.get(CONF_COLD_LIGHT),
            ): selector.EntitySelector({"domain": LIGHT_DOMAIN}),
            vol.Required(
                CONF_COLD_LIGHT_TEMPERATURE_KELVIN,
                default=defaults.get(
                    CONF_COLD_LIGHT_TEMPERATURE_KELVIN,
                    CONF_DEFAULT_COLD_LIGHT_TEMPERATURE,
                ),
            ): cv.positive_int,
        }
    )


def _build_rgbw_schema(defaults: dict) -> vol.Schema:
    """Build the RGBW schema pre-populated with the given defaults (for options flow)."""
    return vol.Schema(
        {
            vol.Required(
                CONF_RGBW_CONTROLLER,
                default=defaults.get(CONF_RGBW_CONTROLLER),
            ): selector.EntitySelector({"domain": LIGHT_DOMAIN}),
            vol.Required(
                CONF_WARM_CHANNEL,
                default=defaults.get(CONF_WARM_CHANNEL, RGBW_CHANNEL_WHITE),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=list(RGBW_CHANNEL_MAP.keys()),
                    mode=selector.SelectSelectorMode.LIST,
                    translation_key=CONF_WARM_CHANNEL,
                )
            ),
            vol.Required(
                CONF_WARM_LIGHT_TEMPERATURE_KELVIN,
                default=defaults.get(
                    CONF_WARM_LIGHT_TEMPERATURE_KELVIN,
                    CONF_DEFAULT_WARM_LIGHT_TEMPERATURE,
                ),
            ): cv.positive_int,
            vol.Required(
                CONF_COLD_CHANNEL,
                default=defaults.get(CONF_COLD_CHANNEL, RGBW_CHANNEL_BLUE),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=list(RGBW_CHANNEL_MAP.keys()),
                    mode=selector.SelectSelectorMode.LIST,
                    translation_key=CONF_COLD_CHANNEL,
                )
            ),
            vol.Required(
                CONF_COLD_LIGHT_TEMPERATURE_KELVIN,
                default=defaults.get(
                    CONF_COLD_LIGHT_TEMPERATURE_KELVIN,
                    CONF_DEFAULT_COLD_LIGHT_TEMPERATURE,
                ),
            ): cv.positive_int,
        }
    )


# Legacy combined schema kept for YAML import compatibility
_DOMAIN_SCHEMA = {
    vol.Required(CONF_NAME): cv.string,
    vol.Required(CONF_WARM_LIGHT): selector.EntitySelector({"domain": LIGHT_DOMAIN}),
    vol.Required(
        CONF_WARM_LIGHT_TEMPERATURE_KELVIN,
        description={"suggested_value": CONF_DEFAULT_WARM_LIGHT_TEMPERATURE},
    ): cv.positive_int,
    vol.Required(CONF_COLD_LIGHT): selector.EntitySelector({"domain": LIGHT_DOMAIN}),
    vol.Required(
        CONF_COLD_LIGHT_TEMPERATURE_KELVIN,
        description={"suggested_value": CONF_DEFAULT_COLD_LIGHT_TEMPERATURE},
    ): cv.positive_int,
}
"""Schema of each CCT virtual light"""
