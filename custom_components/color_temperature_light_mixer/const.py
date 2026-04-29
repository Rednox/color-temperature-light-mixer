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

# Advanced CCT calibration
CONF_CCT_CALIBRATION = "cct_calibration"
CONF_CCT_CAL_TEMP = "temperature_kelvin"
CONF_CCT_CAL_WARM_PCT = "warm_pct"
CONF_CCT_CAL_COLD_PCT = "cold_pct"
CCT_CALIBRATION_POINT_COUNT = 5


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


# ---------------------------------------------------------------------------
# Advanced CCT calibration helpers
# ---------------------------------------------------------------------------

def _cct_field(point_index: int, name: str) -> str:
    """Return the flat form field name for calibration point ``point_index`` (1-based)."""
    return f"cct_cal_{point_index}_{name}"


def default_calibration_points(warm_k: int, cold_k: int) -> list[dict]:
    """Return 5 calibration points that reproduce the linear mired interpolation.

    The returned list spans from *warm_k* (100 % warm, 0 % cold) to *cold_k*
    (0 % warm, 100 % cold) in equal mired steps.  Using these defaults leaves
    the mixing behaviour completely unchanged compared to the built-in formula.
    """
    warm_mired = 1_000_000 / warm_k
    cold_mired = 1_000_000 / cold_k
    points: list[dict] = []
    for i in range(CCT_CALIBRATION_POINT_COUNT):
        frac = i / (CCT_CALIBRATION_POINT_COUNT - 1)
        mired = warm_mired + frac * (cold_mired - warm_mired)
        kelvin = round(1_000_000 / mired)
        warm_pct = round((1.0 - frac) * 100)
        cold_pct = round(frac * 100)
        points.append(
            {
                CONF_CCT_CAL_TEMP: kelvin,
                CONF_CCT_CAL_WARM_PCT: warm_pct,
                CONF_CCT_CAL_COLD_PCT: cold_pct,
            }
        )
    return points


def calibration_to_flat(calibration: list[dict]) -> dict:
    """Convert a stored calibration list to flat form-field key/value pairs."""
    result: dict = {}
    for i, point in enumerate(calibration, 1):
        result[_cct_field(i, "temp")] = point[CONF_CCT_CAL_TEMP]
        result[_cct_field(i, "warm")] = point[CONF_CCT_CAL_WARM_PCT]
        result[_cct_field(i, "cold")] = point[CONF_CCT_CAL_COLD_PCT]
    return result


def flat_to_calibration(form_data: dict) -> list[dict]:
    """Convert flat form-field data back to the stored calibration list.

    Points are sorted by ascending temperature so that interpolation is
    straightforward regardless of the order in which the user entered them.
    """
    points: list[dict] = []
    for i in range(1, CCT_CALIBRATION_POINT_COUNT + 1):
        temp = int(form_data.get(_cct_field(i, "temp"), 0))
        warm = max(0, min(100, int(form_data.get(_cct_field(i, "warm"), 0))))
        cold = max(0, min(100, int(form_data.get(_cct_field(i, "cold"), 0))))
        points.append(
            {
                CONF_CCT_CAL_TEMP: temp,
                CONF_CCT_CAL_WARM_PCT: warm,
                CONF_CCT_CAL_COLD_PCT: cold,
            }
        )
    return sorted(points, key=lambda p: p[CONF_CCT_CAL_TEMP])


def _build_cct_calibration_schema(defaults: dict) -> vol.Schema:
    """Build the CCT calibration schema pre-populated with *defaults*."""
    fields: dict = {}
    for i in range(1, CCT_CALIBRATION_POINT_COUNT + 1):
        fields[
            vol.Required(
                _cct_field(i, "temp"),
                default=defaults.get(_cct_field(i, "temp"), 2700),
            )
        ] = selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=1000,
                max=10000,
                step=50,
                mode=selector.NumberSelectorMode.BOX,
                unit_of_measurement="K",
            )
        )
        fields[
            vol.Required(
                _cct_field(i, "warm"),
                default=defaults.get(_cct_field(i, "warm"), 50),
            )
        ] = selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0,
                max=100,
                step=1,
                mode=selector.NumberSelectorMode.SLIDER,
                unit_of_measurement="%",
            )
        )
        fields[
            vol.Required(
                _cct_field(i, "cold"),
                default=defaults.get(_cct_field(i, "cold"), 50),
            )
        ] = selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0,
                max=100,
                step=1,
                mode=selector.NumberSelectorMode.SLIDER,
                unit_of_measurement="%",
            )
        )
    return vol.Schema(fields)
